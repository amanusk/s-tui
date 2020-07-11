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
""" This module implements a Temperature source """

from __future__ import absolute_import

import warnings
import logging
from collections import OrderedDict
import psutil

from s_tui.sources.source import Source


class TempSource(Source):
    """ This class inherits a source and implements a temprature source """
    THRESHOLD_TEMP = 80

    def __init__(self, temp_thresh=None):
        warnings.filterwarnings('ignore', '.*FileNotFound.*',)
        if (not hasattr(psutil, "sensors_temperatures") and
                psutil.sensors_temperatures()):
            self.is_available = False
            logging.debug("cpu temperature is not available from psutil")
            return

        Source.__init__(self)

        self.name = 'Temp'
        self.measurement_unit = 'C'
        self.max_last_temp = 0
        self.pallet = ('temp light', 'temp dark',
                       'temp light smooth', 'temp dark smooth')
        self.alert_pallet = ('high temp light', 'high temp dark',
                             'high temp light smooth', 'high temp dark smooth')

        self.max_temp = 10
        sensors_dict = None
        try:
            sensors_dict = OrderedDict(sorted(
                psutil.sensors_temperatures().items()))
        except IOError:
            logging.debug("Unable to create sensors dict")
            self.is_available = False
            return
        multi_sensors = []
        for key, value in sensors_dict.items():
            sensor_name = "".join(key.title().split(" "))
            for sensor_idx, sensor in enumerate(value):
                sensor_label = sensor.label
                if (sensor.current <= 1.0 or sensor.current >= 127.0):
                    continue

                full_name = ""
                if not sensor_label:
                    full_name = sensor_name + "," + str(sensor_idx)
                else:
                    full_name = ("".join(sensor_label.title().split(" ")))
                    sensor_count = multi_sensors.count(full_name)
                    multi_sensors.append(full_name)
                    full_name += "," + str(sensor_count)

                logging.debug("Temp sensor name %s", full_name)
                self.available_sensors.append(full_name)

        self.last_measurement = [0] * len(self.available_sensors)

        # Set temperature threshold if a custom one is set
        self.temp_thresh = self.THRESHOLD_TEMP
        if temp_thresh is not None:
            if int(temp_thresh) > 0:
                self.temp_thresh = int(temp_thresh)
                logging.debug("Updated custom threshold to %s",
                              self.temp_thresh)

    def update(self):
        sample = OrderedDict(sorted(psutil.sensors_temperatures().items()))
        self.last_measurement = []
        for sensor in sample:
            for minor_sensor in sample[sensor]:
                if (minor_sensor.current <= 1.0 or
                        minor_sensor.current >= 127.0):
                    continue
                self.last_measurement.append(minor_sensor.current)

        if self.last_measurement:
            self.max_last_temp = max(self.last_measurement)
            # Call check for hooks
            Source.update(self)

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
        top_temp = 10
        available_temps = psutil.sensors_temperatures().values()
        for temp in available_temps:
            for temp_minor in temp:
                try:
                    if temp_minor.high > top_temp:
                        top_temp = temp_minor.critical
                except TypeError:
                    continue
        return min(top_temp, 99)
