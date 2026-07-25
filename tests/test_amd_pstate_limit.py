"""Tests for AMD PStateCurLim decoder."""

from s_tui.sources.amd_pstate_limit import (
    ThrottleStatus,
    available,
    read_therm_status,
)


class TestThrottleStatus:
    def test_no_cap(self):
        assert ThrottleStatus(pstate_capped=False).label == ""

    def test_capped(self):
        assert ThrottleStatus(pstate_capped=True).label == "Pc"


class TestReadThermStatus:
    def test_idle_not_capped(self, mocker):
        # Measured on Rembrandt/Cezanne at idle: PstateMaxVal=2, CurPstateLimit=0
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x20)
        status = read_therm_status(0)
        assert status.pstate_capped is False
        assert status.label == ""

    def test_sustained_load_capped(self, mocker):
        # Measured on Rembrandt under all-core load: CurPstateLimit=1
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x21)
        status = read_therm_status(0)
        assert status.pstate_capped is True
        assert status.label == "Pc"

    def test_ignores_pstate_max_val(self, mocker):
        # Only bits[2:0] matter; PstateMaxVal in bits[6:4] must not leak in
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x70)
        assert read_therm_status(0).pstate_capped is False

    def test_deeper_cap(self, mocker):
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x22)
        assert read_therm_status(3).label == "Pc"


ZEN3 = "vendor_id\t: AuthenticAMD\ncpu family\t: 25\nmodel\t\t: 80\n"
BULLDOZER = "vendor_id\t: AuthenticAMD\ncpu family\t: 21\nmodel\t\t: 2\n"
INTEL = "vendor_id\t: GenuineIntel\ncpu family\t: 6\nmodel\t\t: 158\n"


class TestAvailable:
    def test_available_when_msr_works(self, mocker):
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value=ZEN3)
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x20)
        assert available() is True

    def test_unavailable_without_msr(self, mocker):
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value=ZEN3)
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=False)
        assert available() is False

    def test_unavailable_on_read_error(self, mocker):
        # Non-AMD: PStateCurLim is unimplemented, /dev/cpu/N/msr returns EIO
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value=ZEN3)
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", side_effect=OSError)
        assert available() is False

    def test_unavailable_on_pre_zen_family(self, mocker):
        # Family 15h and older are untested; the limit register may track the
        # configured P-state rather than a hardware cap
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value=BULLDOZER)
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x20)
        assert available() is False

    def test_unavailable_on_intel(self, mocker):
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value=INTEL)
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_pstate_limit.read_msr", return_value=0x20)
        assert available() is False

    def test_unavailable_when_cpuinfo_missing(self, mocker):
        mocker.patch("s_tui.sources.amd_pstate_limit.cat", return_value="")
        mocker.patch("s_tui.sources.amd_pstate_limit.msr_available", return_value=True)
        assert available() is False
