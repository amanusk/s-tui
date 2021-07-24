#!/usr/bin/env python

# Copyright (C) 2017-2020 Alex Manuskin, Maor Veitsman
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
""" This module reads intel power measurements"""

from __future__ import absolute_import

import logging
import glob
import os
import re
from collections import namedtuple
from multiprocessing import cpu_count
from sys import byteorder
from s_tui.helper_functions import cat


INTER_RAPL_DIR = '/sys/class/powercap/intel-rapl/'
AMD_ENERGY_DIR_GLOB = '/sys/devices/platform/amd_energy.0/hwmon/hwmon*/'
MICRO_JOULE_IN_JOULE = 1000000.0


UNIT_MSR = 0xC0010299
CORE_MSR = 0xC001029A
PACKAGE_MSR = 0xC001029B
ENERGY_UNIT_MASK = 0x1F00


RaplStats = namedtuple('rapl', ['label', 'current', 'max'])


class RaplReader:
    def __init__(self):
        basenames = glob.glob('/sys/class/powercap/intel-rapl:*/')
        self.basenames = sorted(set({x for x in basenames}))

    def read_power(self):
        """ Read power stats and return dictionary"""

        pjoin = os.path.join
        ret = list()
        for path in self.basenames:
            name = None
            try:
                name = cat(pjoin(path, 'name'), fallback=None, binary=False)
            except (IOError, OSError, ValueError) as err:
                logging.warning("ignoring %r for file %r",
                                (err, path), RuntimeWarning)
                continue
            if name:
                try:
                    current = cat(pjoin(path, 'energy_uj'))
                    max_reading = 0.0
                    ret.append(RaplStats(name, float(current), max_reading))
                except (IOError, OSError, ValueError) as err:
                    logging.warning("ignoring %r for file %r",
                                    (err, path), RuntimeWarning)
        return ret

    @staticmethod
    def available():
        return os.path.exists("/sys/class/powercap/intel-rapl")


class AMDEnergyReader:
    def __init__(self):
        self.inputs = list(zip((cat(filename, binary=False) for filename in
                                sorted(glob.glob(AMD_ENERGY_DIR_GLOB +
                                                 'energy*_label'))),
                               sorted(glob.glob(AMD_ENERGY_DIR_GLOB +
                                                'energy*_input'))))

        # How many socket does the system have?
        socket_number = sum(1 for label, _ in self.inputs if 'socket' in label)
        self.inputs.sort(
            key=lambda x: self.get_input_position(x[0], socket_number))

    @staticmethod
    def match_label(label):
        return re.search(r'E(core|socket)([0-9]+)', label)

    @staticmethod
    def get_input_position(label, socket_number):
        num = int(AMDEnergyReader.match_label(label).group(2))
        if 'socket' in label:
            return num
        else:
            return num + socket_number

    def read_power(self):
        ret = []
        for label, inp in self.inputs:
            value = cat(inp)
            ret.append(RaplStats(label, float(value), 0.0))
        return ret

    @staticmethod
    def available():
        return os.path.exists("/sys/devices/platform/amd_energy.0")


class AMDRaplMsrReader:
    def __init__(self):
        self.core_msr_files = {}
        self.package_msr_files = {}
        for i in range(cpu_count()):
            curr_core_id = int(cat("/sys/devices/system/cpu/cpu" + str(i) +
                                   "/topology/core_id", binary=False))
            if curr_core_id not in self.core_msr_files:
                self.core_msr_files[curr_core_id] = "/dev/cpu/" + \
                                                    str(i) + "/msr"

            curr_package_id = int(cat("/sys/devices/system/cpu/cpu" + str(i) +
                                      "/topology/physical_package_id",
                                      binary=False))
            if curr_package_id not in self.package_msr_files:
                self.package_msr_files[curr_package_id] = "/dev/cpu/" + \
                                                          str(i) + "/msr"

    @staticmethod
    def read_msr(filename, register):
        f = open(filename, "rb")
        f.seek(register)
        res = int.from_bytes(f.read(8), byteorder)
        f.close()
        return res

    def read_power(self):
        ret = []
        for i, filename in self.package_msr_files.items():
            unit_msr = self.read_msr(filename, UNIT_MSR)
            energy_factor = 0.5 ** ((unit_msr & ENERGY_UNIT_MASK) >> 8)
            package_msr = self.read_msr(filename, PACKAGE_MSR)
            ret.append(RaplStats("Package " + str(i + 1), package_msr *
                                 energy_factor * MICRO_JOULE_IN_JOULE, 0.0))

        for i, filename in self.core_msr_files.items():
            unit_msr = self.read_msr(filename, UNIT_MSR)
            energy_factor = 0.5 ** ((unit_msr & ENERGY_UNIT_MASK) >> 8)
            core_msr = self.read_msr(filename, CORE_MSR)
            ret.append(RaplStats("Core " + str(i + 1), core_msr * energy_factor
                                 * MICRO_JOULE_IN_JOULE, 0.0))

        return ret

    @staticmethod
    def available():
        cpuinfo = cat("/proc/cpuinfo", binary=False)
        # The reader only supports family 17h CPUs
        m = re.search(r"vendor_id[\s]+: ([A-Za-z]+)", cpuinfo)

        if not m or m is None:
            return False

        if m.group(1) != "AuthenticAMD":
            return False

        m = re.search(r"cpu family[\s]+: ([0-9]+)", cpuinfo)
        if int(m[1]) != 0x17:
            return False

        # with open("/proc/cpuinfo", "rb") as cpuinfo:
        #     all_info = cpuinfo.readlines()
        #     for line in all_info:
        #         if b"vendor_id" in line:
        #             print("Verndor id", line)
        #             if b"AuthenticAMD" not in line:
        #                 return False

        #     for line in all_info:
        #         if b"cpu family" in line:
        #             print("cpu family", line)
        #             m = re.search("cpu family[\s]+: ([0-9]+)", cpuinfo)
        #             if int(m[1]) != 0x17:
        #                 return False

        # Check whether MSRs are available and we have permission to read them
        try:
            open("/dev/cpu/0/msr")
            return True
        except (FileNotFoundError, PermissionError):
            return False


def get_power_reader():
    for ReaderType in (RaplReader, AMDEnergyReader, AMDRaplMsrReader):
        if ReaderType.available():
            return ReaderType()
    return None
