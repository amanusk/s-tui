#!/usr/bin/env python
#
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

"""A class to control the optoins of stress in a menu
"""

from __future__ import print_function
import urwid
import re


class StressMenu:
    MAX_TITLE_LEN = 50

    def __init__(self, return_fn):

        self.return_fn = return_fn

        self.time_out = 'none'
        self.sqrt_workers = '1'
        self.sync_workers = '0'
        self.memory_workers = '0'
        self.malloc_byte = '256M'
        self.byte_touch_cnt = '4096'
        self.malloc_delay = 'none'
        self.no_malloc = False
        self.write_workers = '0'
        self.write_bytes = '1G'

        self.time_out_ctrl = urwid.Edit('Time out [sec]: ', self.time_out)
        self.sqrt_workers_ctrl = urwid.Edit(
            'Sqrt() worker count: ', self.sqrt_workers)
        self.sync_workers_ctrl = urwid.Edit(
            'Sync() worker count: ', self.sync_workers)
        self.memory_workers_ctrl = urwid.Edit(
            'Malloc() / Free() worker count: ', self.memory_workers)
        self.malloc_byte_ctrl = urwid.Edit(
            '   Bytes per malloc*: ', self.malloc_byte)
        self.byte_touch_cnt_ctrl = urwid.Edit(
            '   Touch a byte after * bytes: ', self.byte_touch_cnt)
        self.malloc_delay_ctrl = urwid.Edit(
            '   Sleep time between Free() [sec]: ', self.malloc_delay)
        self.no_malloc_ctrl = urwid.CheckBox(
            '"dirty" the memory \ninstead of free / alloc', self.no_malloc)
        self.write_workers_ctrl = urwid.Edit(
            'Write() / Unlink() worker count: ', self.write_workers)
        self.write_bytes_ctrl = urwid.Edit(
            '   Byte per Write(): ', self.write_bytes)

        default_button = urwid.Button('Default', on_press=self.on_default)
        default_button._label.align = 'center'

        save_button = urwid.Button('Save', on_press=self.on_save)
        save_button._label.align = 'center'

        cancel_button = urwid.Button('Cancel', on_press=self.on_cancel)
        cancel_button._label.align = 'center'

        if_buttons = urwid.Columns(
            [default_button, save_button, cancel_button])

        title = urwid.Text(('bold text', u"  Stress Options  \n"), 'center')

        self.titles = [title,
                       self.time_out_ctrl,
                       urwid.Divider(u'\u2500'),
                       self.sqrt_workers_ctrl,
                       urwid.Divider(u'\u2500'),
                       self.sync_workers_ctrl,
                       urwid.Divider(u'\u2500'),
                       self.memory_workers_ctrl,
                       urwid.Divider(),
                       self.malloc_byte_ctrl,
                       urwid.Divider(),
                       self.byte_touch_cnt_ctrl,
                       urwid.Divider(),
                       self.malloc_delay_ctrl,
                       urwid.Divider(),
                       self.no_malloc_ctrl,
                       urwid.Divider(u'\u2500'),
                       self.write_workers_ctrl,
                       urwid.Divider(),
                       self.write_bytes_ctrl,
                       urwid.Divider(u'\u2500'),
                       if_buttons]

        self.main_window = urwid.LineBox(urwid.ListBox(self.titles))

    def set_edit_texts(self):
        self.time_out_ctrl.set_edit_text(self.time_out)
        self.sqrt_workers_ctrl.set_edit_text(self.sqrt_workers)
        self.sync_workers_ctrl.set_edit_text(self.sync_workers)
        self.memory_workers_ctrl.set_edit_text(self.memory_workers)
        self.malloc_byte_ctrl.set_edit_text(self.malloc_byte)
        self.byte_touch_cnt_ctrl.set_edit_text(self.byte_touch_cnt)
        self.malloc_delay_ctrl.set_edit_text(self.malloc_delay)
        self.no_malloc_ctrl.set_state(self.no_malloc)
        self.write_workers_ctrl.set_edit_text(self.write_workers)
        self.write_bytes_ctrl.set_edit_text(self.write_bytes)

    def on_default(self, w):
        self.time_out = 'none'
        self.sqrt_workers = '1'
        self.sync_workers = '0'
        self.memory_workers = '0'
        self.malloc_byte = '256M'
        self.byte_touch_cnt = '4096'
        self.malloc_delay = 'none'
        self.no_malloc = False
        self.write_workers = '0'
        self.write_bytes = '1G'

        self.set_edit_texts()
        self.return_fn()

    def get_size(self):
        return len(self.titles) + 5, self.MAX_TITLE_LEN

    def on_save(self, w):
        self.time_out = self.get_pos_num(
            self.time_out_ctrl.get_edit_text(), 'none')
        self.sqrt_workers = self.get_pos_num(
            self.sqrt_workers_ctrl.get_edit_text(), '4')
        self.sync_workers = self.get_pos_num(
            self.sync_workers_ctrl.get_edit_text(), '0')
        self.memory_workers = self.get_pos_num(
            self.memory_workers_ctrl.get_edit_text(), '0')
        self.malloc_byte = self.get_valid_byte(
            self.malloc_byte_ctrl.get_edit_text(), '256M')
        self.byte_touch_cnt = self.get_valid_byte(
            self.byte_touch_cnt_ctrl.get_edit_text(), '4096')
        self.malloc_delay = self.get_pos_num(
            self.malloc_delay_ctrl.get_edit_text(), 'none')
        self.no_malloc = self.no_malloc_ctrl.get_state()
        self.write_workers = self.get_pos_num(
            self.write_workers_ctrl.get_edit_text(), '0')
        self.write_bytes = self.get_valid_byte(
            self.write_bytes_ctrl.get_edit_text(), '1G')

        self.set_edit_texts()
        self.return_fn()

    def on_cancel(self, w):
        self.set_edit_texts()
        self.return_fn()

    @staticmethod
    def get_pos_num(num, default):
        num_valid = re.match(r"\A([0-9]+)\Z", num, re.I)
        if num_valid or (num == 'none' and default == 'none'):
            return num
        else:
            return default

    @staticmethod
    def get_valid_byte(num, default):
        # check if the format of number is (num)(G|m|B) i.e 500GB, 200mb. 400
        # etc..
        num_valid = re.match(r"\A([0-9]+)(M|G|m|g|)(B|b|\b)\Z", num, re.I)
        if num_valid:
            return num
        else:
            return default
