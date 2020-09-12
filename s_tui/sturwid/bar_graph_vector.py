#!/usr/bin/env python

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

from __future__ import absolute_import

from s_tui.sturwid.complex_bar_graph import LabeledBarGraphVector
from s_tui.sturwid.complex_bar_graph import ScalableBarGraph
import logging
import math
logger = logging.getLogger(__name__)


class BarGraphVector(LabeledBarGraphVector):

    @staticmethod
    def append_latest_value(values, new_val):

        values.append(new_val)
        return values[1:]

    MAX_SAMPLES = 300
    SCALE_DENSITY = 5

    def __init__(self,
                 source,
                 regular_colors,
                 graph_count,
                 visible_graph_list,
                 alert_colors=None,
                 bar_width=1):
        self.source = source
        self.graph_count = graph_count
        self.graph_name = self.source.get_source_name()
        self.measurement_unit = self.source.get_measurement_unit()

        self.num_samples = self.MAX_SAMPLES

        self.graph_data = []
        # We must create new instances for each list
        for _ in range(graph_count):
            self.graph_data.append([0] * self.num_samples)

        # Set max to 1 as default
        self.graph_max = 1

        self.color_a = regular_colors[0]
        self.color_b = regular_colors[1]
        self.smooth_a = regular_colors[2]
        self.smooth_b = regular_colors[3]

        if alert_colors:
            self.alert_colors = alert_colors
        else:
            self.alert_colors = regular_colors
        self.regular_colors = regular_colors

        self.satt = None

        y_label = []

        graph_title = self.graph_name + ' [' + self.measurement_unit + ']'
        sub_title_list = self.source.get_sensor_list()

        # create several different instances of salable bar graph
        w = []
        for _ in range(graph_count):
            graph = ScalableBarGraph(['bg background',
                                      self.color_a, self.color_b])
            w.append(graph)

        super(BarGraphVector, self).__init__(
            graph_title, sub_title_list, y_label, w, visible_graph_list)

        for graph in self.bar_graph_vector:
            graph.set_bar_width(bar_width)

        self.color_counter_vector = [0] * graph_count

    def _set_colors(self, colors):
        self.color_a = colors[0]
        self.color_b = colors[1]
        self.smooth_a = colors[2]
        self.smooth_b = colors[3]
        if self.satt:
            self.satt = {(1, 0): self.smooth_a, (2, 0): self.smooth_b}

        for graph in self.bar_graph_vector:
            graph.set_segment_attributes(
                ['bg background', self.color_a, self.color_b], satt=self.satt)

    def get_graph_name(self):
        return self.graph_name

    def get_measurement_unit(self):
        return self.measurement_unit

    def get_is_available(self):
        return self.source.get_is_available()

    def get_label_scale(self, min_val, max_val, size):
        """Dynamically change the scale of the graph (y lable)"""
        if size < self.SCALE_DENSITY:
            label_cnt = 1
        else:
            label_cnt = int(size / self.SCALE_DENSITY)
        try:
            if max_val >= 100:
                label = [int((min_val + i * (max_val - min_val) / label_cnt))
                         for i in range(label_cnt + 1)]
            else:
                label = [round((min_val + i *
                                (max_val - min_val) / label_cnt), 1)
                         for i in range(label_cnt + 1)]
            return label
        except ZeroDivisionError:
            logging.debug("Side label creation divided by 0")
            return ""

    def set_smooth_colors(self, smooth):
        if smooth:
            self.satt = {(1, 0): self.smooth_a, (2, 0): self.smooth_b}
        else:
            self.satt = None

        for graph in self.bar_graph_vector:
            graph.set_segment_attributes(
                ['bg background', self.color_a, self.color_b], satt=self.satt)

    def update(self):
        if not self.get_is_available():
            return

        # NOTE setting edge trigger causes overhead
        try:
            if self.source.get_edge_triggered():
                self._set_colors(self.alert_colors)
            else:
                self._set_colors(self.regular_colors)
        except NotImplementedError:
            pass

        current_reading = self.source.get_reading_list()
        logging.info("Reading %s", current_reading)

        y_label_size_max = 0
        local_top_value = []

        # update visible graph data, and maximum
        for graph_idx, graph in enumerate(self.bar_graph_vector):
            try:
                _ = self.visible_graph_list[graph_idx]
            except IndexError:
                # If a new graph "Appers", append it to visibles
                self.visible_graph_list.append(True)
            bars = []
            if self.visible_graph_list[graph_idx]:
                self.graph_data[graph_idx] = self.append_latest_value(
                    self.graph_data[graph_idx], current_reading[graph_idx])

                # Get the graph width (dimension 1)
                num_displayed_bars = graph.get_size()[1]
                visible_id = self.MAX_SAMPLES - num_displayed_bars - 1

                visible_graph_data = self.graph_data[graph_idx][visible_id:]
                local_top_value.append(max(visible_graph_data))

        update_max = False
        if self.graph_max == 1:
            self.graph_max = self.source.get_top()
            update_max = True

        local_max = math.ceil(max(local_top_value))
        if (local_max > self.graph_max):
            update_max = True
            self.graph_max = local_max

        # update the graph bars
        for graph_idx, graph in enumerate(self.bar_graph_vector):
            bars = []
            if self.visible_graph_list[graph_idx]:

                # Get the graph width (dimension 1)
                num_displayed_bars = graph.get_size()[1]
                # Iterate over all the information in the graph
                if self.color_counter_vector[graph_idx] % 2 == 0:
                    for n in range(self.MAX_SAMPLES - num_displayed_bars,
                                   self.MAX_SAMPLES):
                        value = round(self.graph_data[graph_idx][n], 1)
                        # toggle between two bar types
                        if n & 1:
                            bars.append([0, value])
                        else:
                            bars.append([value, 0])
                else:
                    for n in range(self.MAX_SAMPLES - num_displayed_bars,
                                   self.MAX_SAMPLES):
                        value = round(self.graph_data[graph_idx][n], 1)
                        if n & 1:
                            bars.append([value, 0])
                        else:
                            bars.append([0, value])
                self.color_counter_vector[graph_idx] += 1

                graph.set_data(bars, float(self.graph_max))
                y_label_size_max = max(y_label_size_max, graph.get_size()[0])

        self.set_y_label(self.get_label_scale(0, self.graph_max,
                                              float(y_label_size_max)))
        # Only create new graphs if the maximum has changed
        if update_max:
            self.set_visible_graphs()

    def reset(self):
        self.graph_data = []
        # Like in init, we create new instances for each list
        for _ in range(self.graph_count):
            self.graph_data.append([0] * self.num_samples)
        self.graph_max = 1
