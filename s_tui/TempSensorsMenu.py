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


class TempSensorsMenu:
    MAX_TITLE_LEN = 40

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

        # What is shown in menu
        self.current_mode = None
        # Sensor Applied
        self.current_active_mode = None

        self.no_malloc = False

        title = urwid.Text(
            ('bold text', u"  Available Temperature Sensors  \n"), 'center')

        self.available_sensors = []
        sensors_dict = dict()
        try:
            sensors_dict = psutil.sensors_temperatures()
        except (AttributeError, IOError):
            logging.debug("Unable to create sensors dict")
        for key, value in sensors_dict.items():
            sensor_name = key
            for itr in range(len(value)):
                sensor_label = ""
                try:
                    sensor_label = value[itr].label
                    logging.debug("Sensor Label")
                    logging.debug(sensor_label)
                except (IndexError):
                    pass

                self.available_sensors.append(sensor_name +
                                              "," + str(itr) +
                                              "," + sensor_label)
        group = []
        self.sensor_buttons = []
        for sensor in self.available_sensors:
            rb = radio_button(group, sensor, self.on_mode_button)
            self.sensor_buttons.append(rb)

        self.return_fn = return_fn

        cancel_button = urwid.Button('Cancel', on_press=self.on_cancel)
        cancel_button._label.align = 'center'
        apply_button = urwid.Button('Apply', on_press=self.on_apply)
        apply_button._label.align = 'center'

        if_buttons = urwid.Columns([apply_button, cancel_button])

        self.titles = [title] + self.sensor_buttons + [if_buttons]

        self.main_window = urwid.LineBox(ViListBox(self.titles))

    def get_size(self):
        return len(self.sensor_buttons) + 6, self.MAX_TITLE_LEN

    def on_cancel(self, w):
        self.return_fn()

    def on_apply(self, w):
        self.current_active_mode = self.current_mode
        self.return_fn()
