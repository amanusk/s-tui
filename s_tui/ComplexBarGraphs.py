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
import logging
from math import ceil

logger = logging.getLogger(__name__)


# custom solid canvas, to allow a custum attribute to be apolied
class StuiSolidCanvas(urwid.SolidCanvas):
    """
    A canvas filled completely with a single character.
    """
    def __init__(self, fill_char, cols, rows, attr):
        self.attribute = attr
        super(StuiSolidCanvas, self).__init__(fill_char, cols, rows)

    def content(self, trim_left=0, trim_top=0, cols=None, rows=None, attr=None):
        if cols is None:
            cols = self.size[0]
        if rows is None:
            rows = self.size[1]

        line = [(self.attribute, self._cs, self._text*cols)]
        for i in range(rows):
            yield line


class ScalableBarGraph(urwid.BarGraph):
    """Scale the graph acording to screen size"""
    _size = (0, 0)
    _counter = 0
    _resize = True

    column_canvas_list = []
    first_run = True

    # initlization rendering functino
    # create a list of bars, ready to be created to a canvas
    # this will allow the bar graph to only update 1 bar per render frame
    def render_init(self, size):
        (maxcol, maxrow) = size
        bardata, top, hlines = self.get_data((maxcol, maxrow))

        back_char = self.char[0]

        self.column_canvas_list = []

        # create the empty bars, for the bar columns that do not have data yet
        for no_data in range(maxcol - len(bardata)):
            back_canvas = urwid.SolidCanvas(back_char, 1, maxrow)
            combine_list_item = [(back_canvas, None, False)]

            column_canvas = urwid.CanvasCombine(combine_list_item)

            self.column_canvas_list.append(
                (column_canvas, None, False, 1))

        # for each data point, create a single bar graph
        color_index = 0
        data_value = 0
        for single_bar_data in bardata:
            for pallet_index, value in enumerate(single_bar_data):
                color_index = pallet_index
                data_value = value

                if data_value != 0:
                    break

            self.render_incremental(size, data_value, color_index)

    # incrementally add one single data point to the bar graph
    # this will pop the first element entered to the graph, and insert the new
    # one into the graph
    def render_incremental(self, size, single_bar_data, color_index):
        (maxcol, maxrow) = size
        bardata, top, hlines = self.get_data((maxcol, maxrow))

        pallet_index = 1 + color_index
        data_char = self.char[pallet_index]
        back_char = self.char[0]

        data_value = single_bar_data

        char_cnt_data = 0
        if data_value >= top:
            char_cnt_data = maxrow
        elif data_value > 0:
            char_cnt_data = int(ceil(maxrow * (data_value / top)))
        char_cnt_background = maxrow - char_cnt_data

        back_canvas = StuiSolidCanvas(back_char, 1, char_cnt_background,
                                      self.attr[0])

        # check if higher resolution smooth graph is enabled
        if len(self.satt) is 0:
            data_canvas = StuiSolidCanvas(data_char, 1, char_cnt_data,
                                          self.attr[pallet_index])

            if char_cnt_data == 0:
                combine_list_item = [(back_canvas, None, False)]
            elif char_cnt_background == 0:
                combine_list_item = [(data_canvas, None, False)]
            else:
                combine_list_item = [(back_canvas, None, False),
                                     (data_canvas, None, False)]
        else:
            data_canvas = StuiSolidCanvas(data_char, 1, char_cnt_data - 1,
                                          self.attr[pallet_index])

            last_char_data_span = top / maxrow
            last_char_data_span_eights = last_char_data_span / 8
            last_char_raw_value = char_cnt_data * last_char_data_span
            last_char_bg_value = last_char_raw_value - data_value
            last_char_data_residue = last_char_data_span - last_char_bg_value
            last_char_portion = int(
                round(last_char_data_residue / last_char_data_span_eights)) - 1
            last_char = self.eighths[last_char_portion]

            edge_canvas = StuiSolidCanvas(last_char, 1, 1,
                                          self.satt[(pallet_index, 0)])

            if char_cnt_data == 0:
                combine_list_item = [(back_canvas, None, False)]
            elif char_cnt_background == 0:
                combine_list_item = [(edge_canvas, None, False),
                                     (data_canvas, None, False)]
            else:
                combine_list_item = [(back_canvas, None, False),
                                     (edge_canvas, None, False),
                                     (data_canvas, None, False)]

        column_canvas = urwid.CanvasCombine(combine_list_item)

        self.column_canvas_list.append(
            (column_canvas, None, False, 1))

    def render(self, size, focus=False):
        # detect graph size change
        new_size = (size[1], size[0])  # reverse tuple order to match _size
        old_size = self._size
        resize = new_size != old_size

        (maxcol, maxrow) = size
        bardata = self.get_data((maxcol, maxrow))[0]
        if resize:
            self.render_init(size)
        elif len(bardata) is not 0:

            # get the most recent data
            color_index = 0
            data_value = 0
            for pallet_index, value in enumerate(bardata[-1]):
                color_index = pallet_index
                data_value = value

                if data_value != 0:
                    break

            logging.info("color_index: " + str(color_index))
            logging.info("data_value: " + str(data_value))
            self.render_incremental(size, data_value, color_index)
            self.column_canvas_list.pop(0)

        canvas = urwid.CanvasJoin(self.column_canvas_list)

        self._size = (int(canvas.rows()), int(canvas.cols()))

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
                # this is the urwid BUG "maxcol / self.bar_width"
                # should be "int(maxcol / self.bar_width)"
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
        if len(title) == 0:
            return
        title_text_w = urwid.Text(title, align="center")
        list_w = urwid.SimpleFocusListWalker([title_text_w])
        self.title.original_widget = urwid.ListBox(list_w)

    def set_y_label(self, y_label):
        if len(y_label) == 0:
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

        vline = urwid.AttrWrap(urwid.SolidFill(u'\u2502'), 'line')

        graph_vector_column_list = []
        for state, graph, sub_title in \
                zip(visible_graph_list,
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
        if len(graph_vector_column_list) == 0:
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
                len(label) == 0 or label is None):
            return True

        return False
