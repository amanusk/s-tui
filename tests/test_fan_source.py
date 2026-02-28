"""Tests for FanSource with mocked psutil."""

import pytest

from s_tui.sources.fan_source import FanSource
from tests.conftest import SensorFan


class TestFanSourceInit:
    def test_name(self, mock_sensors_fans):
        src = FanSource()
        assert src.get_source_name() == "Fan"

    def test_measurement_unit(self, mock_sensors_fans):
        src = FanSource()
        assert src.get_measurement_unit() == "RPM"

    def test_is_available(self, mock_sensors_fans):
        src = FanSource()
        assert src.get_is_available() is True

    def test_sensor_list(self, mock_sensors_fans):
        src = FanSource()
        assert len(src.get_sensor_list()) == 1

    def test_pallet(self, mock_sensors_fans):
        src = FanSource()
        assert "fan" in src.get_pallet()[0]


class TestFanSourceUpdate:
    def test_update_populates_values(self, mock_sensors_fans):
        src = FanSource()
        src.update()
        readings = src.get_reading_list()
        assert readings[0] == 1200

    def test_filters_unreasonable_speeds(self, mocker):
        fans = {
            "hw": [
                SensorFan(label="f0", current=1200),
                SensorFan(label="f1", current=99999),
            ]
        }
        mocker.patch("psutil.sensors_fans", return_value=fans)
        src = FanSource()
        src.update()
        readings = src.get_reading_list()
        assert len(readings) == 1
        assert readings[0] == 1200

    def test_edge_triggered_always_false(self, mock_sensors_fans):
        src = FanSource()
        assert src.get_edge_triggered() is False

    def test_get_top(self, mock_sensors_fans):
        src = FanSource()
        assert src.get_top() == 1


class TestFanSourceUnavailable:
    def test_no_fans(self, mocker):
        mocker.patch("psutil.sensors_fans", return_value={})
        src = FanSource()
        assert src.get_is_available() is False

    def test_attribute_error(self, mocker):
        mocker.patch("psutil.sensors_fans", side_effect=AttributeError)
        src = FanSource()
        assert src.get_is_available() is False
