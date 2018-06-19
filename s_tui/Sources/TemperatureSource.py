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
            if int(temp_thresh) > 0:
                self.temp_thresh = int(temp_thresh)
                logging.debug("Updated custom threshold to " + str(self.temp_thresh))
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

        def set_threshold(sensor):
            try:
                self.temp_thresh = sensor.high
                logging.debug("Temperature threshold set to " + str(self.temp_thresh))
            except:
                self.temp_thresh = self.THRESHOLD_TEMP


        logging.debug("custom temp is " + str(self.custom_temp))
        if self.custom_temp is not None:
            # Use the manual sensor
            logging.debug("Selected custom temp")
            try:
                sensors_info = self.custom_temp.split(",")
                sensor_major = sensors_info[0]
                sensor_minor = sensors_info[1]
                logging.debug("Major " + str(sensor_major) + "Minor " + str(sensor_minor))
                sensor = psutil.sensors_temperatures()[sensor_major][int(sensor_minor)]
                def update():
                    sensors_info = self.custom_temp.split(",")
                    sensor_major = sensors_info[0]
                    sensor_minor = sensors_info[1]
                    last_value = psutil.sensors_temperatures()[sensor_major][int(sensor_minor)].current
                    update_max_temp(last_value)
                    self.last_temp = last_value
                    Source.update(self)
                set_threshold(sensor)
                return update
            except (KeyError, IndexError, AttributeError):
                self.is_available = False
                logging.debug("Illegal sensor")
                return empty_func

        # Update for most Intel systems
        try:
            sensor = psutil.sensors_temperatures()['coretemp'][0]
            def update():
                last_value = psutil.sensors_temperatures()['coretemp'][0].current
                # Update max temp
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            # Try set high temp for trigger
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
            pass
        # Support for Ryzen 1700X
        try:
            sensor = psutil.sensors_temperatures()['k10temp'][0]
            def update():
                last_value = psutil.sensors_temperatures()['k10temp'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
            pass
        # Support for Ryzen 7 + asus
        try:
            sensor = psutil.sensors_temperatures()['it8655'][0]
            def update():
                last_value = psutil.sensors_temperatures()['it8655'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
                last_value = 0
        # Support for specific systems
        try:
            sensor = psutil.sensors_temperatures()['it8622'][0]
            def update():
                last_value = psutil.sensors_temperatures()['it8622'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
            pass
        try:
            sensor = psutil.sensors_temperatures()['it8721'][0]
            def update():
                last_value = psutil.sensors_temperatures()['it8721'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
            pass
        try:
            sensor = psutil.sensors_temperatures()['bcm2835_thermal'][0]
            def update():
                last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError):
            pass

        # Fall back for most single processor systems
        # Take the first value of the first processor
        try:
            temperatures = psutil.sensors_temperatures()
            chips = list(temperatures.keys())
            sensor = temperatures[chips[0]][0]
            logging.debug("Fallback: setting temp sensor " + str(sensor))
            def update():
                temperatures = psutil.sensors_temperatures()
                chips = list(temperatures.keys())
                sensor = temperatures[chips[0]][0].current
                update_max_temp(last_value)
                self.last_temp = last_value
                Source.update(self)
            set_threshold(sensor)
            return update
        except (KeyError, AttributeError, IndexError):
            pass

        # Fall back for many systems, such as raspberry pi
        try:
            last_value = os.popen(
                'cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
            def update():
                last_value = os.popen(
                    'cat /sys/class/thermal/thermal_zone0/temp 2> /dev/null').read()
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
            return update
        except (KeyError, AttributeError):
            # NOTE:  On the last except: return an empty func
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
