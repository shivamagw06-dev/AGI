"""Release observability façade — consume Evaluation Lab / Phase 6 / Drift outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from institutional_evaluation_lab.observability.boards import (
    coverage_dashboard,
    drift_dashboard,
    executive_dashboard,
    governance_dashboard,
    historical_trends,
    performance_dashboard,
    recommendation_distribution,
    sector_dashboard,
)
from institutional_evaluation_lab.observability.loaders import load_release_bundle
from institutional_evaluation_lab.observability.schema import (
    GOVERNANCE_PROGRAMME_STATUS,
    OBSERVABILITY_VERSION,
    POST_GOVERNANCE_ROADMAP,
    PROGRAMME,
    SCOPE_LOCKS,
)


def build_release_dashboard(
    release_id: str,
    *,
    previous_releases: list[str] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Full observability pack for one Evaluation Lab release."""
    bundle = load_release_bundle(release_id)
    if not bundle.get("found"):
        return {
            "found": False,
            "release_id": release_id,
            "version": OBSERVABILITY_VERSION,
            "error": "release_not_found",
        }

    executive = executive_dashboard(bundle)
    pack = {
        "found": True,
        "programme": PROGRAMME,
        "version": OBSERVABILITY_VERSION,
        "scope_locks": dict(SCOPE_LOCKS),
        "release_id": release_id,
        "results_dir": bundle.get("results_dir"),
        "executive": executive,
        "recommendation_distribution": recommendation_distribution(bundle),
        "sector": sector_dashboard(bundle),
        "governance": governance_dashboard(bundle),
        "drift": drift_dashboard(bundle),
        "performance": performance_dashboard(bundle),
        "coverage": coverage_dashboard(bundle),
        "historical": historical_trends(previous_releases or []) if previous_releases else {"releases": [], "n": 0},
        "presentation_only": True,
        "note": (
            "PR #309 — observability only. Consumes PRs #306–#308 artifacts; "
            "does not alter Decision Engine, Constitution, Governance Spec, or scoring."
        ),
    }
    pack["text"] = format_dashboard_text(pack)

    if persist and bundle.get("results_dir"):
        out = Path(bundle["results_dir"]) / "_observability_dashboard.json"
        light = {k: v for k, v in pack.items() if k != "text"}
        out.write_text(json.dumps(light, indent=2, default=str), encoding="utf-8")
        text_path = Path(bundle["results_dir"]) / "_observability_dashboard.md"
        text_path.write_text(pack["text"] + "\n", encoding="utf-8")
        pack["dashboard_path"] = str(out)
        pack["markdown_path"] = str(text_path)

    return pack


def format_dashboard_text(pack: dict[str, Any]) -> str:
    exe = pack.get("executive") or {}
    dist = (pack.get("recommendation_distribution") or {}).get("distribution") or {}
    gov = pack.get("governance") or {}
    drift = pack.get("drift") or {}
    perf = pack.get("performance") or {}
    cov = pack.get("coverage") or {}
    sectors = (pack.get("sector") or {}).get("sectors") or []

    lines = [
        "Executive Release Dashboard",
        "",
        f"Release          {exe.get('release')}",
        f"Status           {exe.get('status')}",
        f"Companies Tested {exe.get('companies_tested')}",
        f"Governance       {exe.get('governance_pct')}%" if exe.get("governance_pct") is not None else "Governance       n/a",
        f"UNKNOWN Drift    {exe.get('unknown_drift')}",
        f"Average Readiness {exe.get('average_readiness_pct')}%" if exe.get("average_readiness_pct") is not None else "Average Readiness n/a",
        f"Runtime          {exe.get('runtime_s')} s" if exe.get("runtime_s") is not None else "Runtime          n/a",
        "",
        "Recommendation Distribution",
        "",
    ]
    for k, v in dist.items():
        lines.append(f"{k:<18} {v}")

    lines += ["", "Sector Dashboard", ""]
    lines.append(f"{'Sector':<22} {'Pass':>6} {'Avg Ready':>10} {'Runtime':>9}")
    for s in sectors[:12]:
        lines.append(
            f"{str(s.get('sector')):<22} {str(s.get('pass_pct'))+ '%':>6} "
            f"{(str(s.get('avg_readiness_pct'))+'%') if s.get('avg_readiness_pct') is not None else 'n/a':>10} "
            f"{(str(s.get('avg_runtime_s'))+'s') if s.get('avg_runtime_s') is not None else 'n/a':>9}"
        )

    lines += ["", "Governance Dashboard", ""]
    for r in gov.get("rules") or []:
        lines.append(f"{r.get('rule_id')}")
        lines.append("")
        lines.append(f"{r.get('status')}")
        lines.append("")
        lines.append(f"{r.get('display')}")
        lines.append("")
    if gov.get("overall_pct") is not None:
        lines += ["Overall", "", f"{gov.get('overall_pct')}%", ""]

    lines += ["Drift Dashboard", ""]
    if drift.get("present"):
        lines += [
            f"Recommendation Changes  {drift.get('recommendation_changes')}",
            f"Expected                {drift.get('expected')}",
            f"Unexpected              {drift.get('unexpected')}",
            f"Budget                  {drift.get('budget')}",
            "",
        ]
    else:
        lines += ["(no drift report for this release)", ""]

    lines += [
        "Performance Dashboard",
        "",
        f"Average Runtime   {perf.get('average_runtime_s')} s",
        f"95th Percentile   {perf.get('p95_runtime_s')} s",
        f"Slowest Module    {perf.get('slowest_module')}",
        f"Fastest Module    {perf.get('fastest_module')}",
        "",
        "Coverage Dashboard",
        "",
        f"Financials  {cov.get('financials_pct')}%",
        f"Ownership   {cov.get('ownership_pct')}%",
        f"Valuation   {cov.get('valuation_pct')}%",
        f"Macro       {cov.get('macro_pct')}%",
        f"News        {cov.get('news_pct')}%",
    ]
    return "\n".join(lines)


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": OBSERVABILITY_VERSION,
        "governance_programme_status": GOVERNANCE_PROGRAMME_STATUS,
        "scope_locks": dict(SCOPE_LOCKS),
        "presentation_only": True,
        "consumes": ["evaluation_lab_results", "phase6_governance", "recommendation_drift"],
        "post_governance_roadmap": list(POST_GOVERNANCE_ROADMAP),
    }
