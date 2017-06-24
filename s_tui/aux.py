#!/usr/bin/env python
#
# Copyright (C) 2017 Alex Manuskin, Gil Tsuker
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


""" Reads the value of the msr containing information on Turbo Boost on intel CPUs
"""
import os
import logging
import signal
import platform
import subprocess
import re

__version__ = "0.2.4"


def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command ="sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in all_info.split("\n"):
            if "model name" in line:
                return re.sub( ".*model name.*:", "", line,1)
    return ""


def read_msr(msr, cpu=0):
    if not os.path.exists("/dev/cpu/0/msr"):
        try:
            os.system("/sbin/modprobe msr")
            logging.debug("Ran modprobe sucessfully")
        except:
            pass
            return None
    msr_file = '/dev/cpu/%d/msr' % (cpu,)
    try:
        with open(msr_file, 'r') as f:
            f.seek(msr)
            read_res = f.read(8)
        s_decoded = [ord(c) for c in read_res]
        return s_decoded
    except IOError as e:
        e.message = e.message + "Unable to read file " + msr_file
        raise e
    except OSError as e:
        e.message = e.message + "File " + msr_file + " does not exist"
        raise e


def kill_child_processes(parent_proc, sig=signal.SIGTERM):
    try:
        for proc in parent_proc.children(recursive=True):
            logging.debug('Killing' + str(proc))
            proc.kill()
        parent_proc.kill()
    except:
        logging.debug('No such process')
