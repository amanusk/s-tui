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

import logging
import psutil

from s_tui.sources.source import Source


class UtilSource(Source):

    def __init__(self):
        Source.__init__(self)

        self.name = 'Util'
        self.measurement_unit = '%'
        self.pallet = ('util light', 'util dark',
                       'util light smooth', 'util dark smooth')

        try:
            self.last_measurement = [0] * psutil.cpu_count()
        except AttributeError:
            logging.debug("cpu_freq is not available from psutil")
            self.is_available = False
            return

        for core_id in range(psutil.cpu_count()):
            self.available_sensors.append("Core " + str(core_id))

    def update(self):
        try:
            for core_id, util in enumerate(psutil.cpu_percent(interval=0.0,
                                                              percpu=True)):
                logging.info("Core id %s util %s", core_id, util)
                self.last_measurement[core_id] = float(util)
        except AttributeError:
            logging.debug("Cpu Utilization unavailable")
            self.is_available = False
        except ValueError:
            logging.debug("Utilization is not a float")

        logging.info("Utilization recorded %s", self.last_measurement)

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return self.is_available
