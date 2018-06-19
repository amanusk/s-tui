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

from s_tui.ComplexBarGraphs import LabeledBarGraph
from s_tui.ComplexBarGraphs import ScalableBarGraph
import logging
logger = logging.getLogger(__name__)


class StuiBarGraph(LabeledBarGraph):

    @staticmethod
    def append_latest_value(values, new_val):

        values.append(new_val)
        return values[1:]

    MAX_SAMPLES = 1000
    SCALE_DENSITY = 5

    def __init__(self, source, color_a, color_b, smooth_a, smooth_b,
                 alert_colors=None, bar_width=1):
        self.source = source
        self.graph_name = self.source.get_source_name()
        self.measurement_unit = self.source.get_measurement_unit()

        self.num_samples = self.MAX_SAMPLES
        self.graph_data = [0] * self.num_samples

        self.color_a = color_a
        self.color_b = color_b
        self.smooth_a = smooth_a
        self.smooth_b = smooth_b

        self.alert_colors = alert_colors
        self.regular_colors = [color_a, color_b, smooth_a, smooth_b]

        self.satt = None

        x_label = []
        y_label = []

        w = ScalableBarGraph(['bg background', color_a, color_b])
        super(StuiBarGraph, self).__init__(
            [w, x_label, y_label, self.graph_name + ' [' +
             self.measurement_unit + ']'])
        self.bar_graph.set_bar_width(bar_width)

        self.color_counter = 0

    def get_current_summary(self):
        pass

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
        except (ZeroDivisionError):
            logging.debug("Side lable creation divided by 0")
            return ""

    def set_smooth_colors(self, smooth):
        if smooth:
            self.satt = {(1, 0): self.smooth_a, (2, 0): self.smooth_b}
        else:
            self.satt = None
        self.bar_graph.set_segment_attributes(
            ['bg background', self.color_a, self.color_b], satt=self.satt)

    def set_regular_colors(self):
        self.color_a = self.regular_colors[0]
        self.color_b = self.regular_colors[1]
        self.smooth_a = self.regular_colors[2]
        self.smooth_b = self.regular_colors[3]
        if self.satt:
            self.satt = {(1, 0): self.smooth_a, (2, 0): self.smooth_b}
        self.bar_graph.set_segment_attributes(
            ['bg background', self.color_a, self.color_b], satt=self.satt)

    def set_alert_colors(self):
        self.color_a = self.alert_colors[0]
        self.color_b = self.alert_colors[1]
        self.smooth_a = self.alert_colors[2]
        self.smooth_b = self.alert_colors[3]
        if self.satt:
            self.satt = {(1, 0): self.smooth_a, (2, 0): self.smooth_b}
        self.bar_graph.set_segment_attributes(
            ['bg background', self.color_a, self.color_b], satt=self.satt)

    def update_displayed_graph_data(self):
        if not self.get_is_available():
            return

        # NOTE setting edge trigger causes overhead
        try:
            if self.source.get_edge_triggered():
                self.set_alert_colors()
            else:
                self.set_regular_colors()
        except (NotImplementedError):
            pass

        l = []

        current_reading = self.source.get_reading()
        logging.info("Reading " + str(current_reading))
        data_max = self.source.get_maximum()
        self.graph_data = self.append_latest_value(
            self.graph_data, current_reading)

        # Get the graph width (dimension 1)
        num_displayed_bars = self.bar_graph.get_size()[1]
        # print num_displayed_bars
        # Iterage over all the information in the graph
        if self.color_counter % 2 == 0:
            for n in range(self.MAX_SAMPLES - num_displayed_bars,
                           self.MAX_SAMPLES):
                value = round(self.graph_data[n], 1)
                # toggle between two bar types
                if n & 1:
                    l.append([0, value])
                else:
                    l.append([value, 0])
        else:
            for n in range(self.MAX_SAMPLES - num_displayed_bars,
                           self.MAX_SAMPLES):
                value = round(self.graph_data[n], 1)
                if n & 1:
                    l.append([value, 0])
                else:
                    l.append([0, value])
        self.color_counter += 1

        self.bar_graph.set_data(l, float(data_max))
        y_label_size = self.bar_graph.get_size()[0]
        s = self.get_label_scale(0, float(data_max), float(y_label_size))
        self.set_y_label(s)

    def reset(self):
        self.graph_data = [0] * self.num_samples

    def get_summary(self):
        pass
