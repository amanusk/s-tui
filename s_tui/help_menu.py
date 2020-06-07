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

"""A class display the help message menu
"""

from __future__ import print_function
from __future__ import absolute_import
import urwid
from s_tui.sturwid.ui_elements import ViListBox

HELP_MESSAGE = """
TUI interface:

The side bar houses the controls for the displayed graphs.\n\
At the bottom, all sensors reading are presented in text form.\n\

* Use the arrow keys or 'hjkl' to navigate the side bar
* Toggle between stressed and regular operation using the radio buttons in \
'Modes'.\n\
* If you wish to alternate stress defaults, you can do it in <Stress \
options>\n\
* Select graphs to display in the <Graphs> menu \n\
* Select summaries to display in the <Summaries> menu \n\
* Change time between updates using the 'Refresh' field\n\
* Use the <Reset> button to reset graphs and statistics\n\
* If your system supports it, you can use the UTF-8 button to get a smoother \
graph\n\
* Save your current configuration with the <Save Settings> button\n\
* Press 'q' or the <Quit> button to quit\n\
\n\
* Run `s-tui --help` to get this message and additional cli options\n\
\n\
"""

MESSAGE_LEN = 30


class HelpMenu:
    """ HelpMenu is a widget containing instructions on usage of s-tui"""
    MAX_TITLE_LEN = 90

    def __init__(self, return_fn):

        self.return_fn = return_fn

        self.help_message = HELP_MESSAGE

        self.time_out_ctrl = urwid.Text(self.help_message)

        cancel_button = urwid.Button(('Exit'), on_press=self.on_cancel)
        cancel_button._label.align = 'center'

        if_buttons = urwid.Columns([cancel_button])

        title = urwid.Text(('bold text', u"  Help Menu  \n"), 'center')

        self.titles = [title,
                       self.time_out_ctrl,
                       if_buttons]

        self.main_window = urwid.LineBox(ViListBox(self.titles))

    def get_size(self):
        """ returns size of HelpMenu"""
        return MESSAGE_LEN + 3, self.MAX_TITLE_LEN

    def on_cancel(self, w):
        """ Returns to original widget"""
        self.return_fn()
