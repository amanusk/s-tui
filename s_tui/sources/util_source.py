#!/usr/bin/env python

# Copyright (C) 2017-2025 Alex Manuskin, Maor Veitsman
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
        if not hasattr(psutil, "cpu_percent") and psutil.cpu_percent():
            self.is_available = False
            logging.debug("cpu utilization is not available from psutil")
            return

        Source.__init__(self)

        self.name = "Util"
        self.measurement_unit = "%"
        self.pallet = (
            "util light",
            "util dark",
            "util light smooth",
            "util dark smooth",
        )

        total_cores = self._get_max_cpu_id()

        self.available_sensors = ["Avg"]
        for core_id in range(total_cores):
            self.available_sensors.append("Core " + str(core_id))

        self.last_measurement = [0.0] * len(self.available_sensors)
        self.sensor_available = [True] * len(self.available_sensors)

        # Affinity cache — refreshed in update() when online core count changes
        self._cached_online_ids = self._get_online_cpu_ids()
        self._cached_online_len = -1  # force refresh on first update()

        self._mark_offline_cores(total_cores, self._cached_online_ids)

    def update(self):
        try:
            per_cpu = psutil.cpu_percent(interval=0.0, percpu=True)
        except OSError:
            return

        if not per_cpu:
            return

        # Only re-query affinity when the online core count changes
        if len(per_cpu) != self._cached_online_len:
            self._cached_online_ids = self._get_online_cpu_ids()
            self._cached_online_len = len(per_cpu)

        online_ids = self._cached_online_ids

        if online_ids is None:
            # No cpu_affinity (e.g. macOS) — direct index mapping
            avg = sum(per_cpu) / len(per_cpu)
            self.last_measurement = [avg] + [float(v) for v in per_cpu]
            return

        # cpu_percent(percpu=True) drops offline cores and shifts indices,
        # so per_cpu[i] belongs to online_ids[i], not to core i.
        value_by_core = dict(zip(online_ids, per_cpu))
        num_cores = len(self.available_sensors) - 1  # index 0 is "Avg"
        online_values = []

        for core_id in range(num_cores):
            if core_id in value_by_core:
                self.last_measurement[core_id + 1] = float(value_by_core[core_id])
                online_values.append(self.last_measurement[core_id + 1])
                self.sensor_available[core_id + 1] = True
            else:
                self.sensor_available[core_id + 1] = False

        self.last_measurement[0] = (
            sum(online_values) / len(online_values) if online_values else 0.0
        )
        logging.info("Utilization recorded %s", self.last_measurement)

    def get_is_available(self):
        return self.is_available

    def get_top(self):
        return 100
