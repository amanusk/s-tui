#!/usr/bin/env python
#
# Copyright (C) 2017 Alex Manuskin, Gil Tsuker
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

"""A class display the About message menu
"""

from __future__ import print_function
import urwid

ABOUT_MESSAGE = " \n\
About:\n\
s-tui is a monitoring tool for your CPU temperature, frequency and utilization. s-tui makes it possilble to monitor your computer over SSH without a need for a GUI\n\
\n\
Authors:\n\
Alex Manuskin, Gil Tsuker\n\
\n\
Code for s-tui is available on github\n\
https://github.com/amanusk/s-tui\n\
"

MESSAGE_LEN = 20


class AboutMenu:
    MAX_TITLE_LEN = 50

    def __init__(self, return_fn):

        self.return_fn = return_fn

        self.about_message = ABOUT_MESSAGE

        self.time_out_ctrl = urwid.Text(self.about_message)

        cancel_button = urwid.Button('Exit', on_press=self.on_cancel)
        cancel_button._label.align = 'center'

        if_buttons = urwid.Columns([cancel_button])

        self.titles = [self.time_out_ctrl,
                       if_buttons]

        self.main_window = urwid.LineBox(urwid.ListBox(self.titles))

    def get_size(self):
        return MESSAGE_LEN + 3, self.MAX_TITLE_LEN

    def on_cancel(self, w):
        self.return_fn()
