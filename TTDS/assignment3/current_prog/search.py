import re
import math
from typing import List, Tuple
from tokenizers import RegexpTokenizer
from itertools import product
from sqlitedict import SqliteDict
from preprocessors import Preprocessor, SimplePreprocessor
from nltk.stem.snowball import SnowballStemmer

# Usage:
#
# >>> from search import Search
# >>> search = Search()
# >>> search.simple_query('"nice day" AND today')
# {3468}
# >>> search.ranked_query('nice day today', 3)
# [(3010, 8.43), (3325, 8.2136), (4511, 8.1993)]

class Search():
    def __init__(self, 
                 index_file:str = './index.sqlite', 
                 preprocessor:Preprocessor = SimplePreprocessor(RegexpTokenizer('(?i)[0-9a-zÀ-ÿ]+'), 
                                                                'englishST.txt', 
                                                                SnowballStemmer('english'))):
        self.index = SqliteDict(index_file)
        self.all_ids = self.get_all_document_ids()
        self.preprocessor = preprocessor
        
    def get_all_document_ids(self) -> set:
        ids = set()
        for key in self.index.keys():
            if self.index[key] == None:
                raise Exception('Index contains a key (%s) with no associated document IDs. Aborting.' % key)
            ids.update(self.index[key])
        return ids
    
    def parse_boolop(self, query:str) -> set:
        sep = re.split(r' (AND|OR)( NOT)? ', query) 
        lhs = sep[0]
        boolop = sep[1]
        neg = sep[2]
        rhs = sep[3]
        lhs = self.simple_query(lhs)
        rhs = self.simple_query(rhs)
        if neg == ' NOT':
            rhs = self.all_ids - rhs
        if boolop == 'AND':
            return lhs & rhs 
        elif boolop == 'OR':
            return lhs | rhs
        return set()
    
    def parse_neg(self, query:str) -> set:
        sep = query.split('NOT')
        rhs = self.simple_query(sep[1])
        return self.all_ids - rhs
    
    def parse_prox(self, query:str) -> set:
        sep = re.split(r'#(\d+)\(([a-zA-Z]+), ?([a-zA-Z]+)\)', query)[1:-1]
        n = int(sep[0])
        term1 = sep[1]
        term2 = sep[2]
        return self.common_prox_phr(n, term1, term2, False)
    
    def common_prox_phr(self, n:int, term1:str, term2:str, phr:bool) -> set:
        common_docs = self.simple_query(term1) & self.simple_query(term2)
        term1 = self.preprocessor.process_text_lines([term1])[0]
        term2 = self.preprocessor.process_text_lines([term2])[0]
        matching_docs = set()
        for doc in common_docs:
            comparison_pairs = list(product(self.index[term1][doc], self.index[term2][doc]))
            comparison_function = lambda n, a, b: (b-a)==1 if phr else abs(b-a)<=n
            if any(comparison_function(n, a, b) for (a,b) in comparison_pairs):
                matching_docs.add(doc)
        return matching_docs
    
    def parse_phr(self, query:str) -> set:
        sep = re.split(r'"([a-zA-Z]+) ([a-zA-Z]+)"', query)[1:-1]  
        term1 = sep[0]
        term2 = sep[1]
        return self.common_prox_phr(None, term1, term2, True)
    
    def simple_query(self, query:str) -> set:
        if not query:
            return set()
        if ' AND ' in query or ' OR ' in query:
            return self.parse_boolop(query)
        elif query.startswith('NOT '):
            return self.parse_neg(query)
        elif query[0] == '#':
            return self.parse_prox(query)
        elif query[0] == '"':
            return self.parse_phr(query)
        else:
            terms = self.preprocessor.process_text_lines([query])
            if len(terms) > 0:
                return set(self.index[terms[0]].keys())
            return set()
        
    def ranked_query(self, query:str, n_results:int) -> List[Tuple[int, float]]:
        query = self.preprocessor.process_text_lines([query])
        relevant = set()
        scores = []
        for term in query:
            relevant = relevant | self.index[term].keys()
        for doc in relevant:
            score = 0
            for term in query:
                if doc in self.index[term]:
                    tf_t_d = len(self.index[term][doc])
                    N = len(self.all_ids)
                    df_t = len(self.index[term])
                    lhs = 1 + math.log(tf_t_d, 10)            
                    rhs = math.log(N / df_t, 10)
                    w_t_d = lhs * rhs
                    score += w_t_d
            scores.append((doc, score))
        scores = [(doc, round(score,4)) for (doc, score) in scores]
        return sorted(sorted(scores, key=lambda i: int(i[0])), key=lambda i: i[1], reverse=True)[:n_results]