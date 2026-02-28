"""Tests for FreqSource with mocked psutil."""

import pytest

from s_tui.sources.freq_source import FreqSource


class TestFreqSourceInit:
    def test_name(self, mock_cpu_freq):
        src = FreqSource()
        assert src.get_source_name() == "Frequency"

    def test_measurement_unit(self, mock_cpu_freq):
        src = FreqSource()
        assert src.get_measurement_unit() == "MHz"

    def test_is_available(self, mock_cpu_freq):
        src = FreqSource()
        assert src.get_is_available() is True

    def test_sensor_list(self, mock_cpu_freq):
        src = FreqSource()
        sensors = src.get_sensor_list()
        assert sensors[0] == "Avg"
        assert len(sensors) == 5  # Avg + 4 cores

    def test_top_freq(self, mock_cpu_freq):
        src = FreqSource()
        assert src.get_top() == 3600.0

    def test_max_freq(self, mock_cpu_freq):
        src = FreqSource()
        assert src.get_maximum() == 3600.0

    def test_pallet(self, mock_cpu_freq):
        src = FreqSource()
        assert "freq" in src.get_pallet()[0]


class TestFreqSourceUpdate:
    def test_update_populates_values(self, mock_cpu_freq):
        src = FreqSource()
        src.update()
        readings = src.get_reading_list()
        # avg of 4 x 2400.0 = 2400.0
        assert readings[0] == pytest.approx(2400.0)
        assert all(r == pytest.approx(2400.0) for r in readings[1:])

    def test_update_summary(self, mock_cpu_freq):
        src = FreqSource()
        src.update()
        summary = src.get_sensors_summary()
        assert "Avg" in summary
        assert "Core 0" in summary
