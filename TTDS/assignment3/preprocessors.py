
from nltk.stem.porter import PorterStemmer
from tokenizers import Tokenizer
from typing import List, Set

class Preprocessor():
    def __init__(self):
        pass

    @staticmethod
    def lowercase_word(word:str) -> str:
        return str.lower(word)
    
    def process_text_lines(self, text_lines:List[str]) -> List[str]:
        pass


class SimplePreprocessor(Preprocessor):
    def __init__(self, tokenizer:Tokenizer, stopwords_file:str, stemmer:PorterStemmer):
        super().__init__()
        self.tokenizer = tokenizer
        self.stop_words_set = SimplePreprocessor.construct_stopwords_set(stopwords_file)
        self.stemmer = stemmer
    
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

    @staticmethod
    def construct_stopwords_set(stopwords_file_name:str) -> Set[str]:
        # Assumes one word per line.
        with open(stopwords_file_name, 'r') as f:
            stopwords = f.read().splitlines()
        return set(stopwords)
        