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


class TemperatureSource(Source):

    THRESHOLD_TEMP = 80
    DEGREE_SIGN = u'\N{DEGREE SIGN}'

    def __init__(self, custom_temp=None):
        Source.__init__(self)

        self.max_temp = 0
        self.measurement_unit = 'C'
        self.last_temp = 0
        self.custom_temp = custom_temp
        self.is_available = True

        self.update()  # Initial update
        # If not relevant sensor found, do not register temperature
        if int(self.max_temp) <= 0:
            self.is_available = False
            logging.debug("Temperature sensor unavailable")

    def update(self):
        """
        Read the latest Temperature reading.
        Reading for temperature might be different between systems
        Support for additional systems can be added here
        """
        last_value = 0
        # NOTE: Negative values might not be supported

        # Temperature on most common systems is in coretemp
        last_value = 0
        if self.custom_temp is not None:
            # Use the manual sensor
            try:
                sensors_info = self.custom_temp.split(",")
                sensor_major = sensors_info[0]
                sensor_minor = sensors_info[1]
                logging.debug("Major" + str(sensor_major) + "Minor" + str(sensor_minor))
                last_value = psutil.sensors_temperatures()[sensor_major][int(sensor_minor)].current
            except (KeyError, IndexError, AttributeError):
                self.is_available = False
                logging.debug("Illegal sensor")
                self.last_temp = 1
        else:  # Choose out a list of known sensors
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['coretemp'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
            # Support for Ryzen 1700X
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['k10temp'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
              # Support for Ryzen 7 + asus
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['it8655'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
            # Support for specific systems
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['it8622'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
            # Support for specific systems
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['it8721'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
            # Raspberry pi 3 running Ubuntu 16.04
            if last_value <= 0:
                try:
                    last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
                except (KeyError, AttributeError):
                    last_value = 0
            # Raspberry pi + raspiban CPU temp
            if last_value <= 0:
                try:
                    last_value = os.popen('cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
                    logging.info("Recorded temp " + last_value)
                    last_value = int(last_value) / 1000
                except (ValueError, TypeError):
                    last_value = 0
            # Fall back for most single processor systems
            # Take the first value of the first processor
            if last_value <= 0:
                try:
                    temperatures = psutil.sensors_temperatures()
                    chips = list(temperatures.keys())
                    last_value = temperatures[chips[0]][0].current
                except:
                    last_value = 0

        # Update max temp
        try:
            if int(last_value) > int(self.max_temp):
                self.max_temp = last_value
        except (ValueError, TypeError):
            self.max_temp = 0

        self.last_temp = last_value

        # Run base update routines
        Source.update(self)

    def get_reading(self):
        return self.last_temp

    def get_maximum(self):
        return self.max_temp

    def get_is_available(self):
        return self.is_available

    def get_edge_triggered(self):
        return self.last_temp > self.THRESHOLD_TEMP

    def get_max_triggered(self):
        return self.max_temp > self.THRESHOLD_TEMP

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
