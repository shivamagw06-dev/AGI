"""Deterministic field normalisation for IEW scoring."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def _s(v: Any) -> str:
    return str(v or "").strip().lower()


def canonical_source(raw: Any, profile: dict[str, Any]) -> str:
    text = _s(raw)
    if not text:
        return "unknown"
    aliases = profile.get("source_aliases") or {}
    cred = profile.get("source_credibility") or {}
    # Exact / alias
    if text in cred:
        return text
    if text in aliases:
        return str(aliases[text])
    # Token / substring heuristics (deterministic order)
    for needle, canon in (
        ("audited", "audited_filing"),
        ("annual report", "annual_report"),
        ("10-k", "annual_report"),
        ("quarterly", "quarterly_results"),
        ("10-q", "quarterly_results"),
        ("exchange", "exchange_filing"),
        ("nse", "exchange_filing"),
        ("bse", "exchange_filing"),
        ("sebi", "regulator"),
        ("rbi", "regulator"),
        ("regulator", "regulator"),
        ("government", "government_notification"),
        ("gazette", "government_notification"),
        ("conference call", "conference_call"),
        ("transcript", "conference_call"),
        ("investor presentation", "investor_presentation"),
        ("press release", "company_ir"),
        ("investor relations", "company_ir"),
        ("reuters", "reuters"),
        ("bloomberg", "bloomberg"),
        ("broker", "broker_research"),
        ("social", "social_media"),
        ("rumour", "rumour"),
        ("rumor", "rumour"),
        ("fixture", "fixture"),
        ("synthetic", "synthetic"),
        ("seed", "seed"),
    ):
        if needle in text:
            return canon
    # snake / slug
    slug = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if slug in cred:
        return slug
    if slug in aliases:
        return str(aliases[slug])
    return "unknown"


def infer_materiality(obj: dict[str, Any]) -> str:
    explicit = _s(obj.get("materiality") or obj.get("materiality_class"))
    if explicit in ("direct", "supporting", "context", "peripheral"):
        return explicit
    rel = _s(obj.get("relationship") or obj.get("kind") or "")
    title = _s(obj.get("title") or obj.get("label") or "")
    strength = obj.get("evidence_strength")
    try:
        es = float(strength) if strength is not None else None
    except (TypeError, ValueError):
        es = None
    if "direct" in rel or "primary" in rel:
        return "direct"
    if es is not None and es >= 0.85:
        return "direct"
    if es is not None and es >= 0.6:
        return "supporting"
    if "context" in rel or "macro" in title:
        return "context"
    if "peripheral" in rel or "rumour" in title:
        return "peripheral"
    # Graph domain / node kind defaults
    kind = _s(obj.get("kind"))
    if kind in ("evidence", "filing", "fact"):
        return "supporting"
    if kind in ("memory", "analogue", "analog"):
        return "context"
    return "unknown"


def infer_quality(obj: dict[str, Any], source_canon: str) -> str:
    explicit = _s(obj.get("evidence_quality") or obj.get("quality_class") or obj.get("quality"))
    if explicit in (
        "audited",
        "primary",
        "secondary",
        "derived",
        "estimated",
        "synthetic",
        "fixture",
        "seed",
    ):
        return explicit
    if obj.get("fabricated") is True or obj.get("fixture") is True:
        return "fixture"
    if source_canon in ("fixture", "seed", "synthetic"):
        return source_canon
    if source_canon in ("audited_filing", "annual_report"):
        return "audited"
    if source_canon in (
        "exchange_filing",
        "quarterly_results",
        "regulator",
        "government_notification",
        "company_ir",
        "conference_call",
    ):
        return "primary"
    if source_canon in ("reuters", "bloomberg", "broker_research", "industry_research"):
        return "secondary"
    if source_canon in ("estimated", "derived"):
        return source_canon
    if obj.get("llm_used") is True:
        return "derived"
    return "unknown"


def infer_specificity(obj: dict[str, Any]) -> str:
    explicit = _s(obj.get("specificity") or obj.get("specificity_class"))
    if explicit in ("company", "business_unit", "segment", "industry", "macro", "general"):
        return explicit
    entity = obj.get("entity") or obj.get("company") or obj.get("ticker")
    domain = _s(obj.get("domain") or obj.get("industry") or "")
    if entity and str(entity).strip() and str(entity).lower() not in ("none", "null", "market"):
        return "company"
    if "segment" in domain or "business unit" in domain:
        return "segment"
    if domain in ("industry", "sector") or "sector" in domain:
        return "industry"
    if "macro" in domain or "policy" in domain:
        return "macro"
    return "unknown"


def _parse_date(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    text = str(raw).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(text[:19].replace("Z", ""), fmt.replace("Z", ""))
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    if re.match(r"^\d{4}$", text):
        try:
            return datetime(int(text), 12, 31, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def infer_freshness(obj: dict[str, Any], *, as_of: str | None) -> str:
    explicit = _s(obj.get("freshness") or obj.get("freshness_class"))
    if explicit in ("current", "recent", "historical", "replay_safe", "stale"):
        return explicit
    as_of_dt = _parse_date(as_of) or datetime.now(timezone.utc)
    ref = (
        _parse_date(obj.get("available_from"))
        or _parse_date(obj.get("timestamp"))
        or _parse_date(obj.get("source_timestamp"))
        or _parse_date(obj.get("effective_date"))
    )
    temporal = _s(obj.get("temporal_status"))
    if ref is None:
        if temporal == "allowed":
            return "replay_safe"
        return "unknown"
    days = max(0, (as_of_dt - ref).days)
    if days <= 90:
        return "current"
    if days <= 365:
        return "recent"
    if temporal == "allowed":
        return "replay_safe"
    if days > 3650:
        return "stale"
    return "historical"


def temporal_status_of(obj: dict[str, Any]) -> str:
    ts = _s(obj.get("temporal_status"))
    if ts in ("allowed", "rejected", "unknown", "n/a"):
        return ts
    if obj.get("tirc_rejected") is True:
        return "rejected"
    return "allowed" if obj.get("available_from") else "unknown"
