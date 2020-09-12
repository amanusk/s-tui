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
""" This module implements a Nvidia Fan source """

from __future__ import absolute_import


import pynvml as N
from s_tui.sources.source import Source


def _decode(b):
    if isinstance(b, bytes):
        return b.decode()    # for python3, to unicode
    return b


class NVTempSource(Source):
    """ This class inherits a source and implements a temprature source """
    THRESHOLD_TEMP = 80

    def __init__(self, temp_thresh=None):
        Source.__init__(self)

        self.name = 'Temp'
        self.measurement_unit = 'C'
        self.max_last_temp = 0
        self.pallet = ('temp light', 'temp dark',
                       'temp light smooth', 'temp dark smooth')
        self.alert_pallet = ('high temp light', 'high temp dark',
                             'high temp light smooth', 'high temp dark smooth')

        self.temp_thresh = 80

        device_count = N.nvmlDeviceGetCount()

        for index in range(device_count):
            handle = N.nvmlDeviceGetHandleByIndex(index)
            name = _decode(N.nvmlDeviceGetName(handle))
            self.available_sensors.append(" ".join(str(name).split(" ")[1:]))

        print(self.available_sensors)
        self.last_measurement = [0] * len(self.available_sensors)

    def update(self):
        device_count = N.nvmlDeviceGetCount()
        self.last_measurement = []
        for index in range(device_count):
            handle = N.nvmlDeviceGetHandleByIndex(index)
            temperature = N.nvmlDeviceGetTemperature(handle,
                                                     N.NVML_TEMPERATURE_GPU)
            self.last_measurement.append(temperature)

    def get_edge_triggered(self):
        return self.max_last_temp > self.temp_thresh

    def get_max_triggered(self):
        """ Returns whether the current temperature threshold is exceeded"""
        return self.max_temp > self.temp_thresh

    def reset(self):
        self.max_temp = 10

    def get_maximum(self):
        raise NotImplementedError("Get maximum is not implemented")

    def get_top(self):
        return 100
