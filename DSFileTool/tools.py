import sys

import huepy
import numpy as np

from DSFileTool.defaults import FILENAMES


class Dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Singleton(type):
    _obj = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._obj:
            cls._obj[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._obj[cls]


# Prompt the user with a Yes / No question, defaults to Yes
def prompt(query):
    try:
        q = huepy.white(f'{huepy.grey(query)} [Y]es / No: ')
        return ['', 'y', 'ye', 'yes', 'n', 'no'].index(input(q).lower()) < 4
    except ValueError:
        return prompt('Unknown response. Respond with')


# Wait for any user input and exit with the provided exit code
def wait_before_exit(exit_code):
    from DSFileTool.logger import Logger
    log = Logger()
    log.run('grey', 'Press ANY key to quit...', same_line=True)
    input()
    sys.exit(exit_code)


# Dark Souls .bhd5 filepath hash function
def get_hash_from_string(s):
    np.warnings.simplefilter('ignore', RuntimeWarning)

    hash_val = np.uint32(0)
    for char in bytearray(s.lower(), encoding='utf-8'):
        hash_val *= np.uint32(37)
        hash_val += np.uint32(char)
    return hash_val.item()


# Return a dictionary that translates known .bhd5 filepath hashes to filepaths
def build_name_hash_dict():
    name_hash_dict = {}
    for name in FILENAMES:
        name_hash_dict[get_hash_from_string(name)] = name
    return name_hash_dict
