# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import os
import urllib2
import sys

import stacktrain.core.helpers as hf
import stacktrain.config.general as conf
import stacktrain.distros.ubuntu_14_04_server_amd64 as distro_boot

#-------------------------------------------------------------------------------
# Functions to get install ISO images
#-------------------------------------------------------------------------------

def download(url, target_path):
    try:
        print("Trying to download from:\n\t%s" % url)
        response = urllib2.urlopen(url)
        with open(target_path, 'wb') as out:
            out.write(response.read())
    except urllib2.URLError as err:
        print("ERROR in download(), type", type(err))
        print("ERROR ", err)
        raise

def find_install_iso():
    iso_name = conf.iso_name
    iso_path = os.path.join(conf.img_dir, iso_name)
    if os.path.isfile(iso_path):
        print("There is a file at given path:\n\t%s" % iso_path)
        if md5_match(iso_path, conf.iso_md5):
            return
        else:
            print("ISO image corrupt:\n\t%s" % iso_path)
            #raise ValueError
            os.remove(iso_path)
    else:
        print("There is no file at given path:\n\t%s" % iso_path)
        hf.create_dir(os.path.dirname(iso_path))

    try:
        download(conf.iso_url, iso_path)
        # TODO specify exception
    except urllib2.URLError as err:
        distro_boot.update_iso_image_variables()
        try:
            download(conf.iso_url, iso_path)
        except urllib2.URLError as err:
            # TODO FIX exceptions
            print("ERROR Download failed for:\n\t%s", conf.iso_url)
            sys.exit(1)

    if md5_match(iso_path, conf.iso_md5):
        return
    else:
        print("ERROR ISO image corrupt.")

def md5_match(path, correct_md5):

    import hashlib
    with open(path, 'rb') as ff:
        hasher = hashlib.md5()
        while True:
            buf = ff.read(2**24)
            if not buf:
                break
            hasher.update(buf)
    actual_md5 = hasher.hexdigest()
    print("MD5", correct_md5, actual_md5)
    if correct_md5 == actual_md5:
        print("MD5 sum matched.")
        return True
    else:
        print("MD5 sum did not match.")
        return False
