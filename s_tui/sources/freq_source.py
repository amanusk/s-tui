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

from __future__ import absolute_import

import logging
import psutil

from s_tui.sources.source import Source


class FreqSource(Source):
    """ Source class implementing CPU frequency information polling """
    def __init__(self):
        self.is_available = True
        if (not hasattr(psutil, "cpu_freq") and
                psutil.cpu_freq()):
            self.is_available = False
            logging.debug("cpu_freq is not available from psutil")
            return

        Source.__init__(self)

        self.name = 'Frequency'
        self.measurement_unit = 'MHz'
        self.pallet = ('freq light', 'freq dark',
                       'freq light smooth', 'freq dark smooth')

        # Check if psutil.cpu_freq is available.
        # +1 for average frequency
        self.last_measurement = [0] * len(psutil.cpu_freq(True))
        if psutil.cpu_freq(False):
            self.last_measurement.append(0)

        self.top_freq = psutil.cpu_freq().max
        self.max_freq = self.top_freq

        if self.top_freq == 0.0:
            # If top freq not available, take the current as top
            if max(self.last_measurement) >= 0:
                self.max_freq = max(self.last_measurement)

        self.available_sensors = ['Avg']
        for core_id, _ in enumerate(psutil.cpu_freq(True)):
            self.available_sensors.append("Core " + str(core_id))

    def update(self):
        self.last_measurement = [psutil.cpu_freq(False).current]
        for core in psutil.cpu_freq(True):
            self.last_measurement.append(core.current)

    def get_maximum(self):
        return self.max_freq

    def get_top(self):
        logging.debug("Returning top %s", self.top_freq)
        return self.top_freq
