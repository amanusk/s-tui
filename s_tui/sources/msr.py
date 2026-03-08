"""Shared utility for reading x86 MSRs via /dev/cpu/N/msr."""

from __future__ import annotations

from sys import byteorder


def read_msr(cpu: int, register: int) -> int:
    """Read a 64-bit MSR value from /dev/cpu/{cpu}/msr."""
    with open(f"/dev/cpu/{cpu}/msr", "rb") as f:
        f.seek(register)
        return int.from_bytes(f.read(8), byteorder)


def msr_available() -> bool:
    """Check if MSR device files are readable (requires root + msr module)."""
    try:
        with open("/dev/cpu/0/msr", "rb"):
            return True
    except (FileNotFoundError, PermissionError, OSError):
        return False
