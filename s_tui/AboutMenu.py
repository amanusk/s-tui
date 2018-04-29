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

"""A class display the About message menu
"""

from __future__ import print_function
from __future__ import absolute_import

import urwid
from s_tui.UiElements import ViListBox
from s_tui.HelperFunctions import __version__

ABOUT_MESSAGE = " \n\
s-tui is a monitoring tool for your CPU temperature, frequency, utilization \
and power.\n\
With s-tui you can monitor your system over SSH without a need for a GUI\n\
\n\
Code for s-tui is available on github\n\
https://github.com/amanusk/s-tui\n\
\n\
***    Please star on github :)    ***\n\
\n\
Created by:\n\
    - Alex Manuskin\n\
    - Gil Tsuker\n\
    - Maor Veitsman\n\
\n\
April 2017\n\
\n\
s-tui " + __version__ +\
    " Released under GNU GPLv2 "

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

        title = urwid.Text(('bold text', u"  About Menu  \n"), 'center')

        self.titles = [title,
                       self.time_out_ctrl,
                       if_buttons]

        self.main_window = urwid.LineBox(ViListBox(self.titles))

    def get_size(self):
        return MESSAGE_LEN + 3, self.MAX_TITLE_LEN

    def on_cancel(self, w):
        self.return_fn()
