#!/usr/bin/env python

# Copyright (C) 2017-2026 Alex Manuskin, Maor Veitsman
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
"""RaplPowerSource is a s-tui Source, used to gather power usage
information
"""

from __future__ import annotations

import logging
import time

from s_tui.sources.rapl_read import get_power_reader
from s_tui.sources.source import Source


class RaplPowerSource(Source):
    MICRO_JOULE_IN_JOULE = 1000000.0

    def __init__(self):
        Source.__init__(self)

        self.name = "Power"
        self.measurement_unit = "W"
        self.pallet = (
            "power light",
            "power dark",
            "power light smooth",
            "power dark smooth",
        )

        self.reader = get_power_reader()
        if not self.reader:
            self.is_available = False
            logging.debug("Power reading is not available")
            return

        self.last_probe_time = time.time()
        self.last_probe = self.reader.read_power()
        self.max_power = 1
        self.last_measurement = [0.0] * len(self.last_probe)

        multi_sensors = []
        for item in self.last_probe:
            name = item.label
            sensor_count = multi_sensors.count(name)
            multi_sensors.append(name)
            name += "," + str(sensor_count)
            self.available_sensors.append(name)

    def update(self) -> None:
        if not self.is_available:
            return
        if self.reader is None:
            logging.warning("RAPL reader is not initialized")
            return
        try:
            current_measurement_value = self.reader.read_power()
        except OSError as e:
            logging.warning("Failed to read RAPL power: %s", e)
            return

        if not current_measurement_value:
            logging.warning("RAPL read_power() returned empty or None")
            return

        current_measurement_time = time.time()
        seconds_passed = current_measurement_time - self.last_probe_time

        if seconds_passed <= 0:
            logging.warning(
                "Non-positive time delta between RAPL measurements: %s",
                seconds_passed,
            )
            return

        for m_idx, _ in enumerate(self.last_probe):
            try:
                joule_used = (
                    current_measurement_value[m_idx].current
                    - self.last_probe[m_idx].current
                ) / float(self.MICRO_JOULE_IN_JOULE)

                logging.debug("seconds passed %s", seconds_passed)
                watts_used = float(joule_used) / float(seconds_passed)
                logging.debug("watts used %s", watts_used)
                logging.info(
                    "Joule_Used %f, seconds passed, %f", joule_used, seconds_passed
                )

                if watts_used > 0:
                    # The information on joules used elapses every once in a
                    # while, this might lead to negative readings.
                    # To prevent this, we keep the last value until the next
                    # update
                    self.last_measurement[m_idx] = watts_used
                    logging.info("Power reading elapsed")
            except (IndexError, AttributeError) as e:
                logging.warning("Error reading RAPL sensor %d: %s", m_idx, e)

        self.last_probe = current_measurement_value
        self.last_probe_time = current_measurement_time

    def get_maximum(self) -> float:
        return self.max_power

    def get_top(self) -> int:
        return 1
