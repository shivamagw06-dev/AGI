#!/usr/bin/env python3
"""Verify acceptance datasets before production regression runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IE = ROOT / "intelligence-engine"
sys.path.insert(0, str(IE))

from ask_product_test.acceptance_data import check_acceptance_data  # noqa: E402


def main() -> int:
    report = check_acceptance_data(verbose=True)
    art_dir = ROOT / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "acceptance_data_health.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    if report.get("status") != "PASS":
        print("\n[acceptance_data] INFRASTRUCTURE FAILURE — stop regression", flush=True)
        return 2
    print("\n[acceptance_data] PASS — safe to run production regression", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
