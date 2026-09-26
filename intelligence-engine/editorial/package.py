"""Sanitize AGIB outputs into editorial structured intelligence packages.

Never include PDFs, news, filings, transcripts, or raw statements.
"""

from __future__ import annotations

from typing import Any

from editorial.schema import ALLOWED_STRUCTURED_KEYS, FORBIDDEN_KEYS


def _txt(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _list(values: Any, limit: int = 5) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        t = _txt(item)
        if t:
            out.append(t[:240])
        if len(out) >= limit:
            break
    return out


def contains_forbidden_payload(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_l = str(key).lower()
            if key_l in FORBIDDEN_KEYS or any(bad in key_l for bad in ("pdf", "transcript", "annual_report")):
                return True
            if contains_forbidden_payload(value):
                return True
    elif isinstance(payload, list):
        return any(contains_forbidden_payload(v) for v in payload)
    return False


def sanitize_structured(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only allowed structured fields. Drop everything else."""
    src = payload if isinstance(payload, dict) else {}
    out: dict[str, Any] = {}
    for key in ALLOWED_STRUCTURED_KEYS:
        if key not in src:
            continue
        value = src[key]
        if key in {"top_reasons", "top_risks"}:
            out[key] = _list(value, 5)
        elif isinstance(value, (dict, list)):
            # Nested blobs are not allowed in editorial packages.
            continue
        else:
            text = _txt(value)
            if text:
                out[key] = text[:200]
    return out


def build_structured_package(
    *,
    question: str | None = None,
    institutional_answer: dict[str, Any] | None = None,
    answer_construction: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    company: str | None = None,
    ticker: str | None = None,
    execution_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build editorial JSON solely from AGIB structured outputs."""
    ia = institutional_answer if isinstance(institutional_answer, dict) else {}
    ac = answer_construction if isinstance(answer_construction, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    ep = execution_policy if isinstance(execution_policy, dict) else {}
    bq = ca.get("business_quality") if isinstance(ca.get("business_quality"), dict) else {}

    valuation_label = (
        _txt((ca.get("valuation") or {}).get("label"))
        if isinstance(ca.get("valuation"), dict)
        else _txt(ca.get("valuation_label"))
    )
    # Never allow unsupported fair/expensive labels when policy withholds narrative.
    if ep and ep.get("narrative_allowed") is False:
        valuation_label = "Insufficient evidence — frameworks pending"
    elif ep.get("summary"):
        # Prefer framework execution summary over vague adjectives when present.
        if not valuation_label or str(valuation_label).lower() in {
            "fair",
            "expensive",
            "cheap",
            "neutral",
            "n/a",
            "na",
        }:
            valuation_label = _txt(ep.get("summary"))

    reasons = (
        _list([ia.get("reason")], 3)
        if ia.get("reason")
        else _list(ac.get("bull") or ac.get("why") or [], 3)
    )
    # Prepend framework status lines so editorial cannot ignore execution policy.
    for hint in (ep.get("ask_agi_hints") or [])[:2]:
        t = _txt(hint)
        if t and t not in reasons:
            reasons.insert(0, t[:240])
    reasons = reasons[:5]

    structured = {
        "question": _txt(question),
        "company": _txt(company) or _txt(ca.get("company_name")) or _txt((ca.get("identity") or {}).get("company_name")),
        "ticker": _txt(ticker),
        "recommendation": _txt(ia.get("recommendation")) or _txt(ac.get("house_label")) or "Hold",
        "conviction": _txt(ia.get("conviction")),
        "business_quality": _txt(bq.get("grade")) or _txt(bq.get("label")) or _txt(ca.get("business_quality_label")),
        "financial_quality": _txt((ca.get("financial_quality") or {}).get("label"))
        if isinstance(ca.get("financial_quality"), dict)
        else _txt(ca.get("financial_quality_label")),
        "valuation": valuation_label,
        "valuation_evidence": _txt(ep.get("summary")),
        "framework_status": _txt(
            "; ".join(
                f"{r.get('name')}:{r.get('status')}"
                for r in (ep.get("results") or [])[:4]
                if isinstance(r, dict)
            )
        ),
        "top_reasons": reasons,
        "top_risks": (
            _list([ia.get("risk")], 3)
            if ia.get("risk")
            else _list(ac.get("risks") or ac.get("bear") or [], 3)
        ),
        "investment_horizon": _txt(ia.get("horizon")) or _txt(ac.get("investment_horizon")) or "Medium Term",
        "stance": _txt(ac.get("house_label")),
        "confidence": _txt(ia.get("conviction")),
        "evidence_insufficient": _txt(ia.get("evidence_insufficient")),
        "investment_thesis_status": _txt(ia.get("investment_thesis_status")),
        "not_a_negative_view": _txt(ia.get("not_a_negative_view")),
        "mode": "recommendation" if ia.get("is_recommendation_query") or ia.get("enabled") else "quick_analysis",
    }
    return sanitize_structured(structured)
