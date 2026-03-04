"""Tests for BuiltinStresser: worker lifecycle and strategy selection."""

import time

from s_tui.builtin_stresser import (
    _HAS_NUMPY,
    STRATEGIES,
    STRATEGY_HASHLIB,
    STRATEGY_LABELS,
    STRATEGY_NUMPY,
    BuiltinStresser,
    get_default_strategy,
    strategy_available,
)


class TestBuiltinStresserLifecycle:
    def test_start_and_stop(self):
        """Workers start and are cleaned up after stop."""
        stresser = BuiltinStresser()
        stresser.start(2)
        assert stresser.is_running()
        stresser.stop(timeout=3)
        assert not stresser.is_running()

    def test_stop_when_not_started(self):
        """Calling stop without start is safe (no-op)."""
        stresser = BuiltinStresser()
        stresser.stop()  # should not raise
        assert not stresser.is_running()

    def test_double_stop(self):
        """Calling stop twice is safe."""
        stresser = BuiltinStresser()
        stresser.start(1)
        stresser.stop(timeout=3)
        stresser.stop(timeout=3)  # should not raise
        assert not stresser.is_running()

    def test_restart(self):
        """Starting after a stop works correctly."""
        stresser = BuiltinStresser()
        stresser.start(1)
        stresser.stop(timeout=3)
        stresser.start(1)
        assert stresser.is_running()
        stresser.stop(timeout=3)
        assert not stresser.is_running()

    def test_start_cleans_previous(self):
        """Calling start while running stops previous workers first."""
        stresser = BuiltinStresser()
        stresser.start(1)
        stresser.start(2)  # should stop first, then start 2
        # Allow brief time for processes to spawn
        time.sleep(0.1)
        assert stresser.is_running()
        stresser.stop(timeout=3)


class TestStrategySelection:
    def test_default_strategy_is_valid(self):
        """get_default_strategy returns one of the known keys."""
        assert get_default_strategy() in STRATEGIES

    def test_default_strategy_matches_numpy_availability(self):
        """Default is numpy when available, hashlib otherwise."""
        if _HAS_NUMPY:
            assert get_default_strategy() == STRATEGY_NUMPY
        else:
            assert get_default_strategy() == STRATEGY_HASHLIB

    def test_hashlib_always_available(self):
        """hashlib strategy is always available."""
        assert strategy_available(STRATEGY_HASHLIB)

    def test_numpy_availability_matches_import(self):
        """numpy strategy availability matches whether numpy can be imported."""
        assert strategy_available(STRATEGY_NUMPY) == _HAS_NUMPY

    def test_all_strategies_have_labels(self):
        """Every strategy key has a human-readable label."""
        for key in STRATEGIES:
            assert key in STRATEGY_LABELS
            assert len(STRATEGY_LABELS[key]) > 0

    def test_start_with_explicit_hashlib(self):
        """Can start workers with explicit hashlib strategy."""
        stresser = BuiltinStresser()
        stresser.start(1, strategy=STRATEGY_HASHLIB)
        assert stresser.is_running()
        stresser.stop(timeout=3)

    def test_start_with_unavailable_strategy_falls_back(self, mocker):
        """Requesting unavailable strategy falls back to hashlib."""
        mocker.patch("s_tui.builtin_stresser.strategy_available", return_value=False)
        mock_warn = mocker.patch("s_tui.builtin_stresser.logging.warning")
        stresser = BuiltinStresser()
        stresser.start(1, strategy=STRATEGY_NUMPY)
        assert stresser.is_running()
        mock_warn.assert_called_once()
        assert "falling back to hashlib" in mock_warn.call_args[0][0]
        stresser.stop(timeout=3)
