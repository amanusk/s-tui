#!/usr/bin/env python

# Copyright (C) 2017-2018 Alex Manuskin, Maor Veitsman
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

from collections import OrderedDict
import logging
import psutil

from s_tui.Sources.Source import Source

logger = logging.getLogger(__name__)


class FreqSource(Source):

    def __init__(self):
        Source.__init__(self)

        self.name = 'Frequency'
        self.measurement_unit = 'MHz'
        self.pallet = ('freq light', 'freq dark',
                       'freq light smooth', 'freq dark smooth')

        self.top_freq = -1
        try:
            self.last_measurement = [0] * len(psutil.cpu_freq(True))
        except AttributeError:
            logging.debug("cpu_freq is not available from psutil")
            self.is_available = False
            return

        try:
            # If top freq not available, take the current as top
            if max(self.last_measurement) >= 0 and self.top_freq == -1:
                self.top_freq = max(self.last_measurement)
        except ValueError:
            self.is_available = False

        for core_id, core in enumerate(psutil.cpu_freq(True)):
            self.available_sensors.append("Core " + str(core_id))

    def update(self):
        for core_id, core in enumerate(psutil.cpu_freq(True)):
            self.last_measurement[core_id] = core.current

    def get_maximum(self):
        return self.top_freq

    def get_sensors_summary(self):
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        for graph_idx, graph_data in enumerate(self.last_measurement):
            val_str = str(int(graph_data)) + " " + self.measurement_unit
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary
