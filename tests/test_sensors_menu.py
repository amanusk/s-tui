"""Tests for SensorsMenu: sensor visibility management and callbacks."""

import pytest
from unittest.mock import MagicMock

from s_tui.sensors_menu import SensorsMenu
from s_tui.sources.source import MockSource


def _make_mock_source(name, sensors):
    """Create a MockSource-like object with a name and sensor list."""
    src = MagicMock()
    src.get_source_name.return_value = name
    src.get_sensor_list.return_value = sensors
    return src


@pytest.fixture
def simple_sources():
    """Two sources with 2 and 3 sensors respectively."""
    return [
        _make_mock_source("CPU Util", ["Avg", "Core 0"]),
        _make_mock_source("Temp", ["Core 0", "Core 1", "Core 2"]),
    ]


@pytest.fixture
def default_conf():
    """Default config: all sensors visible."""
    return {
        "CPU Util": [True, True],
        "Temp": [True, True, True],
    }


@pytest.fixture
def menu(simple_sources, default_conf):
    return_fn = MagicMock()
    return SensorsMenu(return_fn, simple_sources, default_conf)


# =====================================================================
# Initialization
# =====================================================================


class TestSensorsMenuInit:
    def test_active_sensors_match_defaults(self, menu, default_conf):
        """active_sensors should mirror the default config."""
        for name, states in default_conf.items():
            assert menu.active_sensors[name] == states

    def test_sensor_button_dict_populated(self, menu):
        """Each source should have checkbox entries."""
        assert "CPU Util" in menu.sensor_button_dict
        assert "Temp" in menu.sensor_button_dict
        assert len(menu.sensor_button_dict["CPU Util"]) == 2
        assert len(menu.sensor_button_dict["Temp"]) == 3

    def test_get_size(self, menu):
        """get_size returns a (height, width) tuple."""
        size = menu.get_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert size[1] == SensorsMenu.MAX_TITLE_LEN

    def test_main_window_is_urwid_widget(self, menu):
        """main_window should be a urwid LineBox."""
        import urwid

        assert isinstance(menu.main_window, urwid.LineBox)

    def test_no_default_conf_defaults_to_all_true(self, simple_sources):
        """When default_source_conf entry is falsy, all sensors default True."""
        conf = {"CPU Util": None, "Temp": None}
        return_fn = MagicMock()
        m = SensorsMenu(return_fn, simple_sources, conf)
        assert m.active_sensors["CPU Util"] == [True, True]
        assert m.active_sensors["Temp"] == [True, True, True]


# =====================================================================
# on_cancel
# =====================================================================


class TestSensorsMenuCancel:
    def test_on_cancel_calls_return_fn_with_update_false(self, menu):
        """on_cancel should call return_fn(update=False)."""
        menu.on_cancel(None)
        menu.return_fn.assert_called_once_with(update=False)


# =====================================================================
# on_apply
# =====================================================================


class TestSensorsMenuApply:
    def test_on_apply_no_changes(self, menu):
        """on_apply with no changes calls return_fn(update=False)."""
        menu.on_apply(None)
        menu.return_fn.assert_called_once_with(update=False)

    def test_on_apply_with_changes(self, menu):
        """on_apply after toggling a checkbox calls return_fn(update=True)."""
        # Uncheck the first sensor in "Temp"
        menu.sensor_button_dict["Temp"][0].set_state(False)
        menu.on_apply(None)
        menu.return_fn.assert_called_once_with(update=True)
        assert menu.active_sensors["Temp"][0] is False


# =====================================================================
# setall / checkall / uncheckall
# =====================================================================


class TestSensorsMenuCheckAll:
    def test_setall_cb_col(self, menu):
        """setall_cb_col sets all checkboxes in a named column."""
        # Uncheck all in Temp
        menu.setall_cb_col(None, "Temp", False)
        for cb in menu.sensor_button_dict["Temp"]:
            assert cb.get_state() is False

        # Re-check all
        menu.setall_cb_col(None, "Temp", True)
        for cb in menu.sensor_button_dict["Temp"]:
            assert cb.get_state() is True

    def test_setall_ignores_other_columns(self, menu):
        """setall_cb_col should only affect the matching source."""
        menu.setall_cb_col(None, "Temp", False)
        # CPU Util should be unchanged
        for cb in menu.sensor_button_dict["CPU Util"]:
            assert cb.get_state() is True
