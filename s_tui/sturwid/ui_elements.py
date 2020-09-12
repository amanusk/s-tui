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

import urwid

DEFAULT_PALETTE = [
    ('body',                    'default',        'default',     'standout'),
    ('header',                  'default',        'dark red',),
    ('screen edge',             'light blue',     'brown'),
    ('main shadow',             'dark gray',      'black'),
    ('line',                    'default',        'light gray',  'standout'),
    ('menu button',             'light gray',     'black'),
    ('bg background',           'default',        'default'),
    ('overheat dark',           'white',          'light red',   'standout'),
    ('bold text',               'default,bold',   'default',     'bold'),
    ('under text',              'default,underline', 'default',  'underline'),

    ('util light',              'default',       'light green'),
    ('util light smooth',       'light green',   'default'),
    ('util dark',               'default',       'dark green'),
    ('util dark smooth',        'dark green',    'default'),

    ('high temp dark',          'default',       'dark red'),
    ('high temp dark smooth',   'dark red',      'default'),
    ('high temp light',         'default',       'light red'),
    ('high temp light smooth',  'light red',     'default'),

    ('power dark',               'default',      'light gray',    'standout'),
    ('power dark smooth',        'light gray',   'default'),
    ('power light',              'default',      'white',         'standout'),
    ('power light smooth',       'white',        'default'),

    ('temp dark',               'default',        'dark cyan',    'standout'),
    ('temp dark smooth',        'dark cyan',      'default'),
    ('temp light',              'default',        'light cyan',   'standout'),
    ('temp light smooth',       'light cyan',     'default'),

    ('freq dark',               'default',        'dark magenta', 'standout'),
    ('freq dark smooth',        'dark magenta',   'default'),
    ('freq light',              'default',        'light magenta', 'standout'),
    ('freq light smooth',       'light magenta',  'default'),

    ('fan dark',               'default',        'dark blue', 'standout'),
    ('fan dark smooth',        'dark blue',   'default'),
    ('fan light',              'default',        'light blue', 'standout'),
    ('fan light smooth',       'light blue',  'default'),

    ('button normal',           'dark green',     'default',      'standout'),
    ('button select',           'white',          'dark green'),
    ('line',                    'default',        'default',      'standout'),
    ('pg normal',               'white',          'default',      'standout'),
    ('pg complete',             'white',          'dark magenta'),
    ('high temp txt',           'light red',      'default'),
    ('pg smooth',               'dark magenta',   'default')
]


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
        elif key == 'x':
            key = 'enter'
        elif key == 'q':
            key = 'q'
        return super(ViListBox, self).keypress(size, key)


def radio_button(group, label, fn):
    """ Inheriting radio button of urwid """
    w = urwid.RadioButton(group, label, False, on_state_change=fn)
    w = urwid.AttrWrap(w, 'button normal', 'button select')
    return w


def button(t, fn, data=None):
    w = urwid.Button(t, fn, data)
    w = urwid.AttrWrap(w, 'button normal', 'button select')
    return w
