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

"""A class to control the optoins of stress in a menu
"""

from __future__ import print_function
import re
import logging

import psutil
import urwid


class StressMenu:
    MAX_TITLE_LEN = 50

    def __init__(self, return_fn, stress_exe):

        self.return_fn = return_fn

        self.stress_exe = stress_exe

        self.time_out = 'none'
        self.sqrt_workers = '1'
        try:
            self.sqrt_workers = str(psutil.cpu_count())
            logging.info("num cpus %s", self.sqrt_workers)
        except (IOError, OSError) as err:
            logging.debug(err)

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
                       urwid.Divider(u'-'),
                       self.sqrt_workers_ctrl,
                       urwid.Divider(u'-'),
                       self.sync_workers_ctrl,
                       urwid.Divider(u'-'),
                       self.memory_workers_ctrl,
                       urwid.Divider(),
                       self.malloc_byte_ctrl,
                       urwid.Divider(),
                       self.byte_touch_cnt_ctrl,
                       urwid.Divider(),
                       self.malloc_delay_ctrl,
                       urwid.Divider(),
                       self.no_malloc_ctrl,
                       urwid.Divider(u'-'),
                       self.write_workers_ctrl,
                       urwid.Divider(),
                       self.write_bytes_ctrl,
                       urwid.Divider(u'-'),
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

    def on_default(self, _):
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

    def on_save(self, _):
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

    def on_cancel(self, _):
        self.set_edit_texts()
        self.return_fn()

    def get_stress_cmd(self):
        stress_cmd = [self.stress_exe]
        if int(self.sqrt_workers) > 0:
            stress_cmd.append('-c')
            stress_cmd.append(self.sqrt_workers)

        if int(self.sync_workers) > 0:
            stress_cmd.append('-i')
            stress_cmd.append(self.sync_workers)

        if int(self.memory_workers) > 0:
            stress_cmd.append('--vm')
            stress_cmd.append(self.memory_workers)
            stress_cmd.append('--vm-bytes')
            stress_cmd.append(self.malloc_byte)
            stress_cmd.append('--vm-stride')
            stress_cmd.append(self.byte_touch_cnt)

        if self.no_malloc:
            stress_cmd.append('--vm-keep')

        if int(self.write_workers) > 0:
            stress_cmd.append('--hdd')
            stress_cmd.append(self.write_workers)
            stress_cmd.append('--hdd-bytes')
            stress_cmd.append(self.write_bytes)

        if self.time_out != 'none':
            stress_cmd.append('-t')
            stress_cmd.append(self.time_out)

        return stress_cmd

    @staticmethod
    def get_pos_num(num, default):
        num_valid = re.match(r"\A([0-9]+)\Z", num, re.I)
        if num_valid or (num == 'none' and default == 'none'):
            return num
        return default

    @staticmethod
    def get_valid_byte(num, default):
        """check if the format of number is (num)(G|m|B) i.e 500GB, 200mb. 400
        etc.. """
        num_valid = re.match(r"\A([0-9]+)(M|G|m|g|)(B|b|\b)\Z", num, re.I)
        if num_valid:
            return num
        return default
