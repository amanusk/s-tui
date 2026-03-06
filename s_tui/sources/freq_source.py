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

from __future__ import annotations

import logging
import os

import psutil

from s_tui.sources.source import Source

SYSFS_THERMAL_THROTTLE = "/sys/devices/system/cpu/cpu{}/thermal_throttle"


def _read_throttle_count(core_id: int, counter: str) -> int | None:
    """Read a thermal_throttle counter from sysfs. Returns None if unavailable."""
    path = os.path.join(SYSFS_THERMAL_THROTTLE.format(core_id), counter)
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


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
        self.alert_pallet = (
            "freq throttle light",
            "freq throttle dark",
            "freq throttle light smooth",
            "freq throttle dark smooth",
        )

        # cpu_freq can raise NotImplementedError if cores are offline at startup
        try:
            per_cpu_freq = psutil.cpu_freq(True)
        except (OSError, NotImplementedError):
            per_cpu_freq = None

        try:
            overall_freq = psutil.cpu_freq(False)
        except (OSError, NotImplementedError):
            overall_freq = None

        total_cores = self._get_total_core_count()
        if per_cpu_freq and len(per_cpu_freq) > total_cores:
            total_cores = len(per_cpu_freq)

        self.top_freq = overall_freq.max if overall_freq else 0.0
        self.max_freq = self.top_freq

        self.available_sensors = ["Avg"]
        for core_id in range(total_cores):
            self.available_sensors.append("Core " + str(core_id))

        self.last_measurement = [0.0] * len(self.available_sensors)
        self.sensor_available = [True] * len(self.available_sensors)
        # Per-sensor thresholds: None = no alert, 0.0 = any positive reading triggers alert
        self.last_thresholds: list[float | None] = [None] * len(self.available_sensors)

        self._mark_offline_cores(total_cores, self._get_online_cpu_ids())

        if self.top_freq == 0.0 and max(self.last_measurement) >= 0:
            self.max_freq = max(self.last_measurement)

        # Throttle detection state
        self._prev_core_throttle: list[int | None] = [None] * total_cores
        self._prev_pkg_throttle: int | None = None
        self._core_throttled: list[bool] = [False] * total_cores
        self._pkg_throttled: bool = False
        self._throttle_available = self._init_throttle_counters(total_cores)

    def _init_throttle_counters(self, total_cores: int) -> bool:
        """Initialize throttle counter baselines. Returns True if sysfs is available."""
        any_available = False
        for core_id in range(total_cores):
            count = _read_throttle_count(core_id, "core_throttle_count")
            if count is not None:
                self._prev_core_throttle[core_id] = count
                any_available = True

        pkg_count = _read_throttle_count(0, "package_throttle_count")
        if pkg_count is not None:
            self._prev_pkg_throttle = pkg_count
            any_available = True

        return any_available

    def _update_throttle_state(self) -> None:
        """Check sysfs throttle counters for changes since last poll."""
        if not self._throttle_available:
            return

        for core_id in range(len(self._core_throttled)):
            count = _read_throttle_count(core_id, "core_throttle_count")
            prev = self._prev_core_throttle[core_id]
            self._core_throttled[core_id] = (
                count is not None and prev is not None and count > prev
            )
            if count is not None:
                self._prev_core_throttle[core_id] = count
            # Threshold 0.0 triggers alert colors for any positive reading
            throttled = self._core_throttled[core_id] or self._pkg_throttled
            self.last_thresholds[core_id + 1] = 0.0 if throttled else None

        pkg_count = _read_throttle_count(0, "package_throttle_count")
        prev_pkg = self._prev_pkg_throttle
        self._pkg_throttled = (
            pkg_count is not None and prev_pkg is not None and pkg_count > prev_pkg
        )
        if pkg_count is not None:
            self._prev_pkg_throttle = pkg_count

        # Re-evaluate thresholds now that _pkg_throttled is known
        any_throttled = any(self._core_throttled) or self._pkg_throttled
        self.last_thresholds[0] = 0.0 if any_throttled else None
        if self._pkg_throttled:
            for core_id in range(len(self._core_throttled)):
                self.last_thresholds[core_id + 1] = 0.0

    def update(self) -> None:
        try:
            per_cpu_freq = psutil.cpu_freq(True)
        except (OSError, AttributeError, NotImplementedError) as e:
            logging.debug("cpu_freq() raised %s: %s", type(e).__name__, e)
            for i in range(1, len(self.sensor_available)):
                self.sensor_available[i] = False
            return

        if not per_cpu_freq:
            return

        # cpu_freq(percpu=True) uses direct index mapping -- per_cpu_freq[i]
        # corresponds to Core i. Offline cores report current=0.0.
        num_cores = len(self.available_sensors) - 1  # index 0 is "Avg"
        online_freqs = []

        for core_id in range(num_cores):
            if core_id < len(per_cpu_freq) and per_cpu_freq[core_id].current > 0:
                self.last_measurement[core_id + 1] = per_cpu_freq[core_id].current
                online_freqs.append(per_cpu_freq[core_id].current)
                self.sensor_available[core_id + 1] = True
            else:
                self.sensor_available[core_id + 1] = False

        self.last_measurement[0] = (
            sum(online_freqs) / len(online_freqs) if online_freqs else 0.0
        )

        self._update_throttle_state()

    def _format_measurement(self, value: float) -> str:
        return str(int(value))

    def get_edge_triggered(self) -> bool:
        return False

    def get_sensor_suffixes(self) -> list[str]:
        suffixes = [""] * len(self.available_sensors)
        if any(self._core_throttled):
            suffixes[0] = "Tc"
        elif self._pkg_throttled:
            suffixes[0] = "Tp"
        for core_id in range(len(self._core_throttled)):
            idx = core_id + 1
            if idx < len(suffixes) and self.sensor_available[idx]:
                if self._core_throttled[core_id]:
                    suffixes[idx] = "Tc"
                elif self._pkg_throttled:
                    suffixes[idx] = "Tp"
        return suffixes

    def get_sensor_alerts(self) -> list[str | None]:
        alerts: list[str | None] = [None] * len(self.available_sensors)
        any_throttled = any(self._core_throttled) or self._pkg_throttled
        if any_throttled:
            alerts[0] = "throttle txt"
        for core_id in range(len(self._core_throttled)):
            idx = core_id + 1
            if (
                idx < len(alerts)
                and self.sensor_available[idx]
                and (self._core_throttled[core_id] or self._pkg_throttled)
            ):
                alerts[idx] = "throttle txt"
        return alerts

    def get_maximum(self) -> float:
        return self.max_freq

    def get_top(self) -> float:
        logging.debug("Returning top %s", self.top_freq)
        return self.top_freq
