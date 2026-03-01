#!/usr/bin/env python
#
# Copyright (C) 2017-2025 Alex Manuskin, Gil Tsuker
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
"""This module implements a parent source class for s-tui"""

from collections import OrderedDict
import logging

try:
    import psutil
except ImportError:
    psutil = None


class Source:
    """This is a basic source class for s-tui"""

    def __init__(self):
        self.edge_hooks = []
        self.measurement_unit = ""
        self.last_measurement = []
        self.last_thresholds = []
        self.is_available = True
        self.available_sensors = []
        self.sensor_available = []  # Per-sensor availability (True/False)
        self.name = ""
        self.pallet = (
            "temp light",
            "temp dark",
            "temp light smooth",
            "temp dark smooth",
        )
        self.alert_pallet = None

    def update(self):
        """Updates the last measurement, invokes hooks if present"""
        self.eval_hooks()

    def get_maximum(self):
        """Returns the maximum measurement as measured so far"""
        raise NotImplementedError("Get maximum is not implemented")

    def get_top(self):
        """Returns highest theoretical value the sensors can reach"""
        raise NotImplementedError("get_top is not implemented")

    def get_is_available(self):
        """Returns is_available"""
        return self.is_available

    def reset(self):
        """Resets source state, e.g. current max"""
        raise NotImplementedError("Reset is not implemented")

    def get_sensors_summary(self):
        """This returns a dict of sensor of the source and their values"""
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        for graph_idx, sensor_name in enumerate(sub_title_list):
            # Show N/A if sensor is marked unavailable
            if (
                graph_idx < len(self.sensor_available)
                and not self.sensor_available[graph_idx]
            ):
                graph_vector_summary[sensor_name] = "N/A"
            elif graph_idx < len(self.last_measurement):
                val_str = str(round(self.last_measurement[graph_idx], 1))
                graph_vector_summary[sensor_name] = val_str
            else:
                graph_vector_summary[sensor_name] = "N/A"

        return graph_vector_summary

    def get_summary(self):
        """Returns a dict of source name and sensors with their values"""
        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = "[" + self.measurement_unit + "]"
        graph_vector_summary.update(self.get_sensors_summary())
        return graph_vector_summary

    def get_source_name(self):
        """Returns source name"""
        return self.name

    def get_edge_triggered(self):
        """Returns true if a measurement was higher than some thershhold"""
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_measurement_unit(self):
        """Returns measurement unit of source"""
        return self.measurement_unit

    def get_pallet(self):
        """Returns the pallet of the source for graph plotting"""
        return self.pallet

    def get_alert_pallet(self):
        """Returns the 'alert' pallet for graph plotting"""
        return self.alert_pallet

    def get_sensor_list(self):
        """Returns list of a available sensors for source"""
        return self.available_sensors

    def get_reading_list(self):
        """Returns a list of the last measurement"""
        return self.last_measurement

    def get_threshold_list(self):
        """Returns a list of the last threshold values"""
        return self.last_thresholds

    def add_edge_hook(self, hook):
        """
        Add hook to be triggered when the threshold of this Source is surpassed
        """
        if hook is None:
            return

        self.edge_hooks.append(hook)

    def eval_hooks(self):
        """
        Evaluate the current state of this Source and
        invoke any attached hooks if they've been triggered
        """
        logging.debug("Evaluating hooks")
        if self.get_edge_triggered():
            logging.debug("Hook triggered")
            for hook in [h for h in self.edge_hooks if h.is_ready()]:
                logging.debug("Hook invoked")
                hook.invoke()

    @staticmethod
    def _get_online_cpu_ids():
        """Get sorted list of online CPU core IDs using psutil.

        Uses Process.cpu_affinity() which reflects which CPUs are online.
        Available on Linux, Windows, and FreeBSD.
        Returns a sorted list of online core IDs, or None if unavailable.
        """
        if psutil is None:
            return None
        try:
            return sorted(psutil.Process().cpu_affinity())
        except (AttributeError, OSError, psutil.Error):
            return None

    @staticmethod
    def _get_max_cpu_id():
        """Get the highest CPU core ID on the system.

        Combines cpu_count() and cpu_affinity() to detect all cores,
        including offline ones. cpu_count() should return total logical CPUs,
        but cpu_affinity() helps catch cases where higher-numbered cores exist.

        Strategy: Use the maximum of:
        1. cpu_count() - total logical CPUs (should include offline)
        2. max(online_ids) + 1 - ensures we account for all possible core IDs
        """
        if psutil is None:
            return 0
        total = psutil.cpu_count(logical=True) or 0

        # Check cpu_affinity - this gives us the actual online core IDs
        # If max online ID + 1 > cpu_count(), we know there are more cores
        try:
            online_ids = psutil.Process().cpu_affinity()
            if online_ids:
                max_online = max(online_ids)
                # Always use max_online + 1 to ensure we include the highest core
                # even if it's offline (e.g., if cores 0-6 are online, max_online=6,
                # so we need at least 7 cores total, but if core 7 exists offline,
                # cpu_count() should return 8, and max(8, 7) = 8)
                total = max(total, max_online + 1)
        except (AttributeError, OSError, psutil.Error):
            pass

        return total


class MockSource(Source):
    """Mock class for testing"""

    def get_maximum(self):
        return 20

    def get_summary(self):
        return {"MockValue": 5, "Tahat": 34}

    def get_edge_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")
