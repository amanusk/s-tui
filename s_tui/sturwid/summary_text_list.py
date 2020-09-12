#!/usr/bin/env python

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
from collections import OrderedDict


class SummaryTextList:
    MAX_LABEL_L = 12

    def __init__(self, source, visible_sensors_list):
        self.source = source
        self.visible_summaries = OrderedDict()
        keys = list(self.source.get_summary().keys())
        # The title is the first in the list
        self.visible_summaries[keys[0]] = any(visible_sensors_list)
        # All others according to initial visibility
        for key, visible in zip(keys[1:], visible_sensors_list):
            self.visible_summaries[key] = visible

        # We keep a dict of all the items in the summary list
        self.summary_text_items = OrderedDict()

    def get_text_item_list(self):

        summery_text_list = []
        for key, val in self.source.get_summary().items():
            label_w = urwid.Text(str(key[0:self.MAX_LABEL_L]))
            value_w = urwid.Text(str(val), align='right')
            # This can be accessed by the update method
            self.summary_text_items[key] = value_w
            col_w = urwid.Columns([('weight', 1.5, label_w), value_w])
            try:
                _ = self.visible_summaries[key]
            except KeyError:
                # If an unkonwn key appers, add it to list
                self.visible_summaries[key] = True
            if self.visible_summaries[key]:
                summery_text_list.append(col_w)

        return summery_text_list

    def update_visibility(self, visible_sensors):
        keys = list(self.visible_summaries.keys())
        self.visible_summaries[keys[0]] = any(visible_sensors)
        # Do not change visiblity of title
        for sensor, visible in zip(keys[1:], visible_sensors):
            self.visible_summaries[sensor] = visible

    def update(self):
        for key, val in self.source.get_summary().items():
            if key in self.summary_text_items:
                self.summary_text_items[key].set_text(str(val))

    def get_is_available(self):
        return self.source.get_is_available()
