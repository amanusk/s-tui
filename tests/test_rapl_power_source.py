"""Tests for RaplPowerSource with mocked reader."""

import time

import pytest
from unittest.mock import MagicMock

from s_tui.sources.rapl_power_source import RaplPowerSource
from tests.conftest import RaplStats


@pytest.fixture
def mock_power_reader(mocker):
    """Mock get_power_reader to return a fake reader with 2 domains."""
    reader = MagicMock()
    reader.read_power.return_value = [
        RaplStats(label="package-0", current=1000000.0, max=0.0),
        RaplStats(label="core", current=500000.0, max=0.0),
    ]
    mocker.patch(
        "s_tui.sources.rapl_power_source.get_power_reader", return_value=reader
    )
    return reader


@pytest.fixture
def mock_no_power_reader(mocker):
    """Mock get_power_reader to return None (no reader available)."""
    mocker.patch("s_tui.sources.rapl_power_source.get_power_reader", return_value=None)


class TestRaplPowerSourceInit:
    def test_name(self, mock_power_reader):
        src = RaplPowerSource()
        assert src.get_source_name() == "Power"

    def test_measurement_unit(self, mock_power_reader):
        src = RaplPowerSource()
        assert src.get_measurement_unit() == "W"

    def test_is_available(self, mock_power_reader):
        src = RaplPowerSource()
        assert src.get_is_available() is True

    def test_sensor_list(self, mock_power_reader):
        src = RaplPowerSource()
        sensors = src.get_sensor_list()
        assert len(sensors) == 2

    def test_pallet(self, mock_power_reader):
        src = RaplPowerSource()
        assert "power" in src.get_pallet()[0]


class TestRaplPowerSourceUnavailable:
    def test_no_reader(self, mock_no_power_reader):
        src = RaplPowerSource()
        assert src.get_is_available() is False


class TestRaplPowerSourceUpdate:
    def test_update_computes_watts(self, mock_power_reader):
        src = RaplPowerSource()
        # Simulate time passing and energy increasing
        mock_power_reader.read_power.return_value = [
            RaplStats(label="package-0", current=2000000.0, max=0.0),
            RaplStats(label="core", current=1000000.0, max=0.0),
        ]
        # Small sleep to get non-zero seconds_passed
        time.sleep(0.05)
        src.update()
        readings = src.get_reading_list()
        # Values should be positive (energy increased)
        assert all(r >= 0 for r in readings)

    def test_get_maximum(self, mock_power_reader):
        src = RaplPowerSource()
        assert src.get_maximum() == 1

    def test_get_top(self, mock_power_reader):
        src = RaplPowerSource()
        assert src.get_top() == 1
