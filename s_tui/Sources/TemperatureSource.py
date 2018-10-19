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

import psutil
# import os
from s_tui.Sources.Source import Source

import logging
logger = logging.getLogger(__name__)

count = -3


class TemperatureSource(Source):
    THRESHOLD_TEMP = 80
    DEGREE_SIGN = u'\N{DEGREE SIGN}'

    def __init__(self, custom_temp=None, temp_thresh=None):
        Source.__init__(self)

        self.max_temp = 10
        self.measurement_unit = 'C'
        self.last_temp = 0
        self.temp_thresh = self.THRESHOLD_TEMP
        logging.debug("arg temp  " + str(custom_temp))
        self.custom_temp = custom_temp
        self.is_available = True

        self.available_sensors = []
        sensors_dict = dict()
        try:
            sensors_dict = psutil.sensors_temperatures()
        except (AttributeError, IOError):
            logging.debug("Unable to create sensors dict")
            self.is_available = False
        for key, value in sensors_dict.items():
            sensor_name = key
            for itr in range(len(value)):
                sensor_label = ""
                try:
                    sensor_label = value[itr].label
                    logging.debug("Sensor Label")
                    logging.debug(sensor_label)
                except IndexError:
                    pass

                self.available_sensors.append(sensor_name +
                                              "," + str(itr) +
                                              "," + sensor_label)

        self.max_temp_list = [0] * len(self.available_sensors)
        self.last_temp_list = [0] * len(self.available_sensors)

        # Set temperature threshold if a custom one is set
        if temp_thresh is not None:
            if int(temp_thresh) > 0:
                self.temp_thresh = int(temp_thresh)
                logging.debug("Updated custom threshold to " +
                              str(self.temp_thresh))

        self.update()

        self.is_available = len(sensors_dict) == 0
        logging.debug("Update is updated to " + str(self.update))

    def update(self):
        sample = psutil.sensors_temperatures()
        for sensor_id, sensor in enumerate(sample):
            for minor_sensor_id, minor_sensor in enumerate(sample[sensor]):
                sensor_stui_id = sensor_id + minor_sensor_id
                self.last_temp_list[sensor_stui_id] = minor_sensor.current
                self.max_temp_list[sensor_stui_id] = \
                    max(self.max_temp_list[sensor_stui_id],
                        minor_sensor.current)

    def get_reading_list(self):
        return self.last_temp_list

    def get_maximum_list(self):
        return self.max_temp_list

    def get_is_available(self):
        return self.is_available

    def get_edge_triggered(self):
        return self.last_temp > self.temp_thresh

    def get_max_triggered(self):
        return self.max_temp > self.temp_thresh

    def get_summary(self):
        return {'Cur Temp': '%.1f %s' %
                (self.last_temp, self.get_measurement_unit()),
                'Max Temp': '%.1f %s' %
                (self.max_temp, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Temperature'

    def get_sensor_name(self):
        sensors_info = self.custom_temp.split(",")
        sensor_major = sensors_info[0]
        sensor_minor = sensors_info[1]
        return sensor_major + " " + sensor_minor

    def get_sensor_list(self):
        return self.available_sensors

    def reset(self):
        self.max_temp = 1
        # self.cur_temp = 1

    def get_measurement_unit(self):
        return self.measurement_unit

    def set_source(self, source):
        self.custom_temp = source
        return

    def get_pallet(self):
        return 'temp light', \
               'temp dark', \
               'temp light smooth', \
               'temp dark smooth'

    def get_alert_pallet(self):
        return 'high temp light', 'high temp dark', \
               'high temp light smooth', 'high temp dark smooth'
