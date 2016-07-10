#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import re
import os
import os.path

import stacktrain.config.general as conf

import stacktrain.batch_for_windows as wbatch

import stacktrain.virtualbox.vm_create as vm

#def get_base_disk_name():
#    return "base-{}-{}-{}".format(conf.vm_access, conf.openstack_release,
#                                  conf.distro)

# Wrapper around vm_snapshot to deal with collisions with cluster rebuilds
# starting from snapshot. We could delete the existing snapshot first,
# rename the new one, or just skip the snapshot.
def vm_conditional_snapshot(vm_name, shot_name):
    if conf.wbatch:
        # We need to record the proper command for wbatch; if a snapshot
        # exists, something is wrong and the program will abort
        vm.vm_snapshot(vm_name, shot_name)
    # It is not wbatch, so it must be do_build
    elif not vm.vm_snapshot_exists(vm_name, shot_name):
        vm.vm_snapshot(vm_name, shot_name)

#-------------------------------------------------------------------------------
# Files
#-------------------------------------------------------------------------------

#def clean_dir(dir_path):
#    """Non-recursive removal of all files except README.*"""
#    if not os.path.exists(dir_path):
#        return
#    elif not os.path.isdir(dir_path):
#        logging.error("This is not a directory: %s", dir_path)
#        # TODO error handling
#        raise
#
#    dir_entries = os.listdir(dir_path)
#    for dir_entry in dir_entries:
#        path = os.path.join(dir_path, dir_entry)
#        if os.path.isfile(path):
#            if not re.match(r'README.', dir_entry):
#                os.remove(path)
#    #files = [ f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]


#def create_dir(dir_path):
#    """Create directory (including parents if necessary)."""
#    try:
#        os.makedirs(dir_path)
#    except OSError as err:
#        if err.errno == errno.EEXIST and os.path.isdir(dir_path):
#            pass
#        else:
#            raise


#def strip_top_dir(full_path):
#    if re.match(conf.top_dir, full_path):
#        return os.path.relpath(full_path, conf.top_dir)
#    else:
#        # full_path is not in top_dir
#        # TODO error handling
#        raise

def get_next_file_number(dir_path, suffix=None):

    # Get number of files in directory
    entries = os.listdir(dir_path)
    cnt = 0
    for entry in entries:
        if not os.path.isfile(os.path.join(dir_path, entry)):
            continue
        if suffix and not re.match(r'.*\.' + suffix, entry):
            continue
        cnt += 1
    return cnt


def get_next_prefix(dir_path, suffix, digits=3):
    cnt = get_next_file_number(dir_path, suffix)

    return ('{:0'+ str(digits) + 'd}').format(cnt)

#-------------------------------------------------------------------------------
# Virtual VM keyboard using keycodes
#-------------------------------------------------------------------------------

#def keyboard_send_escape(vm_name):
#    _keyboard_push_scancode(vm_name, esc2scancode())

#def keyboard_send_enter(vm_name):
#    _keyboard_push_scancode(vm_name, enter2scancode())

# Turn strings into keycodes and send them to target VM
#def keyboard_send_string(vm_name, string):
#
#    # This loop is inefficient enough that we don't overrun the keyboard input
#    # buffer when pushing scancodes to the VM.
#    for letter in string:
#        scancode=char2scancode(letter)
#        _keyboard_push_scancode(vm_name, scancode)

#-------------------------------------------------------------------------------
# Conditional sleeping
#-------------------------------------------------------------------------------

#def conditional_sleep(seconds):
    # Don't sleep if we are just faking it for wbatch
#    if do_build:
#        sleep(seconds)
#    sleep(seconds)

#    if wbatch:
#        wbatch_sleep(seconds)

#-------------------------------------------------------------------------------
# Networking
#-------------------------------------------------------------------------------

def get_host_network_config():
    with open(os.path.join(conf.config_dir, "openstack")) as cfg:
        for line in cfg:
            # Parse lines looking like this: NETWORK_1="mgmt 10.0.0.0"
            ma = re.match(r'NETWORK_(\d+)=[\'"](\S+)\s+([\.\d]+)', line)
            if ma:
                name = ma.group(2)
                address = ma.group(3)
                # Network order matters, so put them into an array
                conf.networks.append((name, address))
                #print("Network %s: %s" % (name, address))

def get_node_netif_config(vm_name):
    print("get_node_netif_config not implemented.")


def network_to_gateway(network_address):
    ma = re.match(r'(\d+\.\d+.\d+\.)\d+', network_address)
    if ma:
        gw_address = ma.group(1) + '1'
    else:
        raise Exception
    return gw_address


def create_host_networks():
    if conf.do_build and not conf.leave_vms_running:
        vm.stop_running_cluster_vms()

    get_host_network_config()

    if conf.wbatch:
        wbatch.wbatch_begin_hostnet()
    cnt = 0

    # Iterate over values (IP addresses)
    for (net_name, net_address) in conf.networks:
        print("Creating {} network: {}.".format(net_name, net_address))
        gw_address = network_to_gateway(net_address)
        if conf.do_build:
            iface = vm.create_network(gw_address)
        else:
            # TODO use a generator (yield) here
            # If we are here only for wbatch, ignore actual network interfaces;
            # just return a vboxnetX identifier (so it can be replaced with the
            # interface name used by Windows).
            iface = "vboxnet{}".format(cnt)
        cnt += 1
        if conf.wbatch:
            wbatch.wbatch_create_hostnet(gw_address, iface)


    if conf.wbatch:
        wbatch.wbatch_end_file()

def configure_node_netifs(vm_name):

    get_node_netif_config(vm_name)

    for index, iface in enumerate(conf.vm[vm_name].net_ifs):
        if iface["typ"] == "dhcp":
            vm.vm_nic_base(vm_name, iface, index)
        elif iface["typ"] == "manual":
            vm.vm_nic_std(vm_name, iface, index)
        elif iface["typ"] == "static":
            vm.vm_nic_std(vm_name, iface, index)
        else:
            print("ERROR Unknown interface type: %s" % iface.typ)
            raise ValueError
