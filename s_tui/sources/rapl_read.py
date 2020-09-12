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
from s_tui.helper_functions import cat


INTER_RAPL_DIR = '/sys/class/powercap/intel-rapl/'
AMD_ENERGY_DIR_GLOB = '/sys/devices/platform/amd_energy.0/hwmon/hwmon*/'
MICRO_JOULE_IN_JOULE = 1000000.0

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


def get_power_reader():
    for ReaderType in (RaplReader, AMDEnergyReader):
        if ReaderType.available():
            return ReaderType()
    return None
