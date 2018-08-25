#!/usr/bin/env python
#
# Copyright (C) 2017-2018 Alex Manuskin
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

"""
A class displaying all available Temperature sensors
"""

from __future__ import print_function
from __future__ import absolute_import
import urwid
import psutil
from s_tui.UiElements import ViListBox
from s_tui.UiElements import radio_button


import logging
logger = logging.getLogger(__name__)


class SensorsMenu:
    MAX_TITLE_LEN = 70

    def on_mode_button(self, button, state):
        pass

    def __init__(self, return_fn, temp_source, freq_source):

        # What is shown in menu
        self.current_temp_mode = None
        self.current_freq_mode = None

        self.no_malloc = False

        freq_title = urwid.Text(
            ('bold text', u"  Frequency Sensors  \n"), 'center')
        temp_title = urwid.Text(
            ('bold text', u"  Temperature Sensors  \n"), 'center')

        # self.available_sensors = []
        self.available_temp_sensors = temp_source.get_sensor_list()
        self.available_freq_sensors = freq_source.get_sensor_list()

        # Sensor Applied
        # TODO use saved values for default windows that are open
        self.current_active_temp_mode = [True] * len(self.available_temp_sensors)
        self.current_active_freq_mode = [True] * len(self.available_freq_sensors)

        self.freq_sensor_buttons = []
        for sensor in self.available_freq_sensors:
            cb = urwid.CheckBox(sensor, True)
            self.freq_sensor_buttons.append(cb)

        self.temp_sensor_buttons = []
        for sensor in self.available_temp_sensors:
            cb = urwid.CheckBox(sensor, True)
            self.temp_sensor_buttons.append(cb)

        self.return_fn = return_fn

        cancel_button = urwid.Button('Cancel', on_press=self.on_cancel)
        cancel_button._label.align = 'center'
        apply_button = urwid.Button('Apply', on_press=self.on_apply)
        apply_button._label.align = 'center'

        if_buttons = urwid.Columns([apply_button, cancel_button])

        list_temp = [freq_title] + self.freq_sensor_buttons
        listw = urwid.SimpleFocusListWalker(list_temp)
        freq_widget_col = urwid.Pile(listw)

        list_temp = [temp_title] + self.temp_sensor_buttons
        listw = urwid.SimpleFocusListWalker(list_temp)
        temp_widget_col = urwid.Pile(listw)

        sensor_select_widget = urwid.Columns([freq_widget_col, temp_widget_col])
        list_temp = [sensor_select_widget, if_buttons]
        listw = urwid.SimpleFocusListWalker(list_temp)
        self.main_window = urwid.LineBox(ViListBox(listw))

    def get_size(self):
        return max(len(self.available_temp_sensors), len(self.available_freq_sensors)) + 6, self.MAX_TITLE_LEN

    def set_checkbox_value(self):
        logging.info(str(self.current_active_freq_mode))
        logging.info(str(self.freq_sensor_buttons))
        for (checkbox, state) in zip(self.freq_sensor_buttons, self.current_active_freq_mode):
            checkbox.set_state(state)

        for (checkbox, state) in zip(self.temp_sensor_buttons, self.current_active_temp_mode):
            checkbox.set_state(state)

    def on_cancel(self, w):
        self.set_checkbox_value()
        self.return_fn(update=False)

    def on_apply(self, w):

        self.current_temp_mode = []
        self.current_freq_mode = []
        for temp_sensor in self.temp_sensor_buttons:
            self.current_temp_mode.append(temp_sensor.get_state())
        for freq_sensor in self.freq_sensor_buttons:
            self.current_freq_mode.append(freq_sensor.get_state())

        if self.current_temp_mode != self.current_active_temp_mode or \
            self.current_freq_mode != self.current_active_freq_mode:
            logging.info("sensor update detected")
            self.current_active_temp_mode = self.current_temp_mode
            self.current_active_freq_mode = self.current_freq_mode
            self.set_checkbox_value()
            self.return_fn(update=True)
        else:
            self.set_checkbox_value()
            self.return_fn(update=False)
