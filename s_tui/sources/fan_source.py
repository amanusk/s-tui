#!/usr/bin/env python

# Copyright (C) 2017-2020 Alex Manuskin, Maor Veitsman
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
""" This module implements a fan source """


from __future__ import absolute_import

import logging
import psutil
from s_tui.sources.source import Source


class FanSource(Source):
    """ Source for fan information """
    def __init__(self):
        if (not hasattr(psutil, "sensors_fans") and psutil.sensors_fans()):
            self.is_available = False
            logging.debug("Fans sensors is not available from psutil")
            return

        Source.__init__(self)

        self.name = 'Fan'
        self.measurement_unit = 'RPM'
        self.pallet = ('fan light', 'fan dark',
                       'fan light smooth', 'fan dark smooth')

        sensors_dict = dict()
        try:
            sensors_dict = psutil.sensors_fans()
        except IOError:
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

                logging.debug("Fan sensor name %s", full_name)

                self.available_sensors.append(full_name)

        self.last_measurement = [0] * len(self.available_sensors)

    def update(self):
        sample = psutil.sensors_fans()
        self.last_measurement = []
        for sensor in sample.values():
            for minor_sensor in sensor:
                # Ignore unreasonalbe fan speeds
                if (minor_sensor.current > 10000):
                    continue
                self.last_measurement.append(int(minor_sensor.current))

    def get_edge_triggered(self):
        return False

    def get_top(self):
        return 1
