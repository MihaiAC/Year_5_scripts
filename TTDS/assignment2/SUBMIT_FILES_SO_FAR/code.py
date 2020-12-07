import pandas as pd
import numpy as np
from functools import partial
from typing import Tuple, List
from scipy.stats import ttest_1samp
import re
import pickle
from nltk.stem.porter import PorterStemmer
from typing import List, Set, Dict, Tuple, NewType, Optional
from operator import itemgetter
from nltk.corpus import stopwords
import csv
from gensim.models.ldamodel import LdaModel
from gensim.corpora.dictionary import Dictionary
from scipy.sparse import dok_matrix
from sklearn.model_selection import ShuffleSplit
from sklearn.svm import SVC
import seaborn as sns

def filter_on_kwargs(data:pd.DataFrame, **kwargs) -> pd.DataFrame:
    construct_query = []
    for key, item in kwargs.items():
        construct_query.append(key + " == " + str(item))
    construct_query = ' & '.join(construct_query)
    return data.query(construct_query)

def get_number_of_unique_rows(data:pd.DataFrame, col_name:str) -> int:
    return len(set(data[col_name]))

def get_row_number(system_nr:int, query_nr:int, nr_queries:int) -> int:
    ii = system_nr - 1
    jj = query_nr - 1
    return ii * nr_queries + jj

def create_result_df(nr_systems:int, nr_queries:int) -> pd.DataFrame:
    col_names = ['system_number', 'query_number', 'P@10', 'R@50', 'r-precision', 'AP', 'nDCG@10', 'nDCG@20']
    result_df = pd.DataFrame(np.zeros((nr_systems * nr_queries, len(col_names))), columns=col_names)
    result_df['system_number'] = pd.to_numeric(result_df['system_number'], downcast='integer')
    result_df['query_number'] = pd.to_numeric(result_df['query_number'], downcast='integer')
    
    for ii in range(nr_systems):
        for jj in range(nr_queries):
            row_nr = get_row_number(ii+1, jj+1, nr_queries)
            result_df.at[row_nr, 'system_number'] = ii+1
            result_df.at[row_nr, 'query_number'] = jj+1
    return result_df

def calculate_precision_at_10(sys_results:pd.DataFrame, qrels:pd.DataFrame, system_number:int, 
                             query_number:int) -> float:
    retrieved_docs = list(filter_on_kwargs(sys_results, system_number=system_number, 
                                           query_number=query_number)['doc_number'])
    relevant_docs = set(filter_on_kwargs(qrels, query_id=query_number)['doc_id'])
    
    TP = 0
    for doc in retrieved_docs[:10]:
        if doc in relevant_docs:
            TP += 1
    return TP/10

def calculate_all_precision_at_10(sys_results:pd.DataFrame, qrels:pd.DataFrame, nr_systems:int, 
                                 nr_queries:int, result_df:pd.DataFrame):
    for ii in range(1, nr_systems+1):
        for jj in range(1, nr_queries+1):
            precision = calculate_precision_at_10(sys_results, qrels, ii, jj)
            result_df.at[get_row_number(ii, jj, nr_queries), 'P@10'] = precision

def calculate_recall_at_50(sys_results:pd.DataFrame, qrels:pd.DataFrame, system_number:int, 
                             query_number:int) -> float:
    retrieved_docs = list(filter_on_kwargs(sys_results, system_number=system_number, 
                                           query_number=query_number)['doc_number'])
    relevant_docs = set(filter_on_kwargs(qrels, query_id=query_number)['doc_id'])
    
    TP = 0
    for doc in retrieved_docs[:50]:
        if doc in relevant_docs:
            TP += 1

    FN = len(relevant_docs.difference(set(retrieved_docs[:50])))
    return TP/(TP + FN)

def calculate_all_recall_at_50(sys_results:pd.DataFrame, qrels:pd.DataFrame, nr_systems:int, 
                                 nr_queries:int, result_df:pd.DataFrame):
    for ii in range(1, nr_systems+1):
        for jj in range(1, nr_queries+1):
            recall = calculate_recall_at_50(sys_results, qrels, ii, jj)
            result_df.at[get_row_number(ii, jj, nr_queries), 'R@50'] = recall

def calculate_R_precision(sys_results:pd.DataFrame, qrels:pd.DataFrame, system_number:int, 
                          query_number:int) -> float:
    retrieved_docs = list(filter_on_kwargs(sys_results, system_number=system_number, 
                                           query_number=query_number)['doc_number'])
    relevant_docs = set(filter_on_kwargs(qrels, query_id=query_number)['doc_id'])
    R = len(relevant_docs)
    
    TP = 0
    for doc in retrieved_docs[:R]:
        if doc in relevant_docs:
            TP += 1
    return TP/R

def calculate_all_R_precision(sys_results:pd.DataFrame, qrels:pd.DataFrame, nr_systems:int, 
                              nr_queries:int, result_df:pd.DataFrame):
    for ii in range(1, nr_systems+1):
        for jj in range(1, nr_queries+1):
            R_precision = calculate_R_precision(sys_results, qrels, ii, jj)
            result_df.at[get_row_number(ii, jj, nr_queries), 'r-precision'] = R_precision

def calculate_AP(sys_results:pd.DataFrame, qrels:pd.DataFrame, system_number:int, 
                 query_number:int) -> float:
    retrieved_docs = list(filter_on_kwargs(sys_results, system_number=system_number, 
                                           query_number=query_number)['doc_number'])
    relevant_docs = set(filter_on_kwargs(qrels, query_id=query_number)['doc_id'])
    
    R = len(relevant_docs)
    
    AP = 0
    TP = 0
    for ii, doc in enumerate(retrieved_docs):
        if doc in relevant_docs:
            TP += 1
            AP += TP/(ii+1)
    AP = AP/R
    return AP

def calculate_all_AP(sys_results:pd.DataFrame, qrels:pd.DataFrame, nr_systems:int, 
                              nr_queries:int, result_df:pd.DataFrame):
    for ii in range(1, nr_systems+1):
        for jj in range(1, nr_queries+1):
            AP = calculate_AP(sys_results, qrels, ii, jj)
            result_df.at[get_row_number(ii, jj, nr_queries), 'AP'] = AP

def calculate_nDCG(sys_results:pd.DataFrame, qrels:pd.DataFrame, system_number:int, 
                   query_number:int) -> float:
    retrieved_docs = list(filter_on_kwargs(sys_results, system_number=system_number, 
                                           query_number=query_number)['doc_number'])
    qrels_subset = filter_on_kwargs(qrels, query_id=query_number)
    
    relevant_doc_ids = list(qrels_subset['doc_id'])
    relevant_doc_relevance = list(qrels_subset['relevance'])
    relevant_dict = dict()
    for ii, doc_id in enumerate(relevant_doc_ids):
        relevant_dict[doc_id] = relevant_doc_relevance[ii]
    
    nDCG_10 = 0
    nDCG_20 = 0
    DCG_10 = 0
    DCG_20 = 0
    iDCG_k = 0
    sorted_doc_relevance = sorted(relevant_doc_relevance, reverse=True)
    for ii, doc in enumerate(retrieved_docs[:20]):
        if doc in relevant_dict:
            if ii == 0:
                DCG_10 += relevant_dict[doc]
                DCG_20 += relevant_dict[doc]
            elif ii < 10:
                DCG_10 += relevant_dict[doc] / np.log2(ii+1)
                DCG_20 += relevant_dict[doc] / np.log2(ii+1)
            else:
                DCG_20 += relevant_dict[doc] / np.log2(ii+1)
            
        if ii == 0:
            iDCG_k += sorted_doc_relevance[ii]
        elif ii < len(sorted_doc_relevance):
            iDCG_k += sorted_doc_relevance[ii] / np.log2(ii+1)
            
        if ii == 9:
            nDCG_10 = DCG_10 / iDCG_k
            
        if ii == 19:
            nDCG_20 = DCG_20 / iDCG_k
    return nDCG_10, nDCG_20

def calculate_all_nDCG(sys_results:pd.DataFrame, qrels:pd.DataFrame, nr_systems:int, 
                       nr_queries:int, result_df:pd.DataFrame):
    for ii in range(1, nr_systems+1):
        for jj in range(1, nr_queries+1):
            nDCG_10, nDCG_20 = calculate_nDCG(sys_results, qrels, ii, jj)
            result_df.at[get_row_number(ii, jj, nr_queries), 'nDCG@10'] = nDCG_10
            result_df.at[get_row_number(ii, jj, nr_queries), 'nDCG@20'] = nDCG_20

def print_result_df(result_df:pd.DataFrame, nr_systems:int, nr_queries:int, file_name:str='ir_eval.csv'):
    score_means = np.zeros((nr_systems, 6))
    with open(file_name, 'w') as f:
        f.write(','.join(result_df.columns)+'\n')
        for ii in range(nr_systems):
            for jj in range(nr_queries):
                row_nr = get_row_number(ii+1, jj+1, nr_queries)
                row = result_df.loc[row_nr, :]
                line = str(int(row[0])) + ',' + str(int(row[1])) + ','
                
                rest_of_line = ','.join(map(str, [round(x, 3) for x in row[2:]]))
                line += rest_of_line + '\n'
                f.write(line)
            line = str(ii+1) + "," + "mean" + ","
            row_nr = get_row_number(ii+1, 1, nr_queries)
            relevant_stats = np.array(result_df.iloc[row_nr:row_nr+nr_queries, 2:])
            
            means = np.mean(relevant_stats, axis=0)
            score_means[ii, :] = means
            
            rest_of_line = ','.join(map(str, [round(x, 3) for x in means]))
            line += rest_of_line + '\n'
            f.write(line)
    return score_means

def p_values(result_df:pd.DataFrame, score_means:np.ndarray, nr_queries:int, col_names:List[str]):
    nr_systems = score_means.shape[0]
    for ii, stat in enumerate(col_names):
        # For the current stat, need to select the top 2 means.
        means = score_means[:, ii]
        
        sorted_idx = np.argsort(means)
        first_idx = sorted_idx[-1]
        second_idx = sorted_idx[-2]
        last = -2
        
        first_scores = np.array(result_df[stat][nr_queries*first_idx : nr_queries*first_idx + nr_queries])
        second_scores = np.array(result_df[stat][nr_queries*second_idx : nr_queries*second_idx + nr_queries])
        diff = first_scores - second_scores
        
        while np.std(diff) == 0 and last >= -nr_systems:
            last -= 1
            print("System : " + str(second_idx+1) + " has identical performance with the first system.")
            second_idx = sorted_idx[last]
            second_scores = np.array(result_df[stat][nr_queries*second_idx : nr_queries*second_idx + nr_queries])
            diff = first_scores - second_scores
        
        t_value, p_value = ttest_1samp(diff, 0)
        
        print('For statistic ' + stat + ': best = ' + str(first_idx+1) + '; 2nd best = ' + 
             str(second_idx+1) + '; P-value: ' + str(p_value) + '; T-value: ' + str(t_value))
        
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
    
    def tokenize_list_of_strings(self, string_list:List[str]) -> List[List[str]]:
        list_of_tokens = []
        for string in string_list:
            list_of_tokens.append(self.regexp.findall(string))
        return list_of_tokens

def construct_stopwords_set(stopwords_file_name:str) -> Set[str]:
    """Reads stopwords from stopwords_file_name and saves them in a set.

    Args:
        stopwords_file_name (str): Stop words file.

    Returns:
        Set[str]: [description]
    """
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

def pickle_object(obj:object, file_name:str):
    with open(file_name, 'wb') as f:
        pickle.dump(obj, f)

def unpickle_object(file_name:str) -> object:
    with open(file_name, 'rb') as f:
        obj = pickle.load(f)
    return obj

# Read the tsv file + extract the 3 corpora.
# Assumption: 3 corpora Quran, OT, NT.
def read_tsv_extract_corpora(tsv_file_name:str, corpus_names_to_int:Dict[str, int]) -> Dict[int, List[str]]:
    corpora = dict()
    for value in corpus_names_to_int.values():
        corpora[value] = []
    with open(tsv_file_name, mode='r', newline='\n') as f:
        read_tsv = csv.reader(f, delimiter="\t")
        for row in read_tsv:
            corpus_name = row[0]
            corpus_id = corpus_names_to_int[corpus_name]
            corpora[corpus_id].append(row[1])
    return corpora

def preprocess_corpora(corpora:Dict[int, List[str]], preprocessor:SimplePreprocessor) -> Dict[int, List[List[str]]]:
    preprocessed_corpora = dict()
    for key in corpora.keys():
        preprocessed_corpora[key] = []
        for document in corpora[key]:
            document_terms = preprocessor.process_text_lines([document])
            preprocessed_corpora[key].append(document_terms)
    return preprocessed_corpora

# ----------------------------------CREATE INDEX AND DOCID SET----------------------------------
Index = NewType('Index', Dict[str, Dict[int, Dict[int, int]]])
def read_corpora_and_create_index(corpora:Dict[int, List[List[str]]]) -> Tuple[Index, Dict[int, int]]:
    """Reads input trec file and creates a positional inverted index from it, and it also creates a set containing all document IDs.

    Args:
        input_file_name (str): input trec file name.
        preprocessor (SimplePreprocessor): initialized SimplePreprocessor.
    """
    index = dict()
    corpora_nr_docs = dict()
    
    for corpus_id in corpora.keys():
        corpora_nr_docs[corpus_id] = 0
        for (doc_id, doc_tokens) in enumerate(corpora[corpus_id]):
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
    

def compute_MI_score_term_corpus(N:int, N_00:int, N_01:int, N_10:int, N_11:int) -> float:
    N_1x = N_10 + N_11 # 0 iff no corpus contains the term (impossible)
    N_x1 = N_01 + N_11 # 0 iff the corpus doesn't contain any documents (may be possible with a cheater corpus)
    N_0x = N_01 + N_00 # 0 iff ALL documents contain term t (may be possible if you miss a stop word or you tokenize incorrectly -- need to check for assignment imo)
    N_x0 = N_10 + N_00 # 0 N_10 = 0 iff no other documents (from other corpora) contain the term. N_00 = 0 iff every document (from other corpora) contain the term.
    # N_x0 can be 0 iff we have a single corpus.
    
    # 0 * log(0) = 0 by convention.
    MI_score = 0
    if N_10 != 0:
        MI_score += (N_10/N) * np.log2((N * N_10)/(N_1x * N_x0))
    
    if N_01 != 0:
        MI_score += (N_01/N) * np.log2((N * N_01)/(N_0x * N_x1))
    
    if N_11 != 0:
        MI_score += (N_11/N) * np.log2((N * N_11)/(N_1x * N_x1))
    
    if N_00 != 0:
        MI_score += (N_00/N) * np.log2((N * N_00)/(N_0x * N_x0))
        
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

def print_top_k_terms_for_each_corpus(MI_scores, chi_scores, int_to_corpus_names, k):
    for corpus_id in MI_scores.keys():
        corpus_name = int_to_corpus_names[corpus_id]
        # print('Top ' + str(k) + ' terms in ' + corpus_name + ' by MI score: ')
        # print(MI_scores[corpus_id][:k])
        # print('Top ' + str(k) + ' terms in ' + corpus_name + ' by Chi-squared score: ')
        # print(chi_scores[corpus_id][:k])
        
        file_name = corpus_name + '_' + 'MI.csv'
        file_content = "term,mi\n"
        for (term, MI_score) in MI_scores[corpus_id][:k]:
            file_content += term + ',' + str(round(MI_score, 5)) + '\n'
        with open(file_name, 'w') as f:
            f.write(file_content)
        
        file_name = corpus_name + '_' + 'chi.csv'
        file_content = "term,chisq\n"
        for (term, chi_score) in chi_scores[corpus_id][:k]:
            file_content += term + ',' + str(round(chi_score, 3)) + '\n'
        with open(file_name, 'w') as f:
            f.write(file_content)
            
def write_topic_words_to_file(topic_words:List[Tuple[str, float]], corpus_id:int):
    file_name = "topic_words_corpus_" + str(corpus_id) + ".csv"
    content = "Term,Score\n"
    for term, score in topic_words:
        content += term + "," + str(round(score, 3)) + '\n'
    with open(file_name, 'w') as f:
        f.write(content)

def run_topics_task(corpora:Dict[int, List[List[str]]], corpora_nr_docs:Dict[int, int], num_topics=20):
    clean_docs = []
    for corpus_id in corpora:
        clean_docs += corpora[corpus_id]
    
    dictionary = Dictionary(clean_docs)
    dictionary.filter_extremes(no_below=15, no_above=0.6)
    corpus = [dictionary.doc2bow(text) for text in clean_docs]
    lda = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=25)
    
    corpora_topics_scores = dict()
    for corpus_id in corpora:
        corpora_topics_scores[corpus_id] = dict()
        for ii in range(num_topics):
            corpora_topics_scores[corpus_id][ii] = 0
    
    # Sum topic probs for each corpus.
    for corpus_id in corpora:
        for doc in corpora[corpus_id]:
            doc_topics = lda.get_document_topics(dictionary.doc2bow(doc), 0)
            for (topic_id, topic_prob) in doc_topics:
                corpora_topics_scores[corpus_id][topic_id] += topic_prob
    
    # Normalise topic probs.
    for corpus_id in corpora:
        corpus_nr_docs = corpora_nr_docs[corpus_id]
        for topic_id in range(num_topics):
            corpora_topics_scores[corpus_id][topic_id] /= corpus_nr_docs
    
    # Select top topic for each corpus.
    corpora_top_topic = dict()
    for corpus_id in corpora:
        top_topic = -1
        top_score = 0
        for topic_id in range(num_topics):
            topic_score = corpora_topics_scores[corpus_id][topic_id]
            if topic_score > top_score:
                top_topic = topic_id
                top_score = topic_score
        corpora_top_topic[corpus_id] = top_topic
    
    for corpus_id in corpora:
        top_topic = corpora_top_topic[corpus_id]
        print('Top topic for corpus: ' + str(corpus_id) + " is topic nr " + str(top_topic))
        print(lda.print_topic(top_topic, 10))
        topic_words = lda.show_topic(top_topic, 10)
        write_topic_words_to_file(topic_words, corpus_id)
    
    print('\n')
    for ii in range(num_topics):
        print('Topic ' + str(ii) + ': ' + str(round(corpora_topics_scores[0][ii], 3)) + ' ' + 
              str(round(corpora_topics_scores[1][ii], 3)) + ' ' + 
              str(round(corpora_topics_scores[2][ii], 3)))
    
    print('\n')
    for ii in range(num_topics):
        print('Topic ' + str(ii) + ' words: ')
        print(lda.print_topic(ii, 10))
    
    return lda

class NoStemmer():
    def __init__(self):
        pass
    
    def stem(self, token:str) -> str:
        return token

class BOW():
    def __init__(self):
        self.token_to_id = dict()
        self.id_to_token = dict()
    
    @property
    def nr_tokens(self) -> int:
        return len(self.token_to_id)
    
    @property
    def oov_token(self) -> int:
        return len(self.token_to_id)
    
    def transform_tokenized_sent(self, tokenized_sent:List[str]) -> List[int]:
        output = []
        for token in tokenized_sent:
            if token not in self.token_to_id:
                # print('OOV Token detected') # debug stmt
                output.append(self.oov_token)
            else:
                output.append(self.token_to_id[token])
        return output
    
    def add_transform_tokenized_sents(self, tokenized_sents:List[List[str]]) -> List[List[int]]:
        output = []
        for sent in tokenized_sents:
            self.add_list_of_tokens(sent)
            output.append(self.transform_tokenized_sent(sent))
        return output
    
    def transform_tokenized_sents(self, tokenized_sents:List[List[str]]) -> List[List[int]]:
        output = []
        for sent in tokenized_sents:
            output.append(self.transform_tokenized_sent(sent))
        return output
    
    def reverse_transform_sent(self, id_sent:List[int]) -> List[str]:
        output = []
        for token_id in id_sent:
            if token_id not in self.id_to_token:
                output.append("OOV_term")
            else:
                output.append(self.id_to_token[token_id])
        return output
    
    def reverse_transform_sents(self, id_sents:List[List[int]]) -> List[List[str]]:
        output = []
        for sent in id_sents:
            output.append(self.reverse_transform_sent(sent))
        return output
        
    def add_token(self, token:str):
        if token not in self.token_to_id:
            nr_tokens = len(self.token_to_id)
            self.token_to_id[token] = nr_tokens
            self.id_to_token[nr_tokens] = token
    
    def add_list_of_tokens(self, tokens:List[str]):
        for token in tokens:
            self.add_token(token)
            
    def get_token_id(self, token:str) -> int:
        if token not in self.token_to_id:
            print("Token " + token + " not in the BOW")
            return -1
        else:
            return self.token_to_id[token]
    
    def get_token_from_id(self, token_id:int) -> str:
        if token_id not in self.id_to_token:
            print("Token id " + str(token_id) + " is not in the BOW.")
            return ""
        else:
            return self.id_to_token[token_id]

def tokenize_corpora(corpora:Dict[int, List[str]], tokenizer:SimpleTokenizer) -> Dict[int, List[List[str]]]:
    tokenized_corpora = dict()
    for key in corpora.keys():
        tokenized_corpora[key] = []
        for document in corpora[key]:
            document_terms = tokenizer.tokenize_text_lines([document])
            tokenized_corpora[key].append(document_terms)
    return tokenized_corpora

def docs_to_bow_sents(docs:List[List[str]], ref_bow:Optional[BOW]=None) -> Tuple[List[List[int]], BOW]:
    if ref_bow is None:
        bow = BOW()
        bow_sents = bow.add_transform_tokenized_sents(docs)
        return bow_sents, bow 
    else:
        bow_sents = ref_bow.transform_tokenized_sents(docs)
        return bow_sents, None

def bow_sents_to_dok(bow_sents:List[List[int]], bow:BOW) -> dok_matrix:
    nr_tokens = bow.nr_tokens + 1 # extra token for oov words.
    dok = dok_matrix((len(bow_sents), nr_tokens), dtype='int')
    for sent_number, sent in enumerate(bow_sents):
        for token_id in sent:
            dok[sent_number, token_id] += 1
    return dok

def split_train_dev_improved(train_dev_corpora:Dict[int, List[List[str]]], corpus_ids:Set[int], percentage_dev:Optional[float]=0.1) -> Tuple[List[List[str]], List[int], List[List[str]], List[int]]:
    train_set = []
    train_labels = []
    dev_set = []
    dev_labels = []
    splitter = ShuffleSplit(1, test_size=percentage_dev, random_state=0)
    for corpus_id in corpus_ids:
        corpus_docs = train_dev_corpora[corpus_id]
        train_indices, dev_indices = list(splitter.split(corpus_docs))[0]
        
        set_train_idx = set(train_indices)
        for dev_index in dev_indices:
            if dev_index in set_train_idx:
                print('WRONG YO')
            
        
        for train_index in train_indices:
            train_set.append(corpus_docs[train_index])
            train_labels.append(corpus_id)
        
        for dev_index in dev_indices:
            dev_set.append(corpus_docs[dev_index])
            dev_labels.append(corpus_id)
    
    return train_set, train_labels, dev_set, dev_labels

def split_train_dev_baseline(train_dev_corpora:Dict[int, List[List[str]]], corpus_ids:Set[int], 
                    percentage_dev:Optional[float]=0.1) -> Tuple[List[List[str]], List[int], List[List[str]], List[int]]:
    all_docs = []
    all_labels = []
    train_set = []
    train_labels = []
    dev_set = []
    dev_labels = []
    splitter = ShuffleSplit(1, test_size=percentage_dev, random_state=0)
    for corpus_id in corpus_ids:
        all_docs += train_dev_corpora[corpus_id]
        all_labels += [corpus_id] * len(train_dev_corpora[corpus_id])
        
    train_indices, dev_indices = list(splitter.split(all_docs))[0]

    for train_index in train_indices:
        train_set.append(all_docs[train_index])
        train_labels.append(all_labels[train_index])
        
    for dev_index in dev_indices:
        dev_set.append(all_docs[dev_index])
        dev_labels.append(all_labels[dev_index])
    
    return train_set, train_labels, dev_set, dev_labels

def split_test(test_corpora:Dict[int, List[List[str]]], corpus_ids:Set[int]) -> Tuple[List[List[str]], List[int]]:
    test_docs = []
    test_labels = []
    for corpus_id in corpus_ids:
        for test_doc in test_corpora[corpus_id]:
            test_docs.append(test_doc)
            test_labels.append(corpus_id)
    return test_docs, test_labels

def compute_prf_scores(true_labels, pred_labels, value):
    TP = 0
    FN = 0
    FP = 0
    for idx in range(len(true_labels)):
        true = true_labels[idx]
        pred = pred_labels[idx]
        if true == value and pred == value:
            TP += 1
        elif true == value and pred != value:
            FN += 1
        elif true != value and pred == value:
            FP += 1
    if TP + FP == 0 or TP + FN == 0:
        return 0, 0, 0
    precision = TP / (TP + FP)
    recall = TP / (TP + FN)
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1

def create_row(true:List[int], pred:List[int], system:str, split:str) -> str:
    list_row = [system, split]
    p_q, r_q, f_q = compute_prf_scores(true, pred, 0)
    p_ot, r_ot, f_ot = compute_prf_scores(true, pred, 1)
    p_nt, r_nt, f_nt = compute_prf_scores(true, pred, 2)
    p_macro = (p_q + p_ot + p_nt)/3
    r_macro = (r_q + r_ot + r_nt)/3
    f_macro = (f_q + f_ot + f_nt)/3
    values = [p_q, r_q, f_q, p_ot, r_ot, f_ot, p_nt, r_nt, f_nt, p_macro, r_macro, f_macro]
    round_3 = partial(round, ndigits=3)
    values = map(round_3, values)
    values = map(str, values)
    list_row += values
    row = ','.join(list_row)
    row += '\n'
    return row
    
def create_classification_output_file(output_file_name, 
                                      baseline_train_true, baseline_train_pred, 
                                      baseline_dev_true, baseline_dev_pred,
                                      baseline_test_true, baseline_test_pred, 
                                      improved_train_true, improved_train_pred,
                                      improved_dev_true, improved_dev_pred,
                                      improved_test_true, improved_test_pred
                                     ):
    dictionary = dict()
    keys_1 = ['baseline', 'improved']
    keys_2 = ['train', 'dev', 'test']
    dictionary['baseline'] = dict()
    dictionary['improved'] = dict()
    dictionary['baseline']['train'] = (baseline_train_true, baseline_train_pred)
    dictionary['baseline']['dev'] = (baseline_dev_true, baseline_dev_pred)
    dictionary['baseline']['test'] = (baseline_test_true, baseline_test_pred)
    dictionary['improved']['train'] = (improved_train_true, improved_train_pred)
    dictionary['improved']['dev'] = (improved_dev_true, improved_dev_pred)
    dictionary['improved']['test'] = (improved_test_true, improved_test_pred)
    # Current assumption: Quran:0, OT:1, NT:2.
    with open(output_file_name, "w") as f:
        f.write('system,split,p-quran,r-quran,f-quran,p-ot,r-ot,f-ot,p-nt,r-nt,f-nt,p-macro,r-macro,f-macro\n')
        for system in keys_1:
            for split in keys_2:
                true, pred = dictionary[system][split]
                row = create_row(true, pred, system, split)
                f.write(row)     

def get_misclassified_docs(bow_sents:List[List[int]], bow:BOW, true:List[int], pred:List[int]):
    for idx in range(len(true)):
        if true[idx] != pred[idx]:
            sent = bow_sents[idx]
            print(str(true[idx]) + ' ' + str(pred[idx]) + ' ' + 
                  " ".join(bow.reverse_transform_sent(sent)))
            
def plot_confusion_matrix(bow_sents:List[List[int]], bow:BOW, true:List[int], pred:List[int]):
    cm = np.zeros((3,3))
    for idx in range(len(true)):
        ii = true[idx]
        jj = pred[idx]
        cm[ii, jj] += 1
    sns.heatmap(cm, annot=True)


# Code for task 1.
# qrels = pd.read_csv('./qrels.csv')
# sys_results = pd.read_csv('./system_results.csv')
# nr_queries = get_number_of_unique_rows(sys_results, 'query_number')
# nr_systems = get_number_of_unique_rows(sys_results, 'system_number')
# result_df = create_result_df(nr_systems, nr_queries)
# calculate_all_precision_at_10(sys_results, qrels, nr_systems, nr_queries, result_df)
# calculate_all_recall_at_50(sys_results, qrels, nr_systems, nr_queries, result_df)
# calculate_all_R_precision(sys_results, qrels, nr_systems, nr_queries, result_df)
# calculate_all_AP(sys_results, qrels, nr_systems, nr_queries, result_df)
# calculate_all_nDCG(sys_results, qrels, nr_systems, nr_queries, result_df)
# score_means = print_result_df(result_df, nr_systems, nr_queries)
# col_names = ['P@10', 'R@50', 'r-precision', 'AP', 'nDCG@10', 'nDCG@20']
# p_values(result_df, score_means, nr_queries, col_names)

# Part 2 code ----------------------------------------------------------------------------
# tsv_file_name = 'train_and_dev.tsv'
# stopwords_file_name = "englishST.txt"
# index_output_file_name = "index.txt"

# stopwords_set = construct_stopwords_set(stopwords_file_name)
# tokenizer = SimpleTokenizer('[a-zA-Z]+')
# stemmer = PorterStemmer()
# preprocessor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)

# corpus_names_to_int = {'Quran':0, 'OT':1, 'NT':2}
# int_to_corpus_names = {0:'Quran', 1:'OT', 2:'NT'}

# corpora = read_tsv_extract_corpora(tsv_file_name, corpus_names_to_int)
# corpora = preprocess_corpora(corpora, preprocessor)


# index, corpora_nr_docs = read_corpora_and_create_index(corpora)

# MI_scores, chi_scores = compute_MI_chi_scores(index, corpora_nr_docs, corpus_names_to_int.values())
# print_top_k_terms_for_each_corpus(MI_scores, chi_scores, int_to_corpus_names, 10)

# run_topics_task(corpora, corpora_nr_docs)
# ---------------------------------------------------------------------------------------





# Part 3 code. This is the baseline, it should remain uncommented for every experiment.
tokenizer = SimpleTokenizer('[a-zA-Z]+')

tsv_file_name = 'train_and_dev.tsv'
test_tsv_file_name = 'test.tsv'
stopwords_file_name = "englishST.txt"
output_file_name = "classification.csv"
kjv_file_name = 't_kjv.csv'

corpus_names_to_int = {'Quran':0, 'OT':1, 'NT':2}
int_to_corpus_names = {0:'Quran', 1:'OT', 2:'NT'}
corpus_ids = set([0, 1, 2])

corpora = read_tsv_extract_corpora(tsv_file_name, corpus_names_to_int)
test_corpora = read_tsv_extract_corpora(test_tsv_file_name, corpus_names_to_int)

tokenized_corpora = tokenize_corpora(corpora, tokenizer)
test_tokenized_corpora = tokenize_corpora(test_corpora, tokenizer)

baseline_train_docs, baseline_train_labels, baseline_dev_docs, baseline_dev_labels = split_train_dev_baseline(tokenized_corpora, corpus_ids)
baseline_test_docs, baseline_test_labels = split_test(test_tokenized_corpora, corpus_ids)

baseline_train_bow_sents, bow = docs_to_bow_sents(baseline_train_docs)
baseline_dev_bow_sents = docs_to_bow_sents(baseline_dev_docs, bow)[0]
baseline_test_bow_sents = docs_to_bow_sents(baseline_test_docs, bow)[0]

baseline_train_dok = bow_sents_to_dok(baseline_train_bow_sents, bow)
baseline_dev_dok = bow_sents_to_dok(baseline_dev_bow_sents, bow)
baseline_test_dok = bow_sents_to_dok(baseline_test_bow_sents, bow)

baseline_model = SVC(C=1000)
baseline_model.fit(baseline_train_dok, baseline_train_labels)
baseline_train_pred = baseline_model.predict(baseline_train_dok)
baseline_dev_pred = baseline_model.predict(baseline_dev_dok)
baseline_test_pred = baseline_model.predict(baseline_test_dok)
# ---------end of baseline----------------------------------------

# Part 3 code for preprocessing tests.-----------------------------------------------------------
# tokenizer = SimpleTokenizer('[a-zA-Z]+')

# preprocessed_corpora = tokenize_corpora(corpora, tokenizer)
# test_preprocessed_corpora = tokenize_corpora(test_corpora, tokenizer)

# improved_train_docs, improved_train_labels, improved_dev_docs, improved_dev_labels = split_train_dev_improved(preprocessed_corpora, corpus_ids)
# improved_test_docs, improved_test_labels = split_test(test_preprocessed_corpora, corpus_ids)

# improved_train_bow_sents, improved_bow = docs_to_bow_sents(improved_train_docs)
# improved_dev_bow_sents = docs_to_bow_sents(improved_dev_docs, improved_bow)[0]
# improved_test_bow_sents = docs_to_bow_sents(improved_test_docs, improved_bow)[0]

# improved_train_dok = bow_sents_to_dok(improved_train_bow_sents, improved_bow)
# improved_dev_dok = bow_sents_to_dok(improved_dev_bow_sents, improved_bow)
# improved_test_dok = bow_sents_to_dok(improved_test_bow_sents, improved_bow)
# ---------------------------------------------------------------------------------------

# Task 3 extra data experiment-----------------------------------------------------------
# def replace_NT_OT_docs(corpora:Dict[int, List[str]], kjv_file_name:str) -> Dict[int, List[str]]:
#     new_corpora = dict()
#     new_corpora[0] = corpora[0]
#     new_corpora[1] = []
#     new_corpora[2] = []
#     with open(kjv_file_name, mode='r', newline='\n') as f:
#         read_tsv = csv.reader(f, delimiter=",")
#         for row in read_tsv:
#             if row[1] == 'b':
#                 continue
#             chapter = int(row[1])
#             if chapter < 40:
#                 new_corpora[1].append(row[4])
#             elif chapter >= 40:
#                 new_corpora[2].append(row[4])
#     return new_corpora

# new_corpora = replace_NT_OT_docs(corpora, kjv_file_name)
# test_corpora = read_tsv_extract_corpora(test_tsv_file_name, corpus_names_to_int)

# preprocessed_corpora = tokenize_corpora(new_corpora, tokenizer)
# test_preprocessed_corpora = tokenize_corpora(test_corpora, tokenizer)

# improved_train_docs, improved_train_labels, improved_dev_docs, improved_dev_labels = split_train_dev_improved(preprocessed_corpora, corpus_ids)
# improved_test_docs, improved_test_labels = split_test(test_preprocessed_corpora, corpus_ids)

# improved_train_bow_sents, improved_bow = docs_to_bow_sents(improved_train_docs)
# improved_dev_bow_sents = docs_to_bow_sents(improved_dev_docs, improved_bow)[0]
# improved_test_bow_sents = docs_to_bow_sents(improved_test_docs, improved_bow)[0]

# improved_train_dok = bow_sents_to_dok(improved_train_bow_sents, improved_bow)
# improved_dev_dok = bow_sents_to_dok(improved_dev_bow_sents, improved_bow)
# improved_test_dok = bow_sents_to_dok(improved_test_bow_sents, improved_bow)

# improved_model = SVC(C=1000)
# improved_model.fit(improved_train_dok, improved_train_labels)
# improved_train_pred = improved_model.predict(improved_train_dok)
# improved_dev_pred = improved_model.predict(improved_dev_dok)
# improved_test_pred = improved_model.predict(improved_test_dok)
# ---------------------------------------------------------------------------------------

# Code with optimized C-value--------------------------------------------------------------
# preprocessed_corpora = tokenize_corpora(corpora, tokenizer)
# test_preprocessed_corpora = tokenize_corpora(test_corpora, tokenizer)

# improved_train_docs, improved_train_labels, improved_dev_docs, improved_dev_labels = split_train_dev_improved(preprocessed_corpora, corpus_ids)
# improved_test_docs, improved_test_labels = split_test(test_preprocessed_corpora, corpus_ids)

# improved_train_bow_sents, improved_bow = docs_to_bow_sents(improved_train_docs)
# improved_dev_bow_sents = docs_to_bow_sents(improved_dev_docs, improved_bow)[0]
# improved_test_bow_sents = docs_to_bow_sents(improved_test_docs, improved_bow)[0]

# improved_train_dok = bow_sents_to_dok(improved_train_bow_sents, improved_bow)
# improved_dev_dok = bow_sents_to_dok(improved_dev_bow_sents, improved_bow)
# improved_test_dok = bow_sents_to_dok(improved_test_bow_sents, improved_bow)

# improved_model = SVC(C=10, gamma='scale')
# improved_model.fit(improved_train_dok, improved_train_labels)
# improved_train_pred = improved_model.predict(improved_train_dok)
# improved_dev_pred = improved_model.predict(improved_dev_dok)
# improved_test_pred = improved_model.predict(improved_test_dok)

# create_classification_output_file(output_file_name,
#                                  baseline_train_labels, baseline_train_pred,
#                                  baseline_dev_labels, baseline_dev_pred,
#                                  baseline_test_labels, baseline_test_pred,
#                                  improved_train_labels, improved_train_pred,
#                                  improved_dev_labels, improved_dev_pred,
#                                  improved_test_labels, improved_test_pred)

# Code for transformer. ---------------------------------------------------------------
# from simpletransformers.classification import ClassificationModel
# import pandas as pd
# import logging

# def split_train_dev_transformer(train_dev_corpora:Dict[int, List[str]], corpus_ids:Set[int], 
#                     percentage_dev:Optional[float]=0.1):
#     train_set = []
#     train_labels = []
#     dev_set = []
#     dev_labels = []
#     splitter = ShuffleSplit(1, test_size=percentage_dev, random_state=0)
#     for corpus_id in corpus_ids:
#         corpus_docs = train_dev_corpora[corpus_id]
#         train_indices, dev_indices = list(splitter.split(corpus_docs))[0]
        
#         set_train_idx = set(train_indices)
        
#         for train_index in train_indices:
#             train_set.append([corpus_docs[train_index], corpus_id])
#             train_labels.append(corpus_id)
        
#         for dev_index in dev_indices:
#             dev_set.append([corpus_docs[dev_index], corpus_id])
#             dev_labels.append(corpus_id)
    
#     return train_set, train_labels, dev_set, dev_labels

# def split_test_transformer(test_corpora:Dict[int, List[str]], corpus_ids:Set[int]):
#     test_docs = []
#     test_labels = []
#     for corpus_id in corpus_ids:
#         for test_doc in test_corpora[corpus_id]:
#             test_docs.append([test_doc, corpus_id])
#             test_labels.append(corpus_id)
#     return test_docs, test_labels

# improved_train_docs, improved_train_labels, improved_dev_docs, improved_dev_labels = split_train_dev_transformer(corpora, corpus_ids)
# improved_test_docs, improved_test_labels = split_test_transformer(test_corpora, corpus_ids)
# train_df = pd.DataFrame(improved_train_docs)
# eval_df = pd.DataFrame(improved_dev_docs)
# test_df = pd.DataFrame(improved_test_docs)
# model = ClassificationModel('bert', 'bert-base-cased', num_labels=3, args={'reprocess_input_data': True, 'overwrite_output_dir': True})
# model.train_model(train_df)

# result, model_outputs, wrong_predictions = model.eval_model(train_df)
# improved_train_pred = list(map(np.argmax, model_outputs))

# result, model_outputs, wrong_predictions = model.eval_model(eval_df)
# improved_dev_pred = list(map(np.argmax, model_outputs))

# result, model_outputs, wrong_predictions = model.eval_model(test_df)
# improved_test_pred = list(map(np.argmax, model_outputs))

# create_classification_output_file(output_file_name,
#                                  baseline_train_labels, baseline_train_pred,
#                                  baseline_dev_labels, baseline_dev_pred,
#                                  baseline_test_labels, baseline_test_pred,
#                                  improved_train_labels, improved_train_pred,
#                                  improved_dev_labels, improved_eval_pred,
#                                  improved_test_labels, improved_test_pred)
# End transformer code --------------------------------------------------------------------------

# Code for feature selection for classification (best performing model).
tsv_file_name = 'train_and_dev.tsv'
index_output_file_name = "index.txt"
test_tsv_file_name = 'test.tsv'
output_file_name = "classification.csv"
kjv_file_name = 't_kjv.csv'
tokenizer = SimpleTokenizer('[a-zA-Z]+')

corpus_names_to_int = {'Quran':0, 'OT':1, 'NT':2}
int_to_corpus_names = {0:'Quran', 1:'OT', 2:'NT'}

corpora = read_tsv_extract_corpora(tsv_file_name, corpus_names_to_int)
test_corpora = read_tsv_extract_corpora(test_tsv_file_name, corpus_names_to_int)

tokenized_corpora = tokenize_corpora(corpora, tokenizer)
test_tokenized_corpora = tokenize_corpora(test_corpora, tokenizer)

index, tokenized_corpora_nr_docs = read_corpora_and_create_index(tokenized_corpora)

def compute_MI_chi_scores_modified(index:Index, corpora_nr_docs:Dict[int, int], 
                                   corpora_ids:List[int]):
    MI_scores = dict()
    chi_scores = dict()

    for corpus_id in corpora_ids:
        MI_scores[corpus_id] = dict()
        chi_scores[corpus_id] = dict()
    
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

            MI_scores[corpus_id][term] = compute_MI_score_term_corpus(N, N_00, N_01, N_10, N_11)
            chi_scores[corpus_id][term] = compute_chi_score_term_corpus(N, N_00, N_01, N_10, N_11)
            
    return MI_scores, chi_scores

MI_scores, chi_scores = compute_MI_chi_scores_modified(index, tokenized_corpora_nr_docs, 
                                                      corpus_names_to_int.values())

def remove_unimportant_features(target_corpora, chi_scores, critical_value=2.71):
    new_corpora = dict()
    
    for corpus_id in target_corpora.keys():
        new_corpora[corpus_id] = []
    
    for corpus_id in target_corpora.keys():
        for document in target_corpora[corpus_id]:
            new_doc = []
            for term in document:
                if term not in chi_scores[corpus_id]:
                    continue
                if chi_scores[corpus_id][term] >= critical_value:
                    new_doc.append(term)
            if len(new_doc) > 0:
                new_corpora[corpus_id].append(new_doc)
    return new_corpora


preprocessed_corpora = remove_unimportant_features(tokenized_corpora, chi_scores)
test_preprocessed_corpora = remove_unimportant_features(test_tokenized_corpora, chi_scores)

improved_train_docs, improved_train_labels, improved_dev_docs, improved_dev_labels = split_train_dev_improved(preprocessed_corpora, corpus_ids)
improved_test_docs, improved_test_labels = split_test(test_preprocessed_corpora, corpus_ids)

improved_train_bow_sents, improved_bow = docs_to_bow_sents(improved_train_docs)
improved_dev_bow_sents = docs_to_bow_sents(improved_dev_docs, improved_bow)[0]
improved_test_bow_sents = docs_to_bow_sents(improved_test_docs, improved_bow)[0]

improved_train_dok = bow_sents_to_dok(improved_train_bow_sents, improved_bow)
improved_dev_dok = bow_sents_to_dok(improved_dev_bow_sents, improved_bow)
improved_test_dok = bow_sents_to_dok(improved_test_bow_sents, improved_bow)

improved_model = SVC(C=10, gamma='scale')
improved_model.fit(improved_train_dok, improved_train_labels)
improved_train_pred = improved_model.predict(improved_train_dok)
improved_dev_pred = improved_model.predict(improved_dev_dok)
improved_test_pred = improved_model.predict(improved_test_dok)

create_classification_output_file(output_file_name,
                                 baseline_train_labels, baseline_train_pred,
                                 baseline_dev_labels, baseline_dev_pred,
                                 baseline_test_labels, baseline_test_pred,
                                 improved_train_labels, improved_train_pred,
                                 improved_dev_labels, improved_dev_pred,
                                 improved_test_labels, improved_test_pred)