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
        (maxcol, _) = size

        if self.bar_width is not None:
            return [self.bar_width] * min(
                len(bardata), int(maxcol / self.bar_width))

        if len(bardata) >= maxcol:
            return [1] * maxcol

        widths = []
        grow = maxcol
        remain = len(bardata)
        for _ in bardata:
            w = int(float(grow) / remain + 0.5)
            widths.append(w)
            grow -= w
            remain -= 1
        return widths

    def get_size(self):
        return self._size

    def on_resize(self, new_size):
        pass  # place folder for any future implantation


class LabeledBarGraphVector(urwid.WidgetPlaceholder):
    """Add option to add labels for X and Y axes """

    def __init__(self,
                 title,
                 sub_title_list,
                 y_label,
                 bar_graph_vector,
                 visible_graph_list):
        for bar_graph in bar_graph_vector:
            if not isinstance(bar_graph, ScalableBarGraph):
                raise Exception(
                    'graph vector items must be ScalableBarGraph')
        if not self.check_label(y_label):
            raise Exception(
                'Y label must be a valid label')

        self.visible_graph_list = visible_graph_list
        self.bar_graph_vector = []
        self.set_graph(bar_graph_vector)

        self.y_label_and_graphs = urwid.WidgetPlaceholder(urwid.Columns([]))
        self.y_label = []
        self.set_y_label(y_label)

        list_w = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        self.title = urwid.WidgetPlaceholder(list_w)
        self.sub_title_list = sub_title_list
        self.set_title(title)

        super(LabeledBarGraphVector, self).__init__(urwid.Pile([]))
        self.set_visible_graphs(visible_graph_list)

    def set_title(self, title):
        if not title:
            return
        title_text_w = urwid.Text(title, align="center")
        list_w = urwid.SimpleFocusListWalker([title_text_w])
        self.title.original_widget = urwid.ListBox(list_w)

    def set_y_label(self, y_label):
        if not y_label:
            text = urwid.Text("1")
            pile = urwid.Pile([urwid.ListBox([text])])
            self.y_label = ('fixed', 1, pile)
            return

        str_y_label = [str(i) for i in y_label]
        y_label_nums = str_y_label[1:]
        y_list_walker = [(1, urwid.ListBox([urwid.Text(str_y_label[0])]))]

        for num in y_label_nums:
            y_list_walker = [urwid.ListBox([urwid.Text(num)])] + y_list_walker

        y_list_walker = urwid.Pile(y_list_walker, focus_item=0)
        y_scale_len = len(max(str_y_label, key=len))

        self.y_label = ('fixed', y_scale_len, y_list_walker)

    def set_visible_graphs(self, visible_graph_list=None):
        """Show a column of the graph selected for display"""
        if visible_graph_list is None:
            visible_graph_list = self.visible_graph_list

        vline = urwid.AttrWrap(urwid.SolidFill(u'|'), 'line')

        graph_vector_column_list = []
        for state, graph, sub_title in zip(visible_graph_list,
                                           self.bar_graph_vector,
                                           self.sub_title_list):
            if state:
                text_w = urwid.Text(sub_title, align='center')
                sub_title_widget = urwid.ListBox([text_w])
                graph_a = [('fixed', 1, sub_title_widget),
                           ('weight', 1, graph)]
                graph_and_title = urwid.Pile(graph_a)
                graph_vector_column_list.append(('weight', 1, graph_and_title))
                graph_vector_column_list.append(('fixed', 1, vline))

        # if all sub graph are disabled
        if not graph_vector_column_list:
            self.visible_graph_list = visible_graph_list
            self.original_widget = urwid.Pile([])
            return

        # remove the last vertical line separator
        graph_vector_column_list.pop()

        y_label_a = ('weight', 1, urwid.Columns(graph_vector_column_list))
        y_label_and_graphs = [self.y_label,
                              y_label_a]
        column_w = urwid.Columns(y_label_and_graphs, dividechars=1)
        y_label_and_graphs_widget = urwid.WidgetPlaceholder(column_w)

        init_widget = urwid.Pile([('fixed', 1, self.title),
                                  ('weight', 1, y_label_and_graphs_widget)])

        self.visible_graph_list = visible_graph_list
        self.original_widget = init_widget

    def set_graph(self, graph_vector):
        self.bar_graph_vector = graph_vector

    @staticmethod
    def check_label(label):
        if (len(label) >= 2 and not(None in label) or
                not label or label is None):
            return True

        return False
