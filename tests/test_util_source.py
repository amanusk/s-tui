"""Tests for UtilSource with mocked psutil."""

import pytest

from s_tui.sources.util_source import UtilSource


class TestUtilSourceInit:
    def test_name(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert src.get_source_name() == "Util"

    def test_measurement_unit(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert src.get_measurement_unit() == "%"

    def test_is_available(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert src.get_is_available() is True

    def test_sensor_list_length(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        # Avg + 4 cores
        assert len(src.get_sensor_list()) == 5

    def test_sensor_list_names(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        sensors = src.get_sensor_list()
        assert sensors[0] == "Avg"
        assert sensors[1] == "Core 0"
        assert sensors[4] == "Core 3"

    def test_initial_measurement_zeros(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert src.get_reading_list() == [0, 0, 0, 0, 0]

    def test_get_top(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert src.get_top() == 100

    def test_pallet(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        assert "util" in src.get_pallet()[0]


class TestUtilSourceUpdate:
    def test_update_populates_values(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        src.update()
        readings = src.get_reading_list()
        # avg should be mean of [25, 30, 20, 15] = 22.5
        assert readings[0] == pytest.approx(22.5)
        assert readings[1] == 25.0
        assert readings[2] == 30.0
        assert readings[3] == 20.0
        assert readings[4] == 15.0

    def test_update_summary(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        src.update()
        summary = src.get_sensors_summary()
        assert "Avg" in summary
        assert "Core 0" in summary

    def test_update_full_summary(self, mock_cpu_count, mock_cpu_percent):
        src = UtilSource()
        src.update()
        summary = src.get_summary()
        assert summary["Util"] == "[%]"
