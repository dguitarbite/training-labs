# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import time
import os
from os.path import basename, isfile, join
import re
import sys

from glob import glob

import stacktrain.config.general as conf
import stacktrain.core.ssh as ssh
import stacktrain.batch_for_windows as wbatch
import stacktrain.core.functions_host as host
import stacktrain.core.helpers as hf
import stacktrain.virtualbox.install_node as inst_node
import stacktrain.virtualbox.vm_create as vm


def ssh_exec_script(vm_name, script_path):
    ssh.vm_scp_to_vm(vm_name, script_path)

    remote_path = hf.strip_top_dir(conf.top_dir, script_path)

    print("{} start {}".format(hf.get_timestamp(), remote_path), end='')
    sys.stdout.flush()

    script_name = os.path.splitext(os.path.basename(script_path))[0]
    prefix = host.get_next_prefix(conf.log_dir, "auto")
    log_path = os.path.join(conf.log_dir, "{}_{}.auto".format(prefix, script_name))
    try:
        ssh.vm_ssh(vm_name,
                   "bash {} && rm -vf {}".format(remote_path, remote_path),
                   log_file=log_path)
    except EnvironmentError:
        print("ERROR script {}".format(script_name))
        sys.exit()

    print("\n{}  done".format(hf.get_timestamp()))
    sys.stdout.flush()


def ssh_process_autostart(vm_name):
    print("x\nWaiting for ssh server in VM %s to respond at %s:%s." %
          (vm_name, conf.vm[vm_name].ssh_ip, conf.vm[vm_name].ssh_port), end='')
    sys.stdout.flush()
    ssh.wait_for_ssh(vm_name)
    print("connected.")
    sys.stdout.flush()

    ssh.vm_ssh(vm_name, "rm -rf osbash lib config autostart}")
    ssh.vm_scp_to_vm(vm_name, conf.lib_dir, conf.config_dir)

    for script_path in sorted(glob(join(conf.autostart_dir, "*.sh"))):
        #print("ssh_process_autostart: ", script_path)
        ssh_exec_script(vm_name, script_path)
        os.remove(script_path)

    open(join(conf.status_dir, "done"), 'a').close()

#-------------------------------------------------------------------------------
# Autostart mechanism
#-------------------------------------------------------------------------------

def autostart_reset():
    hf.clean_dir(conf.autostart_dir)
    hf.clean_dir(conf.status_dir)


def process_begin_files():
    for begin_file in sorted(glob(join(conf.status_dir, "*.sh.begin"))):
        match = re.match(r'.*/(.*).begin', begin_file)
        os.remove(begin_file)
        print("\nVM processing %s." % match.group(1), end='')


def autofiles_processing_done():
    return isfile(join(conf.status_dir, "done")) or isfile(join(conf.status_dir, "error"))


def wait_for_autofiles():
    if conf.wbatch:
        wbatch.wbatch_wait_auto()

    if not conf.do_build:
        # Remove autostart files and return if we are just faking it for wbatch
        autostart_reset()
        return

    sys.stdout.flush()

    while not autofiles_processing_done():
#        # TODO does this work if conf.do_build=False ?
        if conf.wbatch:
            process_begin_files()
        print('x', end='')
        sys.stdout.flush()
        time.sleep(1)

    # Check for remaining *.sh.begin files
    if conf.wbatch:
        process_begin_files()

    if isfile(join(conf.status_dir, "done")):
        os.remove(join(conf.status_dir, "done"))
    else:
        print("ERROR occured. Exiting.")
        sys.exit(1)
    print("Processing of scripts successful.")

    sys.stdout.flush()

def autostart_and_wait(vm_name):
    sys.stdout.flush()

    if not conf.wbatch:
        from multiprocessing import Process
        try:
            sshp = Process(target=ssh_process_autostart, args=(vm_name,))
            sshp.start()
        except Exception:
            print("GOT EXCEPTION for ssh_process_autostart")
            raise

    sys.stdout.flush()
    wait_for_autofiles()

    if not conf.wbatch:
        sshp.join()
        print("SSHP EXITCODE:", sshp.exitcode)
        if sshp.exitcode:
            print("SSHP RETURNED ERROR!")
            raise ValueError


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _autostart_queue(src_rel_path, target_name=None):
    src_path = join(conf.scripts_dir, src_rel_path)
    src_name = basename(src_path)

    if not target_name:
        target_name = src_name

    if target_name.endswith(".sh"):
        prefix = host.get_next_prefix(conf.autostart_dir, "sh", 2)
        target_name = "{}_{}".format(prefix, target_name)

    if src_name == target_name:
        print("\t%s" % src_name)
    else:
        print("\t%s -> %s" % (src_name, target_name))

    from shutil import copyfile

    copyfile(src_path, join(conf.autostart_dir, target_name))
    if conf.wbatch:
        wbatch.wbatch_cp_auto(src_path, join(conf.autostart_dir, target_name))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def autostart_queue_and_rename(src_dir, src_file, target_file):
    _autostart_queue(join(src_dir, src_file), target_file)

def autostart_queue(*args):
    for script in args:
        _autostart_queue(script)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def command_from_config(line):
    # Drop trailing whitespace and newline
    line = line.rstrip()

    # Drop first argument ("cmd")
    args = line.split(" ")[1:]

    if args[0] == "boot":
        if args[1] == "-n":
            vm_name = args[2]
            vm.vm_boot(vm_name)
            autostart_and_wait(vm_name)
        else:
            print("Syntax error.")
    elif args[0] == "snapshot":
        if args[1] == "-n":
            vm_name = args[2]
            shot_name = args[3]
            host.vm_conditional_snapshot(vm_name, shot_name)
        else:
            print("Syntax error.")
    elif args[0] == "shutdown":
        if args[1] == "-n":
            vm_name = args[2]
            vm.vm_acpi_shutdown(vm_name)
            vm.vm_wait_for_shutdown(vm_name)
        else:
            print("Syntax error.")
    elif args[0] == "wait_for_shutdown":
        if args[1] == "-n":
            vm_name = args[2]
            vm.vm_wait_for_shutdown(vm_name)
        else:
            print("Syntax error.")
    elif args[0] == "snapshot_cycle":
        if not conf.snapshot_cycle:
            return
        elif args[1] == "-n":
            vm_name = args[2]
            shot_name = args[3]
            _autostart_queue("shutdown.sh")
            vm.vm_boot(vm_name)
            autostart_and_wait(vm_name)
            vm.vm_wait_for_shutdown(vm_name)
            host.vm_conditional_snapshot(vm_name, shot_name)
        else:
            print("Syntax error.")
    elif args[0] == "create_node":
        if args[1] == "-n":
            vm_name = args[2]
            conf.vm[vm_name] = conf.VMconfig(vm_name)
            inst_node.vm_create_node(vm_name)
        else:
            print("Syntax error.")
    elif args[0] == "queue_renamed":
        if args[1] == "-n":
            vm_name = args[2]
            conf.vm[vm_name] = conf.VMconfig(vm_name)
            autostart_queue_and_rename("osbash", "init_xxx_node.sh",
                                       "init_{}_node.sh".format(vm_name))
        else:
            print("Syntax error.")
    elif args[0] == "queue":
        script_rel_path = args[1]
        _autostart_queue(script_rel_path)
    else:
        print("ERROR Invalid command:", args[0])


# Parse config/scripts.* configuration files
def autostart_from_config(cfg_file):
    cfg_path = join(conf.config_dir, cfg_file)

    if not isfile(cfg_path):
        print("Config file not found:\n\t%s" % cfg_path)
        raise Exception

    # log_autostart_source(cfg_file)

    with open(cfg_path) as cfg:
        for line in cfg:
            if re.match('#', line):
                continue

            if re.match(r"\s?$", line):
                continue

            if not re.match(r"cmd\s", line):
                print("Syntax error in line:\n\t%s" % line)
                raise Exception

            if hasattr(conf, "jump_snapshot") and conf.jump_snapshot:
                ma = re.match(r"cmd\s+snapshot.*\s+(\S)$", line)
                if ma:
                    print("Skipped forward to snapshot %s." % conf.jump_snapshot)
                    del conf.jump_snapshot
                    continue

            command_from_config(line)
