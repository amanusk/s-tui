#!/usr/bin/env python

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

"""ScalableBarGraph Class extends urwid.BarGraph so that
the current size of the bar graph is also obtainable
get_size() - returns the tuple (row, col)
"""

from __future__ import absolute_import

import urwid


class ScalableBarGraph(urwid.BarGraph):
    """Scale the graph acording to screen size"""
    _size = (0, 0)

    def render(self, size, focus=False):
        canvas = super(ScalableBarGraph, self).render(size, focus)
        new_size = (int(canvas.rows()), int(canvas.cols()))
        old_size = self._size
        # check if to raise *on_resize* event
        if new_size != old_size:
            self.on_resize(new_size)
        self._size = new_size
        return canvas

    def calculate_bar_widths(self, size, bardata):
        """
        Return a list of bar widths, one for each bar in data.

        If self.bar_width is None this implementation will stretch
        the bars across the available space specified by maxcol.
        """
        (maxcol, maxrow) = size

        if self.bar_width is not None:
            return [self.bar_width] * min(
                len(bardata), int(maxcol / self.bar_width))

        if len(bardata) >= maxcol:
            return [1] * maxcol

        widths = []
        grow = maxcol
        remain = len(bardata)
        for row in bardata:
            w = int(float(grow) / remain + 0.5)
            widths.append(w)
            grow -= w
            remain -= 1
        return widths

    def get_size(self):
        return self._size

    def on_resize(self, new_size):
        pass  # place folder for any future implantation


class LabeledBarGraph(urwid.Pile):
    """Add option to add lables for X and Y axes """

    def __init__(self, widget_list, focus_item=None):
        if len(widget_list) != 4:
            raise Exception(
                'Must have 3 items for labeled bar graph')
        if not isinstance(widget_list[0], ScalableBarGraph):
            raise Exception(
                'Item 0 must be ScalableBarGraph')
        if not self.check_label(widget_list[1]):
            raise Exception(
                'Item 1 must be a valid label')
        if not self.check_label(widget_list[2]):
            raise Exception(
                'Item 2 must be a valid label')

        self.bar_graph = []
        self.set_graph(widget_list[0])

        self.y_label = urwid.WidgetPlaceholder(urwid.Columns([]))
        self.set_y_label(widget_list[2])

        self.x_label = urwid.WidgetPlaceholder(urwid.Columns([]))
        self.set_x_label(widget_list[1])

        self.title = urwid.WidgetPlaceholder(urwid.ListBox([]))
        self.set_title(widget_list[3])

        super(LabeledBarGraph, self).__init__([
            ('fixed', 0 if len(widget_list[3]) == 0 else 1, self.title),
            self.y_label,
            ('fixed', 0 if len(widget_list[1]) == 0 else 1, self.x_label)
        ], focus_item=focus_item)

    def set_title(self, title):
        if len(title) == 0:
            return

        self.title.original_widget = urwid.ListBox(
            [urwid.Text(title, align="center")])

    def set_x_label(self, x_label):
        if len(x_label) == 0:
            return

        str_x_label = [str(i) for i in x_label]
        x_label_nums = str_x_label[1:]

        x_label_num_list = [urwid.ListBox([urwid.Text('  ' + str_x_label[0])])]

        for num in x_label_nums:
            x_label_num_list = x_label_num_list + \
                [urwid.ListBox([urwid.Text(num)])]
        x_label_num_list[-1] = (1, x_label_num_list[-1])

        self.x_label.original_widget = urwid.Columns(x_label_num_list)

    def set_y_label(self, y_label):
        if len(y_label) == 0:
            return

        str_y_label = [str(i) for i in y_label]
        y_label_nums = str_y_label[1:]
        y_list_walker = [(1, urwid.ListBox([urwid.Text(str_y_label[0])]))]

        for num in y_label_nums:
            y_list_walker = [urwid.ListBox([urwid.Text(num)])] + y_list_walker

        y_list_walker = urwid.Pile(y_list_walker, focus_item=0)
        y_scale_len = len(max(str_y_label, key=len))

        y_notation = [('fixed',  y_scale_len,        y_list_walker),
                      ('weight', 1,                  self.bar_graph)]

        self.y_label.original_widget = urwid.Columns(y_notation,
                                                     dividechars=1)

    def set_graph(self, graph):
        self.bar_graph = graph

    @staticmethod
    def check_label(label):
        if (len(label) >= 2 and not(None in label) or
                len(label) == 0 or label is None):
            return True

        return False
