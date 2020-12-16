import re
import linecache
import pickle
import nltk
from nltk.stem.porter import PorterStemmer
import numpy as np
from typing import List, Set, Dict, Tuple, NewType
from operator import itemgetter
from nltk.corpus import stopwords

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
    nltk.download("stopwords")

    with open(stopwords_file_name, 'r') as f:
        read_stopwords = f.read().splitlines()
    stopwords_set = set(read_stopwords)
    stopwords_set.update(stopwords.words("english"))
    return stopwords_set

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
Index = NewType('Index', Dict[str, Dict[int, Dict[int, int]]])
def read_corpora_and_create_index(corpora_file_names:List[str], preprocessor:SimplePreprocessor) -> Tuple[Index, Dict[int, int]]:
    """Reads input trec file and creates a positional inverted index from it, and it also creates a set containing all document IDs.

    Args:
        input_file_name (str): input trec file name.
        preprocessor (SimplePreprocessor): initialized SimplePreprocessor.
    """
    index = dict()
    corpora_nr_docs = dict()

    for corpus_id, corpora_file_name in enumerate(corpora_file_names):
        corpora_nr_docs[corpus_id] = 0
        with open(corpora_file_name, 'r') as f:
            # Extract documents of the corpus.
            corpus = f.read()
            documents = re.split(r"\n\n", corpus)
            del corpus
            for (doc_id, doc) in enumerate(documents):
                if len(doc) == 0:
                    continue
                doc_tokens = preprocessor.process_text_lines(doc.split("\n"))
                corpora_nr_docs[corpus_id] += 1
                for token in doc_tokens:
                    if token in index:
                        if corpus_id in index[token]:
                            if doc_id in index[token][corpus_id]:
                                index[token][corpus_id][doc_id] += 1
                            else:
                                index[token][corpus_id][doc_id] = 1
                        else:
                            index[token][corpus_id] = dict()
                            index[token][corpus_id][doc_id] = 1
                    else:
                        index[token] = dict()
                        index[token][corpus_id] = dict()
                        index[token][corpus_id][doc_id] = 1
                    
                    
        print("Index construction for corpus " + str(corpus_id+1) + " finished.")

    return index, corpora_nr_docs

def calculate_freq_term(index:Index, term:str) -> int:
    if term not in index:
        return 0
    
    frequency = 0
    for corpus_id in index[term]:
        for doc_id in index[term][corpus_id]:
            frequency += index[term][corpus_id][doc_id]
    return frequency


def remove_low_freq_words_from_index(corpora_index:Index, threshold_freq:int) -> Index:
    new_index = dict()

    for term in corpora_index:
        freq = calculate_freq_term(corpora_index, term)
        if freq >= threshold_freq:
            new_index[term] = corpora_index[term]
    return new_index

def calculate_nr_docs_per_corpus(index:Index, corpora_ids:List[int]) -> Dict[int, int]:
    corpora_docs = dict()
    for corpus_id in corpora_ids:
        corpora_docs[corpus_id] = set()
    
    for term in index:
        for corpus_id in index[term]:
            corpora_docs[corpus_id].update(index[term][corpus_id].keys())

    corpora_nr_docs = dict()
    for corpus_id in corpora_ids:
        corpora_nr_docs[corpus_id] = len(corpora_docs[corpus_id])
    
    return corpora_nr_docs
    

def compute_MI_score_term_corpus(N:int, N_00:int, N_01:int, N_10:int, N_11:int) -> float:
    N_1x = N_10 + N_11 # 0 iff no corpus contains the term (impossible)
    N_x1 = N_01 + N_11 # 0 iff the corpus doesn't contain any documents (may be possible with a cheater corpus)
    N_0x = N_01 + N_00 # 0 iff ALL documents contain term t (may be possible if you miss a stop word or you tokenize incorrectly -- need to check for assignment imo)
    N_x0 = N_10 + N_00 # 0 N_10 = 0 iff no other documents (from other corpora) contain the term. N_00 = 0 iff every document (from other corpora) contain the term.
    # N_x0 can be 0 iff we have a single corpus.

    if N_10 * N_01 * N_10 * N_11 == 0:
        return 0 # 0 * log(0) = 0 convention as on Piazza

    MI_score = ((N_11/N) * np.log2((N * N_11)/(N_1x * N_x1)) + 
                (N_01/N) * np.log2((N * N_01)/(N_0x * N_x1)) +
                (N_10/N) * np.log2((N * N_10)/(N_1x * N_x0)) + 
                (N_00/N) * np.log2((N * N_00)/(N_0x * N_x0)))
    return MI_score

def compute_chi_score_term_corpus(N:int, N_00:int, N_01:int, N_10:int, N_11:int) -> float:
    chi_score_numerator = (N_11 + N_10 + N_01 + N_00) * (N_11 * N_00 - N_10 * N_01) ** 2
    # Same warning as above. Term in all documents, in no document, or one-corpus dataset.
    chi_score_denominator = (N_11 + N_01) * (N_11 + N_10) * (N_10 + N_00) * (N_01 + N_00)
    chi_score = chi_score_numerator/chi_score_denominator
    
    return chi_score

def compute_MI_chi_scores(index:Index, corpora_nr_docs:Dict[int, int], corpora_ids:List[int]) -> Tuple[Dict[int, List[Tuple[str, int]]], Dict[int, List[Tuple[str, int]]]]:
    MI_scores = dict()
    chi_scores = dict()

    for corpus_id in corpora_ids:
        MI_scores[corpus_id] = []
        chi_scores[corpus_id] = []
    
    N = 0
    for corpus_id in corpora_nr_docs:
        N += corpora_nr_docs[corpus_id]
    
    nr_docs_which_contain_term = dict()
    for term in index:
        N_1x = 0
        for corpus_id in index[term]:
            N_1x += len(index[term][corpus_id])
        nr_docs_which_contain_term[term] = N_1x
    
    for term in index:
        for corpus_id in corpora_ids:
            N_11 = 0
            if corpus_id not in index[term]:
                N_01 = corpora_nr_docs[corpus_id]
            else:
                for _ in index[term][corpus_id]:
                    N_11 += 1
                N_01 = corpora_nr_docs[corpus_id] - N_11
            N_10 = nr_docs_which_contain_term[term] - N_11
            N_00 = N - nr_docs_which_contain_term[term] - N_01

            MI_scores[corpus_id].append((term, compute_MI_score_term_corpus(N, N_00, N_01, N_10, N_11)))
            chi_scores[corpus_id].append((term, compute_chi_score_term_corpus(N, N_00, N_01, N_10, N_11)))
    
    for corpus_id in MI_scores:
        MI_scores[corpus_id] = sorted(MI_scores[corpus_id], key=itemgetter(1), reverse=True)
        chi_scores[corpus_id] = sorted(chi_scores[corpus_id], key=itemgetter(1), reverse=True)
    return MI_scores, chi_scores


# -------------------------------I/O-------------------------------
def save_corpora_index(index:Index, file_name:str):
    with open(file_name, 'wb') as f:
        pickle.dump(index, f)

def load_corpora_index(file_name:str) -> Index:
    with open(file_name, 'rb') as f:
        index = pickle.load(f)
    return index

corpora_file_names = ["corpus1.txt", "corpus2.txt"]
stopwords_file_name = "englishST.txt"
index_output_file_name = "index.txt"

stopwords_set = construct_stopwords_set(stopwords_file_name)
tokenizer = SimpleTokenizer('[a-zA-Z]+')
stemmer = PorterStemmer()
pre_processor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)


# Create pos inverted index and the set of document IDs.
# corpora_index, corpora_nr_docs = read_corpora_and_create_index(corpora_file_names, pre_processor)
# corpora_index = remove_low_freq_words_from_index(corpora_index, 10)
# save_corpora_index(corpora_index, "corpora_index.pkl")

# Warning: must take into account the fact that some documents may disappear.

# corpora_index = load_corpora_index("corpora_index.pkl")


# corpora_ids = [0, 1]
# print(corpora_nr_docs)

# MI_scores, chi_scores = compute_MI_chi_scores(corpora_index, corpora_nr_docs, corpora_ids)
# print("Corpus 1 MI:")
# print(MI_scores[0][:10])
# print("Corpus 1 chi: ")
# print(chi_scores[0][:10])


from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
def get_corpus_topics(corpus_file_name:str, preprocessor:SimplePreprocessor):
    with open(corpus_file_name, 'r') as f:
        # Extract documents of the corpus.
        corpus = f.read()
        clean_docs = []
        documents = re.split(r"\n\n", corpus)
        for doc in documents:
            clean_doc = preprocessor.process_text_lines(doc.split("\n"))
            if len(clean_doc) > 0:
                clean_docs.append(clean_doc)
    
    del documents
    dictionary = Dictionary(clean_docs)
    corpus = [dictionary.doc2bow(text) for text in clean_docs]
    lda = LdaModel(corpus, num_topics=10, id2word=dictionary)
    
    total_prob = []
    for ii in range(10):
        total_prob.append([ii, 0])

    nr_docs = len(clean_docs)
    for doc in clean_docs:
        doc_topics = lda.get_document_topics(dictionary.doc2bow(doc), 0)
        for (topic_id, topic_prob) in doc_topics:
            total_prob[topic_id][1] += topic_prob
    
    for ii in range(10):
        total_prob[ii][1] /= nr_docs
    
    total_prob = sorted(total_prob, key=itemgetter(1), reverse=True)
    
    for (top_topic, probability) in total_prob[:3]:
        print(str(top_topic) + " " + str(probability))
        print(lda.print_topic(top_topic, 10))

get_corpus_topics("corpus1.txt", pre_processor)