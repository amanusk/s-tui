#!/usr/bin/env python
#
# Copyright (C) 2017-2018 Alex Manuskin, Gil Tsuker
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

import psutil

import logging
logger = logging.getLogger(__name__)


class GlobalData:
    """
    Global Data on number of CPUs and whether admin permissions were given
    """
    def __init__(self, is_admin):
        self.is_admin = is_admin
        self.num_cpus = 1
        try:
            self.num_cpus = psutil.cpu_count()
            logging.info("num cpus " + str(self.num_cpus))
        except (IOError, OSError) as e:
            logging.debug(e)
