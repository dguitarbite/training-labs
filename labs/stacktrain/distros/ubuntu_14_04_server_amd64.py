#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import os
import re
import urllib2
import sys

import stacktrain.core.cond_sleep as cs
import stacktrain.core.keycodes as kc
import stacktrain.config.general as conf

conf.base_install_scripts = "scripts.ubuntu_base"

#-------------------------------------------------------------------------------
# Installation from ISO image
#-------------------------------------------------------------------------------

conf.iso_url_base = "http://releases.ubuntu.com/14.04/"
conf.iso_name = "ubuntu-14.04.4-server-amd64.iso"
conf.iso_url = conf.iso_url_base + conf.iso_name
conf.iso_md5 = "2ac1f3e0de626e54d05065d6f549fa3a"

PRESEED_HOST_DIR = ("http://git.openstack.org/cgit/openstack/training-labs/"
                    "plain/labs/osbash/lib/osbash/netboot/")

PRESEED_URL = {}
PRESEED_URL['ssh'] = PRESEED_HOST_DIR + "preseed-ssh-v2.cfg"
PRESEED_URL['shared_folder'] = PRESEED_HOST_DIR + "preseed-vbadd.cfg"
PRESEED_URL['all'] = PRESEED_HOST_DIR + "preseed-all-v2.cfg"

# Arguments for ISO image installer
_BOOT_ARGS = ("/install/vmlinuz"
              " noapic"
              " preseed/url=%s"
              " debian-installer=en_US"
              " auto=true"
              " locale=en_US"
              " hostname=osbash"
              " fb=false"
              " debconf/frontend=noninteractive"
              " keyboard-configuration/modelcode=SKIP"
              " initrd=/install/initrd.gz"
              " console-setup/ask_detect=false")

# Fallback function to find current ISO image in case the file in ISO_URL is
# neither on the disk nor at the configured URL.
# This mechanism was added because old Ubuntu ISOs are removed from the server
# as soon as a new ISO appears.
def update_iso_image_variables():
    # Get matching line from distro repo's MD5SUMS file, e.g.
    # "9e5fecc94b3925bededed0fdca1bd417 *ubuntu-14.04.3-server-amd64.iso"
    try:
        response = urllib2.urlopen(os.path.join(conf.iso_url_base, "MD5SUMS"))
    except urllib2.URLError:
        print("ERROR in update_iso_image_variables")
        print("ERROR Can't find newer ISO image. Aborting.")
        sys.exit(1)

    txt = response.read()
    print("txt:", txt)
    print("//////////// end txt")
    ma = re.search(r"(.*) \*{0,1}(.*server-amd64.iso)", txt)
    if ma:
        print("ma1", ma.group(1))
        conf.iso_md5 = ma.group(1)
        print("ma2", ma.group(2))
        conf.iso_name = ma.group(2)
        conf.iso_url = os.path.join(conf.iso_url_base, conf.iso_name)

    print("New ISO URL:\n\t%s" % conf.iso_url)


# ostype used by VirtualBox to choose icon and flags (64-bit, IOAPIC)
conf.vbox_ostype = "Ubuntu_64"

# Boot the ISO image operating system installer
# TODO pass vm_name here instead of config
def distro_start_installer(config):

    # pick a _PS_* file
    #local preseed=_PS_$VM_ACCESS
    preseed = PRESEED_URL[conf.vm_access]

    print("Using ", preseed)

    # TODO choose appropriate preseed file
    # local boot_args=$(printf "$_BOOT_ARGS" "${!preseed}")
    boot_args = _BOOT_ARGS % preseed

    kc.keyboard_send_escape(config.vm_name)
    kc.keyboard_send_escape(config.vm_name)
    kc.keyboard_send_enter(config.vm_name)

    cs.conditional_sleep(1)

    print("Pushing boot command line.")
    kc.keyboard_send_string(config.vm_name, boot_args)

    print("Initiating boot sequence")
    kc.keyboard_send_enter(config.vm_name)
