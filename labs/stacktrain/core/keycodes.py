#!/usr/bin/env python

# Force Python 2 to use float division even for ints
from __future__ import division
from __future__ import print_function

import stacktrain.virtualbox.keycodes as kc

#-------------------------------------------------------------------------------
# Virtual VM keyboard using keycodes
#-------------------------------------------------------------------------------

def keyboard_send_escape(vm_name):
    kc.keyboard_push_scancode(vm_name, kc.esc2scancode())

def keyboard_send_enter(vm_name):
    kc.keyboard_push_scancode(vm_name, kc.enter2scancode())

# Turn strings into keycodes and send them to target VM
def keyboard_send_string(vm_name, string):

    # This loop is inefficient enough that we don't overrun the keyboard input
    # buffer when pushing scancodes to the VM.
    for letter in string:
        scancode = kc.char2scancode(letter)
        kc.keyboard_push_scancode(vm_name, scancode)
