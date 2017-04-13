#!/usr/bin/python2.7

#!/usr/bin/python

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# This function was inspired by a script msr.py written by Andi Kleen
# https://github.com/andikleen/pmu-tools/blob/master/msr.py


""" Reads the value of the msr containing information on Turbo Boost on intel CPUs
"""
import os

def readmsr(msr, cpu = 0):
    if not os.path.exists("/dev/cpu/0/msr"):
        try:
            os.system("/sbin/modprobe msr")
        except:
            pass
        return None
    f = os.open('/dev/cpu/%d/msr' % (cpu,), os.O_RDONLY)
    os.lseek(f, msr, os.SEEK_SET)
    read_res = os.read(f, 8)
    s_decoded = [ord(c) for c in read_res]
    os.close(f)
    m = min(i for i in s_decoded if i > 0)
    return float(m * 100)
