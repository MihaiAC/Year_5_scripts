import argparse
import nltk
nltk.download('stopwords')
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

cmdline_parser = argparse.ArgumentParser(description="Get file name.")
cmdline_parser.add_argument('input_file_name', type=str, help="Input file name.")
cmdline_parser.add_argument('strip_lines', type=int, help="42 bible, x quran, x wikipedia")
cmdline_parser.add_argument('output_file_name', type=str, help="Output file name.")
args = cmdline_parser.parse_args()

input_file_name = args.input_file_name
strip_lines = args.strip_lines
output_file_name = args.output_file_name

def tokenize_lines(text_lines, tokenizer):
    tokenized_lines = []
    for line in text_lines:
        tokenized_line = tokenizer.tokenize(line)
        if len(tokenized_line) == 0:
            pass
        else:
            tokenized_lines.append(tokenized_line)
    return tokenized_lines

def lowercase_lines(text_lines):
    lowercased_lines = []
    for line in text_lines:
        lowercased_line = []
        for term in line:
            lowercased_line.append(str.lower(term))
        lowercased_lines.append(lowercased_line)
    
    return lowercased_lines

def remove_stopwords_from_lines(text_lines, stopwords):
    clean_lines = []
    for line in text_lines:
        clean_line = []
        for term in line:
            if term not in stopwords:
                clean_line.append(term)
        if len(clean_line) > 0:
            clean_lines.append(clean_line)
    
    return clean_lines

def stem_lines(text_lines, stemmer):
    stemmed_lines = []

    for line in text_lines:
        stemmed_line = []
        for term in line:
            stemmed_line.append(stemmer.stem(term))
        stemmed_lines.append(stemmed_line)
    
    return stemmed_lines
        
    
def pre_process(input_file_name, strip_lines, stopwords, stemmer, tokenizer):
    with open('./' + input_file_name, 'r') as f:
        text_lines = f.readlines()
    
    text_lines = text_lines[strip_lines:]
    tokenized_lines = tokenize_lines(text_lines, tokenizer)
    lowercased_lines = lowercase_lines(tokenized_lines)
    clean_lines = remove_stopwords_from_lines(lowercased_lines, stopwords)
    stemmed_lines = stem_lines(clean_lines, stemmer)
    
    return stemmed_lines

def join_line(line):
    joined_line = " ".join(line)
    joined_line += "\n"
    return joined_line

def write_stemmed_lines(lines, output_file_name):
    with open('./' + output_file_name, 'w') as f:
        for line in lines:
            f.write(join_line(line))
    


    
tokenizer = RegexpTokenizer(r'\w+')
english_stopwords = stopwords.words('english')
stemmer = PorterStemmer()

stemmed_lines = pre_process(input_file_name, strip_lines, english_stopwords, stemmer, tokenizer)
write_stemmed_lines(stemmed_lines, output_file_name)
