#!/usr/bin/env python

# Copyright (C) 2017-2020 Alex Manuskin, Gil Tzuker, Maor Veitsman
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
""" This module implements a Nvidia Util source """

from __future__ import absolute_import


import pynvml as N
from s_tui.sources.source import Source
import logging


def _decode(b):
    if isinstance(b, bytes):
        return b.decode()    # for python3, to unicode
    return b


class NVUtilSource(Source):
    """ This class inherits a source and implements a fan source """

    def __init__(self, temp_thresh=None):
        Source.__init__(self)

        self.name = 'Util'
        self.measurement_unit = '%'
        self.pallet = ('util light', 'util dark',
                       'util light smooth', 'util dark smooth')

        device_count = N.nvmlDeviceGetCount()

        for index in range(device_count):
            handle = N.nvmlDeviceGetHandleByIndex(index)
            name = _decode(N.nvmlDeviceGetName(handle))
            self.available_sensors.append(" ".join(str(name).split(" ")[1:]))

        self.last_measurement = [0] * len(self.available_sensors)

    def update(self):
        device_count = N.nvmlDeviceGetCount()
        self.last_measurement = []
        for index in range(device_count):
            handle = N.nvmlDeviceGetHandleByIndex(index)
            util = N.nvmlDeviceGetUtilizationRates(handle).gpu
            self.last_measurement.append(util)

    def get_edge_triggered(self):
        return False

    def get_top(self):
        return 100
