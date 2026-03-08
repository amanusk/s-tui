"""Tests for the shared MSR reader utility."""

import struct

from s_tui.sources.msr import msr_available, read_msr


class TestReadMsr:
    def test_reads_via_dev_cpu(self, mocker):
        """read_msr opens /dev/cpu/{cpu}/msr and seeks to register."""
        value = 0x42
        data = struct.pack("<Q", value)
        mock_open = mocker.mock_open(read_data=data)
        mocker.patch("builtins.open", mock_open)
        result = read_msr(3, 0x19C)
        mock_open.assert_called_once_with("/dev/cpu/3/msr", "rb")
        mock_open().seek.assert_called_once_with(0x19C)
        assert result == value


class TestMsrAvailable:
    def test_available_when_readable(self, mocker):
        mocker.patch("builtins.open", mocker.mock_open())
        assert msr_available() is True

    def test_unavailable_on_permission_error(self, mocker):
        mocker.patch("builtins.open", side_effect=PermissionError)
        assert msr_available() is False

    def test_unavailable_on_file_not_found(self, mocker):
        mocker.patch("builtins.open", side_effect=FileNotFoundError)
        assert msr_available() is False
