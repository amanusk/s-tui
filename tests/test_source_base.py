"""Tests for the Source base class and MockSource."""

import pytest
from unittest.mock import MagicMock
from collections import OrderedDict

from s_tui.sources.source import Source, MockSource


class TestSourceInit:
    def test_defaults(self):
        src = Source()
        assert src.name == ""
        assert src.measurement_unit == ""
        assert src.is_available is True
        assert src.last_measurement == []
        assert src.last_thresholds == []
        assert src.available_sensors == []
        assert src.edge_hooks == []
        assert src.alert_pallet is None

    def test_pallet_has_four_entries(self):
        src = Source()
        assert len(src.pallet) == 4


class TestSourceAccessors:
    def setup_method(self):
        self.src = Source()
        self.src.name = "TestSrc"
        self.src.measurement_unit = "MHz"
        self.src.available_sensors = ["Avg", "Core 0"]
        self.src.last_measurement = [100.0, 200.0]

    def test_get_source_name(self):
        assert self.src.get_source_name() == "TestSrc"

    def test_get_measurement_unit(self):
        assert self.src.get_measurement_unit() == "MHz"

    def test_get_is_available(self):
        assert self.src.get_is_available() is True

    def test_get_sensor_list(self):
        assert self.src.get_sensor_list() == ["Avg", "Core 0"]

    def test_get_reading_list(self):
        assert self.src.get_reading_list() == [100.0, 200.0]

    def test_get_threshold_list(self):
        self.src.last_thresholds = [80, 80]
        assert self.src.get_threshold_list() == [80, 80]

    def test_get_pallet(self):
        assert len(self.src.get_pallet()) == 4

    def test_get_alert_pallet_default_none(self):
        assert self.src.get_alert_pallet() is None


class TestSourceSummary:
    def test_get_sensors_summary(self):
        src = Source()
        src.available_sensors = ["Avg", "Core 0"]
        src.last_measurement = [25.5, 30.1]
        summary = src.get_sensors_summary()
        assert isinstance(summary, OrderedDict)
        assert summary["Avg"] == "25.5"
        assert summary["Core 0"] == "30.1"

    def test_get_summary_includes_name_and_unit(self):
        src = Source()
        src.name = "Util"
        src.measurement_unit = "%"
        src.available_sensors = ["Avg"]
        src.last_measurement = [50.0]
        summary = src.get_summary()
        assert summary["Util"] == "[%]"
        assert summary["Avg"] == "50.0"

    def test_get_sensors_summary_rounds_to_one_decimal(self):
        src = Source()
        src.available_sensors = ["S1"]
        src.last_measurement = [33.3333333]
        summary = src.get_sensors_summary()
        assert summary["S1"] == "33.3"


class TestSourceNotImplemented:
    def test_get_maximum_raises(self):
        with pytest.raises(NotImplementedError):
            Source().get_maximum()

    def test_get_top_raises(self):
        with pytest.raises(NotImplementedError):
            Source().get_top()

    def test_reset_raises(self):
        with pytest.raises(NotImplementedError):
            Source().reset()

    def test_get_edge_triggered_raises(self):
        with pytest.raises(NotImplementedError):
            Source().get_edge_triggered()


class TestSourceHooks:
    def test_add_edge_hook(self):
        src = Source()
        hook = MagicMock()
        src.add_edge_hook(hook)
        assert len(src.edge_hooks) == 1
        assert src.edge_hooks[0] is hook

    def test_add_none_hook_ignored(self):
        src = Source()
        src.add_edge_hook(None)
        assert len(src.edge_hooks) == 0

    def test_eval_hooks_invokes_when_triggered(self):
        src = Source()
        src.get_edge_triggered = MagicMock(return_value=True)
        hook = MagicMock()
        hook.is_ready.return_value = True
        src.add_edge_hook(hook)
        src.eval_hooks()
        hook.invoke.assert_called_once()

    def test_eval_hooks_skips_not_ready(self):
        src = Source()
        src.get_edge_triggered = MagicMock(return_value=True)
        hook = MagicMock()
        hook.is_ready.return_value = False
        src.add_edge_hook(hook)
        src.eval_hooks()
        hook.invoke.assert_not_called()

    def test_eval_hooks_skips_when_not_triggered(self):
        src = Source()
        src.get_edge_triggered = MagicMock(return_value=False)
        hook = MagicMock()
        hook.is_ready.return_value = True
        src.add_edge_hook(hook)
        src.eval_hooks()
        hook.invoke.assert_not_called()

    def test_update_calls_eval_hooks(self):
        src = Source()
        # Override get_edge_triggered so eval_hooks doesn't raise
        src.get_edge_triggered = MagicMock(return_value=False)
        src.eval_hooks = MagicMock()
        src.update()
        src.eval_hooks.assert_called_once()


class TestMockSource:
    def test_get_maximum(self):
        ms = MockSource()
        assert ms.get_maximum() == 20

    def test_get_summary(self):
        ms = MockSource()
        summary = ms.get_summary()
        assert "MockValue" in summary
        assert summary["MockValue"] == 5

    def test_get_edge_triggered_raises(self):
        with pytest.raises(NotImplementedError):
            MockSource().get_edge_triggered()
