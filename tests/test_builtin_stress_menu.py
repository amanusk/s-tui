"""Tests for BuiltinStressMenu: configuration UI for built-in stresser."""

import psutil

import s_tui.builtin_stresser as builtin_stresser
from s_tui.builtin_stress_menu import BuiltinStressMenu
from s_tui.builtin_stresser import (
    STRATEGY_HASHLIB,
    STRATEGY_NUMPY,
    get_default_strategy,
)


class TestBuiltinStressMenu:
    def test_default_worker_count(self, monkeypatch):
        """Default worker count matches CPU count."""
        monkeypatch.setattr(psutil, "cpu_count", lambda: 4)
        menu = BuiltinStressMenu(return_fn=lambda: None)
        assert menu.get_num_workers() == 4

    def test_get_size(self):
        """get_size returns a (height, width) tuple of ints."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        height, width = menu.get_size()
        assert isinstance(height, int)
        assert isinstance(width, int)
        assert height > 0
        assert width > 0

    def test_get_num_workers_minimum_one(self):
        """get_num_workers never returns less than 1."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        menu.num_workers = "0"
        assert menu.get_num_workers() == 1

    def test_get_num_workers_invalid_string(self):
        """get_num_workers returns 1 for invalid input."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        menu.num_workers = "abc"
        assert menu.get_num_workers() == 1

    def test_default_strategy(self):
        """Default strategy matches get_default_strategy."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        assert menu.get_strategy() == get_default_strategy()

    def test_cancel_restores_strategy(self):
        """Cancel reverts pending strategy change."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        original = menu.get_strategy()
        # Simulate radio button change (would normally be triggered by UI)
        menu._pending_strategy = STRATEGY_HASHLIB
        menu.on_cancel(None)
        assert menu.get_strategy() == original

    def test_save_commits_strategy(self):
        """Save commits the pending strategy change."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        menu._pending_strategy = STRATEGY_HASHLIB
        menu.on_save(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB

    def test_numpy_not_selectable_when_unavailable(self, monkeypatch):
        """When numpy is missing, its strategy has no selectable radio button.

        Guards against the UI showing "numpy" selected while start() silently
        falls back to hashlib.
        """
        monkeypatch.setattr(builtin_stresser, "_HAS_NUMPY", False)
        menu = BuiltinStressMenu(return_fn=lambda: None)

        # numpy must not be among the selectable radio buttons
        assert STRATEGY_NUMPY not in menu._strategy_buttons
        assert STRATEGY_HASHLIB in menu._strategy_buttons

        # Default and committed strategy fall back to an available kernel
        assert menu.get_strategy() == STRATEGY_HASHLIB

        # Even a forced pending numpy selection (not reachable via the UI) is
        # ignored on save rather than desyncing the committed strategy
        menu._pending_strategy = STRATEGY_NUMPY
        menu.on_save(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB

        # on_default re-derives an available strategy
        menu.on_default(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB
