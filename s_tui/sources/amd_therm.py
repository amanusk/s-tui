"""AMD Zen PSTATE_CUR_LIMIT (0xC0010061) throttle detector.

Reads per-core P-state current limit MSR to detect when the SMU
restricts the CPU below P0 (boost). Optionally reads HW_PSTATE_STATUS
to detect when actual frequency falls below P0 base.

Requires root + msr kernel module.

Reference: AMD PPR Vol 2, Core::X86::Msr::PStateCurLmt.
"""

from __future__ import annotations

from typing import NamedTuple

from s_tui.sources.msr import msr_available, read_msr

PSTATE_CUR_LIMIT = 0xC0010061
HW_PSTATE_STATUS = 0xC0010293
PSTATE_DEF_0 = 0xC0010064

_REASON_BITS = (
    (0, "W"),  # SMU power/thermal limit (P-state capped)
    (1, "F"),  # Below base frequency
)


def _decode_freq(fid: int, dfs_id: int) -> float:
    """Decode AMD Zen frequency from FID/DfsID: (fid / dfs_id) * 200 MHz."""
    if dfs_id == 0:
        return 0.0
    return (fid / dfs_id) * 200.0


class AmdThrottleStatus(NamedTuple):
    smu_limited: bool
    below_base: bool

    @property
    def any_active(self) -> bool:
        return any(self)

    @property
    def label(self) -> str:
        """Slash-separated label string, e.g. 'W' or 'W/F' or empty."""
        parts = [lbl for (_, lbl), active in zip(_REASON_BITS, self) if active]
        return "/".join(parts)


def read_throttle_status(cpu: int) -> AmdThrottleStatus:
    """Read AMD throttle status for a CPU."""
    val = read_msr(cpu, PSTATE_CUR_LIMIT)
    cur_pstate_limit = val & 0x7
    smu_limited = cur_pstate_limit > 0

    below_base = False
    try:
        hw_ps = read_msr(cpu, HW_PSTATE_STATUS)
        ps0 = read_msr(cpu, PSTATE_DEF_0)
        if ps0 & (1 << 63):  # PstateEn
            hw_freq = _decode_freq(hw_ps & 0xFF, (hw_ps >> 8) & 0x3F)
            base_freq = _decode_freq(ps0 & 0xFF, (ps0 >> 8) & 0x3F)
            if hw_freq > 0 and base_freq > 0:
                below_base = hw_freq < base_freq
    except (OSError, ValueError):
        pass

    return AmdThrottleStatus(smu_limited=smu_limited, below_base=below_base)


def available() -> bool:
    """Check if AMD MSR throttle detection is usable."""
    if not msr_available():
        return False
    try:
        read_msr(0, PSTATE_CUR_LIMIT)
        return True
    except (OSError, ValueError):
        return False
