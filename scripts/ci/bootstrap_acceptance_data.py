#!/usr/bin/env python3
"""Bootstrap minimal acceptance datasets for CI and local regression parity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IE = ROOT / "intelligence-engine"
sys.path.insert(0, str(IE))

from ask_product_test.acceptance_data import bootstrap_acceptance_data  # noqa: E402


def main() -> int:
    force = "--force" in sys.argv
    result = bootstrap_acceptance_data(force=force, verbose=True)
    art_dir = ROOT / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "acceptance_data_bootstrap.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    health = result.get("health") or {}
    if health.get("status") != "PASS":
        print("\n[bootstrap] INFRASTRUCTURE FAILURE — acceptance data incomplete after bootstrap", flush=True)
        return 2
    print(f"\n[bootstrap] OK — {result.get('files_copied', 0)} files copied", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
