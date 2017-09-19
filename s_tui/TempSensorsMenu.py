#!/usr/bin/env python
#
# Copyright (C) 2017 Alex Manuskin
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""A class display all availalbe Temperature sensors
"""

from __future__ import print_function
from __future__ import absolute_import
import urwid
import psutil


MESSAGE_LEN = 20

import logging
logger = logging.getLogger(__name__)

class TempSensorsMenu:
    MAX_TITLE_LEN = 50

    def radio_button(self, g, l, fn):
        """ Inheriting radio button of urwid """
        w = urwid.RadioButton(g, l, False, on_state_change=fn)
        w = urwid.AttrWrap(w, 'button normal', 'button select')
        return w

    def on_mode_button(self, button, state):
        """Notify the controller of a new mode setting."""
        if state:
            # The new mode is the label of the button
            self.set_mode(button.get_label())
            self.on_mode_change(button.get_label())

    def on_mode_change(self, m):
        """Handle external mode change by updating radio buttons."""
        for rb in self.sensor_buttons:
            if rb.get_label() == m:
                rb.set_state(True, do_callback=False)
                break

    def set_mode(self, mode):
        self.current_mode = mode

    def __init__(self, return_fn):

        self.current_mode = None

        self.no_malloc = False

        self.available_sensors = []

        sensors_dict = psutil.sensors_temperatures()
        for key,value in sensors_dict.items():
            sensor_name = key
            for itr in range(len(value)):
                self.available_sensors.append(sensor_name + "," +str(itr))

        group = []
        self.sensor_buttons = []
        for sensor in self.available_sensors:
            rb = self.radio_button(group, sensor, self.on_mode_button)
            self.sensor_buttons.append(rb)

        rb = self.radio_button(group, "INVALID", self.on_mode_button)
        self.sensor_buttons.append(rb)

        self.return_fn = return_fn

        cancel_button = urwid.Button('Exit', on_press=self.on_cancel)
        cancel_button._label.align = 'center'

        if_buttons = urwid.Columns([cancel_button])

        self.titles = self.sensor_buttons + [if_buttons]

        self.main_window = urwid.LineBox(urwid.ListBox(self.titles))

    def get_size(self):
        return MESSAGE_LEN + 3, self.MAX_TITLE_LEN

    def on_cancel(self, w):
        self.return_fn()

