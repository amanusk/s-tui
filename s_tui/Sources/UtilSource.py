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
# from collections import OrderedDict

import time
import logging
import psutil

from s_tui.Sources.Source import Source

logger = logging.getLogger(__name__)


class UtilSource(Source):

    def __init__(self):
        self.is_available = True
        self.last_util_list = [0]

        try:
            self.last_util_list = [0] * psutil.cpu_count()
        except AttributeError:
            logging.debug("cpu_freq is not available from psutil")
            self.is_available = False
            return

        self.update()

        Source.__init__(self)

    def update(self):
        try:
            for core_id, util in enumerate(psutil.cpu_percent(interval=0.0,
                                                              percpu=True)):
                logging.info("Core id" + str(core_id) + " util " + str(util))
                self.last_util_list[core_id] = float(util)
        except AttributeError:
            logging.debug("Cpu Utilization unavailable")
            self.is_available = False
        except ValueError:
            logging.debug("Utilization is not a float")

        logging.info("Utilization recorded " + str(self.last_util_list))

    def get_reading(self):
        return self.last_util_list

    def get_maximum(self):
        return 100

    def get_is_available(self):
        return True

    def get_summary(self):
        return
        # return OrderedDict([
        #     ('CPU Util', '%d %s' % (self.top_freq,
        #                             self.get_measurement_unit()))
        # ])

    def get_source_name(self):
        return 'Utilization'

    def get_measurement_unit(self):
        return '%'

    def get_pallet(self):
        return ('util light',
                'util dark',
                'util light smooth',
                'util dark smooth')


if '__main__' == __name__:
    util = UtilSource()
    while True:
        print(util.get_reading())
        time.sleep(2)
