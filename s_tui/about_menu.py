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
"""Displays the About message menu """

from __future__ import print_function
from __future__ import absolute_import

import urwid
from s_tui.sturwid.ui_elements import ViListBox
from s_tui.helper_functions import __version__

ABOUT_MESSAGE = """
s-tui is a monitoring tool for your CPU's temperature, frequency, utilization \
and power.\n\

Code for s-tui is available on github\n\
https://github.com/amanusk/s-tui\n\
\n\
Help, issues and pull requests are appreciated.
\n\
Created by:\n\
    - Alex Manuskin\n\
    - Gil Tsuker\n\
    - Maor Veitsman\n\
    And others
\n\
April 2017\n\
\n\
"""

ABOUT_MESSAGE += "s-tui " + __version__ +\
    " Released under GNU GPLv2 "

MESSAGE_LEN = 20


class AboutMenu:
    """Displays the About message menu """
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
