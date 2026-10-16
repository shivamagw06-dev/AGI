"""Phase 6 — execute Governance Spec against Evaluation Lab release results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from governance_spec.assertions import assert_ticker
from governance_spec.registry import load_spec
from governance_spec.schema import GOVERNANCE_SPEC_VERSION, PROGRAMME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_phase6(
    *,
    release_id: str,
    spec_version: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """
    Load results/{release_id}/*.json and evaluate every ticker against GOV-00N.

    Output emphasises rule IDs, not a binary "Phase 6 passed".
    """
    from institutional_evaluation_lab.golden_universe import store as golden_store

    packed = golden_store.load_release_results(release_id)
    if not packed:
        return {
            "ok": False,
            "error": "release_not_found",
            "release_id": release_id,
            "spec_version": spec_version or GOVERNANCE_SPEC_VERSION,
        }

    spec = load_spec(spec_version)
    rows = list(packed.get("rows") or [])
    if not rows:
        # Fallback: read ticker files from disk via manifest
        import json
        from pathlib import Path

        man = packed.get("manifest") or {}
        root = Path(packed["results_dir"])
        rows = []
        for t in man.get("tickers") or []:
            path = root / f"{str(t).upper()}.json"
            if path.exists():
                rows.append(json.loads(path.read_text(encoding="utf-8")))

    if limit is not None:
        rows = rows[: max(1, int(limit))]

    per_ticker = [assert_ticker(r, spec_version=spec["spec_version"]) for r in rows]

    # Aggregate by rule ID across the release
    by_rule: dict[str, dict[str, Any]] = {
        r["rule_id"]: {"rule_id": r["rule_id"], "assertion": r["assertion"], "severity": r["severity"],
                       "pass": 0, "fail": 0, "skip": 0, "failures": []}
        for r in spec["rules"]
    }
    for tr in per_ticker:
        for a in tr.get("assertions") or []:
            bucket = by_rule.get(a["rule_id"])
            if not bucket:
                continue
            status = a.get("status")
            if status == "PASS":
                bucket["pass"] += 1
            elif status == "FAIL":
                bucket["fail"] += 1
                if len(bucket["failures"]) < 20:
                    bucket["failures"].append(
                        {"ticker": tr.get("ticker"), "detail": a.get("detail")}
                    )
            elif status == "SKIP":
                bucket["skip"] += 1

    governance_assertions = []
    for rid in [r["rule_id"] for r in spec["rules"]]:
        b = by_rule[rid]
        # Rule-level status: FAIL if any ticker failed; else PASS if any pass; else SKIP
        if b["fail"] > 0:
            status = "FAIL"
        elif b["pass"] > 0:
            status = "PASS"
        else:
            status = "SKIP"
        governance_assertions.append(
            {
                "rule_id": rid,
                "status": status,
                "severity": b["severity"],
                "assertion": b["assertion"],
                "pass": b["pass"],
                "fail": b["fail"],
                "skip": b["skip"],
                "failures": b["failures"],
            }
        )

    ticker_fails = [t for t in per_ticker if not t.get("passed")]
    critical_rule_fails = [g for g in governance_assertions if g["status"] == "FAIL" and g["severity"] == "Critical"]

    report = {
        "programme": PROGRAMME,
        "phase": "phase6_governance_assertions",
        "spec_version": spec["spec_version"],
        "frozen": spec["frozen"],
        "release_id": release_id,
        "timestamp": _now(),
        "n_tickers": len(per_ticker),
        "tickers_passed": len(per_ticker) - len(ticker_fails),
        "tickers_failed": len(ticker_fails),
        "governance_assertions": governance_assertions,
        "board": [{"rule_id": g["rule_id"], "status": g["status"]} for g in governance_assertions],
        "critical_rule_failures": len(critical_rule_fails),
        "ok": len(critical_rule_fails) == 0,
        "ticker_results": per_ticker,
        "architecture": spec["board"]["architecture"],
        "note": (
            "Phase 6 reports constitutional rule IDs (GOV-00N), not a binary suite label. "
            "Historical releases can be re-evaluated against newer specs (v1.1+) without "
            "losing reproducibility against the original frozen v1.0."
        ),
    }
    return report


def format_board(report: dict[str, Any]) -> str:
    lines = [
        "Governance Assertions",
        f"Spec {report.get('spec_version')} · Release {report.get('release_id')}",
        "",
    ]
    for g in report.get("governance_assertions") or []:
        lines.append(f"{g['rule_id']}  {g['status']}")
    lines.append("")
    lines.append(
        f"Tickers {report.get('tickers_passed')}/{report.get('n_tickers')} clean · "
        f"Critical rule failures: {report.get('critical_rule_failures')}"
    )
    return "\n".join(lines)
