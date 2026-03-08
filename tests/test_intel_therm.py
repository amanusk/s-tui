"""Tests for Intel IA32_THERM_STATUS decoder."""

from s_tui.sources.intel_therm import (
    CRITICAL_STATUS,
    CROSS_DOMAIN_STATUS,
    CURRENT_LIMIT_STATUS,
    POWER_LIMIT_STATUS,
    PROCHOT_STATUS,
    THERMAL_STATUS,
    ThrottleStatus,
    available,
    read_therm_status,
)


class TestThrottleStatus:
    def test_no_throttle(self):
        s = ThrottleStatus(False, False, False, False, False, False)
        assert s.any_active is False
        assert s.label == ""

    def test_single_reason(self):
        s = ThrottleStatus(thermal=True, prochot=False, critical=False,
                           power_limit=False, current_limit=False, cross_domain=False)
        assert s.any_active is True
        assert s.label == "T"

    def test_multiple_reasons(self):
        s = ThrottleStatus(thermal=True, prochot=False, critical=False,
                           power_limit=True, current_limit=False, cross_domain=False)
        assert s.label == "T/W"

    def test_all_reasons(self):
        s = ThrottleStatus(True, True, True, True, True, True)
        assert s.label == "T/H/C/W/A/X"


class TestReadThermStatus:
    def test_decodes_thermal_and_power(self, mocker):
        val = THERMAL_STATUS | POWER_LIMIT_STATUS
        mocker.patch("s_tui.sources.intel_therm.read_msr", return_value=val)
        status = read_therm_status(0)
        assert status.thermal is True
        assert status.power_limit is True
        assert status.prochot is False
        assert status.label == "T/W"

    def test_decodes_prochot(self, mocker):
        mocker.patch("s_tui.sources.intel_therm.read_msr", return_value=PROCHOT_STATUS)
        status = read_therm_status(2)
        assert status.prochot is True
        assert status.label == "H"

    def test_no_bits_set(self, mocker):
        mocker.patch("s_tui.sources.intel_therm.read_msr", return_value=0)
        status = read_therm_status(0)
        assert status.any_active is False

    def test_all_status_bits(self, mocker):
        val = (
            THERMAL_STATUS | PROCHOT_STATUS | CRITICAL_STATUS
            | POWER_LIMIT_STATUS | CURRENT_LIMIT_STATUS | CROSS_DOMAIN_STATUS
        )
        mocker.patch("s_tui.sources.intel_therm.read_msr", return_value=val)
        status = read_therm_status(0)
        assert status.label == "T/H/C/W/A/X"


class TestAvailable:
    def test_available_when_msr_works(self, mocker):
        mocker.patch("s_tui.sources.intel_therm.msr_available", return_value=True)
        mocker.patch("s_tui.sources.intel_therm.read_msr", return_value=0)
        assert available() is True

    def test_unavailable_without_msr(self, mocker):
        mocker.patch("s_tui.sources.intel_therm.msr_available", return_value=False)
        assert available() is False

    def test_unavailable_on_read_error(self, mocker):
        mocker.patch("s_tui.sources.intel_therm.msr_available", return_value=True)
        mocker.patch("s_tui.sources.intel_therm.read_msr", side_effect=OSError)
        assert available() is False
