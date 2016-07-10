# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import errno
import logging
import os
import re
import sys
import time

def strip_top_dir(root_path_to_remove, full_path):
    if re.match(root_path_to_remove, full_path):
        return os.path.relpath(full_path, root_path_to_remove)
    else:
        # TODO error handling
        print("Cannot strip path\n\t{}\n\tfrom\n\t{}".format(full_path,
                                                             root_path_to_remove))
        sys.exit(1)


def create_dir(dir_path):
    """Create directory (including parents if necessary)."""
    try:
        os.makedirs(dir_path)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(dir_path):
            pass
        else:
            raise

def clean_dir(dir_path):
    """Non-recursive removal of all files except README.*"""
    if not os.path.exists(dir_path):
        create_dir(dir_path)
    elif not os.path.isdir(dir_path):
        logging.error("This is not a directory: %s", dir_path)
        # TODO error handling
        raise Exception

    dir_entries = os.listdir(dir_path)
    for dir_entry in dir_entries:
        path = os.path.join(dir_path, dir_entry)
        if os.path.isfile(path):
            if not re.match(r'README.', dir_entry):
                os.remove(path)
    #files = [ f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]


def get_timestamp():
    return time.strftime("%H:%M:%S")
