#!/usr/bin/env python

# Copyright (C) 2017-2025 Alex Manuskin, Gil Tsuker
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

from collections import OrderedDict

import urwid


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

    @staticmethod
    def _format_display_val(val, alerts, suffixes, sensor_idx):
        """Return urwid text markup for a summary value.

        Appends any TUI-only suffix (e.g. throttle label) and applies alert
        coloring when the source signals an alert for this sensor.
        sensor_idx is 0-based aligned with get_sensor_list(); pass -1 for the
        source title row (never colored, never suffixed).
        """
        text = str(val)
        if 0 <= sensor_idx < len(suffixes):
            text += suffixes[sensor_idx]

        alert_attr = (
            alerts[sensor_idx]
            if 0 <= sensor_idx < len(alerts) and alerts[sensor_idx]
            else None
        )
        return (alert_attr, text) if alert_attr else text

    def get_text_item_list(self):
        summery_text_list = []
        alerts = self.source.get_sensor_alerts()
        suffixes = self.source.get_sensor_suffixes()
        summary_items = list(self.source.get_summary().items())
        for item_idx, (key, val) in enumerate(summary_items):
            label_w = urwid.Text(str(key[0 : self.MAX_LABEL_L]))
            # item_idx 0 is the source title row; sensor alerts start at index 1.
            display_val = self._format_display_val(
                val, alerts, suffixes, item_idx - 1
            )
            value_w = urwid.Text(display_val, align="right")
            # This can be accessed by the update method
            self.summary_text_items[key] = value_w
            col_w = urwid.Columns([("weight", 1.5, label_w), value_w])
            # Use setdefault for atomic check-and-set (faster than try/except)
            is_visible = self.visible_summaries.setdefault(key, True)
            if is_visible:
                summery_text_list.append(col_w)

        return summery_text_list

    def update_visibility(self, visible_sensors):
        keys = list(self.visible_summaries.keys())
        self.visible_summaries[keys[0]] = any(visible_sensors)
        # Do not change visibility of title
        for sensor, visible in zip(keys[1:], visible_sensors):
            self.visible_summaries[sensor] = visible

    def update(self):
        alerts = self.source.get_sensor_alerts()
        suffixes = self.source.get_sensor_suffixes()
        summary_items = list(self.source.get_summary().items())
        for item_idx, (key, val) in enumerate(summary_items):
            if key in self.summary_text_items:
                display_val = self._format_display_val(
                    val, alerts, suffixes, item_idx - 1
                )
                self.summary_text_items[key].set_text(display_val)

    def get_is_available(self):
        return self.source.get_is_available()
