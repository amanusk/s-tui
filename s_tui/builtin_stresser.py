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

1. numpy matmul burn — repeated small dense matrix multiplications via BLAS.
   Benchmarked on real hardware (AMD Ryzen 4750G) to reach the platform's PPT
   power ceiling within seconds, beating both the previous sin/sqrt-mix
   kernel and external `stress -c`.
2. hashlib SHA-256 — stdlib fallback; tight C-backed loop on 64KB blocks.
"""

from __future__ import annotations

import hashlib
import importlib.util
import logging
import os
from multiprocessing import Event, Process
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event as EventType

# Checked via find_spec rather than an actual import: importing numpy here
# would initialize OpenBLAS's thread pool in the parent process (inherited
# by forked workers) before _worker_numpy gets a chance to pin it to one
# thread per process, causing every worker to oversubscribe the machine.
_HAS_NUMPY = importlib.util.find_spec("numpy") is not None

STRATEGY_NUMPY = "numpy"
STRATEGY_HASHLIB = "hashlib"
STRATEGIES = [STRATEGY_NUMPY, STRATEGY_HASHLIB]

STRATEGY_LABELS = {
    STRATEGY_NUMPY: "numpy matmul burn",
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
    """CPU-intensive worker using repeated dense matrix multiplication.

    BLAS gemm microkernels keep FMA units busy with little stalling, which
    draws far more sustained power than a transcendental-heavy elementwise
    loop (sin/sqrt are latency-bound, not throughput-bound).  Threads are
    pinned to 1 per process: parallelism already comes from one process per
    core, so letting BLAS spawn its own thread pool would oversubscribe.
    """
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    import numpy as np  # pyright: ignore[reportMissingImports]

    # 128x128 float64 = 128KB per matrix -- comfortably cache-resident
    # across generations/vendors without needing to probe cache sizes.
    n = 128
    rng = np.random.default_rng()
    a = rng.random((n, n))
    b = rng.random((n, n))
    out = np.empty((n, n))
    while not stop_event.is_set():
        np.matmul(a, b, out=out)


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
        try:
            for _ in range(num_workers):
                p = Process(target=worker_fn, args=(self._stop_event,), daemon=True)
                p.start()
                self._workers.append(p)
        except OSError:
            logging.exception(
                "Failed to start all built-in stress workers; cleaning up %d "
                "already-started workers",
                len(self._workers),
            )
            self.stop()
            raise
        logging.info(
            "Built-in stresser started %d workers (strategy: %s)",
            num_workers,
            STRATEGY_LABELS.get(strategy, strategy),
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
