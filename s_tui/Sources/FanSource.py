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

import logging
logger = logging.getLogger(__name__)


class FanSource(Source):

    def __init__(self, custom_fan=None):
        self.fan_speed = 0
        self.max_speed = 1
        self.custom_fan = custom_fan
        self.is_available = True
        self.update()

    def update(self):
        result = 0
        if self.custom_fan is not None:
            try:
                sensors_info = self.custom_fan.split(",")
                sensor_major = sensors_info[0]
                sensor_minor = sensors_info[1]
                logging.debug("Fan Major " + str(sensor_major) +
                              " Fan Minor " + str(sensor_minor))
                result = psutil.sensors_fans()[sensor_major][
                    int(sensor_minor)].current
            except (KeyError, IndexError, ValueError, AttributeError):
                result = 0
                logging.debug("Fan Speend Not Available")
                self.is_available = False
        else:
            try:
                fans = psutil.sensors_fans()
                fan_list = list(fans.keys())
                result = fans[fan_list[0]][0].current
            except (KeyError, IndexError, ValueError, AttributeError):
                result = 0
                logging.debug("Fan Speend Not Available")
                self.is_available = False

        self.fan_speed = float(result)
        if self.fan_speed > self.max_speed:
            self.max_speed = self.fan_speed
        logging.info("Fan speed recorded" + str(self.fan_speed))

    def get_reading(self):
        return self.fan_speed

    def get_maximum(self):
        return self.max_speed

    def get_is_available(self):
        return self.is_available

    def get_summary(self):
        return {'Fan': '%.1f %s' %
                (self.fan_speed, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Fan'

    def get_measurement_unit(self):
        return 'RPM'


if '__main__' == __name__:
    fan = FanSource()
    while True:
        print(fan.get_reading())
        time.sleep(2)
