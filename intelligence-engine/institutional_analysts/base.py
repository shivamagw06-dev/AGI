"""Shared helpers for analyst opinions — no engine calls."""

from __future__ import annotations

import re
from typing import Any

from institutional_analysts.mandates import DOMAIN_FORBIDDEN, mandate_for
from institutional_analysts.memory import get_previous_opinion

_INTERNAL = re.compile(
    r"\b(CID|LEO|IRP|DVC|ECP|SIF|FLE|MEE|AOI|EVE|IIE|KF|KIP|FAA|FRE|AIL|CAE|"
    r"Company Analysis|Financial Intelligence|MarketDataClient|Yahoo|Groww|IndianAPI|"
    r"AlphaVantage|TwelveData|Capital IQ|provider|API|engine|Academy)\b",
    re.I,
)

_STANCE_WORDS = {
    "bullish": "Bullish",
    "constructive": "Bullish",
    "positive": "Bullish",
    "improving": "Bullish",
    "strong": "Bullish",
    "attractive": "Bullish",
    "bearish": "Bearish",
    "cautious": "Bearish",
    "negative": "Bearish",
    "deteriorat": "Bearish",
    "weak": "Bearish",
    "expensive": "Bearish",
    "rich": "Bearish",
    "neutral": "Neutral",
    "mixed": "Neutral",
    "balanced": "Neutral",
    "stable": "Neutral",
}


def scrub_public(text: Any, *, limit: int = 420) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _INTERNAL.sub("institutional research", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def as_list(value: Any, *, limit: int = 8) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = scrub_public(value, limit=220)
        return [item] if item else []
    out: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (str, int, float)) and str(v).strip():
                out.append(scrub_public(f"{k}: {v}", limit=180))
            elif isinstance(v, list):
                out.extend(as_list(v, limit=limit))
            if len(out) >= limit:
                break
        return out[:limit]
    for item in value:
        if isinstance(item, dict):
            title = item.get("title") or item.get("claim") or item.get("label") or item.get("name")
            summary = item.get("summary") or item.get("text") or item.get("snippet")
            piece = scrub_public(title or summary or "", limit=200)
        else:
            piece = scrub_public(item, limit=200)
        if piece and piece not in out:
            out.append(piece)
        if len(out) >= limit:
            break
    return out


def pick_confidence(*values: Any, default: float = 0.55) -> float:
    for v in values:
        if v is None:
            continue
        try:
            n = float(v)
        except Exception:
            continue
        if n > 1.0:
            n = n / 100.0
        return max(0.05, min(0.99, round(n, 4)))
    return default


def company_name(ctx: dict[str, Any]) -> str:
    for key in ("company_name", "name"):
        if ctx.get(key):
            return str(ctx[key])
    cid = ctx.get("company_dossier") or {}
    identity = cid.get("identity") if isinstance(cid, dict) else {}
    if isinstance(identity, dict) and identity.get("company_name"):
        return str(identity["company_name"])
    ca = ctx.get("company_analysis") or {}
    if isinstance(ca, dict):
        ca_identity = ca.get("identity") if isinstance(ca.get("identity"), dict) else {}
        if ca.get("company_name"):
            return str(ca["company_name"])
        if ca_identity.get("company_name"):
            return str(ca_identity["company_name"])
        if ca.get("ticker"):
            return str(ca["ticker"])
    return str(ctx.get("ticker") or "the company")


def ticker_of(ctx: dict[str, Any]) -> str | None:
    for src in (ctx, ctx.get("company_analysis") or {}, ctx.get("company_dossier") or {}, ctx.get("intelligence_layer") or {}):
        if isinstance(src, dict) and src.get("ticker"):
            return str(src["ticker"]).upper()
    return None


def infer_stance(text: str, *, default: str = "Neutral") -> str:
    s = (text or "").lower()
    for needle, label in _STANCE_WORDS.items():
        if needle in s:
            return label
    return default


def confidence_block(
    *,
    evidence: float | None = None,
    knowledge: float | None = None,
    freshness: float | None = None,
    coverage: float | None = None,
    overall: float | None = None,
    default: float = 0.55,
) -> dict[str, float]:
    ev = pick_confidence(evidence, default=default)
    kn = pick_confidence(knowledge, default=default)
    fr = pick_confidence(freshness, default=default)
    cov = pick_confidence(coverage, default=default)
    if overall is None:
        overall = round((ev * 0.35 + kn * 0.25 + fr * 0.2 + cov * 0.2), 4)
    return {
        "evidence": ev,
        "knowledge": kn,
        "freshness": fr,
        "coverage": cov,
        "overall": pick_confidence(overall, default=default),
    }


def domain_scrub(role: str, text: Any, *, limit: int = 280) -> str:
    """Remove out-of-domain phrases and internal names from analyst free text."""
    s = scrub_public(text, limit=limit * 2)
    if not s:
        return ""
    for pattern in DOMAIN_FORBIDDEN.get(role, ()):
        s = re.sub(pattern, "", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" -;,:.")
    return s[:limit]


def _clean_sections(role: str, sections: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for k, v in (sections or {}).items():
        if isinstance(v, list):
            clean[k] = [domain_scrub(role, x, limit=180) for x in as_list(v, limit=8)]
            clean[k] = [x for x in clean[k] if x]
        elif isinstance(v, dict):
            nested = {
                sk: domain_scrub(role, sv, limit=160)
                for sk, sv in v.items()
                if sv not in (None, "", [])
            }
            clean[k] = {sk: sv for sk, sv in nested.items() if sv}
        else:
            piece = domain_scrub(role, v, limit=260)
            if piece:
                clean[k] = piece
    return clean


def _what_changed(previous: dict[str, Any] | None, *, stance: str, summary: str, strengths: list[str], weaknesses: list[str]) -> dict[str, Any] | None:
    if not previous:
        return None
    prev_stance = previous.get("stance") or "Neutral"
    prev_summary = scrub_public(previous.get("summary") or "", limit=200)
    changed = prev_stance != stance
    notes: list[str] = []
    if changed:
        notes.append(f"Stance moved from {prev_stance} to {stance}.")
    if prev_summary and prev_summary != summary:
        notes.append(f"Prior view: {prev_summary}")
    prev_strengths = as_list(previous.get("strengths"), limit=3)
    if strengths and prev_strengths and strengths[0] != prev_strengths[0]:
        notes.append(f"Lead strength shifted toward: {strengths[0]}")
    prev_weak = as_list(previous.get("weaknesses"), limit=3)
    if weaknesses and prev_weak and weaknesses[0] != prev_weak[0]:
        notes.append(f"Lead concern shifted toward: {weaknesses[0]}")
    if not notes:
        notes.append("Opinion stable versus prior review.")
    return {
        "previous_stance": prev_stance,
        "current_stance": stance,
        "changed": changed or bool(prev_summary and prev_summary != summary),
        "notes": notes[:4],
        "previous_summary": prev_summary or None,
    }


def structured_opinion(
    *,
    role: str,
    summary: str,
    strengths: list[Any] | None = None,
    weaknesses: list[Any] | None = None,
    evidence: list[Any] | None = None,
    unanswered_questions: list[Any] | None = None,
    sections: dict[str, Any] | None = None,
    stance: str | None = None,
    confidence: dict[str, Any] | float | None = None,
    score: float | None = None,
    ticker: str | None = None,
    ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical structured analyst opinion — not a prose paragraph dump."""
    meta = mandate_for(role)
    t = ticker or (ticker_of(ctx) if ctx else None)
    previous = get_previous_opinion(t, role)

    clean_summary = domain_scrub(role, summary, limit=280)
    strength_list = [domain_scrub(role, x, limit=160) for x in as_list(strengths, limit=6)]
    strength_list = [x for x in strength_list if x]
    weak_list = [domain_scrub(role, x, limit=160) for x in as_list(weaknesses, limit=6)]
    weak_list = [x for x in weak_list if x]
    evidence_list = [domain_scrub(role, x, limit=180) for x in as_list(evidence, limit=10)]
    evidence_list = [x for x in evidence_list if x]
    open_q = [domain_scrub(role, x, limit=180) for x in as_list(unanswered_questions, limit=6)]
    open_q = [x for x in open_q if x]
    clean_sections = _clean_sections(role, sections or {})

    if isinstance(confidence, dict):
        conf = confidence_block(
            evidence=confidence.get("evidence"),
            knowledge=confidence.get("knowledge"),
            freshness=confidence.get("freshness"),
            coverage=confidence.get("coverage"),
            overall=confidence.get("overall"),
        )
    else:
        base = pick_confidence(confidence, default=0.55)
        conf = confidence_block(evidence=base, knowledge=base, freshness=base * 0.95, coverage=base, overall=base)

    stance_label = stance or infer_stance(" ".join([clean_summary, *strength_list, *weak_list]))
    if stance_label not in {"Bullish", "Neutral", "Bearish"}:
        stance_label = infer_stance(stance_label)

    what_changed = _what_changed(
        previous,
        stance=stance_label,
        summary=clean_summary,
        strengths=strength_list,
        weaknesses=weak_list,
    )

    return {
        "role": role,
        "analyst": meta["analyst"],
        "owner": role,
        "mandate": {
            "text": meta["mandate"],
            "primary_question": meta["primary_question"],
            "primary_inputs": list(meta.get("primary_inputs") or []),
            "outputs": list(meta.get("outputs") or []),
            "never": list(meta.get("never") or []),
        },
        "primary_question": meta["primary_question"],
        "question": meta["primary_question"],  # backward-compatible alias
        "summary": clean_summary,
        "headline": clean_summary,  # UI / AC alias
        "stance": stance_label,
        "strengths": strength_list,
        "weaknesses": weak_list,
        "evidence": evidence_list,
        "unanswered_questions": open_q,
        "sections": clean_sections,
        "confidence": conf,
        "score": None if score is None else round(float(score), 2),
        "what_changed": what_changed,
        "structured": True,
    }


# Backward-compatible name used by older imports
def opinion(
    *,
    role: str,
    question: str = "",
    headline: str = "",
    sections: dict[str, Any] | None = None,
    evidence: list[str] | None = None,
    confidence: float = 0.55,
    score: float | None = None,
    word_limit: int = 500,
    **kwargs: Any,
) -> dict[str, Any]:
    _ = question, word_limit
    return structured_opinion(
        role=role,
        summary=headline,
        strengths=kwargs.get("strengths"),
        weaknesses=kwargs.get("weaknesses"),
        evidence=evidence,
        unanswered_questions=kwargs.get("unanswered_questions"),
        sections=sections,
        stance=kwargs.get("stance"),
        confidence=confidence,
        score=score,
        ticker=kwargs.get("ticker"),
        ctx=kwargs.get("ctx"),
    )


def public_title(role: str) -> str:
    return mandate_for(role).get("analyst") or role.replace("_", " ").title()
