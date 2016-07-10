#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

from os.path import join

from subprocess import check_output, CalledProcessError
import subprocess

import stacktrain.batch_for_windows as wb


import stacktrain.config.general as conf

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

    with open(join(conf.log_dir, "vbm.log"), 'a') as logf:
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
