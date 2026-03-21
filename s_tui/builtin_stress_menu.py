#!/usr/bin/env python
#
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

"""Configuration menu for the built-in Python CPU stresser."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

import psutil
import urwid

from s_tui.builtin_stresser import (
    STRATEGIES,
    STRATEGY_LABELS,
    get_default_strategy,
    strategy_available,
)


class BuiltinStressMenu:
    MAX_TITLE_LEN = 50

    def __init__(self, return_fn: Callable[[], None]) -> None:
        self.return_fn = return_fn

        self.num_workers = "1"
        try:
            self.num_workers = str(psutil.cpu_count() or 1)
            logging.info("builtin stress default workers %s", self.num_workers)
        except OSError as err:
            logging.debug(err)

        self.strategy = get_default_strategy()
        self._pending_strategy = self.strategy

        self.num_workers_ctrl = urwid.Edit("CPU worker count: ", self.num_workers)

        # Strategy radio buttons
        self._strategy_group: list[urwid.RadioButton] = []
        self._strategy_buttons: dict[str, urwid.RadioButton] = {}
        strategy_widgets: list[urwid.Widget] = []
        for key in STRATEGIES:
            label = STRATEGY_LABELS[key]
            if not strategy_available(key):
                label += " (requires numpy)"
            rb = urwid.RadioButton(
                self._strategy_group,
                label,
                state=(key == self.strategy),
                on_state_change=self._on_strategy_change,
                user_data=key,
            )
            self._strategy_buttons[key] = rb
            strategy_widgets.append(rb)

        default_button = urwid.Button("Default", on_press=self.on_default)
        default_button._label.align = "center"

        save_button = urwid.Button("Save", on_press=self.on_save)
        save_button._label.align = "center"

        cancel_button = urwid.Button("Cancel", on_press=self.on_cancel)
        cancel_button._label.align = "center"

        if_buttons = urwid.Columns([default_button, save_button, cancel_button])

        title = urwid.Text(("bold text", "  s-tui stress options  \n"), "center")

        self.titles = [
            title,
            self.num_workers_ctrl,
            urwid.Divider("-"),
            urwid.Text(("bold text", "Strategy:")),
            *strategy_widgets,
            urwid.Divider("-"),
            if_buttons,
        ]

        self.main_window = urwid.LineBox(urwid.ListBox(self.titles))

    def _on_strategy_change(
        self, button: urwid.RadioButton, state: bool, key: str
    ) -> None:
        if state:
            self._pending_strategy = key

    def get_size(self) -> tuple[int, int]:
        return len(self.titles) + 5, self.MAX_TITLE_LEN

    def get_num_workers(self) -> int:
        """Return the configured number of workers (minimum 1)."""
        try:
            return max(1, int(self.num_workers))
        except ValueError:
            return 1

    def get_strategy(self) -> str:
        """Return the selected strategy key."""
        return self.strategy

    def _restore_ui(self) -> None:
        """Reset UI controls to match committed state."""
        self.num_workers_ctrl.set_edit_text(self.num_workers)
        self._strategy_buttons[self.strategy].set_state(True)
        self._pending_strategy = self.strategy

    def on_default(self, _) -> None:
        self.num_workers = str(psutil.cpu_count() or 1)
        self.strategy = get_default_strategy()
        self._restore_ui()
        self.return_fn()

    def on_save(self, _) -> None:
        raw = self.num_workers_ctrl.get_edit_text()
        if re.match(r"\A[0-9]+\Z", raw) and int(raw) > 0:
            self.num_workers = raw
        else:
            self.num_workers = str(psutil.cpu_count() or 1)
        self.strategy = self._pending_strategy
        self._restore_ui()
        self.return_fn()

    def on_cancel(self, _) -> None:
        self._restore_ui()
        self.return_fn()
