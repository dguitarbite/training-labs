# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import logging
import os
import time

import subprocess
import sys

import stacktrain.config.general as conf

import stacktrain.core.helpers as hf

def get_osbash_private_key():
    key_path = os.path.join(conf.lib_dir, "osbash-ssh-keys", "osbash_key")
    if os.path.isfile(key_path):
        mode = os.stat(key_path).st_mode & 0o777
        if mode != 0o400:
            logging.warning("Adjusting permissions for key file (0400):\n\t%s",
                            key_path)
            os.chmod(key_path, 0o400)
    else:
        logging.error("Key file not found at:\n\t%s", key_path)
        sys.exit(1)
    return key_path

# Copy files or directories to VM (incl. implied directories; HOME is
# osbash_dir)
def vm_scp_to_vm(vm_name, *args):

    # XXX do we need show_stderr = kwargs.pop('show_stderr', True)
    key_path = get_osbash_private_key()

    #print("Copying to VM {}.".format(vm_name))
    for src_path in args:
        target_path = hf.strip_top_dir(conf.top_dir, src_path)

        target_dir = os.path.dirname(target_path)
        if not target_dir:
            target_dir = '.'

        vm_ssh(vm_name, "mkdir", "-p", target_dir)

        try:
            full_target = "{}@{}:{}".format(conf.vm_shell_user, conf.vm[vm_name].ssh_ip, target_path)
            subprocess.check_output(["scp", "-q", "-r",
                          "-i", key_path,
                          "-o", "UserKnownHostsFile=/dev/null",
                          "-o", "StrictHostKeyChecking=no",
                          "-P", str(conf.vm[vm_name].ssh_port),
                          src_path, full_target])
        except subprocess.CalledProcessError as err:
            print("ERROR while copying from\n\t%s\n\tto\n\t%s" %
                  (src_path, full_target))
            print("\trc={}: {}".format(err.returncode, err.output))
            sys.exit(1)

def vm_ssh(vm_name, *args, **kwargs):
    key_path = get_osbash_private_key()

    live_log = kwargs.pop('log_file', None)

    try:
        target = "{}@{}".format(conf.vm_shell_user, conf.vm[vm_name].ssh_ip)

        logging.debug("#### Target: %s", target)
        logging.debug("#### args: %s", args)
        full_args = ["ssh", "-q",
                     "-i", key_path,
                     "-o", "UserKnownHostsFile=/dev/null",
                     "-o", "StrictHostKeyChecking=no",
                     "-p", str(conf.vm[vm_name].ssh_port),
                     target] + list(args)
        logging.debug("DEBUG ssh %s", full_args)
        with open(os.path.join(conf.log_dir, "ssh.log"), 'a') as logf:
            print(' '.join(full_args), file=logf)
#            logf.write("%s\n" % (' '.join(args)))

        if live_log:
            hf.create_dir(os.path.dirname(live_log))
            with open(live_log, 'a') as live_logf:
                # Some operating systems (e.g., Mac OS X) export locale settings
                # to the target that cause some Python clients to fail. Override
                # with a standard setting (LC_ALL=C).
                ret = subprocess.call(full_args, env={"LC_ALL":"C"},
                                      stderr=subprocess.STDOUT,
                                      stdout=live_logf)
                if ret:
                    # Show error in ssh.log
                    with open(os.path.join(conf.log_dir, "ssh.log"), 'a') as logf:
                        print("\trc={}".format(ret), file=logf)
                    err_msg = "ssh returned status {}.".format(ret)
                    print("\nERROR {}".format(err_msg))

                    # Write error.log
                    err_file = os.path.join(conf.log_dir, "error.log")
                    with open(err_file, "a") as fi:
                        print(err_msg, file=fi)

                    # Indicate error in status dir
                    open(os.path.join(conf.status_dir, "error"), 'a').close()

                    raise EnvironmentError

            output = None
        else:
            try:
                # Some operating systems (e.g., Mac OS X) export locale settings
                # to the target that cause some Python clients to fail. Override
                # with a standard setting (LC_ALL=C).
                output = subprocess.check_output(full_args, env=dict(os.environ, LC_ALL="C"), stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as err:
                with open(os.path.join(conf.log_dir, "ssh.log"), 'a') as logf:
                    print("\trc={}: {}".format(err.returncode, err.output), file=logf)
                raise EnvironmentError

#        output = check_output(["ssh", "-q",
#        "-i", key_path,
#        "-o", "UserKnownHostsFile", "/dev/null",
#        "-o", "StrictHostKeyChecking", "no",
#        "-p", str(conf.vm[vm_name].ssh_port),
#        target] + list(args))
    except subprocess.CalledProcessError as err:
        logging.debug("ERROR ssh %s", full_args)
        logging.debug("ERROR rc %s", err.returncode)
        logging.debug("ERROR output %s", err.output)
        raise EnvironmentError
    return output

def wait_for_ssh(vm_name):
    while True:
        try:
            vm_ssh(vm_name, "exit")
            break
        except EnvironmentError:
            time.sleep(1)


#def ssh_exec_script(vm_name, script_path):
