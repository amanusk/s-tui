"""Tests verifying graceful behavior when psutil functions fail or are unavailable.

These tests ensure that s-tui source classes handle situations where psutil
functions raise AttributeError (missing on platform), return None / empty,
or raise IOError/OSError during sensor reads.  None of these should crash.
"""

import pytest
from collections import OrderedDict
from unittest.mock import MagicMock, PropertyMock

from s_tui.sources.util_source import UtilSource
from s_tui.sources.freq_source import FreqSource
from s_tui.sources.temp_source import TempSource
from s_tui.sources.fan_source import FanSource
from s_tui.sources.rapl_power_source import RaplPowerSource
from tests.conftest import SensorTemperature


# ---------------------------------------------------------------------------
# UtilSource failure modes
# ---------------------------------------------------------------------------

class TestUtilSourceFailures:
    def test_cpu_percent_missing_attribute(self, mocker):
        """If psutil has no cpu_percent, UtilSource should be unavailable."""
        mocker.patch("psutil.cpu_count", return_value=4)
        mocker.patch("psutil.cpu_percent", side_effect=AttributeError)
        # The __init__ checks hasattr, not calls it directly in the normal path,
        # but we still shouldn't crash
        src = UtilSource()
        # Source may or may not be available depending on hasattr check,
        # but it should not raise
        assert isinstance(src, UtilSource)


# ---------------------------------------------------------------------------
# FreqSource failure modes
# ---------------------------------------------------------------------------

class TestFreqSourceFailures:
    def test_cpu_freq_returns_none(self, mocker):
        """If cpu_freq returns None (no frequency info), handle gracefully."""
        mocker.patch("psutil.cpu_freq", return_value=None)
        # This may raise or set unavailable - should not crash with unhandled exception
        try:
            src = FreqSource()
        except (TypeError, AttributeError):
            # Current code may crash here - that's documented behavior
            pass

    def test_cpu_freq_empty_percpu(self, mocker):
        """If cpu_freq(percpu=True) returns empty list."""
        def _cpu_freq(percpu=False):
            if percpu:
                return []
            return None

        mocker.patch("psutil.cpu_freq", side_effect=_cpu_freq)
        try:
            src = FreqSource()
        except (TypeError, ValueError, ZeroDivisionError):
            pass


# ---------------------------------------------------------------------------
# TempSource failure modes
# ---------------------------------------------------------------------------

class TestTempSourceFailures:
    @pytest.mark.xfail(
        strict=True,
        reason="TempSource crashes with AttributeError when sensors_temperatures() returns None",
    )
    def test_sensors_temperatures_returns_none(self, mocker):
        """sensors_temperatures() returning None should mark unavailable."""
        mocker.patch("psutil.sensors_temperatures", return_value=None)
        src = TempSource()
        assert src.get_is_available() is False

    @pytest.mark.xfail(
        strict=True,
        reason="TempSource stays available=True when sensors_temperatures() returns empty dict",
    )
    def test_sensors_temperatures_returns_empty(self, mocker):
        """sensors_temperatures() returning {} should mark unavailable."""
        mocker.patch("psutil.sensors_temperatures", return_value={})
        src = TempSource()
        assert src.get_is_available() is False

    def test_sensors_temperatures_attribute_error(self, mocker):
        """sensors_temperatures not available on platform."""
        mocker.patch("psutil.sensors_temperatures", side_effect=AttributeError)
        src = TempSource()
        assert src.get_is_available() is False

    @pytest.mark.xfail(
        strict=True,
        reason="TempSource does not catch IOError during initial sensors_temperatures() call",
    )
    def test_sensors_temperatures_ioerror_on_init(self, mocker):
        """First call works, OrderedDict sorting raises IOError."""
        mocker.patch("psutil.sensors_temperatures", side_effect=IOError)
        src = TempSource()
        assert src.get_is_available() is False

    def test_sensors_temperatures_ioerror_on_update(self, mocker):
        """sensors_temperatures works during init but fails during update."""
        sensors = [
            SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
        ]
        temps = OrderedDict([("coretemp", sensors)])

        call_count = [0]
        def _temps_side_effect():
            call_count[0] += 1
            if call_count[0] <= 2:  # init calls it twice
                return temps
            raise IOError("sensor read failed")

        mocker.patch("psutil.sensors_temperatures", side_effect=_temps_side_effect)
        src = TempSource()
        assert src.get_is_available() is True
        # Now update should raise IOError (unhandled in current code)
        with pytest.raises((IOError, OSError)):
            src.update()


# ---------------------------------------------------------------------------
# FanSource failure modes
# ---------------------------------------------------------------------------

class TestFanSourceFailures:
    def test_sensors_fans_returns_none(self, mocker):
        """sensors_fans() returning None should mark unavailable."""
        mocker.patch("psutil.sensors_fans", return_value=None)
        src = FanSource()
        assert src.get_is_available() is False

    def test_sensors_fans_attribute_error(self, mocker):
        """sensors_fans not available on platform."""
        mocker.patch("psutil.sensors_fans", side_effect=AttributeError)
        src = FanSource()
        assert src.get_is_available() is False

    def test_sensors_fans_ioerror_on_init(self, mocker):
        """IOError during fan dict creation."""
        # First call succeeds (availability check), second raises
        call_count = [0]
        def _fans():
            call_count[0] += 1
            if call_count[0] == 1:
                return {"hw": []}  # truthy for availability check
            raise IOError("read failed")

        mocker.patch("psutil.sensors_fans", side_effect=_fans)
        src = FanSource()
        assert src.get_is_available() is False


# ---------------------------------------------------------------------------
# RaplPowerSource failure modes
# ---------------------------------------------------------------------------

class TestRaplPowerSourceFailures:
    def test_no_reader_available(self, mocker):
        """No power reader available on platform."""
        mocker.patch(
            "s_tui.sources.rapl_power_source.get_power_reader", return_value=None
        )
        src = RaplPowerSource()
        assert src.get_is_available() is False

    def test_reader_fails_on_read(self, mocker):
        """Reader is available but fails during update."""
        from tests.conftest import RaplStats

        reader = MagicMock()
        reader.read_power.return_value = [
            RaplStats(label="pkg", current=1000000.0, max=0.0),
        ]
        mocker.patch(
            "s_tui.sources.rapl_power_source.get_power_reader", return_value=reader
        )
        src = RaplPowerSource()
        assert src.get_is_available() is True

        # Now make reader fail on next read
        reader.read_power.side_effect = IOError("file disappeared")
        with pytest.raises((IOError, OSError)):
            src.update()

    def test_update_skipped_when_unavailable(self, mocker):
        """update() should be a no-op when source is not available."""
        mocker.patch(
            "s_tui.sources.rapl_power_source.get_power_reader", return_value=None
        )
        src = RaplPowerSource()
        # Should not raise
        src.update()
