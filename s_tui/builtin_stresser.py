#!/usr/bin/env python
#
# Copyright (C) 2017-2025 Alex Manuskin, Gil Tsuker
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

"""Built-in Python CPU stresser using multiprocessing.

Provides a zero-external-dependency CPU stress test. Two workload strategies
are available, selectable at runtime:

1. numpy FP burn — mixed FMA/sqrt/sin on L2-resident arrays for maximum
   sustained thermal output without triggering AVX-512 frequency penalties.
2. hashlib SHA-256 — stdlib fallback; tight C-backed loop on 64KB blocks.
"""

from __future__ import annotations

import hashlib
import logging
from multiprocessing import Event, Process
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event as EventType

try:
    import numpy  # noqa: F401

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

STRATEGY_NUMPY = "numpy"
STRATEGY_HASHLIB = "hashlib"
STRATEGIES = [STRATEGY_NUMPY, STRATEGY_HASHLIB]

STRATEGY_LABELS = {
    STRATEGY_NUMPY: "numpy FP burn",
    STRATEGY_HASHLIB: "hashlib SHA-256",
}


def get_default_strategy() -> str:
    """Return the best available strategy key."""
    return STRATEGY_NUMPY if _HAS_NUMPY else STRATEGY_HASHLIB


def strategy_available(strategy: str) -> bool:
    """Return True if the given strategy can actually run."""
    if strategy == STRATEGY_NUMPY:
        return _HAS_NUMPY
    return True


def _worker_numpy(stop_event: EventType) -> None:
    """CPU-intensive worker using mixed numpy FP operations.

    Uses a combination of multiply, sqrt, add, and sin on arrays sized
    to stay resident in L2 cache.  This mix of instruction types keeps
    power draw high without fully triggering AVX-512 frequency penalties
    (which actually *reduce* thermal output).  Benchmarks show this
    approach matches external ``stress`` in temperature generation.
    """
    import numpy as np

    # 100K doubles = 800KB — fits in L2, large enough to minimize
    # Python loop overhead relative to time spent in numpy C code.
    size = 100_000
    a = np.random.random(size) + 1.0
    b = np.random.random(size) + 1.0
    out = np.empty(size, dtype=np.float64)
    while not stop_event.is_set():
        np.multiply(a, b, out=out)
        np.sqrt(out, out=out)
        np.add(out, a, out=out)
        np.sin(out, out=out)


def _worker_hashlib(stop_event: EventType) -> None:
    """CPU-intensive worker using SHA-256 hashing."""
    block = b"\x00" * 65536  # 64KB
    while not stop_event.is_set():
        hashlib.sha256(block).digest()


class BuiltinStresser:
    """Manages CPU stress worker processes.

    Uses multiprocessing.Event for clean shutdown signaling and a graduated
    teardown (join → terminate → kill) to ensure workers are cleaned up.
    """

    def __init__(self) -> None:
        self._stop_event: EventType | None = None
        self._workers: list[Process] = []

    def start(self, num_workers: int, strategy: str | None = None) -> None:
        """Spawn *num_workers* CPU stress worker processes.

        *strategy* selects the workload: ``STRATEGY_NUMPY`` or
        ``STRATEGY_HASHLIB``.  Falls back to hashlib if the requested
        strategy is unavailable.
        """
        if strategy is None:
            strategy = get_default_strategy()
        if not strategy_available(strategy):
            logging.warning(
                "Strategy %s unavailable, falling back to hashlib", strategy
            )
            strategy = STRATEGY_HASHLIB

        worker_fn = _worker_numpy if strategy == STRATEGY_NUMPY else _worker_hashlib

        self.stop()  # clean up any previous run
        self._stop_event = Event()
        for _ in range(num_workers):
            p = Process(target=worker_fn, args=(self._stop_event,), daemon=True)
            p.start()
            self._workers.append(p)
        logging.info(
            "Built-in stresser started %d workers (strategy: %s)",
            num_workers,
            STRATEGY_LABELS[strategy],
        )

    def stop(self, timeout: int = 3) -> None:
        """Graduated teardown: signal → join → terminate → kill."""
        if not self._workers:
            return
        if self._stop_event is not None:
            self._stop_event.set()
        for p in self._workers:
            p.join(timeout=timeout)
        for p in self._workers:
            if p.is_alive():
                logging.debug("Terminating straggler worker %s", p.pid)
                p.terminate()
                p.join(timeout=1)
        for p in self._workers:
            if p.is_alive():
                logging.debug("Killing straggler worker %s", p.pid)
                p.kill()
        for p in self._workers:
            p.join(timeout=1)
        self._workers.clear()
        logging.info("Built-in stresser stopped")

    def is_running(self) -> bool:
        """Return True if any worker process is still alive."""
        return any(p.is_alive() for p in self._workers)
