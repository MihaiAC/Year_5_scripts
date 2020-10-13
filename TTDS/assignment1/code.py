import re
import argparse
import linecache
import xml.etree.ElementTree as ElementTree
import pickle
from nltk.stem.porter import PorterStemmer

cmdline_parser = argparse.ArgumentParser(description="Get file name.")
cmdline_parser.add_argument('input_file_name', type=str, help="Input file name.")
cmdline_parser.add_argument('stopwords_file_name', type=str, help="Stopwords file name.")
cmdline_parser.add_argument('strip_lines', type=int, help="42 bible, x quran, x wikipedia")
cmdline_parser.add_argument('output_file_name', type=str, help="Output file name.")
args = cmdline_parser.parse_args()

input_file_name = args.input_file_name
stopwords_file_name = args.stopwords_file_name
strip_lines = args.strip_lines
output_file_name = args.output_file_name

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

def read_input_trec_file_and_create_index(input_file_name, preprocessor):
    pos_inverted_index = dict()

    with open(input_file_name, 'r') as f:
        xml_trec_file = f.read()
    xml = ElementTree.fromstring(xml_trec_file)
    for doc in xml:
        docId = int(doc.find('DOCNO').text.strip())
        docHeadline = doc.find('HEADLINE').text.strip()
        docText = doc.find('TEXT').text.strip()
        
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
    
    return pos_inverted_index

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
    pos_inverted_index = pickle.load(file_name)
    return pos_inverted_index


stopwords_set = construct_stopwords_set(stopwords_file_name)
tokenizer = SimpleTokenizer('[a-zA-Z]+')
stemmer = PorterStemmer()
pre_processor = SimplePreprocessor(tokenizer, stopwords_set, stemmer)

pos_inverted_index = read_input_trec_file_and_create_index(input_file_name, pre_processor)
save_pos_inverted_index(pos_inverted_index, 'pos_inverted_index.pkl')
pretty_print_pos_inverted_index(pos_inverted_index, 'index.txt')
# write_stemmed_lines(stemmed_lines, output_file_name)
