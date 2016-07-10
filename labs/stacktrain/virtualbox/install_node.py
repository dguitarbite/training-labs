#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import os

import stacktrain.config.general as conf
import stacktrain.config.virtualbox as cvb

import stacktrain.virtualbox.vm_create as vm
import stacktrain.core.functions_host as host

# TODO this is only init_node, no other code -> rename; also, could vm_init node
# become generic enough for base_disk install?

def vm_init_node(vm_name):

    try:
        vm_config = conf.vm[vm_name]
    except Exception:
        print("Failed to import VM configuration config.vm_%s." % vm_name)
        raise

    vm.vm_create(vm_config)

    vm.vm_mem(vm_config)

    vm.vm_cpus(vm_config)

    host.configure_node_netifs(vm_name)

    if hasattr(conf.vm[vm_name], "ssh_port"):
        vm.vm_port(vm_name, "ssh", conf.vm[vm_name].ssh_port, 22)

    if hasattr(conf.vm[vm_name], "http_port"):
        vm.vm_port(vm_name, "http", conf.vm[vm_name].http_port, 80)

    if conf.wbatch:
        vm.vm_add_share(vm_name, conf.share_dir, conf.share_name)

    vm.vm_attach_disk_multi(vm_name, cvb.get_base_disk_path())

    if hasattr(conf.vm[vm_name], "add_disk"):
        for index, size in enumerate(conf.vm[vm_name].add_disk):
            disk_num = index + 1
            disk_name = "{}-disk{}.vdi".format(vm_name, disk_num)
            disk_path = os.path.join(conf.img_dir, disk_name)
            print("Adding additional disk to {}:\n\t{}".format(vm_name, disk_path))
            vm.create_vdi(disk_path, size)
            vm.vm_attach_disk(vm_name, disk_path, disk_num)

