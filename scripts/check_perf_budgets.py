#!/usr/bin/env python3
"""Smoke performance budgets for Spec 10 magazine fixture (Stage 8)."""

from __future__ import annotations

import time
from pathlib import Path

from pydesign.runtime import WorkerClient

ROOT = Path(__file__).resolve().parents[1]
MAGAZINE = ROOT / "examples" / "magazine_32"

# Spec 10-inspired soft budgets for CI smoke (seconds).
CHECK_BUDGET_S = 20.0


def main() -> int:
    if not MAGAZINE.is_dir():
        print("magazine_32 fixture missing")
        return 2
    started = time.perf_counter()
    result = WorkerClient().evaluate(MAGAZINE, timeout=CHECK_BUDGET_S)
    elapsed = time.perf_counter() - started
    print(f"magazine_32 check elapsed={elapsed:.3f}s ok={result.ok}")
    if elapsed > CHECK_BUDGET_S:
        print(f"FAIL budget {CHECK_BUDGET_S}s")
        return 2
    if not result.ok:
        print("FAIL evaluation")
        return 2
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
