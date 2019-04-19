#!/usr/bin/env python

# Copyright (C) 2017-2019 Alex Manuskin, Maor Veitsman
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

from __future__ import absolute_import

import pynvml as N
from s_tui.sources.source import Source


def _decode(b):
    if isinstance(b, bytes):
        return b.decode()    # for python3, to unicode
    return b


class NVFreqSource(Source):
    """ Source class implementing CPU frequency information polling """
    def __init__(self):
        Source.__init__(self)

        self.name = 'Frequency'
        self.measurement_unit = 'MHz'
        self.pallet = ('freq light', 'freq dark',
                       'freq light smooth', 'freq dark smooth')

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
            temperature = N.nvmlDeviceGetClockInfo(handle, 3)
            self.last_measurement.append(temperature)

    def get_maximum(self):
        return self.top_freq
