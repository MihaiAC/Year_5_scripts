import json
import argparse
import os
from sqlitedict import SqliteDict

parser = argparse.ArgumentParser()
parser.add_argument('json_file_path', type=str)
parser.add_argument('sqlite_file_name', type=str)


def transform_json_to_sqlite(json_file_path:str, sqlite_file_name:str):
    """ Standardises the IDs in the file found at "file_path", saves the results in
    new_file_name, in the same folder as the source. 

    If the source file name and the new file name are the same, the source file will be deleted.
    It's not efficient storage-wise (needs 2xsource file space).
    """

    folder_path, _ = os.path.split(json_file_path)
    sqlite_file_path = sqlite_file_name if folder_path == '' else folder_path + '/' + sqlite_file_name

    f = open(json_file_path, 'r')
    slitedict = SqliteDict(sqlite_file_path, autocommit=False)

    cache_max_size = 1000
    counter = 0

    for line in f:
        data = json.loads(line)
        doc_id = data['id']
        del data['id']
        slitedict[doc_id] = data

        counter += 1
        if counter % cache_max_size == 0:
            slitedict.commit()
    
    slitedict.commit()
    
    f.close()
    slitedict.close()

if __name__ == '__main__':
    args = parser.parse_args()
    json_file_path = args.json_file_path
    sqlite_file_name = args.sqlite_file_name

    transform_json_to_sqlite(json_file_path, sqlite_file_name)