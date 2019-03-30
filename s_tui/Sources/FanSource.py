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

import time
import psutil
from s_tui.Sources.Source import Source
from collections import OrderedDict

import logging
logger = logging.getLogger(__name__)


class FanSource(Source):

    def __init__(self):
        self.fan_speed = 0
        self.max_speed = 1
        self.measurement_unit = 'RPM'
        self.is_available = True

        self.available_sensors = []
        sensors_dict = dict()
        try:
            sensors_dict = psutil.sensors_fans()
        except (AttributeError, IOError):
            logging.debug("Unable to create sensors dict")
            self.is_available = False
            return
        if not sensors_dict:
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

                logging.debug("Fan sensor name " + full_name)

                self.available_sensors.append(full_name)

        self.last_fan_list = [0] * len(self.available_sensors)

        self.update()

    def update(self):
        sample = psutil.sensors_fans()
        for sensor_id, sensor in enumerate(sample):
            for minor_sensor_id, minor_sensor in enumerate(sample[sensor]):
                sensor_stui_id = sensor_id + minor_sensor_id
                self.last_fan_list[sensor_stui_id] = minor_sensor.current

    def get_reading_list(self):
        return self.last_fan_list

    def get_maximum(self):
        return self.max_speed

    def get_is_available(self):
        return self.is_available

    def get_source_name(self):
        return 'Fan'

    def get_sensor_name(self):
        sensors_info = self.custom_temp.split(",")
        sensor_major = sensors_info[0]
        sensor_minor = sensors_info[1]
        return sensor_major + " " + sensor_minor

    def get_sensor_list(self):
        return self.available_sensors

    def get_measurement_unit(self):
        return self.measurement_unit

    def get_summary(self):
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = ''
        for graph_idx, graph_data in enumerate(self.last_fan_list):
            val_str = str(int(graph_data)) + \
                      ' ' + \
                      self.get_measurement_unit()
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary


if '__main__' == __name__:
    fan = FanSource()
    while True:
        print(fan.get_reading())
        time.sleep(2)
