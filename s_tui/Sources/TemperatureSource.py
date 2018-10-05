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
import os
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
        logging.debug("arg temp  " + str(custom_temp))
        self.custom_temp = custom_temp
        self.is_available = True

        # Set update function
        self.update = self.init_update()  # Initial update

        # Set temperature threshold if a custom one is set
        if temp_thresh is not None:
            try:
                if int(temp_thresh) > 0:
                    self.temp_thresh = int(temp_thresh)
                    logging.debug("Updated custom threshold to " +
                                  str(self.temp_thresh))
                else:
                    self.temp_thresh = self.THRESHOLD_TEMP
            except ValueError:
                self.temp_thresh = self.THRESHOLD_TEMP
        else:
            self.temp_thresh = self.THRESHOLD_TEMP
        self.update()
        logging.debug("Update is updated to " + str(self.update))

    # Replace with a function that does the update
    def init_update(self):
        """
        Read the latest Temperature reading.
        Reading for temperature might be different between systems
        Support for additional systems can be added here
        """
        def empty_func():
            """
            emptly func just returns None, in case no valid update
            was availale
            """
            return None

        def update_max_temp(last_value):
            try:
                if int(last_value) > int(self.max_temp):
                    self.max_temp = last_value
            except (ValueError, TypeError):
                # Not 0 to avoid problems with graph creation
                self.max_temp = 1

        def set_threshold(sensor, idx):
            try:
                sample = psutil.sensors_temperatures()
                self.temp_thresh = sample[sensor][0].high
                logging.debug("Temperature threshold set to " +
                              str(self.temp_thresh))
            except(ValueError, TypeError):
                self.temp_thresh = self.THRESHOLD_TEMP

        def update_func(sensor, idx):
            sample = psutil.sensors_temperatures()
            last_value = sample[sensor][idx].current
            update_max_temp(last_value)
            self.last_temp = last_value
            Source.update(self)

        logging.debug("custom temp is " + str(self.custom_temp))
        # Use the manual sensor
        if self.custom_temp is not None:
            logging.debug("Selected custom temp")
            try:
                sensors_info = self.custom_temp.split(",")
                sensor_major = sensors_info[0]
                sensor_minor = sensors_info[1]
                logging.debug("Major " + str(sensor_major) + " Minor " +
                              str(sensor_minor))

                def update():
                    update_func(sensor_major, int(sensor_minor))
                set_threshold(sensor_major, int(sensor_minor))
                return update
            except (KeyError, IndexError, AttributeError):
                self.is_available = False
                logging.debug("Illegal sensor")
                return empty_func

        # Select from possible known sensors
        try:
            sensors = psutil.sensors_temperatures()
            sensor = None
            if 'coretemp' in sensors:
                sensor = 'coretemp'
            elif 'k10temp' in sensors:
                sensor = 'k10temp'
            elif 'it8655' in sensors:
                sensor = 0
            elif 'it8622' in sensors:
                sensor = 'it8622'
            elif 'it8721' in sensors:
                sensor = 'it8721'
            elif 'bcm2835_thermal' in sensors:
                sensor = 'bcm2835_thermal'
            else:
                # Fallback to first in list
                try:
                    chips = list(sensors.keys())
                    sensor = chips[0]
                    logging.debug("Fallback: setting temp sensor " +
                                  str(sensor))
                except (KeyError, IndexError):
                    pass

            if sensor is not None:
                logging.debug("Temperature sensor is set to " + str(sensor))
                set_threshold(sensor, 0)

                def update():
                    update_func(sensor, 0)
                return update
            # If sensors was not found using psutil, try reading file
            else:
                logging.debug("Unable to set sensors with psutil")
                try:
                    thermal_file = '/sys/class/thermal/thermal_zone0/temp'
                    cmd = 'cat ' + thermal_file + ' 2> /dev/null'
                    os.popen(cmd).read()

                    def update():
                        with os.popen(cmd) as temp_file:
                            last_value = temp_file.read()
                            logging.info("Recorded temp " + last_value)
                            try:
                                last_value = int(last_value) / 1000
                            except(ValueError):
                                logging.debug("Thermal zone contains no data")
                                self.is_available = False
                                return empty_func
                            update_max_temp(last_value)
                            self.last_temp = last_value
                            Source.update(self)
                    self.temp_thresh = self.THRESHOLD_TEMP
                    logging.debug("Used thermal zone as file")
                    return update
                except (KeyError):
                    self.is_available = False
                    return empty_func

        except(AttributeError):
            self.is_available = False
            return empty_func

    def get_reading(self):
        return self.last_temp

    def get_maximum(self):
        return self.max_temp

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

    def reset(self):
        self.max_temp = 1
        self.cur_temp = 1

    def get_measurement_unit(self):
        return self.measurement_unit

    def set_source(self, source):
        self.custom_temp = source
        return
