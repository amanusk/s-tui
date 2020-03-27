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
from collections import namedtuple
from s_tui.helper_functions import cat


INTER_RAPL_DIR = '/sys/class/powercap/intel-rapl/'
MICRO_JOULE_IN_JOULE = 1000000.0

RaplStats = namedtuple('rapl', ['label', 'current', 'max'])


def rapl_read():
    """ Read power stats and return dictionary"""
    basenames = glob.glob('/sys/class/powercap/intel-rapl:*/')
    basenames = sorted(set({x for x in basenames}))

    pjoin = os.path.join
    ret = list()
    for path in basenames:
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
