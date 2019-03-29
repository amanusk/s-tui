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
""" RaplPowerSource is a s-tui Source, used to gather power usage
information
"""

from __future__ import absolute_import

import time
import logging
from collections import OrderedDict

from s_tui.Sources.Source import Source
# from Source import Source
from s_tui.Sources.rapl_read import rapl_read

LOGGER = logging.getLogger(__name__)


class RaplPowerSource(Source):

    MICRO_JOULE_IN_JOULE = 1000000.0

    def __init__(self):
        self.is_available = True
        self.last_measurement_time = time.time()
        self.last_measurement_value = rapl_read()
        if not self.last_measurement_value:
            self.is_available = False
            logging.debug("Power reading is not available")
            return
        self.max_power = 1
        self.last_watts_list = [0] * len(self.last_measurement_value)

        self.available_sensors = []
        for item in self.last_measurement_value:
            self.available_sensors.append(item.label)

        self.update()

    # Source super class implementation
    def get_is_available(self):
        return self.is_available

    def update(self):
        if not self.is_available:
            return
        current_measurement_value = rapl_read()
        current_measurement_time = time.time()

        for m_idx, _ in enumerate(self.last_measurement_value):
            joule_used = ((current_measurement_value[m_idx].current -
                           self.last_measurement_value[m_idx].current) /
                          float(self.MICRO_JOULE_IN_JOULE))
            self.last_measurement_value[m_idx] = joule_used

            seconds_passed = (current_measurement_time -
                              self.last_measurement_time)
            logging.debug("seconds passed " + str(seconds_passed))
            watts_used = float(joule_used) / float(seconds_passed)
            logging.debug("watts used " + str(watts_used))
            logging.info("Joule_Used %d, seconds passed, %d", joule_used,
                         seconds_passed)

            if watts_used > 0:
                # The information on joules used elapses every once in a while,
                # this might lead to negative readings.
                # To prevent this, we keep the last value until the next update
                self.last_watts_list[m_idx] = watts_used
                logging.info("Power reading elapsed")

        self.last_measurement_value = current_measurement_value
        self.last_measurement_time = current_measurement_time

    def get_reading_list(self):
        return self.last_watts_list

    def get_maximum(self):
        return self.max_power

    def reset(self):
        self.max_power = 1
        self.last_watts_list = [0] * len(self.last_measurement_value)

    def get_summary(self):
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = ''
        for graph_idx, graph_data in enumerate(self.last_watts_list):
            val_str = str(round(graph_data, 2)) + \
                      ' ' + \
                      self.get_measurement_unit()
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary

    def get_sensor_list(self):
        return self.available_sensors

    def get_source_name(self):
        return 'Power'

    def get_measurement_unit(self):
        return 'W'

    def get_pallet(self):
        return ('power light',
                'power dark',
                'power light smooth',
                'power dark smooth')


if __name__ == '__main__':
    RAPL = RaplPowerSource()
    while True:
        print(RAPL.update())
        time.sleep(2)
