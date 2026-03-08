"""Intel IA32_THERM_STATUS (0x19C) throttle reason decoder.

Reads per-core thermal status MSR and reports which throttle reasons
are active. Requires root + msr kernel module.

Reference: Intel SDM Vol 4, Table 2-39.
"""

from __future__ import annotations

from typing import NamedTuple

from s_tui.sources.msr import msr_available, read_msr

IA32_THERM_STATUS = 0x19C

# Status bits (real-time, even-numbered) — set only while actively throttling
THERMAL_STATUS = 1 << 0
PROCHOT_STATUS = 1 << 2
CRITICAL_STATUS = 1 << 4
POWER_LIMIT_STATUS = 1 << 10
CURRENT_LIMIT_STATUS = 1 << 12
CROSS_DOMAIN_STATUS = 1 << 14

_REASON_BITS = (
    (THERMAL_STATUS, "T"),
    (PROCHOT_STATUS, "H"),
    (CRITICAL_STATUS, "C"),
    (POWER_LIMIT_STATUS, "W"),
    (CURRENT_LIMIT_STATUS, "A"),
    (CROSS_DOMAIN_STATUS, "X"),
)


class ThrottleStatus(NamedTuple):
    thermal: bool
    prochot: bool
    critical: bool
    power_limit: bool
    current_limit: bool
    cross_domain: bool

    @property
    def any_active(self) -> bool:
        return any(self)

    @property
    def label(self) -> str:
        """Slash-separated label string, e.g. 'T/W' or empty."""
        parts = [lbl for (_, lbl), active in zip(_REASON_BITS, self) if active]
        return "/".join(parts)


def read_therm_status(cpu: int) -> ThrottleStatus:
    """Read IA32_THERM_STATUS for a CPU and decode throttle reasons."""
    val = read_msr(cpu, IA32_THERM_STATUS)
    return ThrottleStatus(
        thermal=bool(val & THERMAL_STATUS),
        prochot=bool(val & PROCHOT_STATUS),
        critical=bool(val & CRITICAL_STATUS),
        power_limit=bool(val & POWER_LIMIT_STATUS),
        current_limit=bool(val & CURRENT_LIMIT_STATUS),
        cross_domain=bool(val & CROSS_DOMAIN_STATUS),
    )


def available() -> bool:
    """Check if Intel MSR throttle detection is usable."""
    if not msr_available():
        return False
    try:
        read_msr(0, IA32_THERM_STATUS)
        return True
    except (OSError, ValueError):
        return False
