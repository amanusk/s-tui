"""Tests for StressMenu: command building, validation helpers, and defaults."""

import pytest
from unittest.mock import MagicMock

from s_tui.stress_menu import StressMenu


@pytest.fixture
def menu(mocker):
    """Create a StressMenu with psutil.cpu_count mocked to 4."""
    mocker.patch("psutil.cpu_count", return_value=4)
    return_fn = MagicMock()
    return StressMenu(return_fn, "stress")


# =====================================================================
# Initialization
# =====================================================================


class TestStressMenuInit:
    def test_defaults(self, menu):
        """Default values after construction."""
        assert menu.stress_exe == "stress"
        assert menu.time_out == "none"
        assert menu.sqrt_workers == "4"  # cpu_count mocked to 4
        assert menu.sync_workers == "0"
        assert menu.memory_workers == "0"
        assert menu.malloc_byte == "256M"
        assert menu.byte_touch_cnt == "4096"
        assert menu.malloc_delay == "none"
        assert menu.no_malloc is False
        assert menu.write_workers == "0"
        assert menu.write_bytes == "1G"

    def test_cpu_count_fallback_on_error(self, mocker):
        """If psutil.cpu_count raises, sqrt_workers defaults to 1."""
        mocker.patch("psutil.cpu_count", side_effect=OSError("no cpus"))
        m = StressMenu(MagicMock(), "stress")
        assert m.sqrt_workers == "1"


# =====================================================================
# get_stress_cmd
# =====================================================================


class TestGetStressCmd:
    def test_default_cmd(self, menu):
        """Default command includes -c with cpu_count."""
        cmd = menu.get_stress_cmd()
        assert cmd[0] == "stress"
        assert "-c" in cmd
        idx = cmd.index("-c")
        assert cmd[idx + 1] == "4"

    def test_no_sqrt_workers(self, menu):
        """When sqrt_workers is 0, -c is omitted."""
        menu.sqrt_workers = "0"
        cmd = menu.get_stress_cmd()
        assert "-c" not in cmd

    def test_sync_workers(self, menu):
        """sync_workers > 0 adds -i flag."""
        menu.sync_workers = "2"
        cmd = menu.get_stress_cmd()
        assert "-i" in cmd
        assert cmd[cmd.index("-i") + 1] == "2"

    def test_memory_workers(self, menu):
        """memory_workers > 0 adds --vm, --vm-bytes, --vm-stride."""
        menu.memory_workers = "3"
        cmd = menu.get_stress_cmd()
        assert "--vm" in cmd
        assert cmd[cmd.index("--vm") + 1] == "3"
        assert "--vm-bytes" in cmd
        assert "--vm-stride" in cmd

    def test_no_malloc_adds_vm_keep(self, menu):
        """When no_malloc is True, --vm-keep is added."""
        menu.no_malloc = True
        cmd = menu.get_stress_cmd()
        assert "--vm-keep" in cmd

    def test_no_malloc_false(self, menu):
        """When no_malloc is False, --vm-keep not present."""
        menu.no_malloc = False
        cmd = menu.get_stress_cmd()
        assert "--vm-keep" not in cmd

    def test_write_workers(self, menu):
        """write_workers > 0 adds --hdd and --hdd-bytes."""
        menu.write_workers = "1"
        cmd = menu.get_stress_cmd()
        assert "--hdd" in cmd
        assert cmd[cmd.index("--hdd") + 1] == "1"
        assert "--hdd-bytes" in cmd

    def test_timeout(self, menu):
        """Non-"none" timeout adds -t flag."""
        menu.time_out = "60"
        cmd = menu.get_stress_cmd()
        assert "-t" in cmd
        assert cmd[cmd.index("-t") + 1] == "60"

    def test_timeout_none(self, menu):
        """When timeout is "none", -t is omitted."""
        menu.time_out = "none"
        cmd = menu.get_stress_cmd()
        assert "-t" not in cmd

    def test_full_cmd(self, menu):
        """A fully configured command has all flags."""
        menu.sqrt_workers = "2"
        menu.sync_workers = "1"
        menu.memory_workers = "1"
        menu.no_malloc = True
        menu.write_workers = "1"
        menu.time_out = "120"
        cmd = menu.get_stress_cmd()
        assert "-c" in cmd
        assert "-i" in cmd
        assert "--vm" in cmd
        assert "--vm-keep" in cmd
        assert "--hdd" in cmd
        assert "-t" in cmd


# =====================================================================
# Validation helpers
# =====================================================================


class TestStressMenuValidation:
    def test_get_pos_num_valid(self):
        assert StressMenu.get_pos_num("42", "0") == "42"

    def test_get_pos_num_zero(self):
        assert StressMenu.get_pos_num("0", "1") == "0"

    def test_get_pos_num_none_with_none_default(self):
        assert StressMenu.get_pos_num("none", "none") == "none"

    def test_get_pos_num_none_with_numeric_default(self):
        assert StressMenu.get_pos_num("none", "4") == "4"

    def test_get_pos_num_invalid(self):
        assert StressMenu.get_pos_num("abc", "5") == "5"

    def test_get_pos_num_negative(self):
        assert StressMenu.get_pos_num("-1", "0") == "0"

    def test_get_pos_num_float(self):
        assert StressMenu.get_pos_num("3.5", "0") == "0"

    def test_get_valid_byte_plain_number(self):
        assert StressMenu.get_valid_byte("256", "0") == "256"

    def test_get_valid_byte_megabytes(self):
        assert StressMenu.get_valid_byte("256M", "0") == "256M"

    def test_get_valid_byte_gigabytes(self):
        assert StressMenu.get_valid_byte("1G", "0") == "1G"

    def test_get_valid_byte_with_b_suffix(self):
        assert StressMenu.get_valid_byte("256MB", "0") == "256MB"

    def test_get_valid_byte_invalid(self):
        assert StressMenu.get_valid_byte("abc", "1G") == "1G"

    def test_get_valid_byte_empty(self):
        assert StressMenu.get_valid_byte("", "1G") == "1G"


# =====================================================================
# on_default resets to defaults
# =====================================================================


class TestStressMenuOnDefault:
    def test_on_default_resets(self, menu):
        """on_default() resets all fields and calls return_fn."""
        menu.sqrt_workers = "8"
        menu.time_out = "60"
        menu.sync_workers = "5"
        menu.on_default(None)
        assert menu.sqrt_workers == "1"
        assert menu.time_out == "none"
        assert menu.sync_workers == "0"
        menu.return_fn.assert_called_once()


# =====================================================================
# get_size
# =====================================================================


class TestStressMenuGetSize:
    def test_get_size(self, menu):
        """get_size() returns tuple of (height, width)."""
        size = menu.get_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert size[1] == StressMenu.MAX_TITLE_LEN
