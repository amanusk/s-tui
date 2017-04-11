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
