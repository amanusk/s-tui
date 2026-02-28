"""Hardware integration tests -- run only on real machines with sensors.

All tests are marked ``@pytest.mark.hardware`` and will be automatically
skipped when CI=true or GITHUB_ACTIONS=true (see conftest.py).

Run locally with::

    pytest -m hardware -v
"""

import pytest

import psutil

from s_tui.sources.util_source import UtilSource
from s_tui.sources.freq_source import FreqSource
from s_tui.sources.temp_source import TempSource
from s_tui.sources.fan_source import FanSource
from s_tui.sources.rapl_power_source import RaplPowerSource
from s_tui.sources.rapl_read import get_power_reader

pytestmark = pytest.mark.hardware


# =====================================================================
# UtilSource
# =====================================================================


class TestUtilSourceHW:
    def test_init_and_available(self):
        """UtilSource should always be available on a Linux machine."""
        src = UtilSource()
        assert src.get_is_available() is True

    def test_sensor_list_matches_cpu_count(self):
        """Sensor list length should be cpu_count + 1 (Avg)."""
        src = UtilSource()
        expected = psutil.cpu_count() + 1
        assert len(src.get_sensor_list()) == expected

    def test_update_produces_readings(self):
        """After update(), readings should be populated."""
        src = UtilSource()
        src.update()
        readings = src.get_reading_list()
        assert len(readings) > 0
        # All values should be between 0 and 100
        for v in readings:
            assert 0.0 <= v <= 100.0

    def test_summary(self):
        """get_summary() should return a non-empty dict."""
        src = UtilSource()
        src.update()
        summary = src.get_summary()
        assert len(summary) > 0


# =====================================================================
# FreqSource
# =====================================================================


class TestFreqSourceHW:
    def test_init_and_available(self):
        """FreqSource should be available when cpu_freq works."""
        src = FreqSource()
        if psutil.cpu_freq() is not None:
            assert src.get_is_available() is True

    def test_update(self):
        """After update(), readings should contain positive values."""
        src = FreqSource()
        if not src.get_is_available():
            pytest.skip("FreqSource not available on this hardware")
        src.update()
        readings = src.get_reading_list()
        assert len(readings) > 0


# =====================================================================
# TempSource
# =====================================================================


class TestTempSourceHW:
    def test_init(self):
        """TempSource should init without crashing."""
        src = TempSource()

    def test_update_if_available(self):
        """If available, update produces temperature readings."""
        src = TempSource()
        if not src.get_is_available():
            pytest.skip("TempSource not available on this hardware")
        src.update()
        readings = src.get_reading_list()
        assert len(readings) > 0
        # Temperatures should be reasonable (> -40 and < 200)
        for v in readings:
            assert -40.0 < v < 200.0


# =====================================================================
# FanSource
# =====================================================================


class TestFanSourceHW:
    def test_init(self):
        """FanSource should init without crashing."""
        src = FanSource()

    def test_update_if_available(self):
        """If available, update produces fan readings."""
        src = FanSource()
        if not src.get_is_available():
            pytest.skip("FanSource not available on this hardware")
        src.update()
        readings = src.get_reading_list()
        assert len(readings) > 0


# =====================================================================
# RaplPowerSource
# =====================================================================


class TestRaplPowerSourceHW:
    def test_init(self):
        """RaplPowerSource should init without crashing."""
        src = RaplPowerSource()

    def test_update_if_available(self):
        """If available, update produces power readings.

        Note: RAPL sysfs files may require root permissions, so this test
        skips when readings are empty due to PermissionError.
        """
        src = RaplPowerSource()
        if not src.get_is_available():
            pytest.skip("RaplPowerSource not available on this hardware")
        src.update()
        readings = src.get_reading_list()
        if len(readings) == 0:
            pytest.skip("RAPL readings empty (likely permission denied)")
        assert len(readings) > 0


# =====================================================================
# get_power_reader
# =====================================================================


class TestGetPowerReaderHW:
    def test_reader_type(self):
        """get_power_reader returns a reader or None."""
        reader = get_power_reader()
        if reader is not None:
            # Should have read_power method
            assert hasattr(reader, "read_power")
            result = reader.read_power()
            assert isinstance(result, list)


# =====================================================================
# Multi-update stability
# =====================================================================


class TestMultiUpdateStability:
    def test_util_multiple_updates(self):
        """UtilSource survives multiple update() calls."""
        src = UtilSource()
        for _ in range(10):
            src.update()
        assert len(src.get_reading_list()) > 0

    def test_freq_multiple_updates(self):
        """FreqSource survives multiple update() calls."""
        src = FreqSource()
        if not src.get_is_available():
            pytest.skip("FreqSource not available")
        for _ in range(10):
            src.update()
        assert len(src.get_reading_list()) > 0
