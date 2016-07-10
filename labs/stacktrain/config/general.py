from __future__ import print_function

from os.path import dirname, join, realpath
import re

do_build = False
wbatch = False

vm = {}
# Network order matters, put the in an array
networks = []

top_dir = dirname(dirname(dirname(realpath(__file__))))

img_dir = join(top_dir, "img")
log_dir = join(top_dir, "log")
status_dir = join(log_dir, "status")

osbash_dir = join(top_dir, "osbash")
config_dir = join(top_dir, "config")
scripts_dir = join(top_dir, "scripts")
autostart_dir = join(top_dir, "autostart")
lib_dir = join(top_dir, "lib")

# FIXME make ssh, shared_folder, all work with combinations of -b and -w
#vm_access = "ssh"
vm_access = "ssh"

openstack_release = "mitaka"
snapshot_cycle = True

provider = "virtualbox"

vm_shell_user = "osbash"

# FIXME virtualbox-only

# override default (base-vm_access-openstack_release-distro)
#base_disk_name = "mydisk"

# Base disk size in MB
base_disk_size = 10000

# FIXME redundancy (also in stacktrain/distros/ubuntu_14...)
install_iso = join(img_dir, "ubuntu-14.04.4-server-amd64.iso")
distro_release = "14.04-server-amd64"
distro = "ubuntu"

#base_install_scripts = "scripts.ubuntu_base"

def get_base_disk_name():
    return "base-{}-{}-{}-{}".format(vm_access, openstack_release, distro,
                                     distro_release)


class VMconfig:

    def __init__(self, vm_name):
        self.vm_name = vm_name
        self.net_ifs = []
        import os
        with open(os.path.join(config_dir, "config." + vm_name)) as cfg_f:
            for line in cfg_f:
                self.parse_cfg_line(line)

        if provider == "virtualbox":
            self.ssh_ip = "127.0.0.1"

    def parse_cfg_line(self, line):
        ma = re.search(r"^VM_SSH_PORT=(\d+)", line)
        if ma:
            self.ssh_port = int(ma.group(1))

        ma = re.search(r"^VM_WWW_PORT=(\d+)", line)
        if ma:
            self.http_port = int(ma.group(1))
            print("Adding second disk", self.http_port, type(self.http_port))

        ma = re.search(r"^VM_MEM=(\d+)", line)
        if ma:
            self.vm_mem = int(ma.group(1))

        ma = re.search(r"^VM_CPUS=(\d+)", line)
        if ma:
            self.vm_cpus = int(ma.group(1))

        ma = re.search(r"^NET_IF_(\d+)=(.+)", line)
        if ma:
            self.netif = int(ma.group(1))
            self.parse_net_line(ma.group(2))

        ma = re.search(r"^SECOND_DISK_SIZE=(\d+)", line)
        if ma:
            self.add_disk = []
            self.add_disk.append(int(ma.group(1)))

        ma = re.search(r"^THIRD_DISK_SIZE=(\d+)", line)
        if ma:
            self.add_disk.append(int(ma.group(1)))


    def parse_net_line(self, line):
        self.net_ifs.append({})

        # Remove quotation marks (if any)
        ma = re.search(r"(?P<quote>['\"])(.+)(?P=quote)", line)
        if ma:
            line = ma.group(2)

        if re.match(r"dhcp$", line):
            self.net_ifs[-1]["typ"] = "dhcp"
        elif re.match(r"static", line):
            ma = re.match(r"static\s+(\S+)", line)
            self.net_ifs[-1]["typ"] = "static"
            self.net_ifs[-1]["ip"] = ma.group(1)
        elif re.match(r"manual", line):
            ma = re.match(r"manual\s+(\S+)", line)
            self.net_ifs[-1]["typ"] = "manual"
            self.net_ifs[-1]["ip"] = ma.group(1)
        else:
            print("Can't parse line:", line)
            import sys
            sys.exit(1)

