"""Tests for FreqSource with mocked psutil."""

import pytest

from s_tui.sources.freq_source import FreqSource, _read_throttle_count


def _make_fake_throttle_reader(
    throttle_core: int = 0,
    core_base: int = 100,
    pkg_base: int = 200,
    pkg_throttle: bool = False,
):
    """Factory for sysfs throttle counter mocks.

    Returns a callable suitable for ``mocker.patch(..., side_effect=...)``.
    By default, core ``throttle_core`` increases its ``core_throttle_count``
    by 1 on the second read (simulating throttle on first update).
    Set ``pkg_throttle=True`` to simulate a package throttle instead.
    """
    call_counts: dict[str, int] = {}

    def fake_read(core_id, counter):
        if counter == "core_throttle_count":
            if not pkg_throttle and core_id == throttle_core:
                key = f"core_{core_id}"
                call_counts[key] = call_counts.get(key, 0) + 1
                return core_base if call_counts[key] <= 1 else core_base + 1
            return core_base
        if counter == "package_throttle_count":
            if pkg_throttle:
                call_counts["pkg"] = call_counts.get("pkg", 0) + 1
                return pkg_base if call_counts["pkg"] <= 1 else pkg_base + 1
            return pkg_base
        return None

    return fake_read


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
        # Frequency summary uses integer values (no decimal)
        assert summary["Avg"] == "2400"


class TestFreqSourceThrottle:
    """Tests for sysfs-based throttle detection in FreqSource."""

    def test_no_throttle_by_default(self, mock_cpu_freq, mocker):
        """When sysfs is unavailable, no throttle suffixes should be set."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.available", return_value=False
        )
        src = FreqSource()
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert all(s == "" for s in suffixes)

    def test_no_throttle_alerts_by_default(self, mock_cpu_freq, mocker):
        """When not throttled, all sensor alerts should be None."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.available", return_value=False
        )
        src = FreqSource()
        src.update()
        alerts = src.get_sensor_alerts()
        assert all(a is None for a in alerts)

    def test_edge_triggered_always_false(self, mock_cpu_freq):
        """FreqSource uses per-sensor thresholds, not global edge trigger."""
        src = FreqSource()
        assert src.get_edge_triggered() is False

    def test_alert_pallet_set(self, mock_cpu_freq):
        """FreqSource should have an alert pallet for throttle coloring."""
        src = FreqSource()
        assert src.get_alert_pallet() is not None
        assert "throttle" in src.get_alert_pallet()[0]

    def test_core_throttle_detected(self, mock_cpu_freq, mocker):
        """When core_throttle_count increases, core gets 'Tc' suffix."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(),
        )
        src = FreqSource()
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert "Tc" in suffixes[0]  # Avg
        assert "Tc" in suffixes[1]  # Core 0
        assert suffixes[2] == ""  # Core 1 - not throttled

    def test_core_throttle_sets_threshold(self, mock_cpu_freq, mocker):
        """Throttled core should have threshold 0.0 to trigger alert colors."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(),
        )
        src = FreqSource()
        src.update()
        # Core 0 (sensor index 1) should have threshold 0.0
        assert src.last_thresholds[1] == 0.0
        # Core 1 (sensor index 2) should have no threshold
        assert src.last_thresholds[2] is None
        # Avg (sensor index 0) should be triggered (any core throttled)
        assert src.last_thresholds[0] == 0.0

    def test_core_throttle_sets_alert(self, mock_cpu_freq, mocker):
        """Throttled core should have alert attribute for summary coloring."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(),
        )
        src = FreqSource()
        src.update()
        alerts = src.get_sensor_alerts()
        assert alerts[0] == "throttle txt"  # Avg
        assert alerts[1] == "throttle txt"  # Core 0
        assert alerts[2] is None  # Core 1

    def test_package_throttle_detected(self, mock_cpu_freq, mocker):
        """When package_throttle_count increases, all cores show 'Tp'."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(pkg_throttle=True),
        )
        src = FreqSource()
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert suffixes[0] == "Tp"  # Avg
        assert suffixes[1] == "Tp"  # Core 0

    def test_throttle_clears_after_interval(self, mock_cpu_freq, mocker):
        """When counts stop increasing, throttle indicators disappear."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(),
        )
        src = FreqSource()
        src.update()  # first update: throttled
        assert src.last_thresholds[1] == 0.0
        src.update()  # second update: count unchanged, no longer throttled
        assert src.last_thresholds[1] is None

    def test_sysfs_unavailable_graceful(self, mock_cpu_freq, mocker):
        """When sysfs files don't exist, throttle detection is disabled."""
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            return_value=None,
        )
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.available", return_value=False
        )
        src = FreqSource()
        assert src._throttle_available is False
        src.update()
        # No crash, no throttle indicators
        summary = src.get_sensors_summary()
        for val in summary.values():
            assert "Tc" not in val
            assert "Tp" not in val


class TestReadThrottleCount:
    """Tests for the _read_throttle_count helper."""

    def test_reads_sysfs_value(self, tmp_path):
        """Reads an integer from a sysfs-like file."""
        throttle_dir = tmp_path / "cpu0" / "thermal_throttle"
        throttle_dir.mkdir(parents=True)
        (throttle_dir / "core_throttle_count").write_text("42\n")

        import s_tui.sources.freq_source as mod

        orig = mod.SYSFS_THERMAL_THROTTLE
        mod.SYSFS_THERMAL_THROTTLE = str(tmp_path / "cpu{}" / "thermal_throttle")
        try:
            assert _read_throttle_count(0, "core_throttle_count") == 42
        finally:
            mod.SYSFS_THERMAL_THROTTLE = orig

    def test_returns_none_on_missing(self):
        """Returns None for non-existent files."""
        assert _read_throttle_count(999, "core_throttle_count") is None


class TestFreqSourceMsrThrottle:
    """Tests for MSR-based throttle detection in FreqSource."""

    def test_msr_label_shown_when_available(self, mock_cpu_freq, mocker):
        """When MSR is available, per-core labels come from IA32_THERM_STATUS."""
        from s_tui.sources.intel_therm import ThrottleStatus

        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=True
        )
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()
        assert src._msr_backend == "intel_msr"

        # Simulate MSR reporting thermal + power limit on core 0
        status_tw = ThrottleStatus(True, False, False, True, False, False)
        status_none = ThrottleStatus(False, False, False, False, False, False)

        def fake_read(cpu):
            return status_tw if cpu == 0 else status_none

        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.read_therm_status",
            side_effect=fake_read,
        )
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert suffixes[0] == "T/W"  # Avg gets first non-empty
        assert suffixes[1] == "T/W"  # Core 0
        assert suffixes[2] == ""  # Core 1

    def test_msr_sets_alerts(self, mock_cpu_freq, mocker):
        """MSR throttle labels trigger alert coloring."""
        from s_tui.sources.intel_therm import ThrottleStatus

        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=True
        )
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()

        status_w = ThrottleStatus(False, False, False, True, False, False)
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.read_therm_status",
            return_value=status_w,
        )
        src.update()
        alerts = src.get_sensor_alerts()
        assert alerts[0] == "throttle txt"
        assert alerts[1] == "throttle txt"

    def test_msr_oserror_clears_label(self, mock_cpu_freq, mocker):
        """If MSR read fails for a core, its label is cleared."""
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=True
        )
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.read_therm_status",
            side_effect=OSError("permission denied"),
        )
        src.update()
        assert all(label == "" for label in src._throttle_labels)

    def test_falls_back_to_sysfs(self, mock_cpu_freq, mocker):
        """When MSR unavailable, sysfs detection still works."""
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.available", return_value=False
        )
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count",
            side_effect=_make_fake_throttle_reader(),
        )
        src = FreqSource()
        assert src._msr_backend is None
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert "Tc" in suffixes[1]


class TestFreqSourceAmdMsrThrottle:
    """Tests for AMD MSR-based throttle detection in FreqSource."""

    def test_amd_msr_label_shown_when_available(self, mock_cpu_freq, mocker):
        """When AMD MSR is available, per-core labels come from PSTATE_CUR_LIMIT."""
        from s_tui.sources.amd_therm import AmdThrottleStatus

        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch("s_tui.sources.freq_source.amd_therm.available", return_value=True)
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()
        assert src._msr_backend == "amd_msr"

        status_w = AmdThrottleStatus(smu_limited=True, below_base=False)
        status_none = AmdThrottleStatus(smu_limited=False, below_base=False)

        def fake_read(cpu):
            return status_w if cpu == 0 else status_none

        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.read_throttle_status",
            side_effect=fake_read,
        )
        src.update()
        suffixes = src.get_sensor_suffixes()
        assert suffixes[0] == "W"  # Avg gets first non-empty
        assert suffixes[1] == "W"  # Core 0
        assert suffixes[2] == ""  # Core 1

    def test_amd_msr_sets_alerts(self, mock_cpu_freq, mocker):
        """AMD throttle labels trigger alert coloring."""
        from s_tui.sources.amd_therm import AmdThrottleStatus

        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch("s_tui.sources.freq_source.amd_therm.available", return_value=True)
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()

        status_wf = AmdThrottleStatus(smu_limited=True, below_base=True)
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.read_throttle_status",
            return_value=status_wf,
        )
        src.update()
        alerts = src.get_sensor_alerts()
        assert alerts[0] == "throttle txt"
        assert alerts[1] == "throttle txt"
        suffixes = src.get_sensor_suffixes()
        assert suffixes[1] == "W/F"

    def test_amd_msr_oserror_clears_label(self, mock_cpu_freq, mocker):
        """If AMD MSR read fails for a core, its label is cleared."""
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=False
        )
        mocker.patch("s_tui.sources.freq_source.amd_therm.available", return_value=True)
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()
        mocker.patch(
            "s_tui.sources.freq_source.amd_therm.read_throttle_status",
            side_effect=OSError("permission denied"),
        )
        src.update()
        assert all(label == "" for label in src._throttle_labels)

    def test_intel_preferred_over_amd(self, mock_cpu_freq, mocker):
        """When both Intel and AMD are available, Intel takes priority."""
        mocker.patch(
            "s_tui.sources.freq_source.intel_therm.available", return_value=True
        )
        mocker.patch("s_tui.sources.freq_source.amd_therm.available", return_value=True)
        mocker.patch(
            "s_tui.sources.freq_source._read_throttle_count", return_value=None
        )
        src = FreqSource()
        assert src._msr_backend == "intel_msr"
