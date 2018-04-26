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

import urwid


class ViListBox(urwid.ListBox):
    # Catch key presses in box and pass them as arrow keys
    def keypress(self, size, key):
        if key == 'j':
            key = 'down'
        elif key == 'k':
            key = 'up'
        elif key == 'h':
            key = 'left'
        elif key == 'l':
            key = 'right'
        elif key == 'G':
            key = 'page down'
        elif key == 'g':
            key = 'page up'
        return super(ViListBox, self).keypress(size, key)


def radio_button(g, l, fn):
    """ Inheriting radio button of urwid """
    w = urwid.RadioButton(g, l, False, on_state_change=fn)
    w = urwid.AttrWrap(w, 'button normal', 'button select')
    return w


def button(t, fn, data=None):
    w = urwid.Button(t, fn, data)
    w = urwid.AttrWrap(w, 'button normal', 'button select')
    return w
