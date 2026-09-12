"""Tests for CLI argument parsing (get_args) and main() entry paths."""

import sys
from unittest.mock import patch

import pytest

from s_tui.s_tui import GraphController, get_args


class TestGetArgs:
    def _parse(self, argv):
        """Helper: parse argv through get_args by patching sys.argv."""
        with patch.object(sys, "argv", ["s-tui", *argv]):
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
        assert args.refresh_rate is None

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


class TestRefreshRatePrecedence:
    @pytest.mark.parametrize(
        "saved_rate, argv, expected",
        [
            (None, [], "2.0"),
            ("5", [], "5.0"),
            ("5", ["--refresh-rate", "1"], "1"),
            ("5", ["-r", "2.0"], "2.0"),
            (None, ["-r", "0.5"], "0.5"),
            ("invalid", [], "2.0"),
            ("invalid", ["-r", "1"], "1"),
        ],
    )
    def test_refresh_rate_precedence(
        self, tmp_path, mocker, saved_rate, argv, expected
    ):
        """Explicit CLI rates override saved settings, which override the default."""
        config_file = tmp_path / "s-tui.conf"
        if saved_rate is not None:
            config_file.write_text(f"[GraphControl]\nrefresh = {saved_rate}\n")

        mocker.patch("s_tui.s_tui.user_config_dir_exists", return_value=True)
        mocker.patch("s_tui.s_tui.get_user_config_dir", return_value=str(tmp_path))
        mocker.patch(
            "s_tui.s_tui.user_config_file_exists", return_value=config_file.exists()
        )
        mocker.patch("s_tui.s_tui.get_user_config_file", return_value=str(config_file))
        mocker.patch("s_tui.s_tui.ScriptHookLoader")
        mocker.patch("s_tui.s_tui.GraphView")
        mocker.patch("s_tui.s_tui.GraphController._config_stress")
        mocker.patch("s_tui.s_tui.which", return_value=None)
        for source_name in (
            "TempSource",
            "FreqSource",
            "UtilSource",
            "RaplPowerSource",
            "FanSource",
        ):
            source = mocker.patch(f"s_tui.s_tui.{source_name}")
            source.return_value.get_is_available.return_value = False

        mocker.patch.object(sys, "argv", ["s-tui", *argv])
        controller = GraphController(get_args())

        assert controller.refresh_rate == expected
        if saved_rate is not None:
            assert (
                config_file.read_text() == f"[GraphControl]\nrefresh = {saved_rate}\n"
            )
        else:
            assert not config_file.exists()
