
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
from tokenizers import Tokenizer
from typing import List, Set
import unicodedata
import spacy
from nltk.tokenize import sent_tokenize

class Preprocessor():
    def __init__(self):
        pass

    @staticmethod
    def lowercase_word(word:str) -> str:
        return str.lower(word)
    
    @staticmethod
    def construct_stopwords_set(stopwords_file_name:str) -> Set[str]:
        # Assumes one word per line.
        with open(stopwords_file_name, 'r') as f:
            stopwords = f.read().splitlines()
        return set(stopwords)
    
    def process_text_lines(self, text_lines:List[str]) -> List[str]:
        pass


class SimplePreprocessor(Preprocessor):
    def __init__(self, tokenizer:Tokenizer, stopwords_file:str, stemmer:SnowballStemmer):
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


class Word2VecPreprocessor(Preprocessor):
    # Ok so: Lemmatize sentence (since it's context dependent) -> 
    # Tokenize -> 
    # Remove stop words.
    def __init__(self, tokenizer:Tokenizer, stopwords_file:str):
        super().__init__()
        self.nlp = spacy.load('en_core_web_sm', disable=["parser", "ner", "textcat", "tagger"])
        self.tokenizer = tokenizer

        self.stop_words_set = Word2VecPreprocessor.construct_stopwords_set(stopwords_file)
        self.stop_words_set = self.stop_words_set.union(set(self.nlp.Defaults.stop_words))
        
    
    def process_text_lines_return_separate(self, text_lines:List[str]) -> List[List[str]]:
        if len(text_lines) == 2:
            text = text_lines[0] + '. ' + text_lines[1]
        else:
            text = text_lines[0] + " ".join(text_lines[1:])
        
        sentences = sent_tokenize(text)
        
        processed_sentences = []
        for text in sentences:
            processed_tokens = []
            text = self.nlp(text)

            for token in text:
                lemmatized_tokens = self.tokenizer.tokenize_string(token.lemma_)
                for token in lemmatized_tokens:
                    token_ = Word2VecPreprocessor.lowercase_word(token)
                    if token_ not in self.stop_words_set:
                        processed_tokens.append(token_)
            processed_sentences.append(processed_tokens)

        return processed_sentences
    
    def process_text_lines(self, text_lines:List[str]) -> List[str]:
        ret = []
        tokenized_sents = self.process_text_lines_return_separate(text_lines)
        for sent in tokenized_sents:
            ret += sent
        return ret
