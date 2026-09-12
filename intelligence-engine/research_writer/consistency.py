"""Consistency engine — one company, ticker, sector, stance, horizon across the report."""

from __future__ import annotations

import re
from typing import Any


def extract_context(pack: dict[str, Any]) -> dict[str, Any]:
    cio = pack.get("cio") if isinstance(pack.get("cio"), dict) else {}
    committee = pack.get("committee") if isinstance(pack.get("committee"), dict) else {}
    decision = pack.get("committee_decision") or committee.get("decision") or {}
    company = (
        pack.get("company")
        or cio.get("company")
        or decision.get("company")
        or "the company"
    )
    ticker = pack.get("ticker") or cio.get("ticker")
    stance = (
        decision.get("committee_position")
        or committee.get("committee_stance")
        or cio.get("committee_stance")
        or "Neutral"
    )
    sector_op = pack.get("sector_intelligence_opinion") or (pack.get("analyst_opinions") or {}).get("sector") or {}
    sector = None
    if isinstance(sector_op, dict):
        sections = sector_op.get("sections") if isinstance(sector_op.get("sections"), dict) else {}
        sector = sections.get("industry_structure") or sector_op.get("summary")
    conf = cio.get("confidence")
    if isinstance(pack.get("confidence"), (int, float)):
        conf = pack.get("confidence")
    return {
        "company": str(company),
        "ticker": str(ticker).upper() if ticker else None,
        "stance": str(stance),
        "sector": str(sector)[:80] if sector else None,
        "horizon": "12–24 months",
        "confidence": conf,
        "valuation_label": (decision.get("valuation") if isinstance(decision, dict) else None) or "Neutral",
    }


def enforce_consistency(text: str, ctx: dict[str, Any]) -> str:
    """Light rename / stance alignment — never invent facts."""
    s = text or ""
    company = ctx.get("company") or "the company"
    # Normalize generic "the company" when we have a real name
    if company and company != "the company":
        s = re.sub(r"\b[Tt]he company\b", company, s, count=2)
    ticker = ctx.get("ticker")
    if ticker and ticker not in s and company in s:
        # Do not force ticker into every paragraph — only leave as-is
        pass
    return s


def consistency_check(sections: dict[str, str], ctx: dict[str, Any]) -> dict[str, Any]:
    company = (ctx.get("company") or "").lower()
    issues: list[str] = []
    for key, text in sections.items():
        if not text:
            continue
        low = text.lower()
        if company and company != "the company" and company not in low and key in {
            "executive_summary",
            "investment_thesis",
            "conclusion",
        }:
            issues.append(f"{key}: company name not present")
    return {"ok": not issues, "issues": issues, "context": ctx}
