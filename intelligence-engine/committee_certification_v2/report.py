"""Markdown / JSON report helpers for Committee Certification v2.0."""

from __future__ import annotations

from typing import Any


def format_markdown(result: dict[str, Any]) -> str:
    agg = result.get("aggregate") or {}
    areas = agg.get("areas") or {}
    lines = [
        f"# AGIB Institutional Committee Certification (IC-10 v2.0)",
        "",
        f"**Version:** {result.get('version')}",
        f"**Total score:** {agg.get('total_score')}/100 — **{agg.get('grade')}**",
        f"**Runs:** {result.get('robustness', {}).get('runs', 1)}",
        "",
        "## Rubric",
        "",
        "| Area | Weight | Score % | Points |",
        "|---|---:|---:|---:|",
    ]
    for key, row in areas.items():
        lines.append(
            f"| {key.replace('_', ' ').title()} | {row.get('weight')} | {row.get('score_pct')} | {row.get('points')} |"
        )
    lines += [
        "",
        f"**Governance:** {'PASS' if (agg.get('governance') or {}).get('pass') else 'FAIL'} "
        f"({(agg.get('governance') or {}).get('score_pct')}%)",
        "",
        "## Committee verdicts",
        "",
    ]
    for v, n in (agg.get("verdicts") or {}).items():
        lines.append(f"- {v}: {n}")

    lines += ["", "## Per company", ""]
    for c in result.get("companies") or []:
        tests = c.get("tests") or {}
        lines.append(
            f"### {c.get('display')} → {c.get('verdict')} "
            f"(resolve `{c.get('resolve')}`, sector `{c.get('sector_key')}`)"
        )
        lines.append("")
        lines.append("| Test | % | Pass | Notes |")
        lines.append("|---|---:|:---:|---|")
        for name, block in tests.items():
            note = ""
            if name == "sector_differentiation":
                note = ", ".join(block.get("vocab_hits") or []) or ("specific" if block.get("specific_reasoning") else "weak vocab")
            elif name == "valuation_intelligence":
                peers = block.get("primary_peers") or []
                note = f"peers={','.join(peers[:4])}; stance={block.get('stance')}"
            elif name == "ownership_intelligence":
                note = "missing" if block.get("ownership_missing") else "fields ok"
            elif name == "evidence_completeness":
                flags = block.get("flags") or {}
                missing = [k for k, v in flags.items() if not v]
                note = f"missing={missing}" if missing else "complete"
            lines.append(
                f"| {name} | {block.get('score_pct')} | {'✅' if block.get('pass') else '❌'} | {note} |"
            )
        lines.append("")

    rob = result.get("robustness") or {}
    lines += [
        "## Robustness",
        "",
        f"- Stable fingerprints: {rob.get('stable_pct')}% ({rob.get('stable_n')}/{rob.get('n')})",
        f"- Pass: {'✅' if rob.get('pass') else '❌'}",
    ]
    if rob.get("unstable"):
        lines.append(f"- Unstable: {', '.join(rob['unstable'])}")

    expect = result.get("expectation_check") or {}
    if expect:
        lines += ["", "## Expectation check (sponsor ranges)", ""]
        for k, v in expect.items():
            lines.append(f"- {k}: {v}")

    return "\n".join(lines) + "\n"


def expectation_check(aggregate: dict[str, Any]) -> dict[str, str]:
    """Compare area points to sponsor expected ranges."""
    areas = aggregate.get("areas") or {}
    ranges = {
        "evidence_completeness": (19.0, 20.0),
        "financial_intelligence": (14.0, 15.0),
        "ownership_intelligence": (10.0, 10.0),
        "valuation_intelligence": (14.0, 15.0),
        "sector_differentiation": (8.0, 10.0),
        "decision_quality": (9.0, 10.0),
        "governance_integrity": (10.0, 10.0),
        "narrative_quality": (4.0, 5.0),
    }
    out = {}
    for k, (lo, hi) in ranges.items():
        pts = float((areas.get(k) or {}).get("points") or 0)
        if pts >= lo:
            status = "meets_or_exceeds" if pts <= hi + 0.5 else "above_expected"
        elif pts >= lo - 2:
            status = "near_expected"
        else:
            status = "below_expected"
        out[k] = f"{pts}/{AREA_WEIGHTS_SAFE(k)} ({status}; expected {lo}-{hi})"
    total = float(aggregate.get("total_score") or 0)
    out["overall"] = f"{total}/100 ({aggregate.get('grade')}; expected ~90-95)"
    return out


def AREA_WEIGHTS_SAFE(k: str) -> float:
    from committee_certification_v2.schema import AREA_WEIGHTS

    return float(AREA_WEIGHTS.get(k) or 0)
