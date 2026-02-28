"""Tests for s_tui.helper_functions module."""

import os
import sys
import json
import tempfile

import pytest

from s_tui.helper_functions import (
    __version__,
    cat,
    get_processor_name,
    kill_child_processes,
    make_user_config_dir,
    output_to_json,
    output_to_terminal,
    seconds_to_text,
    str_to_bool,
    which,
    get_config_dir,
    get_user_config_dir,
    get_user_config_file,
    user_config_dir_exists,
    config_dir_exists,
    user_config_file_exists,
)


# ---------------------------------------------------------------------------
# seconds_to_text
# ---------------------------------------------------------------------------

class TestSecondsToText:
    def test_zero(self):
        assert seconds_to_text(0) == "00:00:00"

    def test_seconds_only(self):
        assert seconds_to_text(45) == "00:00:45"

    def test_minutes_and_seconds(self):
        assert seconds_to_text(125) == "00:02:05"

    def test_hours_minutes_seconds(self):
        assert seconds_to_text(3661) == "01:01:01"

    def test_large_value(self):
        assert seconds_to_text(86400) == "24:00:00"


# ---------------------------------------------------------------------------
# str_to_bool
# ---------------------------------------------------------------------------

class TestStrToBool:
    def test_true(self):
        assert str_to_bool("True") is True

    def test_false(self):
        assert str_to_bool("False") is False

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            str_to_bool("true")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            str_to_bool("")

    def test_random_string_raises(self):
        with pytest.raises(ValueError):
            str_to_bool("yes")


# ---------------------------------------------------------------------------
# cat
# ---------------------------------------------------------------------------

class TestCat:
    def test_read_binary(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world\n")
        result = cat(str(f), binary=True)
        assert result == b"hello world"

    def test_read_text(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world\n")
        result = cat(str(f), binary=False)
        assert result == "hello world"

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("  content  \n")
        result = cat(str(f), binary=False)
        assert result == "content"

    def test_missing_file_raises(self):
        with pytest.raises((IOError, OSError)):
            cat("/nonexistent/file/path")

    def test_missing_file_with_fallback(self):
        result = cat("/nonexistent/file/path", fallback="default")
        assert result == "default"

    def test_missing_file_fallback_none(self):
        result = cat("/nonexistent/file/path", fallback=None)
        assert result is None


# ---------------------------------------------------------------------------
# which
# ---------------------------------------------------------------------------

class TestWhich:
    def test_finds_existing_program(self):
        # python3 should be on PATH
        result = which("python3")
        assert result is not None
        assert os.path.isfile(result)

    def test_returns_none_for_nonexistent(self):
        assert which("nonexistent_program_xyz_12345") is None

    def test_absolute_path_executable(self, tmp_path):
        exe = tmp_path / "myexe"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        assert which(str(exe)) == str(exe)

    def test_absolute_path_not_executable(self, tmp_path):
        f = tmp_path / "notexe"
        f.write_text("not executable")
        f.chmod(0o644)
        assert which(str(f)) is None


# ---------------------------------------------------------------------------
# get_processor_name
# ---------------------------------------------------------------------------

class TestGetProcessorName:
    def test_returns_something(self):
        """get_processor_name should return a non-empty value on any platform."""
        result = get_processor_name()
        assert result is not None


# ---------------------------------------------------------------------------
# Config directory helpers
# ---------------------------------------------------------------------------

class TestConfigDirHelpers:
    def test_get_config_dir_with_xdg(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/test_xdg")
        assert get_config_dir() == "/tmp/test_xdg"

    def test_get_config_dir_fallback(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        result = get_config_dir()
        assert result.endswith(".config")

    def test_get_user_config_dir(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/test_xdg")
        assert get_user_config_dir() == "/tmp/test_xdg/s-tui"

    def test_get_user_config_file(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/test_xdg")
        assert get_user_config_file() == "/tmp/test_xdg/s-tui/s-tui.conf"

    def test_user_config_dir_exists_false(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/nonexistent_xdg_test")
        assert user_config_dir_exists() is False

    def test_config_dir_exists_false(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/nonexistent_xdg_test")
        assert config_dir_exists() is False

    def test_user_config_file_exists_false(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/nonexistent_xdg_test")
        assert user_config_file_exists() is False

    def test_make_user_config_dir(self, tmp_path, monkeypatch):
        xdg = tmp_path / "xdg_config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        result = make_user_config_dir()
        assert result is not None
        assert os.path.isdir(result)
        assert os.path.isdir(os.path.join(result, "hooks.d"))


# ---------------------------------------------------------------------------
# kill_child_processes
# ---------------------------------------------------------------------------

class TestKillChildProcesses:
    def test_none_parent(self):
        """Should handle None gracefully (AttributeError caught)."""
        kill_child_processes(None)  # should not raise


# ---------------------------------------------------------------------------
# output_to_terminal / output_to_json
# ---------------------------------------------------------------------------

class TestOutputFunctions:
    def _make_mock_source(self, name, sensors_summary):
        """Create a minimal mock source object."""

        class _MockSrc:
            def get_is_available(self):
                return True

            def update(self):
                pass

            def get_source_name(self):
                return name

            def get_sensors_summary(self):
                return sensors_summary

        return _MockSrc()

    def test_output_to_terminal(self, capsys):
        src = self._make_mock_source("Util", {"Avg": "25.0", "Core 0": "30.0"})
        with pytest.raises(SystemExit):
            output_to_terminal([src])
        captured = capsys.readouterr()
        assert "Util" in captured.out
        assert "25.0" in captured.out

    def test_output_to_json(self, capsys):
        src = self._make_mock_source("Util", {"Avg": "25.0"})
        with pytest.raises(SystemExit):
            output_to_json([src])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "Util" in data
        assert data["Util"]["Avg"] == "25.0"

    def test_output_to_terminal_skips_unavailable(self, capsys):
        class _Unavailable:
            def get_is_available(self):
                return False

        with pytest.raises(SystemExit):
            output_to_terminal([_Unavailable()])
        captured = capsys.readouterr()
        # Only newline should be printed
        assert captured.out.strip() == ""


# ---------------------------------------------------------------------------
# __version__
# ---------------------------------------------------------------------------

class TestVersion:
    def test_version_is_string(self):
        assert isinstance(__version__, str)

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()
