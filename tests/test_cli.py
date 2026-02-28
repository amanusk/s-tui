"""Tests for CLI argument parsing (get_args) and main() entry paths."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from s_tui.s_tui import get_args


class TestGetArgs:
    def _parse(self, argv):
        """Helper: parse argv through get_args by patching sys.argv."""
        with patch.object(sys, "argv", ["s-tui"] + argv):
            return get_args()

    def test_default_args(self):
        """Default args with no flags."""
        args = self._parse([])
        assert args.debug is False
        assert args.terminal is False
        assert args.json is False
        assert args.version is False
        assert args.csv is False
        assert args.no_mouse is False
        assert args.debug_run is False
        assert args.t_thresh is None
        assert args.refresh_rate == "2.0"

    def test_debug_flag(self):
        args = self._parse(["-d"])
        assert args.debug is True

    def test_debug_long(self):
        args = self._parse(["--debug"])
        assert args.debug is True

    def test_debug_run(self):
        args = self._parse(["-dr"])
        assert args.debug_run is True

    def test_terminal_flag(self):
        args = self._parse(["-t"])
        assert args.terminal is True

    def test_json_flag(self):
        args = self._parse(["-j"])
        assert args.json is True

    def test_version_flag(self):
        args = self._parse(["-v"])
        assert args.version is True

    def test_csv_flag(self):
        args = self._parse(["-c"])
        assert args.csv is True

    def test_no_mouse(self):
        args = self._parse(["-nm"])
        assert args.no_mouse is True

    def test_t_thresh(self):
        args = self._parse(["-tt", "90"])
        assert args.t_thresh == "90"

    def test_refresh_rate(self):
        args = self._parse(["-r", "1.0"])
        assert args.refresh_rate == "1.0"

    def test_debug_file(self):
        args = self._parse(["--debug-file", "/tmp/test.log"])
        assert args.debug_file == "/tmp/test.log"

    def test_csv_file(self):
        args = self._parse(["--csv-file", "/tmp/test.csv"])
        assert args.csv_file == "/tmp/test.csv"

    def test_combined_flags(self):
        args = self._parse(["-d", "-c", "-nm", "-tt", "75", "-r", "0.5"])
        assert args.debug is True
        assert args.csv is True
        assert args.no_mouse is True
        assert args.t_thresh == "75"
        assert args.refresh_rate == "0.5"
