#!/usr/bin/env python
#
# Copyright (C) 2017-2020 Alex Manuskin, Gil Tsuker
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
""" This module implements a parent source class for s-tui"""

from collections import OrderedDict
import logging


class Source:
    """ This is a basic source class for s-tui"""
    def __init__(self):
        self.edge_hooks = []
        self.measurement_unit = ''
        self.last_measurement = []
        self.is_available = True
        self.available_sensors = []
        self.name = ''
        self.pallet = ('temp light', 'temp dark',
                       'temp light smooth', 'temp dark smooth')
        self.alert_pallet = None

    def update(self):
        """ Updates the last measurement, invokes hooks if present """
        self.eval_hooks()

    def get_maximum(self):
        """ Returns the maximum measurement as measured so far """
        raise NotImplementedError("Get maximum is not implemented")

    def get_top(self):
        """ Returns higest theoretical value the sensors can reach """
        raise NotImplementedError("get_top is not implemented")

    def get_is_available(self):
        """ Returns is_available """
        return self.is_available

    def reset(self):
        """ Resets source state, e.g. current max """
        raise NotImplementedError("Reset is not implemented")

    def get_sensors_summary(self):
        """ This returns a dict of sensor of the source and their values """
        sub_title_list = self.get_sensor_list()

        graph_vector_summary = OrderedDict()
        for graph_idx, graph_data in enumerate(self.last_measurement):
            val_str = str(round(graph_data, 1))
            graph_vector_summary[sub_title_list[graph_idx]] = val_str

        return graph_vector_summary

    def get_summary(self):
        """ Returns a dict of source name and sensors with their values """
        graph_vector_summary = OrderedDict()
        graph_vector_summary[self.get_source_name()] = (
            '[' + self.measurement_unit + ']')
        graph_vector_summary.update(self.get_sensors_summary())
        return graph_vector_summary

    def get_source_name(self):
        """ Returns source name """
        return self.name

    def get_edge_triggered(self):
        """ Returns true if a measurement was higher than some thershhold"""
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_measurement_unit(self):
        """ Returns measurement unit of source """
        return self.measurement_unit

    def get_pallet(self):
        """ Returns the pallet of the source for graph plotting """
        return self.pallet

    def get_alert_pallet(self):
        """ Returns the 'alert' pallet for graph plotting """
        return self.alert_pallet

    def get_sensor_list(self):
        """ Returns list of a available sensors for source """
        return self.available_sensors

    def get_reading_list(self):
        """ Returns a list of the last measurement """
        return self.last_measurement

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


class MockSource(Source):
    """ Mock class for testing """
    def get_maximum(self):
        return 20

    def get_summary(self):
        return {'MockValue': 5, 'Tahat': 34}

    def get_edge_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")
