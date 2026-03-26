"""Tests for AMD PSTATE_CUR_LIMIT throttle decoder."""

from s_tui.sources.amd_therm import (
    HW_PSTATE_STATUS,
    PSTATE_CUR_LIMIT,
    PSTATE_DEF_0,
    AmdThrottleStatus,
    _decode_freq,
    available,
    read_throttle_status,
)


class TestAmdThrottleStatus:
    def test_no_throttle(self):
        s = AmdThrottleStatus(smu_limited=False, below_base=False)
        assert s.any_active is False
        assert s.label == ""

    def test_smu_limited_only(self):
        s = AmdThrottleStatus(smu_limited=True, below_base=False)
        assert s.any_active is True
        assert s.label == "W"

    def test_below_base_only(self):
        s = AmdThrottleStatus(smu_limited=False, below_base=True)
        assert s.any_active is True
        assert s.label == "F"

    def test_both_reasons(self):
        s = AmdThrottleStatus(smu_limited=True, below_base=True)
        assert s.any_active is True
        assert s.label == "W/F"


class TestDecodeFreq:
    def test_normal(self):
        # FID=144, DfsID=8 -> (144/8)*200 = 3600 MHz
        assert _decode_freq(144, 8) == 3600.0

    def test_zero_dfs_id(self):
        assert _decode_freq(144, 0) == 0.0

    def test_boost_freq(self):
        # FID=172, DfsID=8 -> (172/8)*200 = 4300 MHz
        assert _decode_freq(172, 8) == 4300.0


class TestReadThrottleStatus:
    def test_throttled_pstate_limit(self, mocker):
        """CurPstateLimit=1 means SMU is throttling."""

        # PSTATE_CUR_LIMIT: 0x21 -> bits[2:0]=1 (P1), bits[6:4]=2 (P2)
        # HW_PSTATE_STATUS: FID=122, DfsID=8 -> 3050 MHz (below P0 base)
        # PSTATE_DEF_0: FID=128, DfsID=8 -> 3200 MHz, PstateEn=1
        def fake_msr(cpu, reg):
            if reg == PSTATE_CUR_LIMIT:
                return 0x21
            if reg == HW_PSTATE_STATUS:
                return 0x0000_0000_0060_C87A  # FID=0x7A=122, DfsID=0x08
            if reg == PSTATE_DEF_0:
                return 0x8000_0000_0000_0880  # FID=0x80=128, DfsID=0x08, PstateEn=1
            return 0

        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=fake_msr)
        status = read_throttle_status(0)
        assert status.smu_limited is True
        assert status.below_base is True
        assert status.label == "W/F"

    def test_not_throttled(self, mocker):
        """CurPstateLimit=0, freq above base."""

        # PSTATE_CUR_LIMIT: 0x20 -> bits[2:0]=0 (P0 allowed)
        # HW_PSTATE_STATUS: FID=172, DfsID=8 -> 4300 MHz (boost)
        # PSTATE_DEF_0: FID=128, DfsID=8 -> 3200 MHz
        def fake_msr(cpu, reg):
            if reg == PSTATE_CUR_LIMIT:
                return 0x20
            if reg == HW_PSTATE_STATUS:
                return 0x0000_0000_0036_08AC  # FID=0xAC=172, DfsID=0x08
            if reg == PSTATE_DEF_0:
                return 0x8000_0000_0000_0880  # FID=128, DfsID=8
            return 0

        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=fake_msr)
        status = read_throttle_status(0)
        assert status.smu_limited is False
        assert status.below_base is False
        assert status.label == ""

    def test_smu_limited_but_above_base(self, mocker):
        """CurPstateLimit>0 but HW freq is still above P0 base."""

        def fake_msr(cpu, reg):
            if reg == PSTATE_CUR_LIMIT:
                return 0x21
            if reg == HW_PSTATE_STATUS:
                return 0x0000_0000_0036_08AC  # 4300 MHz
            if reg == PSTATE_DEF_0:
                return 0x8000_0000_0000_0880  # 3200 MHz
            return 0

        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=fake_msr)
        status = read_throttle_status(0)
        assert status.smu_limited is True
        assert status.below_base is False
        assert status.label == "W"

    def test_secondary_msr_failure_defaults_safe(self, mocker):
        """If HW_PSTATE_STATUS read fails, below_base defaults to False."""

        def fake_msr(cpu, reg):
            if reg == PSTATE_CUR_LIMIT:
                return 0x21
            raise OSError("permission denied")

        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=fake_msr)
        status = read_throttle_status(0)
        assert status.smu_limited is True
        assert status.below_base is False
        assert status.label == "W"

    def test_pstate_def_disabled(self, mocker):
        """If P0 PstateEn=0, below_base defaults to False."""

        def fake_msr(cpu, reg):
            if reg == PSTATE_CUR_LIMIT:
                return 0x21
            if reg == HW_PSTATE_STATUS:
                return 0x0000_0000_0060_C87A
            if reg == PSTATE_DEF_0:
                return 0x0000_0000_0000_0880  # PstateEn=0
            return 0

        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=fake_msr)
        status = read_throttle_status(0)
        assert status.smu_limited is True
        assert status.below_base is False

    def test_reads_correct_cpu(self, mocker):
        """read_throttle_status passes the cpu argument to read_msr."""
        mock_read = mocker.patch("s_tui.sources.amd_therm.read_msr", return_value=0x20)
        read_throttle_status(7)
        mock_read.assert_any_call(7, PSTATE_CUR_LIMIT)


class TestAvailable:
    def test_available_when_msr_works(self, mocker):
        mocker.patch("s_tui.sources.amd_therm.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_therm.read_msr", return_value=0x20)
        assert available() is True

    def test_unavailable_without_msr(self, mocker):
        mocker.patch("s_tui.sources.amd_therm.msr_available", return_value=False)
        assert available() is False

    def test_unavailable_on_read_error(self, mocker):
        """Intel CPUs will fail reading AMD-specific MSR."""
        mocker.patch("s_tui.sources.amd_therm.msr_available", return_value=True)
        mocker.patch("s_tui.sources.amd_therm.read_msr", side_effect=OSError)
        assert available() is False
