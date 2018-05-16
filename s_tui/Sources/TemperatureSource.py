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
        logging.debug("arg temp  " + str(custom_temp))
        self.custom_temp = custom_temp
        self.is_available = True

        self.update = self.init_update()  # Initial update
        self.update()
        logging.debug("Update is updated to " + str(self.update))
        # If not relevant sensor found, do not register temperature
        if int(self.max_temp) <= 0:
            self.is_available = False
            logging.debug("Temperature sensor unavailable")

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
                self.max_temp = 0

        logging.debug("custom temp is " + str(self.custom_temp))
        if self.custom_temp is not None:
            # Use the manual sensor
            logging.debug("Selected custom temp")
            try:
                sensors_info = self.custom_temp.split(",")
                sensor_major = sensors_info[0]
                sensor_minor = sensors_info[1]
                logging.debug("Major " + str(sensor_major) + "Minor " + str(sensor_minor))
                last_value = psutil.sensors_temperatures()[sensor_major][int(sensor_minor)].current
                def update():
                    sensors_info = self.custom_temp.split(",")
                    sensor_major = sensors_info[0]
                    sensor_minor = sensors_info[1]
                    last_value = psutil.sensors_temperatures()[sensor_major][int(sensor_minor)].current
                    update_max_temp(last_value)
                    self.last_temp = last_value
                    Source.update(self)
                return update
            except (KeyError, IndexError, AttributeError):
                self.is_available = False
                logging.debug("Illegal sensor")
                return empty_func

        # Update for most Intel systems
        try:
            last_value = psutil.sensors_temperatures()['coretemp'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['coretemp'][0].current
                # Update max temp

                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        # Support for Ryzen 1700X
        try:
            last_value = psutil.sensors_temperatures()['k10temp'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['k10temp'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        # Support for Ryzen 7 + asus
        try:
            last_value = psutil.sensors_temperatures()['it8655'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['it8655'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        # Support for specific systems
        try:
            last_value = psutil.sensors_temperatures()['it8622'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['it8622'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        try:
            last_value = psutil.sensors_temperatures()['it8721'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['it8721'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        try:
            last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
            def update():
                last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        # Fall back for many systems, such as raspberry pi
        try:
            last_value = os.popen(
                'cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
            def update():
                last_value = os.popen(
                    'cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
                logging.info("Recorded temp " + last_value)
                last_value = int(last_value) / 1000
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            return update
        except (KeyError, AttributeError):
                last_value = 0
                # NOTE:  On the last except: return an empty func
                return empty_func


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
