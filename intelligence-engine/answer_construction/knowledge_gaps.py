"""Translate internal missing-field checklists into professional knowledge-gap language.

Never expose raw snake_case evidence keys to clients.
"""

from __future__ import annotations

import re
from typing import Any

_GAP_MAP = {
    "financial_statements": "Additional financial statement history is still being collected.",
    "financial_statement": "Additional financial statement history is still being collected.",
    "income_statement": "Income-statement history coverage is still being completed.",
    "balance_sheet": "Balance-sheet history coverage is still being completed.",
    "cash_flow": "Cash-flow statement coverage is still being completed.",
    "cash_flow_statement": "Cash-flow statement coverage is still being completed.",
    "market_data": "Live market context remains incomplete for a full institutional read.",
    "valuation_metrics": "Historical valuation coverage is incomplete.",
    "valuation": "Historical valuation coverage is incomplete.",
    "market_cap": "Market capitalisation coverage is still limited.",
    "shares_outstanding": "Share-count / dilution coverage is still limited.",
    "ownership": "Institutional ownership data is still limited.",
    "institutional_ownership": "Institutional ownership data is still limited.",
    "insider_ownership": "Insider ownership data is still limited.",
    "sector_kpis": "Sector operating metrics require additional evidence.",
    "sector_kpi": "Sector operating metrics require additional evidence.",
    "filings": "Additional quarterly filings are being processed.",
    "latest_filings": "Additional quarterly filings are being processed.",
    "announcements": "Recent corporate announcements coverage is still forming.",
    "earnings": "Latest earnings detail is still being assembled.",
    "peer_comparison": "Peer comparison coverage remains incomplete.",
    "management": "Management-quality evidence remains limited.",
    "business_model": "Business-model documentation is still being enriched.",
    "roic": "Return-on-capital history requires additional validated evidence.",
    "roe": "Return metrics require additional validated evidence.",
    "margins": "Margin history requires additional validated evidence.",
    "revenue_growth": "Growth history requires additional validated evidence.",
    "free_cash_flow": "Free-cash-flow history requires additional validated evidence.",
    "ev_ebitda": "EV-based valuation coverage is incomplete.",
    "pe": "Earnings-multiple history remains incomplete.",
    "pb": "Book-value multiple history remains incomplete.",
    "dividend": "Dividend / capital-return history remains incomplete.",
    "must_have": "Core institutional evidence items are still being completed.",
}

_CHECKLIST_RE = re.compile(
    r"(?i)\b(missing|coverage|research grade|data grade|knowledge grade|recommendation withheld|"
    r"cid coverage|ecp coverage|company analysis readiness|gate:)\b"
)
_SNAKE_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+){1,}\b")


def _norm_key(item: Any) -> str:
    s = str(item or "").strip().lower()
    s = s.replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def professional_gap(item: Any) -> str:
    key = _norm_key(item)
    if not key:
        return "Additional institutional evidence is still being assembled."
    if key in _GAP_MAP:
        return _GAP_MAP[key]
    for token, phrase in _GAP_MAP.items():
        if token in key or key in token:
            return phrase
    label = str(item).replace("_", " ").strip()
    if not label or _SNAKE_RE.fullmatch(str(item).strip().lower()):
        return "Additional institutional evidence is still being assembled for this dimension."
    return f"{label[:1].upper()}{label[1:]} coverage is still being completed."


def knowledge_gaps_from_sources(
    *,
    evidence_completion: dict[str, Any] | None = None,
    company_dossier: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    limit: int = 8,
) -> list[str]:
    raw: list[Any] = []
    ecp = evidence_completion if isinstance(evidence_completion, dict) else {}
    panel = ecp.get("quality_panel") or {}
    raw.extend(panel.get("missing_items") or [])
    raw.extend(panel.get("must_have_missing") or [])
    raw.extend(ecp.get("still_missing") or [])
    if isinstance(ecp.get("pass2"), dict):
        raw.extend((ecp.get("pass2") or {}).get("still_missing") or [])

    cid = company_dossier if isinstance(company_dossier, dict) else {}
    raw.extend(cid.get("missing_evidence") or [])

    leo = live_evidence if isinstance(live_evidence, dict) else {}
    gate = leo.get("quality_gate") or {}
    raw.extend(gate.get("must_have_missing") or [])
    raw.extend(gate.get("missing") or [])

    ca = company_analysis if isinstance(company_analysis, dict) else {}
    readiness = ca.get("recommendation_readiness") or {}
    for reason in readiness.get("explanation") or []:
        if reason and "sufficient for analysis" not in str(reason).lower():
            raw.append(reason)

    out: list[str] = []
    for item in raw:
        phrase = professional_gap(item)
        if phrase not in out:
            out.append(phrase)
        if len(out) >= limit:
            break
    if not out and (panel.get("gate_blocked") or gate.get("blocked")):
        out = [
            "Additional financial statement history is still being collected.",
            "Historical valuation coverage is incomplete.",
            "Sector operating metrics require additional evidence.",
        ]
    return out[:limit]


def is_checklist_bullet(text: Any) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    low = s.lower()
    if s.lower().startswith("missing:"):
        return True
    if "recommendation withheld" in low:
        return True
    if re.search(r"(?i)\b(cid coverage|ecp coverage|research grade|data grade|knowledge grade)\b", s):
        return True
    if re.search(r"(?i)data confidence grades", s):
        return True
    if re.search(r"(?i)company analysis readiness .*gate:", s):
        return True
    if re.search(r"(?i)\b(ecp auto-completed|still missing after ecp|quality gates —)\b", s):
        return True
    if re.search(r"(?i)company monitor:\s*\d+\s*change", s):
        return True
    if re.search(r"(?i)\d+\s+supporting .* items retrieved", s):
        return True
    if re.search(r"(?i)related news items included for freshness", s):
        return True
    if "intelligence construction" in low or "academy concepts attached" in low:
        return True
    if "living dossier" in low and len(s) < 160:
        return True
    # Raw snake_case checklist residue
    snakes = _SNAKE_RE.findall(low)
    if snakes and any(k in _GAP_MAP for k in snakes) and _CHECKLIST_RE.search(s):
        return True
    if low.startswith("insufficient evidence"):
        return True
    if "insufficient company evidence" in low:
        return True
    return False


def filter_why_bullets(why: list[Any] | None, *, gaps: list[str] | None = None, limit: int = 12) -> list[str]:
    out: list[str] = []
    for item in why or []:
        s = str(item or "").strip()
        if not s or is_checklist_bullet(s):
            continue
        if s not in out:
            out.append(s[:420])
        if len(out) >= limit:
            break
    # Knowledge gaps belong in their own section — do not stuff them into why.
    _ = gaps
    return out[:limit]


def looks_like_gate_failure_summary(text: Any) -> bool:
    s = str(text or "").strip().lower()
    if not s:
        return False
    markers = (
        "recommendation withheld",
        "insufficient evidence view",
        "insufficient company evidence",
        "missing:",
        "to reach institutional grade retrieve",
        "coverage:",
        "research grade:",
        "data grade:",
        "knowledge grade:",
    )
    hits = sum(1 for m in markers if m in s)
    return hits >= 1 and (
        "withheld" in s
        or "insufficient" in s
        or s.startswith("recommendation")
        or "missing:" in s
    )
