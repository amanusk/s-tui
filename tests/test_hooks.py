"""Tests for Hook, ScriptHook, and ScriptHookLoader."""

import os
import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, call

from s_tui.sources.hook import Hook
from s_tui.sources.hook_script import ScriptHook
from s_tui.sources.script_hook_loader import ScriptHookLoader


# =====================================================================
# Hook
# =====================================================================

class TestHook:
    def test_init_callback_stored(self):
        """Hook stores the callback."""
        cb = MagicMock()
        h = Hook(cb)
        assert h.callback is cb

    def test_init_default_timeout_zero(self):
        """Default timeout is 0 (no cooldown)."""
        h = Hook(MagicMock())
        assert h.timeout_milliseconds == 0

    def test_init_custom_timeout(self):
        """Custom timeout is stored."""
        h = Hook(MagicMock(), timeout_milliseconds=500)
        assert h.timeout_milliseconds == 500

    def test_is_ready_initially_true(self):
        """A freshly created hook should be ready immediately."""
        h = Hook(MagicMock())
        assert h.is_ready() is True

    def test_invoke_calls_callback(self):
        """invoke() should call the callback with callback_args."""
        cb = MagicMock()
        h = Hook(cb, 0, "arg1", "arg2")
        h.invoke()
        cb.assert_called_once_with(("arg1", "arg2"))

    def test_invoke_no_args(self):
        """invoke() passes empty tuple when no extra args given."""
        cb = MagicMock()
        h = Hook(cb)
        h.invoke()
        cb.assert_called_once_with(())

    def test_invoke_no_cooldown_always_ready(self):
        """With timeout_milliseconds=0 the hook is always ready."""
        cb = MagicMock()
        h = Hook(cb, 0)
        h.invoke()
        assert h.is_ready() is True
        h.invoke()
        assert h.is_ready() is True

    def test_invoke_with_cooldown_sets_not_ready(self):
        """After invoke with timeout>0, the hook should not be ready."""
        cb = MagicMock()
        h = Hook(cb, timeout_milliseconds=5000)
        h.invoke()
        assert h.is_ready() is False

    def test_cooldown_expires(self):
        """After cooldown expires the hook is ready again."""
        cb = MagicMock()
        h = Hook(cb, timeout_milliseconds=50)
        h.invoke()
        assert h.is_ready() is False
        time.sleep(0.06)
        assert h.is_ready() is True

    def test_multiple_invokes_with_cooldown(self):
        """Multiple invoke() calls extend the cooldown each time."""
        cb = MagicMock()
        h = Hook(cb, timeout_milliseconds=50)
        h.invoke()
        time.sleep(0.06)
        assert h.is_ready() is True
        h.invoke()
        assert h.is_ready() is False
        assert cb.call_count == 2


# =====================================================================
# ScriptHook
# =====================================================================

class TestScriptHook:
    def test_init_stores_path(self, tmp_path):
        """ScriptHook stores the script path."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        sh = ScriptHook(str(script))
        assert sh.path == str(script)

    def test_is_ready_initially(self, tmp_path):
        """ScriptHook is ready immediately after creation."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        sh = ScriptHook(str(script))
        assert sh.is_ready() is True

    def test_is_ready_with_timeout(self, tmp_path):
        """ScriptHook respects timeout from underlying Hook."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        sh = ScriptHook(str(script), timeout_milliseconds=5000)
        assert sh.is_ready() is True
        sh.invoke()
        assert sh.is_ready() is False

    def test_invoke_runs_script(self, tmp_path, mocker):
        """invoke() triggers a subprocess call."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o755)

        mock_popen = mocker.patch("subprocess.Popen")
        sh = ScriptHook(str(script))
        sh.invoke()
        mock_popen.assert_called_once()
        # First arg to Popen should be ["/bin/sh", script_path]
        args, kwargs = mock_popen.call_args
        assert args[0] == ["/bin/sh", str(script)]

    def test_internal_hook_type(self, tmp_path):
        """The internal hook attribute should be a Hook instance."""
        script = tmp_path / "test.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        sh = ScriptHook(str(script))
        assert isinstance(sh.hook, Hook)


# =====================================================================
# ScriptHookLoader
# =====================================================================

class TestScriptHookLoader:
    def test_init_sets_hooks_dir(self, tmp_path):
        """ScriptHookLoader computes the hooks.d subdirectory path."""
        loader = ScriptHookLoader(str(tmp_path))
        expected = os.path.join(str(tmp_path), "hooks.d")
        assert loader.scripts_dir_path == expected

    def test_source_to_script_name(self):
        """_source_to_script_name converts source name to lowercase .sh."""
        loader = ScriptHookLoader("/tmp")
        assert loader._source_to_script_name("TempSource") == "tempsource.sh"
        assert loader._source_to_script_name("UtilSource") == "utilsource.sh"
        assert loader._source_to_script_name("CPU Freq") == "cpu freq.sh"

    def test_load_script_returns_none_if_missing(self, tmp_path):
        """load_script() returns None when the script file doesn't exist."""
        hooks_dir = tmp_path / "hooks.d"
        hooks_dir.mkdir()
        loader = ScriptHookLoader(str(tmp_path))
        result = loader.load_script("NoSource")
        assert result is None

    def test_load_script_returns_script_hook(self, tmp_path):
        """load_script() returns a ScriptHook when the script file exists."""
        hooks_dir = tmp_path / "hooks.d"
        hooks_dir.mkdir()
        script = hooks_dir / "tempsource.sh"
        script.write_text("#!/bin/sh\necho 'hot'\n")
        script.chmod(0o755)

        loader = ScriptHookLoader(str(tmp_path))
        result = loader.load_script("TempSource")
        assert isinstance(result, ScriptHook)
        assert result.path == str(script)

    def test_load_script_with_timeout(self, tmp_path):
        """load_script() passes timeout to ScriptHook."""
        hooks_dir = tmp_path / "hooks.d"
        hooks_dir.mkdir()
        script = hooks_dir / "fansource.sh"
        script.write_text("#!/bin/sh\necho 'fan'\n")
        script.chmod(0o755)

        loader = ScriptHookLoader(str(tmp_path))
        result = loader.load_script("FanSource", timeoutMilliseconds=1000)
        assert isinstance(result, ScriptHook)
        assert result.hook.timeout_milliseconds == 1000

    def test_load_script_no_hooks_dir(self, tmp_path):
        """load_script() returns None when hooks.d directory doesn't exist."""
        loader = ScriptHookLoader(str(tmp_path))
        result = loader.load_script("TempSource")
        assert result is None
