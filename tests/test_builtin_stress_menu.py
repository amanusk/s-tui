"""Tests for BuiltinStressMenu: configuration UI for built-in stresser."""

import psutil

from s_tui.builtin_stress_menu import BuiltinStressMenu
from s_tui.builtin_stresser import STRATEGY_HASHLIB, get_default_strategy


class TestBuiltinStressMenu:
    def test_default_worker_count(self):
        """Default worker count matches CPU count."""
        menu = BuiltinStressMenu(return_fn=lambda: None)
        assert menu.get_num_workers() == psutil.cpu_count()

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
