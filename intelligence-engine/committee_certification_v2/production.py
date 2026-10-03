"""Committee Certification IC-10 v2.0 — production façade."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from committee_certification_v2.collect import collect_company, collect_universe
from committee_certification_v2.evaluate import fingerprint_row, governance_integrity
from committee_certification_v2.report import expectation_check, format_markdown
from committee_certification_v2.schema import (
    CERT_VERSION,
    IC10_V2_ROWS,
    IC10_V2_UNIVERSE,
    PROGRAMME,
)
from committee_certification_v2.score import aggregate, robustness, score_company

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": CERT_VERSION,
        "universe": list(IC10_V2_UNIVERSE),
        "resolve_map": {d: r for d, r, _ in IC10_V2_ROWS},
        "tests": [
            "evidence_completeness",
            "sector_differentiation",
            "ownership_intelligence",
            "valuation_intelligence",
            "financial_intelligence",
            "decision_quality",
            "governance_integrity",
            "narrative_quality",
            "robustness",
            "committee_readiness",
        ],
        "modifies_decision_engine": False,
        "modifies_gate_thresholds": False,
        "acceptance_exam_only": True,
    }


def _score_bundle(rows: list[dict[str, Any]]) -> dict[str, Any]:
    companies = [score_company(r) for r in rows]
    gov = governance_integrity(rows)
    agg = aggregate(companies, governance=gov)
    return {
        "companies": companies,
        "aggregate": agg,
        "expectation_check": expectation_check(agg),
    }


def run_certification(
    *,
    robustness_runs: int = 3,
    force: bool = False,
    max_peers: int = 3,
    persist: bool = True,
    injected_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Execute IC-10 Committee Certification v2.0.

    Live mode collects P2.6/P2.3/P2.1/P2.2 + company_analysis + decision_engine.
    Injected mode supports unit tests without network.
    """
    t0 = datetime.now(timezone.utc)
    fingerprints: list[dict[str, str]] = []
    primary: dict[str, Any] | None = None
    run_meta: list[dict[str, Any]] = []

    n_runs = 1 if injected_rows is not None else max(1, int(robustness_runs))

    for i in range(n_runs):
        if injected_rows is not None:
            rows = list(injected_rows)
            order = [r.get("display") for r in rows]
        else:
            order_rows = list(IC10_V2_ROWS)
            if i % 2 == 1:
                order_rows = list(reversed(order_rows))
            rows = [
                collect_company(
                    disp,
                    force=force or (i == 0),
                    max_peers=max_peers,
                    ownership_xbrl=2,
                    quarterly_xbrl=4,
                    annual_xbrl=2,
                )
                for disp, _, _ in order_rows
            ]
            # Restore display order for scoring tables
            by_disp = {r["display"]: r for r in rows}
            rows = [by_disp[d] for d, _, _ in IC10_V2_ROWS if d in by_disp]
            order = [r["display"] for r in rows]

        scored = _score_bundle(rows)
        fp = {r["display"]: fingerprint_row(r) for r in rows}
        fingerprints.append(fp)
        run_meta.append(
            {
                "run": i + 1,
                "order": order,
                "total_score": scored["aggregate"]["total_score"],
                "grade": scored["aggregate"]["grade"],
                "cache": "cold" if i == 0 else "warm",
            }
        )
        if primary is None:
            primary = {**scored, "rows_raw": rows}

    assert primary is not None
    rob = robustness(fingerprints)
    # UNKNOWN drift: any company without resolve / ok evidence engines
    unknown = [
        r.get("display")
        for r in primary.get("rows_raw") or []
        if not r.get("resolve")
    ]
    result = {
        "found": True,
        "programme": PROGRAMME,
        "version": CERT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": list(IC10_V2_UNIVERSE),
        "companies": primary["companies"],
        "aggregate": primary["aggregate"],
        "expectation_check": primary["expectation_check"],
        "robustness": rob,
        "run_meta": run_meta,
        "unknown_drift": len(unknown),
        "unknown_tickers": unknown,
        "latency_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
        "markdown": None,
    }
    result["markdown"] = format_markdown(result)

    if persist and injected_rows is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_json = RESULTS_DIR / f"ic10_v2_{stamp}.json"
        out_md = RESULTS_DIR / f"ic10_v2_{stamp}.md"
        # Drop raw rows from persisted JSON (large)
        persist_body = {k: v for k, v in result.items() if k != "markdown"}
        out_json.write_text(json.dumps(persist_body, indent=2, default=str), encoding="utf-8")
        out_md.write_text(result["markdown"], encoding="utf-8")
        # Also write latest pointers
        (RESULTS_DIR / "latest.json").write_text(out_json.read_text(encoding="utf-8"), encoding="utf-8")
        (RESULTS_DIR / "latest.md").write_text(result["markdown"], encoding="utf-8")
        result["persisted"] = {"json": str(out_json), "markdown": str(out_md)}

    return result


def package_for_ask_agi(**kwargs: Any) -> dict[str, Any]:
    result = run_certification(robustness_runs=1, persist=False, **kwargs)
    return {
        "enabled": True,
        "engine": "committee_certification_v2",
        "version": CERT_VERSION,
        "total_score": (result.get("aggregate") or {}).get("total_score"),
        "grade": (result.get("aggregate") or {}).get("grade"),
        "verdicts": (result.get("aggregate") or {}).get("verdicts"),
        "expectation_check": result.get("expectation_check"),
        "markdown": result.get("markdown"),
    }
