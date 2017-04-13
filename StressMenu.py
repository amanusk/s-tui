#!/usr/bin/env python

"""A simple python script template.
"""

from __future__ import print_function
import urwid


class StressMenu:
    # data...
    # max_box_levels = 4
    MAX_TITLE_LEN = 50

    titles = [urwid.IntEdit('Time out [sec]: '),
              urwid.Divider(u'\u2500'),
              urwid.IntEdit('Sqrt() worker count: '),
              urwid.Divider(u'\u2500'),
              urwid.IntEdit('Sync() worker count: '),
              urwid.Divider(u'\u2500'),
              urwid.IntEdit('Malloc() / Free() worker count: '),
              urwid.Divider(),
              urwid.IntEdit('   Bytes per malloc*: '),
              urwid.Divider(),
              urwid.IntEdit('   Touch a byte after * bytes: '),
              urwid.Divider(),
              urwid.IntEdit('   Sleep time between Free() [sec]: '),
              urwid.Divider(),
              urwid.CheckBox('"dirty" the memory \ninstead of free / alloc'),
              urwid.Divider(u'\u2500'),
              urwid.IntEdit('Write() / Unlink() worker count: '),
              urwid.Divider(),
              urwid.IntEdit('   Byte per Write(): '),
              urwid.Divider(u'\u2500'),
              urwid.Columns([urwid.Button('Save'), urwid.Button('Cancel')])]

    def __init__(self):
        self.main_window = urwid.LineBox(urwid.ListBox(self.titles))

    def get_size(self):
        return len(self.titles) + 3, self.MAX_TITLE_LEN

    # def open_menu(self, w, base_w):
    #     return urwid.Overlay(urwid.ListBox([urwid.Text('test')]), base_w,
    #                            ('fixed left', 2), ('fixed right', 3),
    #                            ('fixed top', 1), ('fixed bottom', 2)
    #                            )
    #     # grid = urwid.GridFlow([urwid.Text('-t'), urwid.Text('-v')], 5, 1, 1, 'left')
    #
    #     self.original_widget = urwid.Overlay(urwid.LineBox(urwid.Text('-t')),
    #                                          self.original_widget,
    #                                          align='center', width=('relative', 80),
    #                                          valign='middle', height=('relative', 80),
    #                                          min_width=24, min_height=8,
    #                                          left=self.box_level * 3,
    #                                          right=(self.max_box_levels - self.box_level - 1) * 3,
    #                                          top=self.box_level * 2,
    #                                          bottom=(self.max_box_levels - self.box_level - 1) * 2)
    #
    # def keypress(self, size, key):
    #     if key == 'esc' and self.box_level > 1:
    #         self.original_widget = self.original_widget[0]
    #         self.box_level -= 1
    #     else:
    #         return super(StressMenu, self).keypress(size, key)

