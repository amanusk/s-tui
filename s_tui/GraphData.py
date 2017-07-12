#!/usr/bin/env python
#
# Copyright (C) 2017 Alex Manuskin, Gil Tsuker
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.


import logging
import os

import psutil

from HelperFunctions import TURBO_MSR
from HelperFunctions import read_msr


class GraphData:
    """
    A class responsible for gathering and storing the data
    """
    THRESHOLD_TEMP = 80
    WAIT_SAMPLES = 5
    MAX_SAMPLES = 1000
    MAX_UTIL = 100
    MAX_TEMP = 100

    def update_data(self):
        self.update_temp()
        self.update_util()
        self.update_freq()

    def update_graph_val(self, values, new_val):

        values.append(new_val)
        return values[1:]

    def __init__(self, is_admin):
        # Constants data
        self.is_admin = is_admin
        self.num_samples = self.MAX_SAMPLES
        # Data for graphs
        self.cpu_util = [0] * self.num_samples
        self.cpu_temp = [0] * self.num_samples
        self.cpu_freq = [0] * self.num_samples
        # Data for statistics
        self.overheat = False
        self.overheat_detected = False
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0
        self.core_num = "N/A"
        try:
            self.core_num = psutil.cpu_count()
        except:
            self.core_num = 1
            logging.debug("Num of cores unavailable")
        self.top_freq = 100
        self.turbo_freq = False

        # Top frequency in case using Intel Turbo Boost
        if self.is_admin:
            try:
                num_cpus = psutil.cpu_count(logical=False)
                available_freq = read_msr(TURBO_MSR, 0)
                logging.debug(available_freq)
                self.top_freq = float(available_freq[num_cpus - 1] * 100)
                self.turbo_freq = True
            except (IOError, OSError) as e:
                logging.debug(e.message)

        if self.top_freq == 100:
            try:
                self.top_freq = psutil.cpu_freq().max
                self.turbo_freq = False
            except:
                logging.debug("Top frequency is not supported")

    def update_util(self):
        try:
            last_value = psutil.cpu_percent(interval=None)
        except:
            last_value = 0
            logging.debug("Cpu Utilization unavailable")

        self.cpu_util = self.update_graph_val(self.cpu_util, last_value)

    def update_freq(self):
        self.samples_taken += 1
        try:
            self.cur_freq = int(psutil.cpu_freq().current)
        except:
            self.cur_freq = 0
            logging.debug("Frequency unavailable")

        self.cpu_freq = self.update_graph_val(self.cpu_freq, self.cur_freq)

        if self.is_admin and self.samples_taken > self.WAIT_SAMPLES:
            self.perf_lost = int(self.top_freq) - int(self.cur_freq)
            if self.top_freq != 0:
                self.perf_lost = (round(float(self.perf_lost) / float(self.top_freq) * 100, 1))
            else:
                self.perf_lost = 0
            if self.perf_lost > self.max_perf_lost:
                self.max_perf_lost = self.perf_lost
        elif not self.is_admin:
            self.max_perf_lost = "N/A (no root)"

    def update_temp(self):
        """
        Read the latest Temperature reading.
        Reading for temperature might be different between systems
        Support for additional systems can be added here
        """
        last_value = 0
        # NOTE: Negative values might not be supported

        # Temperature on most common systems is in coretemp
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['coretemp'][0].current
            except:
                pass
        # Support for specific systems
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['it8622'][0].current
            except:
                pass
        # Raspberry pi 3 running Ubuntu 16.04
        if last_value <= 0:
            try:
                last_value = psutil.sensors_temperatures()['bcm2835_thermal'][0].current
            except:
                pass
        # Raspberry pi + raspiban CPU temp
        if last_value <= 0:
            try:
                last_value = os.popen('cat /sys/class/thermal/thermal_zone0/temp').read()
                last_value = int(last_value) / 1000
            except:
                pass
        # If not relevant sensor found, do not register temperature
        if last_value <= 0:
            logging.debug("Temperature sensor unavailable")

        self.cpu_temp = self.update_graph_val(self.cpu_temp, last_value)
        # Update max temp
        try:
            if last_value > int(self.max_temp):
                self.max_temp = last_value
        except:
            self.max_temp = 0

        # Update current temp
        self.cur_temp = last_value
        try:
            if self.cur_temp >= self.THRESHOLD_TEMP:
                self.overheat = True
                self.overheat_detected = True
            else:
                self.overheat = False
        except:
            self.cur_temp = 0
            self.overheat = False

    # On reset, restore all values to 0 and clear the graph
    def reset(self):
        """Reset all data values to 0"""
        self.overheat = False
        self.cpu_util = [0] * self.num_samples
        self.cpu_temp = [0] * self.num_samples
        self.cpu_freq = [0] * self.num_samples
        self.max_temp = 0
        self.cur_temp = 0
        self.cur_freq = 0
        self.perf_lost = 0
        self.max_perf_lost = 0
        self.samples_taken = 0
        self.overheat_detected = False
