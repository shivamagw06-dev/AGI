"""Structured memory_delta + human-readable observations."""

from __future__ import annotations

from typing import Any

from knowledge_delta_engine.detect import detect_evidence_items, detect_section_changes, summary_status
from knowledge_delta_engine.util import memory_fingerprint


def _arrow(before: Any, after: Any) -> str:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        if after > before:
            return "↑"
        if after < before:
            return "↓"
        return "→"
    return "→"


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1000 else f"{v:,.2f}"
    return str(v)


def build_memory_delta(
    prev_memory: dict[str, Any] | None,
    next_memory: dict[str, Any],
) -> dict[str, Any]:
    sections = detect_section_changes(prev_memory, next_memory)
    observations: list[str] = []

    # Friendly labels
    labels = {
        "revenue.ttm": "Revenue",
        "revenue.yoy": "Revenue YoY",
        "pat.ttm": "PAT",
        "pat.yoy": "PAT YoY",
        "roe": "ROE",
        "promoter": "Promoter",
        "fii": "FII",
        "dii": "DII",
        "mutual_funds": "MF",
        "pe": "Valuation PE",
        "premium_pct": "Valuation premium",
        "stance": "Valuation stance",
        "direction": "Trend",
        "latest_price": "Price",
        "max_drawdown_pct": "Max drawdown",
    }

    for section, block in sections.items():
        for ch in block.get("changes") or []:
            field = ch.get("field")
            path = str(ch.get("path") or "")
            # Prefer short semantic label (e.g. revenue.ttm → Revenue)
            short_path = ".".join(path.split(".")[-2:]) if path.count(".") >= 1 else path
            label = labels.get(short_path) or labels.get(field) or field
            before, after = ch.get("before"), ch.get("after")
            if ch.get("delta_type") == "ADDED":
                observations.append(f"{label} added: {_fmt(after)}")
            elif ch.get("delta_type") == "REMOVED":
                observations.append(f"{label} removed (was {_fmt(before)})")
            elif isinstance(before, (int, float)) and isinstance(after, (int, float)):
                pct = ch.get("change_pct")
                arrow = _arrow(before, after)
                if pct is not None:
                    observations.append(f"{label} {arrow} {pct:+.1f}% ({_fmt(before)} → {_fmt(after)})")
                else:
                    observations.append(f"{label} {arrow} {_fmt(before)} → {_fmt(after)}")
            else:
                observations.append(f"{label} {before} → {after}")

    # Section-level narrative shortcuts
    fin = sections.get("financial") or {}
    own = sections.get("ownership") or {}
    val = sections.get("valuation") or {}
    if not fin.get("changed"):
        observations.append("Financial snapshot unchanged vs prior memory.")
    if own.get("changed"):
        for ch in own.get("changes") or []:
            if ch.get("field") == "promoter" and ch.get("delta_type") == "UNCHANGED":
                pass
    else:
        # Explicit no-change for promoter if present
        prom_b = ((prev_memory or {}).get("ownership_history") or {}).get("latest", {}).get("promoter")
        prom_a = (next_memory.get("ownership_history") or {}).get("latest", {}).get("promoter")
        if prom_b is not None and prom_a is not None and prom_b == prom_a:
            observations.append("Promoter — no change.")

    if val.get("changed"):
        for ch in val.get("changes") or []:
            if ch.get("field") == "premium_pct" and isinstance(ch.get("after"), (int, float)):
                if ch.get("before") is not None and float(ch["after"]) > float(ch["before"]):
                    observations.append("Valuation — premium expanded.")
                elif ch.get("before") is not None and float(ch["after"]) < float(ch["before"]):
                    observations.append("Valuation — premium compressed / discount widened.")

    corp = sections.get("corporate") or {}
    if corp.get("changed"):
        observations.append("Strategy / corporate themes updated.")

    evidence_delta = detect_evidence_items(
        (prev_memory or {}).get("lineage"),
        next_memory.get("lineage"),
    )

    status = summary_status(sections)
    identical = (
        prev_memory is not None
        and memory_fingerprint(prev_memory) == memory_fingerprint(next_memory)
    )
    if identical:
        status = "UNCHANGED"

    return {
        "status": status,
        "identical_to_prior": identical,
        "prior_version": (prev_memory or {}).get("memory_version"),
        "sections": {
            "financial": sections.get("financial"),
            "ownership": sections.get("ownership"),
            "valuation": sections.get("valuation"),
            "corporate": sections.get("corporate"),
            "sector": sections.get("sector"),
            "market": sections.get("market"),
            "governance": sections.get("governance"),
            "events": sections.get("events"),
            "risk": sections.get("risk"),
        },
        "observations": observations[:40],
        "summary": "; ".join(observations[:8]) if observations else "No material memory changes.",
        "evidence_items": evidence_delta,
        "n_section_changes": sum(1 for s in sections.values() if s.get("changed")),
        "n_field_changes": sum(int(s.get("n_changes") or 0) for s in sections.values()),
    }
