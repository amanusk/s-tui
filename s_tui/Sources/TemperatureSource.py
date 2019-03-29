#!/usr/bin/env python

# Copyright (C) 2017-2019 Alex Manuskin, Gil Tzuker, Maor Veitsman
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

import psutil
from s_tui.Sources.Source import Source
from collections import OrderedDict

import logging
logger = logging.getLogger(__name__)


class TemperatureSource(Source):
    THRESHOLD_TEMP = 80
    DEGREE_SIGN = u'\N{DEGREE SIGN}'

    def __init__(self, temp_thresh=None):
        Source.__init__(self)

        self.max_temp = 10
        self.measurement_unit = 'C'
        self.last_temp = 0
        self.temp_thresh = self.THRESHOLD_TEMP
        self.is_available = True

        self.available_sensors = []
        sensors_dict = dict()
        try:
            sensors_dict = psutil.sensors_temperatures()
        except (AttributeError, IOError):
            logging.debug("Unable to create sensors dict")
            self.is_available = False
            return
        for key, value in sensors_dict.items():
            sensor_name = key
            for sensor_idx, sensor in enumerate(value):
                sensor_label = sensor.label

                full_name = ""
                if not sensor_label:
                    full_name = sensor_name + "," + str(sensor_idx)
                else:
                    full_name = sensor_label

                logging.debug("Temp sensor name " + full_name)

                self.available_sensors.append(full_name)

        # Set temperature threshold if a custom one is set
        if temp_thresh is not None:
            if int(temp_thresh) > 0:
                self.temp_thresh = int(temp_thresh)
                logging.debug("Updated custom threshold to " +
                              str(self.temp_thresh))

        self.update()

    def update(self):
        sample = psutil.sensors_temperatures()
        self.last_temp_list = []
        for sensor_id, sensor in enumerate(sample):
            for minor_sensor_id, minor_sensor in enumerate(sample[sensor]):
                self.last_temp_list.append(minor_sensor.current)

    def get_reading_list(self):
        return self.last_temp_list

    def get_is_available(self):
        return self.is_available

    def get_edge_triggered(self):
        return self.last_temp > self.temp_thresh

    def get_max_triggered(self):
        return self.max_temp > self.temp_thresh

    def get_summary(self):
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = ''
        for graph_idx, graph_data in enumerate(self.last_temp_list):
            val_str = str(int(graph_data)) + \
                      ' ' + \
                      self.get_measurement_unit()
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary

    def get_source_name(self):
        return 'Temp'

    def get_sensor_list(self):
        return self.available_sensors

    def reset(self):
        self.max_temp = 1

    def get_measurement_unit(self):
        return self.measurement_unit

    def get_pallet(self):
        return 'temp light', \
               'temp dark', \
               'temp light smooth', \
               'temp dark smooth'

    def get_alert_pallet(self):
        return 'high temp light', 'high temp dark', \
               'high temp light smooth', 'high temp dark smooth'
