import re
import linecache
import xml.etree.ElementTree as ElementTree
import pickle
from nltk.stem.porter import PorterStemmer
import numpy as np
from typing import List, Set, Dict, Tuple, TypeVar

class SimpleTokenizer():
    def __init__(self, pattern:str):
        """Initialise the regular expression which will be used to tokenize our expression.

        Args:
            pattern (str): pattern to be used.
        """
        self.regexp = re.compile(pattern, re.MULTILINE | re.DOTALL)
    
    def tokenize_text_lines(self, text_lines:List[str]) -> List[str]:
        """Accepts a list of strings. Tokenizes each string and creates a list of the tokens.

        Args:
            text_lines (List[str]): List of strings.

        Returns:
            List[str]: List of tokens produced from the input strings.
        """
        tokens = []
        for line in text_lines:
            tokens += self.regexp.findall(line)
        return tokens

def construct_stopwords_set(stopwords_file_name:str) -> Set[str]:
    """Reads stopwords from stopwords_file_name and saves them in a set.

    Args:
        stopwords_file_name (str): Stop words file.

    Returns:
        Set[str]: [description]
    """
    with open(stopwords_file_name, 'r') as f:
        stopwords = f.read().splitlines()
    return set(stopwords)

class SimplePreprocessor():
    """Class for pre-processing text. Given a list of strings, it tokenizes them, removes stop words, lowercases and stems them.
    """
    def __init__(self, tokenizer:SimpleTokenizer, stop_words_set:Set[str], stemmer:PorterStemmer):
        self.tokenizer = tokenizer
        self.stop_words_set = stop_words_set
        self.stemmer = stemmer
    
    @staticmethod
    def lowercase_word(word:str) -> str:
        return str.lower(word)
    
    def remove_stop_words_lowercase_and_stem(self, tokens:List[str]) -> List[str]:
        final_tokens = []
        for token in tokens:
            lowercase_token = SimplePreprocessor.lowercase_word(token)
            if lowercase_token not in self.stop_words_set:
                stemmed_token = self.stemmer.stem(lowercase_token)
                final_tokens.append(stemmed_token)
        return final_tokens
    
    def process_text_lines(self, text_lines:List[str]) -> List[str]:
        tokens = self.tokenizer.tokenize_text_lines(text_lines)
        tokens = self.remove_stop_words_lowercase_and_stem(tokens)
        return tokens

# ----------------------------------CREATE INDEX AND DOCID SET----------------------------------
PosInvertedIndex = TypeVar('PosInvertedIndex', Dict[str, Dict[int, List[int]]])
def read_input_trec_file_and_create_index_and_docId_set(input_file_name:str, preprocessor:SimplePreprocessor) -> Tuple[PosInvertedIndex, Set[int]]:
    """Reads input trec file and creates a positional inverted index from it, and it also creates a set containing all document IDs.

    Args:
        input_file_name (str): input trec file name.
        preprocessor (SimplePreprocessor): initialized SimplePreprocessor.

    Returns:
        Tuple[PosInvertedIndex, Set[int]]: [description]
    """
    pos_inverted_index = dict()
    docId_set = set()

    # Read trec xml file.
    with open(input_file_name, 'r') as f:
        xml_trec_file = f.read()
    xml = ElementTree.fromstring(xml_trec_file)

    # For each document, pre-process the headline and body and add the term occurences to the positional inverted index.
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
    
    # This might be useless as indices are added in-order -> TODO: check.
    for term in pos_inverted_index:
        for docId in pos_inverted_index[term]:
            pos_inverted_index[term][docId].sort()
    
    return pos_inverted_index, docId_set

#------------------------SEARCH functions-----------------------------------------
def answer_simple_search(term:str, pos_inverted_index:PosInvertedIndex) -> Set[int]:
    """Finds the documents that contain the term and returns their docIDs.

    Args:
        term (str): term to search.
        pos_inverted_index (PosInvertedIndex): pos. inverted index.

    Returns:
        Set[int]: docs which contain the term.
    """
    if term not in pos_inverted_index:
        return set()
    
    term_docIDs = set(pos_inverted_index[term].keys())
    return term_docIDs


def answer_phrase_search(term1:str, term2:str, pos_inverted_index:PosInvertedIndex) -> Set[int]:
    """Search for the documents which contain the phrase "term1 term2".
    """
    if term1 not in pos_inverted_index or term2 not in pos_inverted_index:
        return set()
    
    # Retrieve documents which contain both terms.
    term1_docIDs = set(pos_inverted_index[term1].keys())
    term2_docIDs = set(pos_inverted_index[term2].keys())
    common_docIDs = term1_docIDs.intersection(term2_docIDs)

    # If no docs were found, return an empty set.
    if len(common_docIDs) == 0:
        return set()
    
    # Search for an occurence of "term1 term2" in every common document.
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

def answer_proximity_search(term1:str, term2:str, distance:int, pos_inverted_index:PosInvertedIndex) -> Set[int]:
    """Search for documents which answer the query #distance(term1, term2).
    Implementation is analogous to "answer_phrase_search".
    """
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
def parse_and_answer_boolean_term(term:str, docIDs:Set[int], pos_inverted_index:PosInvertedIndex, pre_processor:SimplePreprocessor) -> Set[int]:
    """Parses the term obtained from "parse_and_answer_boolean_query". The term can be a simple term, a negation of a simple term or a phrase query.
    Returns the documents which contain the terms.

    Returns:
        Set[int]: Documents which contain the term.
    """
    not_term = False
    result_set = set()

    if term[:4] == "NOT ":
        not_term = True
        term = term[4:]
    
    # If the term contains a " -> it is a phrase query. Parse it accordingly and return the documents containing it.
    if "\"" in term:
        term1_re = re.compile("\"(.+) ")
        term2_re = re.compile(" (.+)\"")

        term1 = term1_re.search(term).group(1)
        term1 = pre_processor.remove_stop_words_lowercase_and_stem([term1])[0]

        term2 = term2_re.search(term).group(1)
        term2 = pre_processor.remove_stop_words_lowercase_and_stem([term2])[0]

        result_set = answer_phrase_search(term1, term2, pos_inverted_index)
    # Otherwise, it is a simple search.
    else:
        term = pre_processor.remove_stop_words_lowercase_and_stem([term])[0]
        result_set = answer_simple_search(term, pos_inverted_index)
    
    # If the term was negated, return the documents which do not contain it.
    if not_term:
        result_set = docIDs.difference(result_set)
    
    return result_set


def parse_and_answer_boolean_query(query:str, docIDs:Set[int], pos_inverted_index:PosInvertedIndex, pre_processor:SimplePreprocessor) -> Set[int]:
    """Returns the documents which answer the input query.

    Args:
        query (str): input boolean query.
        docIDs (Set[int]): set of all document ids.
        pos_inverted_index (PosInvertedIndex): pos inverted index.
        pre_processor (SimplePreprocessor): the same SimplePreprocessor which was used to pre-process the text used to 
        create the positional inverted index.

    Returns:
        Set[int]: Documents which answer the query.
    """
    result_set = set()

    # If the query contains "#" -> it is a proximity query. Parse it and answer it.
    if "#" in query:
        distance_re = re.compile("#([0-9]+)\(")
        term1_re = re.compile("\(([a-zA-Z0-9]+),")
        term2_re = re.compile(", ?([a-zA-Z0-9]+)\)")

        distance = distance_re.search(query).group(1)
        distance = int(distance)

        term1 = term1_re.search(query).group(1)
        term1 = pre_processor.remove_stop_words_lowercase_and_stem([term1])[0]

        term2 = term2_re.search(query).group(1)
        term2 = pre_processor.remove_stop_words_lowercase_and_stem([term2])[0]

        result_set = answer_proximity_search(term1, term2, distance, pos_inverted_index)
    
    else:
        # If the query contains and, the query will be term1 AND term2.
        # Retrieve the documents which contain both terms.
        if " AND " in query:
            term1_re = re.compile("(.+) AND ")
            term2_re = re.compile(" AND (.+)")

            term1 = term1_re.search(query).group(1)
            term2 = term2_re.search(query).group(1)

            results_q1 = parse_and_answer_boolean_term(term1, docIDs, pos_inverted_index, pre_processor)
            results_q2 = parse_and_answer_boolean_term(term2, docIDs, pos_inverted_index, pre_processor)
            result_set = results_q1.intersection(results_q2)
            
        # If the query contains or, the query will be term1 OR term2.
        # Retrieve the documents which contain either term.
        elif " OR " in query:
            term1_re = re.compile("(.+) OR ")
            term2_re = re.compile(" OR (.+)")

            term1 = term1_re.search(query).group(1)
            term2 = term2_re.search(query).group(1)

            results_q1 = parse_and_answer_boolean_term(term1, docIDs, pos_inverted_index, pre_processor)
            results_q2 = parse_and_answer_boolean_term(term2, docIDs, pos_inverted_index, pre_processor)
            result_set = results_q1.union(results_q2)
        
        # If the query is not a proximity query and does not contain AND or OR, then it is comprised of a single "term".
        # This "term" is either a proper term or a phrase query (or a negation of either of those).
        else:
            result_set = parse_and_answer_boolean_term(query, docIDs, pos_inverted_index, pre_processor)
    
    return result_set

def tf_idf(tf_term:int, df_term:int, N:int) -> float:
    """Calculate tf_idf.

    Args:
        tf_term (int): Term frequency.
        df_term (int): Document frequency.
        N (int): Number of documents.
    """
    tf_idf_weight = (1+np.log10(tf_term)) * np.log10(N/df_term)
    return tf_idf_weight

def parse_and_answer_ranked_query(query:str, N:int, pos_inverted_index:PosInvertedIndex, pre_processor:SimplePreprocessor, tokenizer:SimpleTokenizer) -> List[Tuple[int, float]]:
    """Analogous to "parse_and_answer_boolean_query".

    Args:
        query (str): string containing the ranked query.
        N (int): number of unique documents in the collection.
        pos_inverted_index (PosInvertedIndex): pos inverted index constructed from the collection.
        pre_processor (SimplePreprocessor): pre-processor used to extract terms from the collection.
        tokenizer (SimpleTokenizer): tokenizer used to create the pos inverted index.

    Returns:
        A list of (docID, score), docID = document id, score = the relevance score of the document relative to the query.
    """
    # Extract terms from the query.
    tokens = tokenizer.tokenize_text_lines([query])
    terms = pre_processor.remove_stop_words_lowercase_and_stem(tokens)
    
    # Select all documents which contain at least one of the query terms.
    docIDs = set()
    for term in terms:
        if term in pos_inverted_index:
            docIDs.update(set(pos_inverted_index[term].keys()))

    doc_scores = []
    for docID in docIDs:
        # Compute the score for document docID.
        tfidf_score = 0
        for term in terms:

            # Is our term in the collection?
            if term not in pos_inverted_index:
                continue
            
            # Is our term in document docID?
            if docID not in pos_inverted_index[term]:
                continue
            
            # Number of times the term appeared in document docID.
            tf_term = len(pos_inverted_index[term][docID])

            # Number of documents the term appeared in.
            df_term = len(pos_inverted_index[term].keys())

            # Compute the tf-idf score of document docID.
            tfidf_score += tf_idf(tf_term, df_term, N)
        
        # Add the document and its scores to the list.
        doc_scores.append((docID, tfidf_score))
    
    return doc_scores

# -------------------------------I/O-------------------------------
def save_pos_inverted_index(pos_inverted_index:PosInvertedIndex, file_name:str):
    with open(file_name, 'wb') as f:
        pickle.dump(pos_inverted_index, f)

def pretty_print_pos_inverted_index(pos_inverted_index:PosInvertedIndex, file_name:str):
    """ This method produces the file "index.txt", by saving the positional inverted index in the required format.

    Args:
        pos_inverted_index (PosInvertedIndex): pos. inverted index to save
        file_name (str): file name, "index.txt" in our case
    """
    terms = list(pos_inverted_index.keys())
    terms.sort()

    tab = '\t'
    
    with open(file_name, 'w') as f:
        for term in terms:
            docIDs = list(pos_inverted_index[term].keys())
            docIDs.sort()
            
            f.write(term + ':' + str(len(docIDs)) + '\n')
            for docID in docIDs:
                line = ''
                line += tab
                line += str(docID) + ': '
                for position in pos_inverted_index[term][docID]:
                    line += str(position) + ', '
                line = line[:-2]
                line += '\n'
                f.write(line)
    
    return True

def load_pos_inverted_index(file_name:str) -> PosInvertedIndex:
    with open(file_name, 'rb') as f:
        pos_inverted_index = pickle.load(f)
    return pos_inverted_index

def read_queries(file_name:str) -> Dict[int, str]:
    """Read queries from the specified file (+ strip the number of the query).
    """
    queries = dict()

    with open(file_name, 'r') as f:
        raw_queries = f.readlines()
    
    for query in raw_queries:
        query = query.strip('\n')
        
        space_idx = query.find(" ")
        
        query_nr = int(query[:space_idx])
        query = query[space_idx+1:]
        queries[query_nr] = query
    
    return queries

def execute_and_write_ranked_queries(ranked_queries:Dict[int, str], docIDs:Set[str], pos_inverted_index:PosInvertedIndex, file_name:str, pre_processor:SimplePreprocessor, tokenizer:SimpleTokenizer, query_answer_limit:int):
    with open(file_name, 'w') as f:
        for query_id in ranked_queries:
            query_answers = parse_and_answer_ranked_query(ranked_queries[query_id], len(docIDs), pos_inverted_index, pre_processor, tokenizer)
            
            if len(query_answers) == 0:
                continue
            
            # Sort documents in descending order of their tf-idf score.
            query_answers.sort(key=lambda x: x[1], reverse=True)

            for query_answer in query_answers[:query_answer_limit]:
                f.write(str(query_id) + ", " + str(query_answer[0]) + ", " + str(round(query_answer[1], 4)) + "\n")


def execute_and_write_boolean_queries(boolean_queries:Dict[int, str], docIDs:Set[str], pos_inverted_index:PosInvertedIndex, file_name:str, pre_processor:SimplePreprocessor):
    with open(file_name, 'w') as f:
        for query_id in boolean_queries:
            query_answers = parse_and_answer_boolean_query(boolean_queries[query_id], docIDs, pos_inverted_index, pre_processor)
            query_answers = list(query_answers)
            query_answers.sort()

            for doc_nr in query_answers:
                line = str(query_id) + ", " + str(doc_nr) + "\n"
                f.write(line)

# Hardcoded assignment variables:
stopwords_file_name = "englishST.txt"
boolean_queries_file_name = "queries.boolean.txt"
ranked_queries_file_name = "queries.ranked.txt"
input_trec_file_name = "trec.sample.xml"

index_output_file_name = "index.txt"
boolean_queries_output_file_name = "results.boolean.txt"
ranked_queries_output_file_name = "results.ranked.txt"

# Read the stop words set, initialise the preprocessor, tokenizer and stemmer.
stopwords_set = construct_stopwords_set(stopwords_file_name)
tokenizer = SimpleTokenizer('[a-zA-Z0-9]+')
stemmer = PorterStemmer()
pre_processor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)

# Create pos inverted index and the set of document IDs.
pos_inverted_index, docId_set = read_input_trec_file_and_create_index_and_docId_set(input_trec_file_name, pre_processor)

# Pickle pos inverted index and also create "index.txt".
save_pos_inverted_index(pos_inverted_index, 'pos_inverted_index.pkl')
pretty_print_pos_inverted_index(pos_inverted_index, index_output_file_name)

# Read boolean queries, execute them and write the results.
boolean_queries = read_queries(boolean_queries_file_name)
execute_and_write_boolean_queries(boolean_queries, docId_set, pos_inverted_index, boolean_queries_output_file_name, pre_processor)

# Read ranked queries, execute them and write the results.
query_answer_limit = 150
ranked_queries = read_queries(ranked_queries_file_name)
execute_and_write_ranked_queries(ranked_queries, docId_set, pos_inverted_index, ranked_queries_output_file_name, pre_processor, tokenizer, query_answer_limit)