import os
import json
import pickle
import multiprocessing as mp
import gc
from time import time
from functools import wraps
from sqlitedict import SqliteDict
from preprocessors import Preprocessor, SimplePreprocessor
from tokenizers import RegexpTokenizer
from typing import List, Optional, Dict
from nltk.stem import PorterStemmer

# Assumptions:
# 1. File is in standard format: 1 json entry per line, each entry must have: fields: headline and fields:bodyText, + id field.
# 2. IDs are assumed to have already been standardised.

# Q: What happens if the whole index does not fit in memory?
# A: The sqlitedict does not load the whole index into memory.

# Q: What happens if one of the index chunks does not fit into memory?
# A: Decrease flush_every_x_lines.

# To think about: 
# An alternative way of saving indices would be to have an entry of docIDs
# for a given word, + the occurrences for a given (word,docId).
# This way, we would not load the whole dictionary of postings for a word, but
# only the posting specific to a word, docID pair (may be a drawback or not, depending
# on the use case).

# Current assumption: no commas are left after preprocessing.
def merge_indices(merged_index_file_name:str, indices_files:List[str], delete:Optional[bool]=True):
    with SqliteDict(merged_index_file_name, autocommit=False) as slitedict:
        for index_file in indices_files:
            index = load_pos_inverted_index(index_file)
            for word in index:
                word_dict = slitedict.get(word)
                if word_dict is None:
                    slitedict[word] = index[word]
                else:
                    slitedict[word].update(index[word])
            if delete:
                os.remove(index_file)
            slitedict.commit()
    print('Indices successfully merged?')
                

def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('func:%r args:[%r, %r] took: %2.4f sec' % \
          (f.__name__, args, kw, te-ts))
        return result
    return wrap

def build_indices(preprocessor:Preprocessor, 
                  file_names:List[str], 
                  flush_every_x_lines:int,
                  ) -> List[str]:
    nr_processors = mp.cpu_count()
    with mp.Pool(processes=nr_processors) as pool:
        list_of_indices = pool.starmap(construct_index, ((preprocessor, x, flush_every_x_lines) for x in file_names))
    indices = []
    for x in list_of_indices:
        indices += x
    print('Indices construction finished.')
    return indices

def save_pos_inverted_index(pos_inverted_index, file_name:str):
    with open(file_name, 'wb') as f:
        pickle.dump(pos_inverted_index, f)

def load_pos_inverted_index(file_name:str):
    with open(file_name, 'rb') as f:
        pos_inverted_index = pickle.load(f)
    return pos_inverted_index

# Test without sqlite and with sqlite.
def construct_index(preprocessor:Preprocessor, data_path:str, flush_every_x_lines:int) -> List[str]:
    indices = []

    pos_inverted_index = dict()
    line_count = 0
    _, file_name = os.path.split(data_path)
    
    
    with open(data_path, 'r') as f:
        for line in f:
            if line_count % flush_every_x_lines == 0:
                if line_count != 0:
                    save_pos_inverted_index(pos_inverted_index, index_name)
                    del pos_inverted_index
                    gc.collect()
                pos_inverted_index = dict()
                index_name = str(line_count//flush_every_x_lines) + '_' + file_name
                indices.append(index_name)
            
            data = json.loads(line)
            headline = data['fields']['headline']
            body = data['fields']['bodyText']
            docId = data['id']

            terms = preprocessor.process_text_lines([headline, body])
            for index, term in enumerate(terms):
                if term in pos_inverted_index:
                    if docId in pos_inverted_index[term]:
                        pos_inverted_index[term][docId].append(index)
                    else:
                        pos_inverted_index[term][docId] = [index]
                else:
                    pos_inverted_index[term] = dict()
                    pos_inverted_index[term][docId] = [index]
            
            line_count += 1

        save_pos_inverted_index(pos_inverted_index, index_name)
    return indices

def count_nr_lines(file_path:str) -> int:
    nr_lines = 0
    with open(file_path, 'r') as f:
        for _ in f:
            nr_lines += 1
    return nr_lines

def calculate_optimal_partitions(nr_lines:int, n:int) -> Dict[int, int]:
    div = nr_lines // n
    mod = nr_lines % n
    partitions = []
    for _ in range(n):
        x = div
        if mod > 0:
            mod -= 1
            x += 1
        partitions.append(x)

    # Accumulate values:
    for ii in range(1, n):
        partitions[ii] += partitions[ii-1]
    
    partitions_dict = dict()
    for ii in range(n):
        partitions_dict[ii] = partitions[ii]
    
    return partitions_dict
    

def partition_data_into_n(data_path:str, nr_lines:int, n:int) -> List[str]:
    path, file_name = os.path.split(data_path)
    file_path = path + '/' + file_name

    if nr_lines is None:
        nr_lines = count_nr_lines(data_path)
    
    partitions_dict = calculate_optimal_partitions(nr_lines, n)
    partition = 0

    partitions_names = []
    gs = []
    for ii in range(n):
        new_file_path = './' + str(ii) + '_' + file_name
        partitions_names.append(new_file_path)
        g = open(new_file_path, 'w')
        gs.append(g)
    
    count = 0

    with open(file_path, 'r') as f:
        for line in f:
            if partitions_dict[partition] == count:
                partition += 1
            count += 1
            gs[partition].write(line)

    for ii in range(n):
        gs[ii].close()
    
    print('Partition finished.')
    return partitions_names

def delete_data_partitions(file_paths:List[str]):
    for file in file_paths:
        os.remove(file)

if __name__ == '__main__':
    tokenizer = RegexpTokenizer(pattern='[a-zA-Z]+')

    stopwords_file_name = "englishST.txt"
    stemmer = PorterStemmer()
    preprocessor = SimplePreprocessor(tokenizer, stopwords_file_name, stemmer)

    chunks = partition_data_into_n("./standard_politics.large", None, 4)
    indices = build_indices(preprocessor, chunks, 10000)
    merge_indices('index.sqlite', indices)
    delete_data_partitions(chunks)
    