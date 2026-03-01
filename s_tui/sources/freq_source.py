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


class FreqSource(Source):
    """Source class implementing CPU frequency information polling"""

    def __init__(self):
        self.is_available = True
        if not hasattr(psutil, "cpu_freq"):
            self.is_available = False
            logging.debug("cpu_freq is not available from psutil")
            return

        Source.__init__(self)

        self.name = "Frequency"
        self.measurement_unit = "MHz"
        self.pallet = (
            "freq light",
            "freq dark",
            "freq light smooth",
            "freq dark smooth",
        )

        # cpu_freq can raise NotImplementedError if cores are offline at startup
        try:
            per_cpu_freq = psutil.cpu_freq(True)
        except (OSError, IOError, NotImplementedError):
            per_cpu_freq = None

        try:
            overall_freq = psutil.cpu_freq(False)
        except (OSError, IOError, NotImplementedError):
            overall_freq = None

        total_cores = self._get_max_cpu_id()
        if per_cpu_freq and len(per_cpu_freq) > total_cores:
            total_cores = len(per_cpu_freq)

        self.top_freq = overall_freq.max if overall_freq else 0.0
        self.max_freq = self.top_freq

        self.available_sensors = ["Avg"]
        for core_id in range(total_cores):
            self.available_sensors.append("Core " + str(core_id))

        self.last_measurement = [0.0] * len(self.available_sensors)
        self.sensor_available = [True] * len(self.available_sensors)

        # Mark offline cores as unavailable from the start
        online_ids = self._get_online_cpu_ids()
        if online_ids is not None:
            online_set = set(online_ids)
            for core_id in range(total_cores):
                if core_id not in online_set:
                    self.sensor_available[core_id + 1] = False

        if self.top_freq == 0.0 and max(self.last_measurement) >= 0:
            self.max_freq = max(self.last_measurement)

    def update(self):
        try:
            per_cpu_freq = psutil.cpu_freq(True)
        except (OSError, IOError, AttributeError, NotImplementedError) as e:
            logging.debug("cpu_freq() raised %s: %s", type(e).__name__, e)
            # cpu_freq fails entirely when cores are offline — mark all N/A
            for i in range(1, len(self.sensor_available)):
                self.sensor_available[i] = False
            return

        if not per_cpu_freq:
            return

        online_ids = self._get_online_cpu_ids()

        if online_ids is None:
            # No cpu_affinity — direct index mapping
            freqs = [f.current for f in per_cpu_freq]
            valid = [f for f in freqs if f > 0]
            avg = sum(valid) / len(valid) if valid else 0.0
            self.last_measurement = [avg] + freqs
            return

        # psutil drops offline cores and shifts indices, so
        # per_cpu_freq[i] belongs to online_ids[i], not to core i.
        # A frequency of 0 means the core reported no useful data.
        freq_by_core = {}
        for core_id, freq_obj in zip(online_ids, per_cpu_freq):
            if freq_obj.current > 0:
                freq_by_core[core_id] = freq_obj.current

        num_cores = len(self.available_sensors) - 1  # index 0 is "Avg"
        online_freqs = []

        for core_id in range(num_cores):
            if core_id in freq_by_core:
                self.last_measurement[core_id + 1] = freq_by_core[core_id]
                online_freqs.append(freq_by_core[core_id])
                self.sensor_available[core_id + 1] = True
            else:
                # Offline or 0 freq — stale value stays in last_measurement
                self.sensor_available[core_id + 1] = False

        self.last_measurement[0] = (
            sum(online_freqs) / len(online_freqs) if online_freqs else 0.0
        )

    def get_maximum(self):
        return self.max_freq

    def get_top(self):
        logging.debug("Returning top %s", self.top_freq)
        return self.top_freq
