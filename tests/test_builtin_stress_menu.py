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

    def test_cancel_restores_strategy(self, monkeypatch):
        """Cancel reverts an unsaved radio selection."""
        monkeypatch.setattr(builtin_stresser, "_HAS_NUMPY", True)
        menu = BuiltinStressMenu(return_fn=lambda: None)
        original = menu.get_strategy()
        other = STRATEGY_HASHLIB if original != STRATEGY_HASHLIB else STRATEGY_NUMPY
        # Select the other radio the way a real click does, then cancel.
        menu._strategy_buttons[other].set_state(True)
        menu.on_cancel(None)
        assert menu.get_strategy() == original
        assert menu._strategy_buttons[original].state is True

    def test_save_commits_strategy(self, monkeypatch):
        """Save persists the strategy selected in the radio group (issue #289)."""
        monkeypatch.setattr(builtin_stresser, "_HAS_NUMPY", True)
        menu = BuiltinStressMenu(return_fn=lambda: None)
        # Select hashlib via the actual widget state, not an internal shortcut.
        menu._strategy_buttons[STRATEGY_HASHLIB].set_state(True)
        menu.on_save(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB

    def test_initial_strategy_restored_from_config(self, monkeypatch):
        """A saved strategy is honoured on construction (issue #289)."""
        monkeypatch.setattr(builtin_stresser, "_HAS_NUMPY", True)
        menu = BuiltinStressMenu(
            return_fn=lambda: None, initial_strategy=STRATEGY_HASHLIB
        )
        assert menu.get_strategy() == STRATEGY_HASHLIB
        assert menu._strategy_buttons[STRATEGY_HASHLIB].state is True

    def test_initial_strategy_falls_back_when_unavailable(self, monkeypatch):
        """A saved but unrunnable strategy falls back to an available one."""
        monkeypatch.setattr(builtin_stresser, "_HAS_NUMPY", False)
        menu = BuiltinStressMenu(
            return_fn=lambda: None, initial_strategy=STRATEGY_NUMPY
        )
        assert menu.get_strategy() == STRATEGY_HASHLIB

    def test_initial_strategy_ignores_garbage(self):
        """An unknown saved value falls back to the default strategy."""
        menu = BuiltinStressMenu(return_fn=lambda: None, initial_strategy="bogus")
        assert menu.get_strategy() == get_default_strategy()

    def test_initial_workers_restored_from_config(self):
        """A saved worker count is honoured on construction (issue #289)."""
        menu = BuiltinStressMenu(return_fn=lambda: None, initial_workers="3")
        assert menu.get_num_workers() == 3

    def test_initial_workers_ignores_invalid(self, monkeypatch):
        """An invalid saved worker count falls back to the CPU count."""
        monkeypatch.setattr(psutil, "cpu_count", lambda: 8)
        for bad in ("0", "-2", "abc", ""):
            menu = BuiltinStressMenu(return_fn=lambda: None, initial_workers=bad)
            assert menu.get_num_workers() == 8

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

        # numpy has no radio button, so it cannot be selected or committed;
        # saving keeps the available kernel rather than desyncing.
        menu.on_save(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB

        # on_default re-derives an available strategy
        menu.on_default(None)
        assert menu.get_strategy() == STRATEGY_HASHLIB
