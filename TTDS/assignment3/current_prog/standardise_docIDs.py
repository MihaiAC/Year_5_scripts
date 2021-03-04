import json
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('start_id', type=int)
parser.add_argument('file_path', type=str)
parser.add_argument('new_file_name', type=str)
parser.add_argument('file_type', type=str, choices=['theguardian'])

def standardise_docIDs_file(start_id:int, file_path:str, new_file_name:str, file_type:str):
    """ Standardises the IDs in the file found at "file_path", saves the results in
    new_file_name, in the same folder as the source. 
    If the source file name and the new file name are the same, the source file will be deleted.
    It's not efficient storage-wise (needs 2xsource file space).
    """
    folder_path, file_name = os.path.split(file_path)
    new_file_path = new_file_name if folder_path == '' else folder_path + '/' + new_file_name

    with open(file_path, 'r') as f:
        with open(new_file_path, 'w') as g:
            cache = []
            cache_max_size = 100

            for line in f:
                data = json.loads(line)
                canonical_id = data['id']
                data['canonical_id'] = canonical_id
                data['id'] = start_id
                start_id += 1
                cache.append(json.dumps(data))

                if len(cache) == cache_max_size:
                    for line in cache:
                        g.write(line + '\n')
                    cache = []
            
            if len(cache) > 0:
                for line in cache:
                    g.write(line + '\n')
    
    if file_name == new_file_name:
        os.remove(file_path)
        os.rename(new_file_path, file_path)
    
    print(start_id)

if __name__ == '__main__':
    args = parser.parse_args()
    start_id = args.start_id
    file_path = args.file_path
    new_file_name = args.new_file_name
    file_type = args.file_type

    standardise_docIDs_file(start_id, file_path, new_file_name, file_type)

