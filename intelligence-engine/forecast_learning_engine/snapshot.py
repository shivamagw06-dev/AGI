"""Create compact, reproducible point-in-time input manifests."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _version(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _cutoff(rows: list[dict[str, Any]]) -> str | None:
    stamps = []
    for row in rows:
        meta = row.get("_meta") or {}
        stamp = row.get("last_updated") or row.get("filing_date") or meta.get("updated_at") or meta.get("created_at")
        if stamp:
            stamps.append(str(stamp))
    return max(stamps) if stamps else None


def build_snapshot(bundle: dict[str, Any], *, generated_at: str, engine_version: str) -> dict[str, Any]:
    groups = {
        "financial": (bundle.get("annual") or []) + (bundle.get("quarterly") or []),
        "valuation": (bundle.get("historical_valuation") or []) + (bundle.get("valuation_ratios") or []),
        "consensus": bundle.get("consensus") or [],
        "research": [bundle.get("rie") or {}, *(bundle.get("research_timeline") or [])],
        "macro": [bundle.get("mie") or {}, bundle.get("mie_scenarios") or {}],
    }
    manifest = {
        name: {"version": _version(rows), "rows": len(rows), "cutoff": _cutoff(rows)}
        for name, rows in groups.items()
    }
    cutoffs = [v["cutoff"] for v in manifest.values() if v.get("cutoff")]
    symbol = str(bundle.get("symbol") or "").upper()
    snapshot_id = _version({"symbol": symbol, "generated_at": generated_at, "manifest": manifest})
    return {
        "snapshot_id": snapshot_id,
        "symbol": symbol,
        "forecast_timestamp": generated_at,
        # Unknown is preferable to pretending the forecast timestamp was the
        # source cutoff when legacy warehouse rows carry no ingestion stamp.
        "data_cutoff_timestamp": max(cutoffs) if cutoffs else None,
        "financial_data_version": manifest["financial"]["version"],
        "valuation_data_version": manifest["valuation"]["version"],
        "consensus_version": manifest["consensus"]["version"],
        "research_version": manifest["research"]["version"],
        "macro_version": manifest["macro"]["version"],
        "forecast_version": engine_version,
        "engine_version": engine_version,
        "input_manifest": manifest,
    }
