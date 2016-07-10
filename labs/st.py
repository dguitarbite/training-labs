#!/usr/bin/env python

"""
Main program for stacktrain.
"""

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import argparse
import importlib
import logging
import os
import sys

import stacktrain.config.general as conf
import stacktrain.batch_for_windows as wbatch

import stacktrain.core.autostart as autostart
import stacktrain.core.node_builder as node_builder
import stacktrain.core.functions_host as host
import stacktrain.core.helpers as hf

#importlib.import_module("stacktrain.config.vm_controller")
#importlib.import_module("stacktrain.config.vm_compute1")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="stacktrain main program.")
    parser.add_argument('-w', '--wbatch', action='store_true',
                        help='Create Windows batch files')
    parser.add_argument('-b', '--build', action='store_true',
                        help='Build cluster on local machine')
    parser.add_argument('-n', '--no-snap-cycle', action='store_true',
                        help='Disable snapshot cycles during build')
    parser.add_argument('-t', '--jump-snapshot', metavar='TARGET_SNAPSHOT',
                        help='Jump to target snapshot and continue build')
    parser.add_argument('-g', '--gui', metavar='GUI_TYPE',
                        help=('GUI type during build (gui, headless, '
                              'vnc [KVM only]'))
    parser.add_argument('target', metavar='TARGET',
                        help="usually basedisk or cluster")
    parser.add_argument('-p', metavar='PROVIDER', nargs='?',
                        help='Either vbox (VirtualBox) or kvm (KVM)')
    parser.add_argument('--verbose', action='store_true')
    return parser.parse_args()

def set_conf_vars(args):
    """Store command line args in configuration variables"""
    if not args.wbatch and not args.build:
        print("Neither -b nor -w given, nothing to do. Exiting.")
        return 1

    if hasattr(args, "provider"):
        conf.provider = args.provider

    if args.gui:
        conf.vm_ui = args.gui

    if os.environ.get('SNAP_CYCLE') == 'no':
        conf.snapshot_cycle = False

    if args.no_snap_cycle:
        conf.snapshot_cycle = False

    if args.jump_snapshot:
        conf.jump_snapshot = args.jump_snapshot

    conf.leave_vms_running = bool(os.environ.get('LEAVE_VMS_RUNNING') == 'yes')

    conf.do_build = args.build
    conf.wbatch = args.wbatch

   # FIXME
    wbatch.init()

def main():
    """Main function"""
    args = parse_args()
    set_conf_vars(args)

    # pylint: disable=W0612
    # Only for the benefit of sfood
    import stacktrain.virtualbox.install_base

    install_base = importlib.import_module("stacktrain.%s.install_base" %
                                           conf.provider)

    print("{} stacktrain start".format(hf.get_timestamp()))

    autostart.autostart_reset()
    hf.clean_dir(conf.log_dir)

    #import stacktrain.virtualbox.storage as storage
    #storage.vm_get_disk_path("base")

    if conf.wbatch:
        wbatch.wbatch_reset()

    logging.info("Calling a function")

    if conf.do_build and install_base.base_disk_exists():
        if args.target == "basedisk":
            print("Basedisk exists. Destroy and recreate? [y/N] ", end='')
            ans = raw_input().lower()
            if ans == 'y':
                print("Deleting existing basedisk.")
                install_base.vm_install_base()
            elif conf.wbatch:
                print("Windows batch file build only.")
                tmp_do_build = conf.do_build
                conf.do_build = False
                install_base.vm_install_base()
                conf.do_build = tmp_do_build
            else:
                print("Nothing to do.")
            print("Done, returning now.")
            return
        elif conf.wbatch:
            print("Windows batch file build only.")
            tmp_do_build = conf.do_build
            conf.do_build = False
            install_base.vm_install_base()
            conf.do_build = tmp_do_build
    else:
        install_base.vm_install_base()

    if args.target == "basedisk":
        print("We are done.")
        return

    host.create_host_networks()

    #if conf.wbatch:
    #    wbatch.wbatch_create_hostnet()

    node_builder.build_nodes("cluster")

if __name__ == "__main__":
    sys.exit(main())
