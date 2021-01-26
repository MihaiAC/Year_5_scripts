import re
import pickle
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

##################################### TASK 1 - IR EVALUATION ###############################


corpora_file_names = ["corpus1.txt", "corpus2.txt"]
stopwords_file_name = "englishST.txt"
index_output_file_name = "index.txt"

stopwords_set = construct_stopwords_set(stopwords_file_name)
tokenizer = SimpleTokenizer('[a-zA-Z]+')
stemmer = PorterStemmer()
pre_processor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)

