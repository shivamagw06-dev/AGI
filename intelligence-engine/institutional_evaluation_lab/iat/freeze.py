"""Baseline freeze — only after IAT PASS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_evaluation_lab.iat.schema import (
    ARCHITECTURE_VERSION,
    BASELINE_INCLUDES,
    BASELINE_NAME,
    IAT_VERSION,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def format_freeze_prompt(pack: dict[str, Any], *, effective: str | None = None) -> str:
    effective = effective or _now()
    includes = "\n".join(f"✓ {item}" for item in BASELINE_INCLUDES)
    return "\n".join(
        [
            BASELINE_NAME,
            "",
            "Status",
            "",
            "FROZEN",
            "",
            "Effective",
            "",
            effective,
            "",
            "Includes",
            "",
            includes,
            "",
            "Future intelligence improvements",
            "must not modify this baseline",
            "without passing Institutional Evaluation.",
            "",
            f"Qualified by: {pack.get('release_id')} · IAT {IAT_VERSION} · Architecture {ARCHITECTURE_VERSION}",
        ]
    )


def freeze_baseline(
    pack: dict[str, Any],
    *,
    results_dir: str | Path | None,
    force: bool = False,
) -> dict[str, Any]:
    """Persist freeze artifacts. Refuses unless overall status is PASS (unless force)."""
    overall = (pack.get("overall") or {}).get("status")
    if overall != "PASS" and not force:
        return {
            "frozen": False,
            "refused": True,
            "reason": "IAT_DID_NOT_PASS",
            "overall": overall,
            "note": "Baseline freeze is only allowed after Institutional Acceptance Test PASS.",
        }

    effective = _now()
    payload = {
        "name": BASELINE_NAME,
        "status": "FROZEN",
        "effective": effective,
        "architecture_version": ARCHITECTURE_VERSION,
        "iat_version": IAT_VERSION,
        "release_id": pack.get("release_id"),
        "includes": list(BASELINE_INCLUDES),
        "rule": (
            "Future intelligence improvements must not modify this baseline "
            "without passing Institutional Evaluation."
        ),
        "overall": pack.get("overall"),
        "areas": {
            "governance": (pack.get("governance") or {}).get("status"),
            "evidence": (pack.get("evidence") or {}).get("status"),
            "decision_quality": (pack.get("decision_quality") or {}).get("status"),
            "operational": (pack.get("operational") or {}).get("status"),
            "drift": (pack.get("drift") or {}).get("status"),
            "universe": (pack.get("universe") or {}).get("status"),
        },
        "report_text": pack.get("report_text"),
    }
    text = format_freeze_prompt(pack, effective=effective)
    payload["freeze_prompt"] = text

    paths: dict[str, str] = {}
    if results_dir:
        root = Path(results_dir)
        root.mkdir(parents=True, exist_ok=True)
        json_path = root / "_institutional_baseline_v1_0.json"
        md_path = root / "_institutional_baseline_v1_0.md"
        json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        md_path.write_text(text + "\n", encoding="utf-8")
        paths = {"json": str(json_path), "markdown": str(md_path)}

        # Also write a package-level pointer under IEL reports/
        try:
            from institutional_evaluation_lab.golden_universe import store as golden_store

            reports = Path(golden_store.results_root()).parent / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            (reports / "institutional_baseline_v1_0.json").write_text(
                json.dumps(payload, indent=2, default=str), encoding="utf-8"
            )
            (reports / "institutional_baseline_v1_0.md").write_text(text + "\n", encoding="utf-8")
            paths["reports_json"] = str(reports / "institutional_baseline_v1_0.json")
            paths["reports_markdown"] = str(reports / "institutional_baseline_v1_0.md")
        except Exception:
            pass

    return {"frozen": True, "refused": False, "effective": effective, "paths": paths, "baseline": payload}
