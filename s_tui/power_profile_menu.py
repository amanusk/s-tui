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

"""A menu to view and change CPU governor and energy performance preference."""

from __future__ import annotations

import glob
import logging
import subprocess
from collections.abc import Callable

import urwid

from s_tui.helper_functions import cat
from s_tui.sturwid.ui_elements import ViListBox

# Sysfs paths (cpu0 used for reading available options and current state)
SYSFS_AVAIL_GOVERNORS = (
    "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
)
SYSFS_GOVERNOR = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
SYSFS_AVAIL_EPP = (
    "/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_available_preferences"
)
SYSFS_EPP = "/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference"

# Glob patterns for writing to all cores
_SYSFS_ALL_GOVERNORS = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
_SYSFS_ALL_EPP = "/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference"

# Mapping from EPP sysfs value to powerprofilesctl profile name
_EPP_TO_PROFILE = {
    "performance": "performance",
    "balance_performance": "balanced",
    "power": "power-saver",
}


def read_available(path: str) -> list[str]:
    """Read space-separated values from a sysfs file, return empty list on failure."""
    try:
        return cat(path, binary=False).split()
    except OSError:
        return []


def _read_current(path: str) -> str:
    """Read the current value from a sysfs file."""
    try:
        return cat(path, binary=False).strip()
    except OSError:
        return ""


def _write_all_cores(pattern: str, value: str) -> None:
    """Write a value to all matching sysfs paths (requires root)."""
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise OSError(f"No sysfs paths found for {pattern}")
    errors: list[OSError] = []
    for path in paths:
        try:
            with open(path, "w") as f:
                f.write(value)
        except OSError as e:
            errors.append(e)
    if errors:
        # Produce a short message when all cores fail with the same reason
        reasons = {e.strerror or str(e) for e in errors}
        if len(reasons) == 1:
            reason = reasons.pop()
            if "busy" in reason.lower():
                gov = _read_current(SYSFS_GOVERNOR) or "unknown"
                raise OSError(f"Device busy — cannot write '{value}' (governor: {gov})")
            raise OSError(f"{reason} (all {len(errors)} cores)")
        raise OSError("; ".join(f"{e.filename}: {e}" for e in errors))


def _set_epp_via_powerprofilesctl(exe: str, epp_value: str) -> None:
    """Set EPP using powerprofilesctl. Raises OSError on failure."""
    profile = _EPP_TO_PROFILE.get(epp_value)
    if profile is None:
        raise OSError(
            f"No powerprofilesctl mapping for '{epp_value}', "
            f"direct sysfs write required"
        )
    try:
        result = subprocess.run(
            [exe, "set", profile],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise OSError(f"powerprofilesctl timed out setting '{profile}'") from exc
    if result.returncode != 0:
        stderr = result.stderr.strip().lower()
        if "busy" in stderr:
            gov = _read_current(SYSFS_GOVERNOR) or "unknown"
            raise OSError(f"Cannot change EPP (governor: {gov})")
        raise OSError(f"powerprofilesctl set {profile} failed")


class PowerProfileMenu:
    MAX_TITLE_LEN = 50

    def __init__(
        self,
        return_fn: Callable[[], None],
        powerprofilesctl_exe: str | None,
        can_write_governor: bool,
        can_write_epp: bool,
        available_governors: list[str] | None = None,
        available_epp: list[str] | None = None,
    ) -> None:
        self.return_fn = return_fn
        self.powerprofilesctl_exe = powerprofilesctl_exe
        self.can_write_governor = can_write_governor
        self.can_write_epp = can_write_epp

        # Read available options if not provided
        self.available_governors = (
            available_governors
            if available_governors is not None
            else read_available(SYSFS_AVAIL_GOVERNORS)
        )
        self.available_epp = (
            available_epp
            if available_epp is not None
            else read_available(SYSFS_AVAIL_EPP)
        )

        # Determine what's controllable
        self.governor_controllable = (
            can_write_governor and len(self.available_governors) > 1
        )
        self.epp_controllable = (
            can_write_epp or powerprofilesctl_exe is not None
        ) and len(self.available_epp) > 0

        # Status message area
        self.status_text = urwid.Text("")

        # Build UI
        self.titles: list[urwid.Widget] = []
        self._build_ui()

        self.main_window = urwid.LineBox(
            ViListBox(urwid.SimpleFocusListWalker(self.titles)),
            title="Power Profile",
        )

    def _build_ui(self) -> None:
        title = urwid.Text(("bold text", "  Power Profile  \n"), "center")
        self.titles = [title]

        # Governor section
        self.governor_group: list[urwid.RadioButton] = []
        self.governor_buttons: list[urwid.AttrMap] = []
        if len(self.available_governors) > 1:
            self.titles.append(urwid.Text(("bold text", "Governor"), align="center"))
            if self.governor_controllable:
                current_gov = _read_current(SYSFS_GOVERNOR)
                for gov in self.available_governors:
                    w = urwid.RadioButton(
                        self.governor_group, gov, state=(gov == current_gov)
                    )
                    am = urwid.AttrMap(w, "button normal", "button select")
                    self.governor_buttons.append(am)
                    self.titles.append(am)
            else:
                current_gov = _read_current(SYSFS_GOVERNOR)
                for gov in self.available_governors:
                    marker = " *" if gov == current_gov else ""
                    self.titles.append(urwid.Text(f"  {gov}{marker}"))
                self.titles.append(
                    urwid.Text(("high temp txt", "  (read-only, needs root)"))
                )
            self.titles.append(urwid.Divider())

        # EPP section
        self.epp_group: list[urwid.RadioButton] = []
        self.epp_buttons: list[urwid.AttrMap] = []
        if len(self.available_epp) > 0:
            self.titles.append(urwid.Text(("bold text", "Energy Pref"), align="center"))
            if self.epp_controllable:
                current_epp = _read_current(SYSFS_EPP)
                for epp in self.available_epp:
                    w = urwid.RadioButton(
                        self.epp_group, epp, state=(epp == current_epp)
                    )
                    am = urwid.AttrMap(w, "button normal", "button select")
                    self.epp_buttons.append(am)
                    self.titles.append(am)
            else:
                current_epp = _read_current(SYSFS_EPP)
                for epp in self.available_epp:
                    marker = " *" if epp == current_epp else ""
                    self.titles.append(urwid.Text(f"  {epp}{marker}"))
                self.titles.append(urwid.Text(("high temp txt", "  (read-only)")))
            self.titles.append(urwid.Divider())

        # Status + buttons
        self.titles.append(self.status_text)

        apply_button = urwid.Button("Apply", on_press=self.on_apply)
        apply_button._label.align = "center"
        cancel_button = urwid.Button("Cancel", on_press=self.on_cancel)
        cancel_button._label.align = "center"
        self.titles.append(urwid.Columns([apply_button, cancel_button]))

    def get_size(self) -> tuple[int, int]:
        return len(self.titles) + 5, self.MAX_TITLE_LEN

    def is_controllable(self) -> bool:
        """Return True if at least one section is controllable."""
        return self.governor_controllable or self.epp_controllable

    def refresh_state(self) -> None:
        """Re-read current governor/EPP from sysfs and update radio buttons."""
        if self.governor_controllable:
            current_gov = _read_current(SYSFS_GOVERNOR)
            for btn_map in self.governor_buttons:
                rb = btn_map.original_widget
                rb.set_state(rb.label == current_gov, do_callback=False)

        if self.epp_controllable:
            current_epp = _read_current(SYSFS_EPP)
            for btn_map in self.epp_buttons:
                rb = btn_map.original_widget
                rb.set_state(rb.label == current_epp, do_callback=False)

        self.status_text.set_text("")

    def _get_selected_governor(self) -> str | None:
        """Return the currently selected governor radio button label."""
        for rb in self.governor_group:
            if rb.state:
                return rb.label
        return None

    def _get_selected_epp(self) -> str | None:
        """Return the currently selected EPP radio button label."""
        for rb in self.epp_group:
            if rb.state:
                return rb.label
        return None

    def on_apply(self, _: object) -> None:
        """Apply the selected governor and/or EPP."""
        errors = []

        # Apply governor
        if self.governor_controllable:
            gov = self._get_selected_governor()
            if gov:
                try:
                    _write_all_cores(_SYSFS_ALL_GOVERNORS, gov)
                    logging.info("Set governor to %s", gov)
                except OSError as e:
                    logging.debug("Failed to set governor: %s", e)
                    errors.append(str(e))

        # Apply EPP
        if self.epp_controllable:
            epp = self._get_selected_epp()
            if epp:
                try:
                    self._apply_epp(epp)
                    logging.info("Set EPP to %s", epp)
                except OSError as e:
                    logging.debug("Failed to set EPP: %s", e)
                    errors.append(str(e))

        if errors:
            self.status_text.set_text(("high temp txt", "\n".join(errors)))
        else:
            self.status_text.set_text("")
            self.return_fn()

    def _apply_epp(self, epp: str) -> None:
        """Apply EPP value using the best available method."""
        # Prefer powerprofilesctl if available and EPP maps to a profile
        if self.powerprofilesctl_exe and epp in _EPP_TO_PROFILE:
            try:
                _set_epp_via_powerprofilesctl(self.powerprofilesctl_exe, epp)
                return
            except OSError:
                if self.can_write_epp:
                    logging.debug("powerprofilesctl failed, falling back to sysfs")
                else:
                    raise
        # Fall back to direct sysfs write
        if self.can_write_epp:
            _write_all_cores(_SYSFS_ALL_EPP, epp)
            return
        raise OSError(
            f"Cannot set EPP to '{epp}': no powerprofilesctl mapping "
            f"and no sysfs write permission"
        )

    def on_cancel(self, _: object) -> None:
        """Reset radio buttons to current state and close."""
        self.refresh_state()
        self.return_fn()
