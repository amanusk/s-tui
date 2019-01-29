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
        self.is_available = True
        self.top_freq = -1
        self.last_freq_list = [0]
        self.samples_taken = 0
        self.stress_started = False

        try:
            self.last_freq_list = [0] * len(psutil.cpu_freq(True))
        except AttributeError:
            logging.debug("cpu_freq is not available from psutil")
            self.is_available = False
            return

        self.update()

        try:
            # If top freq not available, take the current as top
            if max(self.last_freq_list) >= 0 and self.top_freq == -1:
                self.top_freq = max(self.last_freq_list)
        except ValueError:
            self.is_available = False

        Source.__init__(self)

    def update(self):
        for core_id, core in enumerate(psutil.cpu_freq(True)):
            self.last_freq_list[core_id] = core.current

    def get_reading_list(self):
        return self.last_freq_list

    def get_maximum(self):
        return self.top_freq

    def get_is_available(self):
        return self.is_available

    def reset(self):
        self.max_perf_lost = 0

    def set_stress_started(self):
        self.stress_started = True

    def set_stress_stopped(self):
        self.stress_started = False
        self.samples_taken = 0

    def get_sensor_list(self):
        cpu_list = []
        for core_id, core in enumerate(psutil.cpu_freq(True)):
            cpu_list.append("core " + str(core_id))

        return cpu_list

    def get_summary(self):
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = ''
        for graph_idx, graph_data in enumerate(self.last_freq_list):
            val_str = str(int(graph_data)) + \
                      ' ' + \
                      self.get_measurement_unit()
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary

    def get_source_name(self):
        return 'Frequency'

    def get_measurement_unit(self):
        return 'MHz'

    def get_pallet(self):
        return ('freq light',
                'freq dark',
                'freq light smooth',
                'freq dark smooth')
