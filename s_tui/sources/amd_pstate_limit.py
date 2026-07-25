"""AMD Zen PStateCurLim (0xC0010061) P-state cap detector.

Reports whether the SMU has barred a core from its top P-state. This is a
severity indicator, not a reason code: the register carries no thermal/power
distinction. Observed to assert only once sustained load drove the chip below
its rated base clock, staying clear while it was merely boost-limited.

Requires root + msr kernel module.

Field layout per AMD AGESA (PSTATE_CURLIM_MSR: CurPstateLimit:3, :1,
PstateMaxVal:3). FreeBSD's hwpstate driver decodes the same register with the
same mask and treats the field as a floor on the P-state index.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from s_tui.helper_functions import cat
from s_tui.sources.msr import msr_available, read_msr

PSTATE_CUR_LIMIT = 0xC0010061

CUR_PSTATE_LIMIT_MASK = 0x7

PSTATE_CAP_LABEL = "Pc"

# Zen and newer. On some older families the limit register tracks the
# configured P-state instead of a hardware cap, which would read as a
# permanent throttle -- FreeBSD disables its equivalent by default for this.
MIN_CPU_FAMILY = 0x17


def _family_supported() -> bool:
    cpuinfo = cat("/proc/cpuinfo", fallback="", binary=False)
    if "AuthenticAMD" not in cpuinfo:
        return False
    match = re.search(r"cpu family\s*:\s*(\d+)", cpuinfo)
    return match is not None and int(match[1]) >= MIN_CPU_FAMILY


class ThrottleStatus(NamedTuple):
    pstate_capped: bool

    @property
    def label(self) -> str:
        return PSTATE_CAP_LABEL if self.pstate_capped else ""


def read_therm_status(cpu: int) -> ThrottleStatus:
    """Read PStateCurLim for a CPU and decode the P-state cap."""
    val = read_msr(cpu, PSTATE_CUR_LIMIT)
    return ThrottleStatus(pstate_capped=bool(val & CUR_PSTATE_LIMIT_MASK))


def available() -> bool:
    """Check if AMD MSR P-state cap detection is usable."""
    if not _family_supported():
        return False
    if not msr_available():
        return False
    try:
        read_msr(0, PSTATE_CUR_LIMIT)
        return True
    except (OSError, ValueError):
        return False
