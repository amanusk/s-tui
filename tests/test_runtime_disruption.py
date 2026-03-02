"""Runtime disruption tests -- simulating mid-run sensor/core changes.

These tests mock psutil to return normal data during __init__, then change
the mock before calling update() to simulate real-world events like CPU
hotplug, sensor disconnection, or permission changes.

All tests are marked @pytest.mark.xfail(strict=True) to document current
crashes without blocking CI.  When each crash is fixed, remove the xfail
marker so the test becomes a regression guard.
"""

import pytest
from collections import OrderedDict, namedtuple
from unittest.mock import MagicMock

from s_tui.sources.util_source import UtilSource
from s_tui.sources.freq_source import FreqSource
from s_tui.sources.temp_source import TempSource
from s_tui.sources.fan_source import FanSource
from s_tui.sources.rapl_power_source import RaplPowerSource
from tests.conftest import (
    CpuFreq,
    SensorTemperature,
    SensorFan,
    RaplStats,
    make_cpu_freq_list,
    make_cpu_freq_overall,
    make_temperatures_dict,
    make_fans_dict,
)

# =====================================================================
# UtilSource -- core count changes
# =====================================================================


class TestUtilCoreCountChanges:
    @pytest.mark.xfail(
        strict=True,
        reason="get_sensors_summary() IndexError when last_measurement > available_sensors",
    )
    def test_core_count_grows(self, mocker):
        """Simulate a core coming online mid-run (e.g. CPU hotplug)."""
        mocker.patch("psutil.cpu_count", return_value=4)
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0])
        src = UtilSource()
        assert len(src.get_sensor_list()) == 5  # Avg + 4 cores

        # Core comes online: 5 values now returned
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0, 10.0])
        src.update()

        # This should not crash
        summary = src.get_sensors_summary()
        assert summary is not None

    def test_core_count_shrinks(self, mocker):
        """Simulate a core going offline mid-run.

        The code marks offline cores as N/A and keeps the sensor list
        at its original length.
        """
        mocker.patch("psutil.cpu_count", return_value=4)
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0])
        mocker.patch("s_tui.sources.source.Source._get_max_cpu_id", return_value=4)
        mocker.patch(
            "s_tui.sources.source.Source._get_online_cpu_ids",
            return_value=[0, 1, 2, 3],
        )
        src = UtilSource()
        assert len(src.get_sensor_list()) == 5

        # Core goes offline: only 3 values, online_ids shrinks
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0])
        mocker.patch(
            "s_tui.sources.source.Source._get_online_cpu_ids",
            return_value=[0, 1, 2],
        )
        src.update()

        # Does not crash; sensor_list keeps original length
        summary = src.get_sensors_summary()
        assert summary is not None


# =====================================================================
# FreqSource -- core count changes
# =====================================================================


class TestFreqCoreCountChanges:
    def test_freq_core_count_shrinks(self, mocker):
        """cpu_freq(percpu=True) returns fewer cores after init.

        The code marks disappeared cores as N/A without crashing.
        """
        per_cpu_4 = make_cpu_freq_list(4)
        overall = make_cpu_freq_overall()

        def _freq_init(percpu=False):
            return per_cpu_4 if percpu else overall

        mocker.patch("psutil.cpu_freq", side_effect=_freq_init)
        mocker.patch("s_tui.sources.source.Source._get_max_cpu_id", return_value=4)
        mocker.patch(
            "s_tui.sources.source.Source._get_online_cpu_ids",
            return_value=[0, 1, 2, 3],
        )
        src = FreqSource()
        assert len(src.get_sensor_list()) == 5

        # Now fewer cores
        per_cpu_2 = make_cpu_freq_list(2)

        def _freq_shrunk(percpu=False):
            return per_cpu_2 if percpu else overall

        mocker.patch("psutil.cpu_freq", side_effect=_freq_shrunk)
        mocker.patch(
            "s_tui.sources.source.Source._get_online_cpu_ids",
            return_value=[0, 1],
        )
        src.update()

        summary = src.get_sensors_summary()
        assert summary is not None


# =====================================================================
# TempSource -- sensor appear / disappear
# =====================================================================


class TestTempSensorChanges:
    def test_temp_sensor_disappears(self, mocker):
        """sensors_temperatures() returns fewer sensors mid-run.

        Current behaviour: no crash; sensor list retains original length,
        missing sensors may show stale data.
        """
        sensors_2 = [
            SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
            SensorTemperature(label="Core 1", current=60.0, high=80.0, critical=100.0),
        ]
        temps_2 = OrderedDict([("coretemp", sensors_2)])
        mocker.patch("psutil.sensors_temperatures", return_value=temps_2)
        src = TempSource()
        assert len(src.get_sensor_list()) == 2

        # Sensor disappears
        sensors_1 = [
            SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
        ]
        temps_1 = OrderedDict([("coretemp", sensors_1)])
        mocker.patch("psutil.sensors_temperatures", return_value=temps_1)
        src.update()

        summary = src.get_sensors_summary()
        assert summary is not None

    @pytest.mark.xfail(
        strict=True,
        reason="TempSource summary IndexError when new sensor appears mid-run",
    )
    def test_temp_sensor_appears(self, mocker):
        """New sensor shows up in sensors_temperatures() mid-run."""
        sensors_1 = [
            SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
        ]
        temps_1 = OrderedDict([("coretemp", sensors_1)])
        mocker.patch("psutil.sensors_temperatures", return_value=temps_1)
        src = TempSource()
        assert len(src.get_sensor_list()) == 1

        # New sensor appears
        sensors_2 = [
            SensorTemperature(label="Core 0", current=55.0, high=80.0, critical=100.0),
            SensorTemperature(label="Core 1", current=60.0, high=80.0, critical=100.0),
        ]
        temps_2 = OrderedDict([("coretemp", sensors_2)])
        mocker.patch("psutil.sensors_temperatures", return_value=temps_2)
        src.update()

        summary = src.get_sensors_summary()
        assert len(summary) == len(src.get_reading_list())


# =====================================================================
# FanSource -- sensor disappear / None
# =====================================================================


class TestFanSensorChanges:
    def test_fan_returns_none_during_update(self, mocker):
        """sensors_fans() returns None mid-run — keeps stale data (GH-256)."""
        fans = make_fans_dict(count=1)
        mocker.patch("psutil.sensors_fans", return_value=fans)
        src = FanSource()
        assert src.get_is_available() is True
        src.update()
        prev_measurement = list(src.last_measurement)

        # Mid-run: returns None
        mocker.patch("psutil.sensors_fans", return_value=None)
        src.update()  # should not crash
        # Stale data preserved
        assert src.last_measurement == prev_measurement

    def test_fan_typeerror_during_update(self, mocker):
        """sensors_fans() raises TypeError mid-run — keeps stale data (GH-256)."""
        fans = make_fans_dict(count=1)
        mocker.patch("psutil.sensors_fans", return_value=fans)
        src = FanSource()
        assert src.get_is_available() is True
        src.update()
        prev_measurement = list(src.last_measurement)

        # Mid-run: psutil raises TypeError (sysfs None bug)
        mocker.patch("psutil.sensors_fans", side_effect=TypeError)
        src.update()  # should not crash
        # Stale data preserved
        assert src.last_measurement == prev_measurement

    def test_fan_sensor_disappears(self, mocker):
        """sensors_fans() returns empty dict mid-run.

        Current behaviour: no crash; sensor list retains original length,
        missing fans show stale data.
        """
        fans = make_fans_dict(count=1)
        mocker.patch("psutil.sensors_fans", return_value=fans)
        src = FanSource()
        assert len(src.get_sensor_list()) == 1

        # Sensor disappears
        mocker.patch("psutil.sensors_fans", return_value={})
        src.update()

        summary = src.get_sensors_summary()
        assert summary is not None


# =====================================================================
# RaplPowerSource -- reader failure mid-run
# =====================================================================


class TestRaplReaderFailsMidRun:
    def test_rapl_reader_fails_during_update(self, mocker):
        """RAPL energy file becomes unreadable mid-run."""
        reader = MagicMock()
        reader.read_power.return_value = [
            RaplStats(label="pkg", current=1000000.0, max=0.0),
        ]
        mocker.patch(
            "s_tui.sources.rapl_power_source.get_power_reader", return_value=reader
        )
        src = RaplPowerSource()
        assert src.get_is_available() is True

        # File disappears
        reader.read_power.side_effect = IOError("permission denied")
        src.update()  # should not crash
        assert src.get_is_available() is True  # or False, but no crash


# =====================================================================
# Source.update() exception propagation
# =====================================================================


class TestSourceUpdateExceptionPropagation:
    def test_source_update_raises_oserror(self, mocker):
        """Any psutil call raises OSError during update() — should not propagate."""
        mocker.patch("psutil.cpu_count", return_value=4)
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0])
        mocker.patch("s_tui.sources.source.Source._get_max_cpu_id", return_value=4)
        mocker.patch(
            "s_tui.sources.source.Source._get_online_cpu_ids",
            return_value=[0, 1, 2, 3],
        )
        src = UtilSource()

        mocker.patch("psutil.cpu_percent", side_effect=OSError("device gone"))
        # In current code this propagates unhandled
        # The test verifies we want it to NOT propagate
        try:
            src.update()
        except OSError:
            pytest.fail("update() should not propagate OSError to caller")


# =====================================================================
# Summary after sensor mismatch
# =====================================================================


class TestSummaryAfterMismatch:
    @pytest.mark.xfail(
        strict=True,
        reason="get_sensors_summary() IndexError when last_measurement length != available_sensors",
    )
    def test_summary_after_measurement_grows(self, mocker):
        """get_summary() after last_measurement has more entries than available_sensors."""
        mocker.patch("psutil.cpu_count", return_value=2)
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0])
        src = UtilSource()
        assert len(src.get_sensor_list()) == 3  # Avg + 2 cores

        # 4 cores now
        mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0])
        src.update()

        # This is the crash point: available_sensors has 3, last_measurement has 5
        summary = src.get_summary()
        assert summary is not None
