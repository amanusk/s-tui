#!/usr/bin/env python

"""ScalableBarGraph Class extends urwid.BarGraph so that
the current size of the bar graph is also obtainable
get_size() - returns the tuple (row, col)
"""

import urwid


class ScalableBarGraph(urwid.BarGraph):
    _size = (0, 0)

    def render(self, size, focus=False):
        canvas = super(ScalableBarGraph, self).render(size, focus)
        new_size = (canvas.rows(), canvas.cols())
        old_size = self._size
        # check if to raise *on_resize* event
        if new_size != old_size:
            self.on_resize(new_size)
        self._size = new_size
        return canvas

    def get_size(self):
        return self._size

    def on_resize(self, new_size):
        pass  # place folder for any future implantation


class LabeledBarGraph(urwid.Pile):

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
        self.sef_graph(widget_list[0])

        self.x_label = []
        self.set_x_label(widget_list[1])

        self.y_label = []
        self.set_y_label(widget_list[2])

        self.title = []
        self.set_title(widget_list[3])

        if self.y_label is not None and self.x_label is not None:
            super(LabeledBarGraph, self).__init__([self.title, ('weight', 1, self.y_label), self.x_label], focus_item=focus_item)
        elif self.y_label is not None:
            super(LabeledBarGraph, self).__init__([self.title, self.y_label], focus_item=focus_item)
        elif self.x_label is not None:
            super(LabeledBarGraph, self).__init__([self.title, self.bar_graph, self.x_label], focus_item=focus_item)
        else:
            super(LabeledBarGraph, self).__init__([self.title, self.bar_graph], focus_item=focus_item)

    def set_title(self, title):
        if len(title) == 0:
            self.title = None
            return

        self.title = ('fixed', 1, urwid.ListBox([urwid.Text(title, align="center")]))

    def set_x_label(self, x_label):
        if len(x_label) == 0:
            self.x_label = None
            return

        x_label = [str(i) for i in x_label]

        x_label_nums = x_label[1:]
        x_label_num_list = [urwid.ListBox([urwid.Text('  ' + x_label[0])])]
        for num in x_label_nums:
            x_label_num_list = x_label_num_list + [urwid.ListBox([urwid.Text(num)])]

        x_label_num_list[-1] = (1, x_label_num_list[-1])

        self.x_label = ('fixed', 1, urwid.Columns(x_label_num_list))

    def set_y_label(self, y_label):
        if len(y_label) == 0:
            self.y_label = None
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

        self.y_label = urwid.Columns(y_notation,
                                     dividechars=1)

    def sef_graph(self, graph):
        self.bar_graph = graph

    @staticmethod
    def check_label(label):
        if len(label) >= 2 and not(None in label) or len(label) == 0 or label is None:
            return True

        return False
