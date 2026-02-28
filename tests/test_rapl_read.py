"""Tests for rapl_read module: reader classes and get_power_reader selection."""

import os
import pytest
from unittest.mock import MagicMock, mock_open, patch, call
from collections import namedtuple

from s_tui.sources.rapl_read import (
    RaplReader,
    AMDEnergyReader,
    AMDRaplMsrReader,
    RaplStats,
    get_power_reader,
    INTER_RAPL_DIR,
    MICRO_JOULE_IN_JOULE,
)

# =====================================================================
# RaplReader
# =====================================================================


class TestRaplReader:
    def test_available_true(self, mocker):
        """available() returns True when intel-rapl sysfs exists."""
        mocker.patch("os.path.exists", return_value=True)
        assert RaplReader.available() is True

    def test_available_false(self, mocker):
        """available() returns False when intel-rapl sysfs missing."""
        mocker.patch("os.path.exists", return_value=False)
        assert RaplReader.available() is False

    def test_init_discovers_basenames(self, mocker):
        """__init__ globs for intel-rapl:* directories."""
        mocker.patch(
            "glob.glob",
            return_value=[
                "/sys/class/powercap/intel-rapl:0/",
                "/sys/class/powercap/intel-rapl:1/",
            ],
        )
        reader = RaplReader()
        assert len(reader.basenames) == 2

    def test_read_power_returns_rapl_stats(self, mocker):
        """read_power() returns list of RaplStats namedtuples."""
        mocker.patch(
            "glob.glob",
            return_value=[
                "/sys/class/powercap/intel-rapl:0/",
            ],
        )
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            side_effect=[
                "package-0",  # name
                "123456789",  # energy_uj
            ],
        )
        reader = RaplReader()
        result = reader.read_power()
        assert len(result) == 1
        assert result[0].label == "package-0"
        assert result[0].current == 123456789.0
        assert result[0].max == 0.0

    def test_read_power_skips_on_ioerror(self, mocker):
        """read_power() skips entries that raise IOError."""
        mocker.patch(
            "glob.glob",
            return_value=[
                "/sys/class/powercap/intel-rapl:0/",
                "/sys/class/powercap/intel-rapl:1/",
            ],
        )
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            side_effect=[
                IOError("read failed"),  # name read for :0
                "package-1",  # name read for :1
                "999",  # energy_uj for :1
            ],
        )
        reader = RaplReader()
        result = reader.read_power()
        assert len(result) == 1
        assert result[0].label == "package-1"

    def test_read_power_empty_when_no_basenames(self, mocker):
        """read_power() returns empty list when no basenames found."""
        mocker.patch("glob.glob", return_value=[])
        reader = RaplReader()
        result = reader.read_power()
        assert result == []

    def test_read_power_skips_none_name(self, mocker):
        """read_power() skips entry when name is None."""
        mocker.patch(
            "glob.glob",
            return_value=[
                "/sys/class/powercap/intel-rapl:0/",
            ],
        )
        mocker.patch("s_tui.sources.rapl_read.cat", return_value=None)
        reader = RaplReader()
        result = reader.read_power()
        assert result == []


# =====================================================================
# AMDEnergyReader
# =====================================================================


class TestAMDEnergyReader:
    def test_available_true(self, mocker):
        """available() returns True when amd_energy sysfs exists."""
        mocker.patch("os.path.exists", return_value=True)
        assert AMDEnergyReader.available() is True

    def test_available_false(self, mocker):
        """available() returns False when amd_energy sysfs missing."""
        mocker.patch("os.path.exists", return_value=False)
        assert AMDEnergyReader.available() is False

    def test_match_label_socket(self):
        """match_label extracts socket info."""
        m = AMDEnergyReader.match_label("Esocket0")
        assert m is not None
        assert m.group(1) == "socket"
        assert m.group(2) == "0"

    def test_match_label_core(self):
        """match_label extracts core info."""
        m = AMDEnergyReader.match_label("Ecore3")
        assert m is not None
        assert m.group(1) == "core"
        assert m.group(2) == "3"

    def test_match_label_no_match(self):
        """match_label returns None for non-matching labels."""
        m = AMDEnergyReader.match_label("something_else")
        assert m is None

    def test_get_input_position_socket(self):
        """Socket labels get positions 0..socket_number-1."""
        assert AMDEnergyReader.get_input_position("Esocket0", 2) == 0
        assert AMDEnergyReader.get_input_position("Esocket1", 2) == 1

    def test_get_input_position_core(self):
        """Core labels get positions starting after socket_number."""
        assert AMDEnergyReader.get_input_position("Ecore0", 2) == 2
        assert AMDEnergyReader.get_input_position("Ecore1", 2) == 3


# =====================================================================
# AMDRaplMsrReader
# =====================================================================


class TestAMDRaplMsrReader:
    def test_available_non_amd_cpu(self, mocker):
        """available() returns False for Intel CPU."""
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            return_value="model name\t: Intel Core\nvendor_id\t: GenuineIntel\ncpu family\t: 6\n",
        )
        assert AMDRaplMsrReader.available() is False

    def test_available_wrong_family(self, mocker):
        """available() returns False for AMD CPU with wrong family."""
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            return_value="vendor_id\t: AuthenticAMD\ncpu family\t: 25\n",
        )
        assert AMDRaplMsrReader.available() is False

    def test_available_correct_family_no_msr(self, mocker):
        """available() returns False when MSR device is missing."""
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            return_value="vendor_id\t: AuthenticAMD\ncpu family\t: 23\n",
        )
        mocker.patch("builtins.open", side_effect=FileNotFoundError)
        assert AMDRaplMsrReader.available() is False

    def test_available_correct_family_with_msr(self, mocker):
        """available() returns True for family 0x17 AMD with MSR access."""
        mocker.patch(
            "s_tui.sources.rapl_read.cat",
            return_value="vendor_id\t: AuthenticAMD\ncpu family\t: 23\n",
        )
        mock_file = MagicMock()
        mocker.patch("builtins.open", return_value=mock_file)
        assert AMDRaplMsrReader.available() is True

    def test_available_cpuinfo_not_found(self, mocker):
        """available() returns False when /proc/cpuinfo is missing."""
        mocker.patch("s_tui.sources.rapl_read.cat", side_effect=FileNotFoundError)
        assert AMDRaplMsrReader.available() is False


# =====================================================================
# get_power_reader selection
# =====================================================================


class TestGetPowerReader:
    def test_returns_rapl_reader_when_available(self, mocker):
        """get_power_reader prefers RaplReader when available."""
        mocker.patch.object(RaplReader, "available", return_value=True)
        mocker.patch("glob.glob", return_value=[])
        reader = get_power_reader()
        assert isinstance(reader, RaplReader)

    def test_returns_amd_energy_reader_second(self, mocker):
        """get_power_reader falls back to AMDEnergyReader."""
        mocker.patch.object(RaplReader, "available", return_value=False)
        mocker.patch.object(AMDEnergyReader, "available", return_value=True)
        # Mock glob for AMDEnergyReader init
        mocker.patch("glob.glob", return_value=[])
        mocker.patch("s_tui.sources.rapl_read.cat", return_value="Esocket0")
        reader = get_power_reader()
        assert isinstance(reader, AMDEnergyReader)

    def test_returns_none_when_nothing_available(self, mocker):
        """get_power_reader returns None when no reader is available."""
        mocker.patch.object(RaplReader, "available", return_value=False)
        mocker.patch.object(AMDEnergyReader, "available", return_value=False)
        mocker.patch.object(AMDRaplMsrReader, "available", return_value=False)
        reader = get_power_reader()
        assert reader is None

    def test_rapl_stats_namedtuple(self):
        """RaplStats has the expected fields."""
        stat = RaplStats(label="pkg", current=42.0, max=100.0)
        assert stat.label == "pkg"
        assert stat.current == 42.0
        assert stat.max == 100.0
