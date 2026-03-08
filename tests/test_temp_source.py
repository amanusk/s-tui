"""Tests for TempSource with mocked psutil."""

from collections import OrderedDict

import pytest

from s_tui.sources.temp_source import TempSource
from tests.conftest import SensorTemperature


def _make_temp_dict(sensors_list, group_name="coretemp"):
    return OrderedDict([(group_name, sensors_list)])


@pytest.fixture
def basic_temp_mock(mocker):
    """Mock sensors_temperatures with 2 valid sensors."""
    sensors = [
        SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
        SensorTemperature(label="Core 1", current=60.0, high=80.0, critical=100.0),
    ]
    temps = _make_temp_dict(sensors)
    mocker.patch("psutil.sensors_temperatures", return_value=temps)
    return temps


class TestTempSourceInit:
    def test_name(self, basic_temp_mock):
        src = TempSource()
        assert src.get_source_name() == "Temp"

    def test_measurement_unit(self, basic_temp_mock):
        src = TempSource()
        assert src.get_measurement_unit() == "C"

    def test_is_available(self, basic_temp_mock):
        src = TempSource()
        assert src.get_is_available() is True

    def test_sensor_count(self, basic_temp_mock):
        src = TempSource()
        assert len(src.get_sensor_list()) == 2

    def test_default_threshold(self, basic_temp_mock):
        src = TempSource()
        assert src.temp_thresh == 80

    def test_custom_threshold(self, basic_temp_mock):
        src = TempSource(temp_thresh=90)
        assert src.temp_thresh == 90

    def test_threshold_list_length(self, basic_temp_mock):
        src = TempSource()
        assert len(src.get_threshold_list()) == 2

    def test_pallet(self, basic_temp_mock):
        src = TempSource()
        assert "temp" in src.get_pallet()[0]

    def test_alert_pallet(self, basic_temp_mock):
        src = TempSource()
        pallet = src.get_alert_pallet()
        assert pallet is not None
        assert "high temp" in pallet[0]


class TestTempSourceFiltering:
    def test_filters_out_low_temp(self, mocker):
        sensors = [
            SensorTemperature(label="Good", current=55.0, high=80.0, critical=100.0),
            SensorTemperature(label="Low", current=0.5, high=80.0, critical=100.0),
        ]
        mocker.patch(
            "psutil.sensors_temperatures", return_value=_make_temp_dict(sensors)
        )
        src = TempSource()
        assert len(src.get_sensor_list()) == 1

    def test_filters_out_high_temp(self, mocker):
        sensors = [
            SensorTemperature(label="Good", current=55.0, high=80.0, critical=100.0),
            SensorTemperature(label="High", current=127.5, high=80.0, critical=100.0),
        ]
        mocker.patch(
            "psutil.sensors_temperatures", return_value=_make_temp_dict(sensors)
        )
        src = TempSource()
        assert len(src.get_sensor_list()) == 1


class TestTempSourceUpdate:
    def test_update_populates_values(self, basic_temp_mock):
        src = TempSource()
        src.update()
        readings = src.get_reading_list()
        assert readings[0] == pytest.approx(55.0)
        assert readings[1] == pytest.approx(60.0)

    def test_update_thresholds(self, basic_temp_mock):
        src = TempSource()
        src.update()
        thresholds = src.get_threshold_list()
        # Sensors have high=80.0, so thresholds should use that
        assert all(t == 80.0 for t in thresholds)


class TestTempSourceEdgeTriggered:
    def test_not_triggered_below_thresh(self, basic_temp_mock):
        src = TempSource()
        src.update()
        assert src.get_edge_triggered() is False

    def test_triggered_above_thresh(self, mocker):
        sensors = [
            SensorTemperature(label="Hot", current=85.0, high=80.0, critical=100.0),
        ]
        mocker.patch(
            "psutil.sensors_temperatures", return_value=_make_temp_dict(sensors)
        )
        src = TempSource()
        src.update()
        assert src.get_edge_triggered() is True

    def test_reset(self, basic_temp_mock):
        src = TempSource()
        src.update()
        src.reset()
        assert src.max_temp == 10


class TestTempSourceAlerts:
    def test_no_alerts_below_threshold(self, basic_temp_mock):
        """Sensors at 55/60 with threshold 80 should have no alerts."""
        src = TempSource()
        src.update()
        alerts = src.get_sensor_alerts()
        assert all(a is None for a in alerts)

    def test_alert_when_above_threshold(self, mocker):
        """Sensor above its threshold should get 'high temp txt' alert."""
        sensors = [
            SensorTemperature(label="Hot", current=85.0, high=80.0, critical=100.0),
            SensorTemperature(label="Cool", current=50.0, high=80.0, critical=100.0),
        ]
        mocker.patch(
            "psutil.sensors_temperatures", return_value=_make_temp_dict(sensors)
        )
        src = TempSource()
        src.update()
        alerts = src.get_sensor_alerts()
        assert alerts[0] == "high temp txt"
        assert alerts[1] is None

    def test_alert_matches_graph_coloring(self, mocker):
        """Alert should trigger for exactly the same sensors as graph coloring."""
        sensors = [
            SensorTemperature(label="Core 0", current=82.0, high=80.0, critical=100.0),
            SensorTemperature(label="Core 1", current=78.0, high=80.0, critical=100.0),
            SensorTemperature(label="Core 2", current=90.0, high=85.0, critical=100.0),
        ]
        mocker.patch(
            "psutil.sensors_temperatures", return_value=_make_temp_dict(sensors)
        )
        src = TempSource()
        src.update()
        alerts = src.get_sensor_alerts()
        # Core 0: 82 > 80 threshold → alert
        assert alerts[0] == "high temp txt"
        # Core 1: 78 < 80 threshold, but global triggered (82 > 80) and has per-sensor
        # threshold, so only per-sensor check applies → no alert
        assert alerts[1] is None
        # Core 2: 90 > 85 threshold → alert
        assert alerts[2] == "high temp txt"
