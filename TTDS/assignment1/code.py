import re
import linecache
import xml.etree.ElementTree as ElementTree
import pickle
from nltk.stem.porter import PorterStemmer

class SimplePreprocessor():
    def __init__(self, tokenizer, stop_words_set, stemmer):
        self.tokenizer = tokenizer
        self.stop_words_set = stop_words_set
        self.stemmer = stemmer
    
    @staticmethod
    def lowercase_word(word):
        return str.lower(word)
    
    def remove_stop_words_lowercase_and_stem(self, tokens):
        final_tokens = []
        for token in tokens:
            lowercase_token = SimplePreprocessor.lowercase_word(token)
            if lowercase_token not in self.stop_words_set:
                stemmed_token = self.stemmer.stem(lowercase_token)
                final_tokens.append(stemmed_token)
        return final_tokens
    
    def process_text_lines(self, text_lines):
        tokens = self.tokenizer.tokenize_text_lines(text_lines)
        tokens = self.remove_stop_words_lowercase_and_stem(tokens)
        return tokens

class SimpleTokenizer():
    def __init__(self, pattern):
        self.regexp = re.compile(pattern, re.MULTILINE | re.DOTALL)
    
    def tokenize_text_lines(self, text_lines):
        tokens = []
        for line in text_lines:
            tokens += self.regexp.findall(line)
        return tokens

def construct_stopwords_set(stopwords_file_name):
    with open(stopwords_file_name, 'r') as f:
        stopwords = f.read().splitlines()
    return set(stopwords)

# ----------------------------------CREATE INDEX AND DOCID SET----------------------------------
def read_input_trec_file_and_create_index_and_docId_set(input_file_name, preprocessor):
    pos_inverted_index = dict()
    docId_set = set()

    with open(input_file_name, 'r') as f:
        xml_trec_file = f.read()
    xml = ElementTree.fromstring(xml_trec_file)
    for doc in xml:
        docId = int(doc.find('DOCNO').text.strip())
        docHeadline = doc.find('HEADLINE').text.strip()
        docText = doc.find('TEXT').text.strip()

        docId_set.add(docId)
        
        text = [docHeadline, docText]
        tokens = preprocessor.process_text_lines(text)

        for index, token in enumerate(tokens):
            if token in pos_inverted_index:
                if docId in pos_inverted_index[token]:
                    pos_inverted_index[token][docId].append(index)
                else:
                    pos_inverted_index[token][docId] = [index]
            else:
                pos_inverted_index[token] = dict()
                pos_inverted_index[token][docId] = [index]
    
    for term in pos_inverted_index:
        for docId in pos_inverted_index[term]:
            pos_inverted_index[term][docId].sort()
    
    return pos_inverted_index, docId_set

#------------------------SEARCH functions-----------------------------------------
def answer_simple_search(term, pos_inverted_index):
    if term not in pos_inverted_index:
        return set()
    
    term_docIDs = set(pos_inverted_index[term].keys())
    return term_docIDs


def answer_phrase_search(term1, term2, pos_inverted_index):
    if term1 not in pos_inverted_index or term2 not in pos_inverted_index:
        return set()
    
    term1_docIDs = set(pos_inverted_index[term1].keys())
    term2_docIDs = set(pos_inverted_index[term2].keys())
    common_docIDs = term1_docIDs.intersection(term2_docIDs)

    if len(common_docIDs) == 0:
        return set()
    
    result_set = set()
    for docID in common_docIDs:
        term1_indices = pos_inverted_index[term1][docID]
        term2_indices = pos_inverted_index[term2][docID]

        term2_indices = set(term2_indices)
        for index in term1_indices:
            if (index+1) in term2_indices:
                result_set.add(docID)
                break
    
    return result_set

def answer_proximity_search(term1, term2, distance, pos_inverted_index):
    if term1 not in pos_inverted_index or term2 not in pos_inverted_index:
        return set()

    term1_docIDs = set(pos_inverted_index[term1].keys())
    term2_docIDs = set(pos_inverted_index[term2].keys())
    common_docIDs = term1_docIDs.intersection(term2_docIDs)

    if len(common_docIDs) == 0:
        return set()
    
    result_set = set()
    for docID in common_docIDs:
        term1_indices = pos_inverted_index[term1][docID]
        term2_indices = pos_inverted_index[term2][docID]

        list_idx1, list_idx2 = 0, 0
        len1, len2 = len(term1_indices), len(term2_indices)

        close = lambda i1, i2, dist: -dist <= i1-i2 and i1-i2 <= dist

        while list_idx1 <= len1-1 and list_idx2 <= len2-1:
            if close(term1_indices[list_idx1], term2_indices[list_idx2], distance):
                result_set.add(docID)
                break
            else:
                if term1_indices[list_idx1] < term2_indices[list_idx2]:
                    if list_idx1 == len1-1:
                        break
                    else:
                        list_idx1 += 1
                else:
                    if list_idx2 == len2-1:
                        break
                    else:
                        list_idx2 += 1
    
    return result_set

# -------------------------BOOL_query_parser + answer-er----------------
def parse_and_answer_boolean_term(term, docIDs, pos_inverted_index, pre_processor):
    not_term = False
    result_set = set()

    if term[:4] == "NOT ":
        not_term = True
        term = term[4:]
    
    if "\"" in term:
        term1_re = re.compile("\".+ ")
        term2_re = re.compile(" .+\"")

        term1 = term1_re.search(term).group(0)
        term1 = term1[1:-1]
        term1 = pre_processor.remove_stop_words_lowercase_and_stem([term1])[0]

        term2 = term2_re.search(term).group(0)
        term2 = term2[1:-1]
        term2 = pre_processor.remove_stop_words_lowercase_and_stem([term2])[0]

        result_set = answer_phrase_search(term1, term2, pos_inverted_index)
    
    else:
        term = pre_processor.remove_stop_words_lowercase_and_stem([term])[0]
        result_set = answer_simple_search(term, pos_inverted_index)
    
    if not_term:
        result_set = docIDs.difference(result_set)
    
    return result_set


def parse_and_answer_boolean_query(query, docIDs, pos_inverted_index, pre_processor):
    result_set = set()

    if "#" in query:
        distance_re = re.compile("#.+\(")
        term1_re = re.compile("\(.+,")
        term2_re = re.compile(" .+\)")

        distance = distance_re.search(query).group(0)
        distance = int(distance[1:-1])

        term1 = term1_re.search(query).group(0)
        term1 = term1[1:-1]
        term1 = pre_processor.remove_stop_words_lowercase_and_stem([term1])[0]

        term2 = term2_re.search(query).group(0)
        term2 = term2[1:-1]
        term2 = pre_processor.remove_stop_words_lowercase_and_stem([term2])[0]

        result_set = answer_proximity_search(term1, term2, distance, pos_inverted_index)
    
    else:
        if " AND " in query:
            term1_re = re.compile(".+ AND ")
            term2_re = re.compile(" AND .+")

            term1 = term1_re.search(query).group(0)
            term1 = term1[:-5]

            term2 = term2_re.search(query).group(0)
            term2 = term2[5:]

            results_q1 = parse_and_answer_boolean_term(term1, docIDs, pos_inverted_index, pre_processor)
            results_q2 = parse_and_answer_boolean_term(term2, docIDs, pos_inverted_index, pre_processor)
            result_set = results_q1.intersection(results_q2)
            
        
        elif " OR " in query:
            term1_re = re.compile(".+ OR ")
            term2_re = re.compile(" OR .+")

            term1 = term1_re.search(query).group(0)
            term1 = term1[:-4]

            term2 = term2_re.search(query).group(0)
            term2 = term2[4:]

            results_q1 = parse_and_answer_boolean_term(term1, docIDs, pos_inverted_index, pre_processor)
            results_q2 = parse_and_answer_boolean_term(term2, docIDs, pos_inverted_index, pre_processor)
            result_set = results_q1.union(results_q2)
        
        else:
            result_set = parse_and_answer_boolean_term(query, docIDs, pos_inverted_index, pre_processor)
    
    return result_set

# -------------------------------I/O-------------------------------
def save_pos_inverted_index(pos_inverted_index, file_name):
    with open(file_name, 'wb') as f:
        pickle.dump(pos_inverted_index, f)

def pretty_print_pos_inverted_index(pos_inverted_index, file_name):
    terms = list(pos_inverted_index.keys())
    terms.sort()

    space = '   '
    
    with open(file_name, 'w') as f:
        for term in terms:
            docIDs = list(pos_inverted_index[term].keys())
            docIDs.sort()
            
            f.write(term + ':' + str(len(docIDs)) + '\n')
            for docID in docIDs:
                line = ''
                line += space
                line += str(docID) + ': '
                for position in pos_inverted_index[term][docID]:
                    line += str(position) + ', '
                line = line[:-2]
                line += '\n'
                f.write(line)
    
    return True

def load_pos_inverted_index(file_name):
    with open(file_name, 'rb') as f:
        pos_inverted_index = pickle.load(f)
    return pos_inverted_index

def read_boolean_queries(file_name):
    boolean_queries = dict()

    with open(file_name, 'r') as f:
        queries1 = f.readlines()
    
    for query in queries1:
        query = query.strip('\n')
        
        space_idx = query.find(" ")
        
        query_nr = int(query[:space_idx])
        query = query[space_idx+1:]
        boolean_queries[query_nr] = query
    
    return boolean_queries

def execute_and_write_boolean_queries(boolean_queries, docIDs, pos_inverted_index, file_name, pre_processor):
    with open(file_name, 'w') as f:
        for query_id in boolean_queries:

            query_answers = parse_and_answer_boolean_query(boolean_queries[query_id], docIDs, pos_inverted_index, pre_processor)
            query_answers = list(query_answers)
            query_answers.sort()

            for doc_nr in query_answers:
                line = str(query_id) + ", " + str(doc_nr) + "\n"
                f.write(line)

# Assignment variables:
stopwords_file_name = "englishST.txt"
boolean_queries_file_name = "queries.boolean.txt"
ranked_queries_file_name = "queries.ranked.txt"
input_trec_file_name = "trec.sample.xml"

index_output_file_name = "index.txt"
boolean_queries_output_file_name = "results.boolean.txt"
ranked_queries_output_file_name = "results.ranked.txt"


stopwords_set = construct_stopwords_set(stopwords_file_name)
tokenizer = SimpleTokenizer('[a-zA-Z]+')
stemmer = PorterStemmer()
pre_processor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)

# pos_inverted_index, docId_set = read_input_trec_file_and_create_index_and_docId_set(input_trec_file_name, pre_processor)
pos_inverted_index = load_pos_inverted_index("pos_inverted_index.pkl")
docId_set = set(range(1, 3948))

save_pos_inverted_index(pos_inverted_index, 'pos_inverted_index.pkl')
pretty_print_pos_inverted_index(pos_inverted_index, 'index.txt')

boolean_queries = read_boolean_queries(boolean_queries_file_name)
execute_and_write_boolean_queries(boolean_queries, docId_set, pos_inverted_index, boolean_queries_output_file_name, pre_processor)
# queries = parse_and_answer_boolean_query("Scotland", docId_set, pos_inverted_index, pre_processor)
# print(queries)