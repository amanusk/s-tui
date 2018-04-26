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


class UtilSource(Source):

    def __init__(self):
        self.last_freq = 0
        self.update()

    def update(self):
        result = 0
        try:
            result = float(psutil.cpu_percent(interval=0.0))
        except:
            result = 0
            logging.debug("Cpu Utilization unavailable")

        self.last_freq = float(result)
        logging.info("Utilization recorded " + str(self.last_freq))

    def get_reading(self):
        return self.last_freq

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return True

    def get_summary(self):
        return {'Utilization': '%.1f %s' %
                (self.last_freq, self.get_measurement_unit())}

    def get_source_name(self):
        return 'Utilization'

    def get_measurement_unit(self):
        return '%'


if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
