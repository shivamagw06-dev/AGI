"""Load Evaluation Lab / Phase 6 / Drift artifacts — never recompute decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from institutional_evaluation_lab.golden_universe import store as golden_store


def load_release_bundle(release_id: str) -> dict[str, Any]:
    """Assemble consume-only inputs for observability dashboards."""
    packed = golden_store.load_release_results(release_id)
    if not packed:
        return {"found": False, "release_id": release_id}

    root = Path(packed["results_dir"])
    rows = list(packed.get("rows") or [])
    if not rows:
        for t in (packed.get("manifest") or {}).get("tickers") or []:
            path = root / f"{str(t).upper()}.json"
            if path.exists():
                rows.append(json.loads(path.read_text(encoding="utf-8")))

    phase6 = _read_json(root / "_phase6_governance.json")
    drift = _read_json(root / "_drift_report.json")
    summary = packed.get("summary") or _read_json(root / "_summary.json") or {}
    manifest = packed.get("manifest") or _read_json(root / "_manifest.json") or {}

    return {
        "found": True,
        "release_id": release_id,
        "results_dir": str(root),
        "rows": rows,
        "n": len(rows),
        "manifest": manifest,
        "summary": summary,
        "phase6": phase6,
        "drift": drift,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None
