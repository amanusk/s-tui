"""Test for issue #252, fixed in PR #254.

Issue #252: ConfigParser delimiter inconsistency between save_settings() and
_load_config() causes config files with colons in values to be corrupted.

PR #254 fixed this by ensuring both save_settings() and _load_config() use
the same delimiter setting (delimiters="=").

This test verifies that config files can be saved and loaded correctly even
when values contain colons (e.g., time strings like "12:34:56").
"""

import os
import pytest
from collections import defaultdict
from unittest.mock import MagicMock, patch
import configparser

from s_tui.helper_functions import get_user_config_file


class TestConfigDelimiter:
    """Test that config files with colons in values work correctly.

    These tests verify the fix for issue #252 (PR #254) which ensures
    ConfigParser delimiter consistency between save_settings() and _load_config().
    """

    @pytest.fixture
    def temp_config_dir(self, tmp_path, mocker):
        """Create a temporary config directory for testing."""
        config_dir = tmp_path / "s-tui"
        config_dir.mkdir()
        mocker.patch(
            "s_tui.helper_functions.get_user_config_dir",
            return_value=str(config_dir),
        )
        mocker.patch(
            "s_tui.helper_functions.user_config_dir_exists",
            return_value=True,
        )
        mocker.patch(
            "s_tui.helper_functions.make_user_config_dir",
            return_value=str(config_dir),
        )
        return config_dir

    def test_save_settings_uses_correct_delimiter(self, temp_config_dir, mocker):
        """Test that save_settings() uses delimiters="=" (fix from PR #254).

        Issue #252: save_settings() used ConfigParser() without delimiters="=",
        causing values with colons to be corrupted when saved.

        PR #254 fixed this by ensuring save_settings() uses delimiters="="
        to match _load_config().
        """
        from s_tui.s_tui import GraphController
        from s_tui.sources.util_source import UtilSource

        # Mock sources
        util_source = UtilSource()

        # Create a minimal controller setup
        mocker.patch("s_tui.s_tui.which", return_value=None)
        mocker.patch("argparse.ArgumentParser.parse_args").return_value = MagicMock(
            debug=False,
            debug_file=None,
            terminal=False,
            json=False,
            csv=False,
            csv_file=None,
            no_mouse=False,
            t_thresh=None,
            refresh_rate="2.0",
        )

        # Create controller with mocked view
        with patch("s_tui.s_tui.GraphView") as mock_view_class:
            mock_view = MagicMock()
            mock_view.graphs_menu = MagicMock()
            mock_view.graphs_menu.active_sensors = {
                "CPU Util": [True, True],
            }
            mock_view.summary_menu = MagicMock()
            mock_view.summary_menu.active_sensors = {
                "CPU Util": [True, True],
            }
            mock_view_class.return_value = mock_view

            controller = GraphController(MagicMock())
            controller.sources = [util_source]
            controller.view = mock_view
            controller.refresh_rate = "2.0"
            controller.smooth_graph_mode = False
            controller.temp_thresh = None

            # Save settings - should use delimiters="=" (after PR #254 fix)
            controller.save_settings()

            # Verify the config file was created
            config_file = get_user_config_file()
            assert os.path.exists(config_file)

            # Read the config file and verify it uses '=' as delimiter
            # (not ':' which would corrupt values with colons)
            with open(config_file, "r") as f:
                config_content = f.read()

            # The config should use '=' as delimiter
            assert "refresh" in config_content
            # Verify format uses '=' not ':' as key-value separator
            lines = [
                l.strip()
                for l in config_content.split("\n")
                if "refresh" in l and "=" in l
            ]
            assert len(lines) > 0, "Config file should contain refresh setting"
            # The line should use '=' as delimiter (PR #254 fix)
            assert any(
                "=" in line and ":" not in line.split("=")[0] for line in lines
            ), "Config should use '=' as delimiter, not ':' (PR #254 fix)"

    def test_configparser_delimiter_consistency(self):
        """Test that ConfigParser with delimiters="=" preserves colons in values.

        This is the core fix from PR #254: using delimiters="=" ensures that
        colons in values are not treated as key-value separators.

        This test verifies the fix works by writing and reading a config with
        a colon in the value.
        """
        # Create a config with a value containing a colon
        conf_write = configparser.ConfigParser(delimiters="=")
        conf_write.add_section("GraphControl")
        conf_write.set("GraphControl", "refresh", "12:34:56")  # Time-like string

        # Write to a temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            conf_write.write(f)
            temp_file = f.name

        try:
            # Read it back with delimiters="=" (as _load_config does after PR #254)
            conf_read = configparser.ConfigParser(delimiters="=")
            conf_read.read(temp_file)

            # Verify the colon was preserved
            refresh_value = conf_read.get("GraphControl", "refresh")
            assert refresh_value == "12:34:56", (
                f"Expected '12:34:56' but got '{refresh_value}'. "
                "This verifies that delimiters='=' preserves colons in values."
            )
        finally:
            os.unlink(temp_file)


class TestConfigSensorNameMatching:
    """Test that sensor config is matched by name, not position.

    Verifies the fix for config loading that uses sensor names as keys
    instead of positional lists, so reordering/adding/removing sensors
    between restarts doesn't misalign visibility settings.
    """

    def test_config_fewer_sensors_than_system(self):
        """Config has fewer sensors than currently on the system.

        New sensors should default to visible (True).
        """
        from s_tui.sensors_menu import SensorsMenu

        # Create a mock source with 3 sensors
        source = MagicMock()
        source.get_source_name.return_value = "Temp"
        source.get_sensor_list.return_value = ["Core0,0", "Core1,0", "Core2,0"]

        # Config only knows about 2 of them (dict keyed by lowercase name)
        default_conf = {"Temp": {"core0,0": True, "core1,0": False}}

        menu = SensorsMenu(MagicMock(), [source], default_conf)
        active = menu.active_sensors["Temp"]
        assert active[0] is True   # Core0,0 from config
        assert active[1] is False  # Core1,0 from config
        assert active[2] is True   # Core2,0 new, defaults visible

    def test_config_more_sensors_than_system(self):
        """Config has more sensors than currently on the system.

        Extra config entries should be silently ignored.
        """
        from s_tui.sensors_menu import SensorsMenu

        # System has only 1 sensor
        source = MagicMock()
        source.get_source_name.return_value = "Temp"
        source.get_sensor_list.return_value = ["Core0,0"]

        # Config has entries for 3 sensors
        default_conf = {
            "Temp": {"core0,0": False, "core1,0": True, "core2,0": True}
        }

        menu = SensorsMenu(MagicMock(), [source], default_conf)
        active = menu.active_sensors["Temp"]
        assert len(active) == 1
        assert active[0] is False  # Core0,0 from config

    def test_config_empty_defaults_all_visible(self):
        """No config for a source means all sensors default to visible."""
        from s_tui.sensors_menu import SensorsMenu

        source = MagicMock()
        source.get_source_name.return_value = "Fan"
        source.get_sensor_list.return_value = ["fan0", "fan1"]

        default_conf = defaultdict(dict)

        menu = SensorsMenu(MagicMock(), [source], default_conf)
        active = menu.active_sensors["Fan"]
        assert active == [True, True]
