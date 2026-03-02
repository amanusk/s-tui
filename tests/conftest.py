"""Shared fixtures, markers, and psutil mock helpers for the s-tui test suite."""

import os
from collections import namedtuple, OrderedDict

import pytest

# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "hardware: test requires real hardware sensors (skipped in CI)"
    )


def _is_ci():
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def pytest_collection_modifyitems(config, items):
    """Auto-skip hardware-marked tests when running inside CI."""
    if _is_ci():
        skip_hw = pytest.mark.skip(reason="Hardware not available in CI")
        for item in items:
            if "hardware" in item.keywords:
                item.add_marker(skip_hw)


# ---------------------------------------------------------------------------
# Named-tuple helpers (mirror psutil's own types)
# ---------------------------------------------------------------------------

CpuFreq = namedtuple("scpufreq", ["current", "min", "max"])
SensorTemperature = namedtuple("shwtemp", ["label", "current", "high", "critical"])
SensorFan = namedtuple("sfan", ["label", "current"])
RaplStats = namedtuple("rapl", ["label", "current", "max"])


# ---------------------------------------------------------------------------
# Default fake data builders
# ---------------------------------------------------------------------------


def make_cpu_freq_list(count=4, current=2400.0, min_freq=800.0, max_freq=3600.0):
    """Return a list of *count* CpuFreq named-tuples."""
    return [CpuFreq(current=current, min=min_freq, max=max_freq) for _ in range(count)]


def make_cpu_freq_overall(current=2400.0, min_freq=800.0, max_freq=3600.0):
    """Return a single CpuFreq named-tuple (overall)."""
    return CpuFreq(current=current, min=min_freq, max=max_freq)


def make_temperatures_dict(
    count=2,
    label_prefix="Core",
    current=55.0,
    high=80.0,
    critical=100.0,
    group_name="coretemp",
):
    """Return an OrderedDict matching psutil.sensors_temperatures() shape."""
    sensors = []
    for i in range(count):
        sensors.append(
            SensorTemperature(
                label=f"{label_prefix} {i}",
                current=current,
                high=high,
                critical=critical,
            )
        )
    return OrderedDict([(group_name, sensors)])


def make_fans_dict(count=1, label_prefix="fan", current=1200, group_name="thinkpad"):
    """Return a dict matching psutil.sensors_fans() shape."""
    fans = []
    for i in range(count):
        fans.append(SensorFan(label=f"{label_prefix}{i}", current=current))
    return {group_name: fans}


# ---------------------------------------------------------------------------
# Reusable psutil mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_cpu_count(mocker):
    """Mock psutil.cpu_count to return 4, with matching topology helpers."""
    mocker.patch(
        "s_tui.sources.source.Source._get_max_cpu_id", return_value=4
    )
    mocker.patch(
        "s_tui.sources.source.Source._get_online_cpu_ids",
        return_value=[0, 1, 2, 3],
    )
    return mocker.patch("psutil.cpu_count", return_value=4)


@pytest.fixture
def mock_cpu_percent(mocker):
    """Mock psutil.cpu_percent to return per-cpu values for 4 cores."""
    return mocker.patch("psutil.cpu_percent", return_value=[25.0, 30.0, 20.0, 15.0])


@pytest.fixture
def mock_cpu_freq(mocker):
    """Mock psutil.cpu_freq for 4 cores + overall, with matching topology helpers."""
    per_cpu = make_cpu_freq_list(4)
    overall = make_cpu_freq_overall()

    def _cpu_freq(percpu=False):
        if percpu:
            return per_cpu
        return overall

    mocker.patch(
        "s_tui.sources.source.Source._get_max_cpu_id", return_value=4
    )
    mocker.patch(
        "s_tui.sources.source.Source._get_online_cpu_ids",
        return_value=[0, 1, 2, 3],
    )
    return mocker.patch("psutil.cpu_freq", side_effect=_cpu_freq)


@pytest.fixture
def mock_sensors_temperatures(mocker):
    """Mock psutil.sensors_temperatures with 2 coretemp sensors."""
    temps = make_temperatures_dict(count=2)
    return mocker.patch("psutil.sensors_temperatures", return_value=temps)


@pytest.fixture
def mock_sensors_fans(mocker):
    """Mock psutil.sensors_fans with 1 fan."""
    fans = make_fans_dict(count=1)
    return mocker.patch("psutil.sensors_fans", return_value=fans)
