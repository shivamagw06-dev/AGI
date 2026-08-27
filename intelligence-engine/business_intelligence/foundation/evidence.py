"""Assemble company/industry evidence from CapIQ IKT + soft sector context.

Deterministic only. Never fabricates company facts.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from business_intelligence.foundation.taxonomy import (
    canonical_industry_key,
    classify_industry,
    normalize_industry,
)


def _cell(row: dict[str, Any], key: str) -> Any:
    cell = row.get(key)
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def load_ikt_company(ticker: Optional[str]) -> dict[str, Any]:
    if not ticker:
        return {}
    try:
        from institutional_knowledge_tables.store import get_table

        master = get_table(ticker, "company_master").get("row") or {}
        biz = get_table(ticker, "business_model").get("row") or {}
        return {
            "ticker": ticker,
            "company_name": _cell(master, "company_name") or ticker,
            "sector": _cell(master, "sector"),
            "industry": _cell(master, "industry"),
            "country": _cell(master, "country"),
            "description": _cell(biz, "description") or _cell(biz, "description_short"),
            "products": _cell(biz, "products") or _cell(biz, "products_services"),
            "competitors": _cell(biz, "competitors") or _cell(biz, "key_competitors"),
            "customers": _cell(biz, "customers"),
            "geography": _cell(biz, "geography"),
            "business_segments": _cell(biz, "business_segments"),
            "revenue_mix": _cell(biz, "revenue_mix"),
            "competitive_position": _cell(biz, "competitive_position"),
            "source": "institutional_knowledge_tables",
        }
    except Exception:
        return {"ticker": ticker}


_PEDAGOGY_RE = re.compile(
    r"\b(what is|what are|what creates|explain|how should|how to|classify|compare)\b",
    re.I,
)
_CORPORATE_FORM_RE = re.compile(
    r"\b(limited|ltd\.?|industries|bank|motors|enterprises|corporation|inc\.?)\b",
    re.I,
)
_KNOWN_COMPANY_ALIASES = (
    "hdfc bank", "icici bank", "reliance", "infosys", "tcs", "wipro", "ongc",
    "state bank", "kotak", "axis bank", "sbi", "dmart", "asian paints",
    "jsw steel", "indigo", "interglobe", "adani", "tata motors", "tata steel",
    "air india",
)


def detect_ticker(question: str) -> Optional[str]:
    q = question or ""
    # Pure pedagogy / concept questions must not bind CapIQ noise
    # ("capital allocation" → B.P. Capital, "key risks" → Key Corp).
    if _PEDAGOGY_RE.search(q) and not _CORPORATE_FORM_RE.search(q):
        low = q.lower()
        if not any(a in low for a in _KNOWN_COMPANY_ALIASES):
            return None
    try:
        from app.ui.company_router import detect_ikt_company

        return detect_ikt_company(q)
    except Exception:
        return None


_COMPARE_RE = re.compile(
    r"\b(compare|vs\.?|versus|against|more profitable than|higher margins than|"
    r"better margins than)\b",
    re.I,
)


def extract_compare_names(question: str) -> list[str]:
    """Lightweight pair extraction for 'TCS vs Infosys' / 'Compare A and B'."""
    q = question or ""
    if not _COMPARE_RE.search(q):
        return []

    # Prefer explicit "Compare X and Y ..." before vs-splitting.
    m = re.search(
        r"\bcompare\s+(.+?)\s+and\s+(.+?)(?:\s+as\b|\s+on\b|\s+business\b|\s*$)",
        q,
        flags=re.I,
    )
    m2 = re.search(
        r"\b(?:why (?:is|does|do)\s+)?(.+?)\s+(?:more profitable|higher margins|better margins)\s+than\s+(.+?)(?:\?|$)",
        q,
        flags=re.I,
    )
    if m:
        raw_parts = [m.group(1), m.group(2)]
    elif m2:
        raw_parts = [m2.group(1), m2.group(2)]
    else:
        raw_parts = re.split(r"\bvs\.?|versus\b", q, flags=re.I)[:2]

    names: list[str] = []
    for part in raw_parts:
        cleaned = re.sub(
            r"\b(compare|and|the|business|models?|moat|of|for|with|on|"
            r"axes?|economics?|as|capital|allocators?|earn|earns|is|does|do|why)\b",
            " ",
            part,
            flags=re.I,
        )
        cleaned = re.sub(r"[^A-Za-z0-9 &\-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -&")
        if cleaned and len(cleaned) >= 2:
            names.append(cleaned)
    return names[:2]


def _synthetic_uncovered_company(name: str) -> dict[str, Any]:
    """Industry-template placeholder for a named firm outside CapIQ coverage."""
    from business_intelligence.foundation.named_pedagogy import lookup_named_pedagogy

    ped = lookup_named_pedagogy(name=name)
    industry_key = (ped or {}).get("industry_key") or classify_industry(question=name, industry=name)
    return {
        "ticker": None,
        "company_name": name.strip(),
        "sector": None,
        "industry": industry_key,
        "description": (ped or {}).get("how_it_makes_money"),
        "source": "name_only_uncovered",
        "uncovered": True,
        "archetype": (ped or {}).get("archetype"),
    }


def assemble_evidence(
    question: str,
    *,
    ticker: Optional[str] = None,
    industry_hint: Optional[str] = None,
) -> dict[str, Any]:
    from business_intelligence.foundation.named_pedagogy import lookup_named_pedagogy

    tk = ticker or detect_ticker(question)
    company = load_ikt_company(tk) if tk else {}
    ped = lookup_named_pedagogy(
        name=company.get("company_name"),
        ticker=tk,
        question=question,
    )
    # Capital IQ classification is canonical and outranks named pedagogy,
    # caller hints, and any description-derived guess.
    industry_key = (
        canonical_industry_key(tk)
        or (ped or {}).get("industry_key")
        or normalize_industry(industry_hint)
        or classify_industry(
            sector=company.get("sector"),
            industry=company.get("industry"),
            description=str(company.get("description") or ""),
            question=question,
        )
    )
    compare_names = extract_compare_names(question)
    compare_tickers: list[str] = []
    compare_companies: list[dict[str, Any]] = []
    for name in compare_names:
        ct = detect_ticker(name) or detect_ticker(f"Explain {name}")
        if ct:
            compare_tickers.append(ct)
            compare_companies.append(load_ikt_company(ct))
        else:
            # Keep the named company in the comparison axis set without
            # inventing CapIQ facts (e.g. Air India outside IKT coverage).
            compare_companies.append(_synthetic_uncovered_company(name))

    # Soft industry playbook (optional)
    playbook: dict[str, Any] = {}
    try:
        from knowledge_factory.industry_intelligence.production import playbook as iivi_playbook

        pb = iivi_playbook(industry_key) if industry_key != "unknown" else {}
        if isinstance(pb, dict) and pb.get("ok") is not False:
            playbook = pb
    except Exception:
        playbook = {}

    evidence_items: list[dict[str, Any]] = []
    if company.get("description"):
        evidence_items.append(
            {
                "source": "capiq_ikt.business_model",
                "title": f"{tk}.description",
                "snippet": str(company["description"])[:280],
            }
        )
    if company.get("sector") or company.get("industry"):
        evidence_items.append(
            {
                "source": "capiq_ikt.company_master",
                "title": f"{tk}.sector_industry",
                "snippet": f"{company.get('sector')} / {company.get('industry')}",
            }
        )

    return {
        "question": question,
        "ticker": tk,
        "company": company,
        "industry_key": industry_key,
        "compare_names": compare_names,
        "compare_tickers": compare_tickers,
        "compare_companies": compare_companies,
        "playbook": playbook,
        "evidence": evidence_items,
        "fabricated": False,
    }
