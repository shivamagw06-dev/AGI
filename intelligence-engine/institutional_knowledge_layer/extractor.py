"""Universal Knowledge Extractor — structured facts from any ingested document.

Soft heuristic extraction. Downstream LLM extractors (CID/CM) can enrich later.
Never raises.
"""

from __future__ import annotations

import re
from typing import Any

from institutional_knowledge_layer.schema import (
    EXTRACTION_SLOTS,
    IKL_SCHEMA_VERSION,
    now_ts,
)

_TICKER_RE = re.compile(r"\b([A-Z]{2,12})\b")
_KPI_RE = re.compile(
    r"\b(revenue|ebitda|pat|margins?|roe|roce|capex|guidance|npa|nim|aum)\b",
    re.I,
)
_RISK_RE = re.compile(
    r"\b(risks?|headwinds?|uncertainty|volatilit(?:y|ies)|volatile|downgrade)\b",
    re.I,
)
_OPP_RE = re.compile(
    r"\b(opportunit(?:y|ies)|tailwinds?|upside|expansion|growth)\b",
    re.I,
)
_POLICY_RE = re.compile(r"\b(policy|regulation|rbi|sebi|gst|pli|budget|subsidy)\b", re.I)
_EVENT_RE = re.compile(
    r"\b(earnings|acquisition|merger|ipo|buyback|dividend|rating|guidance)\b",
    re.I,
)
_GUIDANCE_RE = re.compile(r"\b(guidance|outlook|guided|expects?|forecast)\b", re.I)

_STOP = {
    "THE",
    "AND",
    "FOR",
    "WITH",
    "FROM",
    "THIS",
    "THAT",
    "HAVE",
    "WILL",
    "WHAT",
    "WHEN",
    "WHERE",
    "WHICH",
    "ABOUT",
    "INDIA",
    "USD",
    "INR",
    "CEO",
    "CFO",
    "GDP",
    "RBI",
    "SEBI",
    "NSE",
    "BSE",
    "PDF",
    "HTTP",
    "HTTPS",
    "API",
    "JSON",
}


def _clip(text: str, n: int = 280) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 24][:40]


def extract_knowledge(
    *,
    text: str,
    title: str = "",
    source_id: str = "",
    source_type: str = "",
    company_hint: str | None = None,
    industry_hint: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a structured knowledge bag for one document."""
    try:
        blob = f"{title or ''}\n{text or ''}".strip()
        if not blob:
            return {
                "schema_version": IKL_SCHEMA_VERSION,
                "extracted_at": now_ts(),
                "source_id": source_id or None,
                "source_type": source_type or None,
                "slots": {s: [] for s in EXTRACTION_SLOTS},
                "confidence": 0.0,
            }

        meta = meta if isinstance(meta, dict) else {}
        companies: list[str] = []
        if company_hint:
            companies.append(str(company_hint).strip().upper())
        for m in meta.get("tickers") or meta.get("companies") or []:
            if isinstance(m, str) and m.strip():
                cu = m.strip().upper()
                if cu not in companies:
                    companies.append(cu)
        # Only harvest ALL-CAPS tokens that look like equity tickers when we
        # already have a hint — avoid prose pollution (REVENUE, GROWTH, …).
        if company_hint or meta.get("tickers") or meta.get("companies"):
            known = set(companies)
            for tok in _TICKER_RE.findall(blob.upper()):
                if tok in _STOP or len(tok) < 3 or len(tok) > 12:
                    continue
                # Prefer tokens already known / short exchange-style codes
                if tok in known:
                    continue
                if len(tok) <= 10 and tok.isalpha() and tok in {
                    str(company_hint or "").upper(),
                    *[str(x).upper() for x in (meta.get("competitors") or []) if isinstance(x, str)],
                }:
                    companies.append(tok)
                if len(companies) >= 12:
                    break
        else:
            # No hint: keep at most a few uppercase tokens that appear with
            # company-ish context; still soft / best-effort.
            for tok in _TICKER_RE.findall(blob.upper()):
                if tok in _STOP or not (3 <= len(tok) <= 12):
                    continue
                if tok not in companies:
                    companies.append(tok)
                if len(companies) >= 3:
                    break

        industries: list[str] = []
        if industry_hint:
            industries.append(str(industry_hint).strip())
        for m in meta.get("industries") or meta.get("sectors") or []:
            if isinstance(m, str) and m.strip():
                industries.append(m.strip())

        themes = [
            t.strip()
            for t in (meta.get("themes") or [])
            if isinstance(t, str) and t.strip()
        ][:12]

        sents = _sentences(blob)
        kpis = [_clip(s) for s in sents if _KPI_RE.search(s)][:8]
        risks = [_clip(s) for s in sents if _RISK_RE.search(s)][:8]
        opps = [_clip(s) for s in sents if _OPP_RE.search(s)][:8]
        policies = [_clip(s) for s in sents if _POLICY_RE.search(s)][:6]
        events = [_clip(s) for s in sents if _EVENT_RE.search(s)][:8]
        guidance = [_clip(s) for s in sents if _GUIDANCE_RE.search(s)][:6]

        products = [
            str(x).strip()
            for x in (meta.get("products") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        segments = [
            str(x).strip()
            for x in (meta.get("segments") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        management = [
            str(x).strip()
            for x in (meta.get("management") or [])
            if isinstance(x, str) and x.strip()
        ][:8]
        countries = [
            str(x).strip()
            for x in (meta.get("countries") or meta.get("geographies") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        commodities = [
            str(x).strip()
            for x in (meta.get("commodities") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        competitors = [
            str(x).strip().upper()
            for x in (meta.get("competitors") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        suppliers = [
            str(x).strip().upper()
            for x in (meta.get("suppliers") or [])
            if isinstance(x, str) and x.strip()
        ][:12]
        customers = [
            str(x).strip().upper()
            for x in (meta.get("customers") or [])
            if isinstance(x, str) and x.strip()
        ][:12]

        relationships: list[dict[str, Any]] = []
        primary = companies[0] if companies else None
        for ind in industries[:3]:
            if primary:
                relationships.append(
                    {
                        "from_type": "company",
                        "from_id": primary,
                        "rel": "belongs_to",
                        "to_type": "industry",
                        "to_id": ind,
                        "confidence": 0.55,
                    }
                )
        for c in competitors[:5]:
            if primary and c != primary:
                relationships.append(
                    {
                        "from_type": "company",
                        "from_id": primary,
                        "rel": "competes_with",
                        "to_type": "company",
                        "to_id": c,
                        "confidence": 0.45,
                    }
                )
        for theme in themes[:5]:
            if primary:
                relationships.append(
                    {
                        "from_type": "theme",
                        "from_id": theme,
                        "rel": "linked_to",
                        "to_type": "company",
                        "to_id": primary,
                        "confidence": 0.4,
                    }
                )

        filled = sum(
            1
            for v in (
                companies,
                industries,
                themes,
                kpis,
                risks,
                opps,
                events,
                relationships,
            )
            if v
        )
        confidence = min(0.95, 0.15 + 0.1 * filled)

        slots = {
            "companies": companies[:12],
            "industries": industries[:8],
            "themes": themes[:12],
            "products": products,
            "segments": segments,
            "management": management,
            "countries": countries,
            "commodities": commodities,
            "competitors": competitors,
            "suppliers": suppliers,
            "customers": customers,
            "government_policies": policies,
            "financial_kpis": kpis,
            "guidance": guidance,
            "risks": risks,
            "opportunities": opps,
            "events": events,
            "relationships": relationships[:40],
        }
        # Ensure all declared slots exist
        for s in EXTRACTION_SLOTS:
            slots.setdefault(s, [])

        return {
            "schema_version": IKL_SCHEMA_VERSION,
            "extracted_at": now_ts(),
            "source_id": source_id or None,
            "source_type": source_type or None,
            "title": _clip(title, 160) if title else None,
            "slots": slots,
            "confidence": round(confidence, 3),
            "excerpt": _clip(blob, 400),
        }
    except Exception:
        return {
            "schema_version": IKL_SCHEMA_VERSION,
            "extracted_at": now_ts(),
            "source_id": source_id or None,
            "slots": {s: [] for s in EXTRACTION_SLOTS},
            "confidence": 0.0,
            "error": "extract_failed",
        }
