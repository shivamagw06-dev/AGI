"""Question-cue → framework overlays (Sprint 3.3 — selector optimisation).

Cue overlays fire even when intent routing is imperfect, so sector-correct
frameworks are composed alongside risk / document / ops frameworks.
"""

from __future__ import annotations

import re
from typing import Any

# (cue pattern, list of (framework_id, role), tag)
# Multi-word cues match as substrings; single tokens use word boundaries.
CUE_FRAMEWORKS: list[tuple[str, list[tuple[str, str]], str]] = [
    # Risk / falsification
    ("institutional risks", [("FW_RISK", "primary"), ("FW_SCENARIO", "secondary")], "risk"),
    ("risk checklist", [("FW_RISK", "primary"), ("FW_SCENARIO", "secondary")], "risk"),
    ("falsify", [("FW_RISK", "primary"), ("FW_SCENARIO", "supporting")], "risk"),
    ("bullish thesis", [("FW_RISK", "primary"), ("FW_SCENARIO", "secondary")], "risk"),
    ("invalidate", [("FW_RISK", "primary")], "risk"),
    # Documents / governance
    ("institutional documents", [("FW_CORPORATE_GOVERNANCE", "primary"), ("FW_RISK", "secondary"), ("FW_CAPITAL_ALLOCATION", "supporting")], "documents"),
    ("annual report", [("FW_CORPORATE_GOVERNANCE", "primary"), ("FW_RISK", "secondary")], "documents"),
    ("md&a", [("FW_RISK", "primary"), ("FW_CORPORATE_GOVERNANCE", "secondary")], "documents"),
    ("notes to accounts", [("FW_ACCOUNTING_QUALITY", "primary"), ("FW_RISK", "secondary")], "documents"),
    ("related party", [("FW_CORPORATE_GOVERNANCE", "primary"), ("FW_RISK", "secondary")], "documents"),
    ("auditor", [("FW_ACCOUNTING_QUALITY", "primary"), ("FW_CORPORATE_GOVERNANCE", "supporting")], "documents"),
    ("investor presentation", [("FW_CORPORATE_GOVERNANCE", "primary"), ("FW_ACCOUNTING_QUALITY", "secondary")], "documents"),
    ("capital allocation", [("FW_CAPITAL_ALLOCATION", "primary"), ("FW_CORPORATE_GOVERNANCE", "secondary")], "documents"),
    ("emerging risks", [("FW_RISK", "primary"), ("FW_CORPORATE_GOVERNANCE", "supporting")], "documents"),
    # Bank / NBFC valuation language
    ("residual income", [("FW_RESIDUAL_INCOME", "primary"), ("FW_PB", "primary")], "banks_val"),
    ("price-to-book", [("FW_PB", "primary"), ("FW_RESIDUAL_INCOME", "primary")], "banks_val"),
    ("p/b", [("FW_PB", "primary"), ("FW_RESIDUAL_INCOME", "supporting")], "banks_val"),
    # IT operating / valuation language
    ("deal wins", [("FW_ROIC", "secondary"), ("FW_CASH_FLOW_QUALITY", "supporting")], "it_ops"),
    ("attrition", [("FW_ROIC", "secondary"), ("FW_BUSINESS_QUALITY", "supporting")], "it_ops"),
    ("tcv", [("FW_DCF", "primary"), ("FW_CASH_FLOW_QUALITY", "secondary")], "it_ops"),
    ("cash conversion", [("FW_CASH_FLOW_QUALITY", "primary"), ("FW_DCF", "secondary")], "it_ops"),
    ("utilisation", [("FW_ROIC", "secondary"), ("FW_INDUSTRY_STRUCTURE", "supporting")], "ops"),
    # Airlines
    ("load factor", [("FW_AVIATION_OPS", "primary"), ("FW_EV_EBITDAR", "primary")], "airlines"),
    ("atf", [("FW_AVIATION_OPS", "primary"), ("FW_MACRO_TRANSMISSION", "supporting")], "airlines"),
    ("fuel cost", [("FW_AVIATION_OPS", "primary"), ("FW_MACRO_TRANSMISSION", "supporting")], "airlines"),
    ("yield", [("FW_AVIATION_OPS", "primary")], "airlines"),
    # Macro transmission soft
    ("transmission", [("FW_MACRO_TRANSMISSION", "primary"), ("FW_SCENARIO", "secondary")], "macro"),
    ("first-order", [("FW_MACRO_TRANSMISSION", "primary"), ("FW_SCENARIO", "secondary")], "macro"),
]


def cue_overlays(question: str) -> list[tuple[str, str, str]]:
    """Return (framework_id, role, source_tag) for matching cues."""
    low = (question or "").lower()
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for cue, frameworks, tag in CUE_FRAMEWORKS:
        if " " in cue or "/" in cue or "&" in cue or "-" in cue:
            hit = cue in low
        else:
            hit = re.search(rf"(?<![a-z0-9]){re.escape(cue)}(?![a-z0-9])", low) is not None
        if not hit:
            continue
        for fid, role in frameworks:
            key = f"{fid}:{role}"
            if key in seen:
                continue
            seen.add(key)
            out.append((fid, role, f"cue:{tag}"))
    return out


def sector_enrichment(sector: str | None) -> list[tuple[str, str, str]]:
    """Extra supporting frameworks per sector (Sprint 3.3 composition)."""
    s = (sector or "").lower()
    table: dict[str, list[tuple[str, str]]] = {
        "banks": [
            ("FW_MACRO_TRANSMISSION", "supporting"),
            ("FW_RISK", "supporting"),
            ("FW_SCENARIO", "supporting"),
        ],
        "nbfc": [
            ("FW_RISK", "secondary"),
            ("FW_SCENARIO", "supporting"),
            ("FW_MACRO_TRANSMISSION", "supporting"),
        ],
        "it_services": [
            ("FW_CASH_FLOW_QUALITY", "supporting"),
            ("FW_BUSINESS_QUALITY", "supporting"),
            ("FW_PEER_COMPARISON", "supporting"),
        ],
        "airlines": [
            ("FW_MACRO_TRANSMISSION", "supporting"),
            ("FW_SCENARIO", "supporting"),
            ("FW_RISK", "supporting"),
        ],
    }
    return [(fid, role, f"sector_enrich:{s}") for fid, role in table.get(s, [])]
