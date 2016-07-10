#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

from time import sleep

import os
import re
import sys


import stacktrain.config.general as conf
import stacktrain.core.helpers as hf
import stacktrain.core.cond_sleep as cs
import stacktrain.batch_for_windows as wb

from subprocess import check_output, CalledProcessError
import subprocess




def vbm(*args, **kwargs):
    # wbatch parameter can override config.wbatch setting
    wbatch = kwargs.pop('wbatch', conf.wbatch)
    if wbatch:
        wb.wbatch_log_vbm(args)

    # FIXME caller expectations: where should stderr go (console, logfile)
    show_stderr = kwargs.pop('show_stderr', True)
    if show_stderr:
        errout = None
    else:
        errout = subprocess.STDOUT

    vbm_exe = "VBoxManage"

    call_args = [vbm_exe] + list(args)

    with open(os.path.join(conf.log_dir, "vbm.log"), 'a') as logf:
        #logf.write("%s %s\n" % (vbm_exe, ' '.join(args)))
        if conf.do_build:
            logf.write("%s\n" % (' '.join(args)))
        else:
            logf.write("(not executed) %s\n" % (' '.join(args)))
            return
        #logf.write("%s\n" % (call_args))

    try:
#        output = check_output(call_args, stderr=subprocess.STDOUT)
        output = check_output(call_args, stderr=errout)
    except CalledProcessError as err:
        print("WARN", vbm_exe, *args)
        print("WARN kwargs: ", kwargs)
        print("WARN rc: ", err.returncode)
        print("WARN output:\n", err.output)
        print("WARN -------------------------------------------\n", err.output)
        raise EnvironmentError

    return output


#-------------------------------------------------------------------------------
# VM status
#-------------------------------------------------------------------------------

def vm_exists(vm_name):
    output = vbm("list", "vms", wbatch=False)
    return True if re.search('"' + vm_name + '"', output) else False

def vm_is_running(vm_name):
    output = vbm("showvminfo", "--machinereadable", vm_name, wbatch=False)
    return True if re.search(r'VMState="running"', output) else False

def vm_wait_for_shutdown(vm_name):
    if conf.wbatch:
        wb.wbatch_wait_poweroff(vm_name)

    if not conf.do_build:
        return

    print("Machine shutting down.", end='')
    cond = re.compile(r'="poweroff"')
    while True:
        try:
            output = vbm("showvminfo", "--machinereadable", vm_name,
                         wbatch=False)
        except EnvironmentError:
            print("RLX Ignoring exception.")
            # VBoxManage returns error status while the machine is shutting
            # down
            pass
        else:
            if cond.search(output):
                break
        print('.', end='')
        sleep(1)
    print("\nMachine powered off.")

def vm_power_off(vm_name):
    if vm_is_running(vm_name):
        print("Powering off VM ", vm_name)
        vbm("controlvm", vm_name, "poweroff")
    # VirtualBox VM needs a break before taking new commands
    cs.conditional_sleep(1)

def vm_acpi_shutdown(vm_name):
    if vm_is_running(vm_name):
        print("Shutting down VM  %s." % vm_name)
        vbm("controlvm", vm_name, "acpipowerbutton")
    # VirtualBox VM needs a break before taking new commands
    cs.conditional_sleep(1)

# Shut down all VMs in group VM_GROUP
def stop_running_cluster_vms():
    # Get VM ID from a line looking like this:
    # "My VM" {0a13e26d-9543-460d-82d6-625fa657b7c4}
    output = vbm("list", "runningvms")
    if not output:
        return
    for runvm in output.splitlines():
        mat = re.match(r'".*" {(\S+)}', runvm)
        if mat:
            vm_id = mat.group(1)
            output = vbm("showvminfo", "--machinereadable", vm_id)
            for line in output.splitlines():
                if re.match('groups="/{}'.format(conf.vm_group), line):
                    vm_acpi_shutdown(vm_id)

#-------------------------------------------------------------------------------
# Host-only network functions
#-------------------------------------------------------------------------------

#def network_to_gateway(network_address):
#    ma = re.match(r'(\d+\.\d+.\d+\.)\d+', network_address)
#    if ma:
#        gw_address = ma.group(1) + '1'
#    else:
#        raise Exception
#    return gw_address

def ip_to_net_address(ip):
    ma = re.match(r'(\d+\.\d+.\d+\.)\d+', ip)
    if ma:
        host_net_address = ma.group(1) + '0'
    else:
        raise Exception
    return host_net_address


def hostonlyif_in_use(if_name):
    output = vbm("list", "-l", "runningvms", wbatch=False)
    return re.search("NIC.*Host-only Interface '{}'".format(if_name), output, flags=re.MULTILINE)


def ip_to_hostonlyif(ip):
    net_address = ip_to_net_address(ip)

    if not conf.do_build:
        # Add placeholders for wbatch code
        for index, iface in enumerate(conf.networks):
            if iface[1] == net_address:
                if_name = "vboxnet{}".format(index)
                print("IFACE", iface, index, if_name)
                return if_name

    output = vbm("list", "hostonlyifs", wbatch=False)
    host_net_address = None

    for line in output.splitlines():

        ma = re.match(r"Name:\s+(\S+)", line)
        if ma:
            if_name = ma.group(1)
            continue

        ma = re.match(r"IPAddress:\s+(\S+)", line)
        if ma:
            host_ip = ma.group(1)
            host_net_address = ip_to_net_address(host_ip)

        if host_net_address == net_address:
            return if_name

def create_hostonlyif():
    output = vbm("hostonlyif", "create", wbatch=False)
    # output is something like "Interface 'vboxnet3' was successfully created"
    ma = re.search(r"^Interface '(\S+)' was successfully created", output, flags=re.MULTILINE)
    if ma:
        if_name = ma.group(1)
    else:
        print("Host-only interface creation failed.")
        raise Exception
    return if_name

def fake_hostif():
    if not hasattr(fake_hostif, "cnt"):
        fake_hostif.cnt = 0
    else:
        fake_hostif.cnt += 1
    return "vboxnet{}".format(fake_hostif.cnt)
#    if [ "${NET_IFNAME[0]:-""}" = "" ]; then
#        numifs=0
#    else
#        numifs=${#NET_IFNAME[@]}
#    fi
#    NET_IFNAME[index]="vboxnet${numifs}"

def create_network(ip_address):
    # The host-side interface is the default gateway of the network
    #local if_ip=${NET_GW[index]}

    # If we are here only for wbatch, ignore actual network interfaces; just
    # return a vboxnetX identifier (so it can be replaced with the interface
    # name used by Windows).
#    if not conf.do_build:
#        fake_hostif()
#        return

    if_name = ip_to_hostonlyif(ip_address)

    if if_name:
        if hostonlyif_in_use(if_name):
            print("Host-only interface %s (%s) is in use. Using it, too." %
                  (if_name, ip_address))
        # else: TODO destroy network if not in use?
    else:
        print("Creating host-only interface.")
        if_name = create_hostonlyif()

    print("Configuring host-only network with gateway address %s (%s)."% (ip_address, if_name))
    vbm("hostonlyif", "ipconfig", if_name,
        "--ip", ip_address,
        "--netmask", "255.255.255.0",
        wbatch=False)
    return if_name
    #NET_IFNAME[index]=$if_name

#-------------------------------------------------------------------------------
# VM create and configure
#-------------------------------------------------------------------------------

def vm_mem(vm_config):
    try:
        mem = vm_config.vm_mem
    except AttributeError:
        # Default RAM allocation is 512 MB per VM
        mem = 512

    vbm("modifyvm", vm_config.vm_name, "--memory", str(mem))


def vm_cpus(vm_config):
    try:
        cpus = vm_config.cpus
    except AttributeError:
        # Default RAM allocation is 512 MB per VM
        cpus = 1

    vbm("modifyvm", vm_config.vm_name, "--cpus", str(cpus))


def vm_port(vm_name, desc, hostport, guestport):
    natpf1_arg = "{},tcp,127.0.0.1,{},,{}".format(desc, hostport, guestport)
    vbm("modifyvm", vm_name, "--natpf1", natpf1_arg)


def vm_nic_base(vm_name, iface, index):
    # We start counting interfaces at 0, but VirtualBox starts NICs at 1
    nic = index + 1
    vbm("modifyvm", vm_name,
        "--nictype{}".format(nic), "virtio",
        "--nic{}".format(nic), "nat")


def vm_nic_std(vm_name, iface, index):
    # We start counting interfaces at 0, but VirtualBox starts NICs at 1
    nic = index + 1
    hostif = ip_to_hostonlyif(iface["ip"])
    vbm("modifyvm", vm_name,
        "--nictype{}".format(nic), "virtio",
        "--nic{}".format(nic), "hostonly",
        "--hostonlyadapter{}".format(nic), hostif,
        "--nicpromisc{}".format(nic), "allow-all")


def vm_create(vm_config):
    vm_name = vm_config.vm_name

    if conf.wbatch:
        wb.wbatch_abort_if_vm_exists(vm_name)

    if conf.do_build:
        wbatch_tmp = conf.wbatch
        conf.wbatch = False
        vm_delete(vm_name)
        conf.wbatch = wbatch_tmp

    vbm("createvm", "--name", vm_name, "--register",
        "--ostype", conf.vbox_ostype, "--groups", "/" + conf.vm_group)

    if conf.do_build:
        output = vbm("showvminfo", "--machinereadable", vm_name, wbatch=False)
        if re.search(r'longmode="off"', output):
            print("Nodes run 32-bit OS, enabling PAE.")
            vbm("modifyvm", vm_name, "--pae", "on")

    vbm("modifyvm", vm_name, "--rtcuseutc", "on")
    vbm("modifyvm", vm_name, "--biosbootmenu", "disabled")
    vbm("modifyvm", vm_name, "--largepages", "on")
    vbm("modifyvm", vm_name, "--boot1", "disk")

    # Enough ports for three disks
    vbm("storagectl", vm_name, "--name", "SATA", "--add", "sata", "--portcount",
        str(3))
    vbm("storagectl", vm_name, "--name", "SATA", "--hostiocache", "on")
    vbm("storagectl", vm_name, "--name", "IDE", "--add", "ide")

    print("Created VM %s." % vm_name)

#-------------------------------------------------------------------------------
# VM unregister, remove, delete
#-------------------------------------------------------------------------------

def vm_unregister_del(vm_name):
    print("Unregistering and deleting VM:", vm_name)
    vbm("unregistervm", vm_name, "--delete")


def vm_delete(vm_name):
    print("Asked to delete VM %s " % vm_name, end='')
    if vm_exists(vm_name):
        print("(found)")
        vm_power_off(vm_name)
        hd_path = vm_get_disk_path(vm_name)
        if hd_path:
            print("Disk attached: %s" % hd_path)
            vm_detach_disk(vm_name)
            disk_unregister(hd_path)
            try:
                os.remove(hd_path)
            except OSError:
                # File is probably gone already
                pass
        vm_unregister_del(vm_name)
    else:
        print("(not found)")

#-------------------------------------------------------------------------------

#def disk_delete_child_vms(disk):

#def base_disk_delete():

#-------------------------------------------------------------------------------
# VM shared folders
#-------------------------------------------------------------------------------

def vm_add_share_automount(vm_name, share_dir, share_name):
    vbm("sharedfolder", "add", vm_name,
        "--name", share_name,
        "--hostpath", share_dir,
        "--automount")


def vm_add_share(vm_name, share_dir, share_name):
    vbm("sharedfolder", "add", vm_name,
        "--name", share_name,
        "--hostpath", share_dir)

#-------------------------------------------------------------------------------
# Disk functions
#-------------------------------------------------------------------------------

def get_next_child_disk_uuid(disk):
    if not disk_registered(disk):
        return

    output = vbm("showhdinfo", disk, wbatch=False)

    child_uuid = None

    line = re.search(r'^Child UUIDs:\s+(\S+)$', output, flags=re.MULTILINE)
    try:
        child_uuid = line.group(1)
    except AttributeError:
        # No more child UUIDs
        pass

    return child_uuid

def disk_to_vm(disk):
    output = vbm("showhdinfo", disk, wbatch=False)

    line = re.search(r'^In use by VMs:\s+(\S+)', output, flags=re.MULTILINE)
    try:
        vm_name = line.group(1)
    except AttributeError:
        # No VM attached to disk
        pass
    return vm_name


def disk_to_path(disk):
    output = vbm("showhdinfo", disk, wbatch=False)

    # Note: path may contain whitespace
    line = re.search(r'^Location:\s+(\S.*)$', output, flags=re.MULTILINE)
    try:
        disk_path = line.group(1)
    except AttributeError:
        print("No disk path found for disk {}.".format(disk))
        raise
    return disk_path


#def disk_delete_child_vms(disk):

#def get_base_disk_path():

#def base_disk_exists():

#def base_disk_delete():

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Creating, registering and unregistering disk images with VirtualBox
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def disk_registered(disk):
    """disk can be either a path or a disk UUID"""
    output = vbm("list", "hdds", wbatch=False)
    return re.search(disk, output)


def disk_unregister(disk):
    print("Unregistering disk\n\t%s" % disk)
    vbm("closemedium", "disk", disk)


def create_vdi(path, size):

    # Make sure target directory exists
    hf.create_dir(os.path.dirname(path))

    print("Creating disk (size: %s MB):\n\t%s" % (size, path))
    vbm("createhd",
        "--format", "VDI",
        "--filename", path,
        "--size", str(size))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Attaching and detaching disks from VMs
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def vm_get_disk_path(vm_name):
    output = vbm("showvminfo", "--machinereadable", vm_name, wbatch=False)
    line = re.search(r'^"SATA-0-0"="(.*vdi)"$', output, flags=re.MULTILINE)
    try:
        path = line.group(1)
    except AttributeError:
        print("No disk path found for VM %s." % vm_name)
        path = None
    return path

def vm_detach_disk(vm_name, port=0):
    print("Detaching disk from VM %s." % vm_name)
    vbm("storageattach", vm_name,
        "--storagectl", "SATA",
        "--port", str(port),
        "--device", "0",
        "--type", "hdd",
        "--medium", "none")
    # VirtualBox VM needs a break before taking new commands
    cs.conditional_sleep(1)

def vm_attach_disk(vm_name, disk, port=0):
    """disk can be either a path or a disk UUID"""
    print("Attaching to VM %s:\n\t%s" % (vm_name, disk))
    vbm("storageattach", vm_name,
        "--storagectl", "SATA",
        "--port", str(port),
        "--device", "0",
        "--type", "hdd",
        "--medium", disk)

# disk can be either a path or a disk UUID
def vm_attach_disk_multi(vm_name, disk, port=0):
    vbm("modifyhd", "--type", "multiattach", disk)

    print("Attaching to VM {}:\n\t{}".format(vm_name, disk))
    vbm("storageattach", vm_name,
        "--storagectl", "SATA",
        "--port", str(port),
        "--device", "0",
        "--type", "hdd",
        "--medium", disk)

#------------------------------------------------------------------------------
# VirtualBox guest add-ons
#------------------------------------------------------------------------------

def _vm_attach_guestadd_iso(vm_name, medium):
    print("Attaching medium {} on VM {}.".format(medium, vm_name))
    vbm("storageattach", vm_name,
        "--storagectl", "IDE",
        "--port", "1",
        "--device", "0",
        "--type", "dvddrive",
        "--medium", medium,
        show_stderr=False)


def vm_attach_guestadd_iso(vm_name):
    if conf.wbatch:
        tmp_do_build = conf.do_build
        conf.do_build = False
        _vm_attach_guestadd_iso(vm_name, "emptydrive")
        _vm_attach_guestadd_iso(vm_name, "additions")
        conf.do_build = tmp_do_build
    # Return if we are just faking it for wbatch
    if not conf.do_build:
        return

    if not hasattr(conf, "guestadd_iso") or not conf.guestadd_iso:
        # No location provided, asking VirtualBox for one

        # An existing drive is needed to make additions shortcut work
        # (at least VirtualBox 4.3.12 and below)
        tmp_wbatch = conf.wbatch
        conf.wbatch = False
        _vm_attach_guestadd_iso(vm_name, "emptydrive")
        try:
            _vm_attach_guestadd_iso(vm_name, "additions")
        except Exception:
            # TODO implement search, guessing
            print("No additions found.")
            raise
        conf.wbatch = tmp_wbatch

#------------------------------------------------------------------------------
# Snapshots
#------------------------------------------------------------------------------

def vm_snapshot_list(vm_name):
    if vm_exists(vm_name):
        try:
            output = vbm("snapshot", vm_name, "list", "--machinereadable", show_stderr=False)
        except EnvironmentError:
            # No snapshots
            output = None
    return output


def vm_snapshot_exists(vm_name, shot_name):
    snap_list = vm_snapshot_list(vm_name)
    if snap_list:
        return re.search('SnapshotName.*="{}"'.format(shot_name), snap_list)
    else:
        return False

def vm_snapshot(vm_name, shot_name):
    vbm("snapshot", vm_name, "take", shot_name)

    # VirtualBox VM needs a break before taking new commands
    cs.conditional_sleep(1)

#-------------------------------------------------------------------------------
# Booting a VM
#-------------------------------------------------------------------------------

def vm_boot(vm_name):
    print("Starting VM %s" % vm_name, end='')
    sys.stdout.flush()
    if conf.vm_ui:
        vbm("startvm", vm_name, "--type", conf.vm_ui)
        print(" with %s GUI" % conf.vm_ui, end='')
    else:
        vbm("startvm", vm_name)
    print()
