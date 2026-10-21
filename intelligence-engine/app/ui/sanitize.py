"""Strip internal engine / platform identifiers from client payloads."""

from __future__ import annotations

import re
from typing import Any

# Public label map — never leak E0x / L4 / ORCH codes to clients.
_ENGINE_LABELS = {
    "E01": "market_regime",
    "E02": "factor_context",
    "E03": "technical",
    "E04": "relative_value",
    "E05": "events",
    "E08": "volatility",
    "E09": "trend",
    "E10": "model_portfolio",
    "E11": "sentiment",
    "E13": "fundamentals",
    "E14": "market_risk",
    "L4": "composite_view",
    "e01": "market_regime",
    "e02": "factor_context",
    "e03": "technical",
    "e04": "relative_value",
    "e05": "events",
    "e08": "volatility",
    "e09": "trend",
    "e10": "model_portfolio",
    "e11": "sentiment",
    "e13": "fundamentals",
    "e14": "market_risk",
    "l4": "composite_view",
}

_ENGINE_RE = re.compile(
    r"(?<![A-Za-z0-9])(E0[1-9]|E1[0-4]|L4|ORCH|CRE|RSP|RMS|KIP|IOC|AWS|AIP|CID|IRP|LEO|SIF|ECP|DVC|FAPI|CAE|CMS|FIML|AGIB_INVESTMENT_DECISION_ENGINE)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Drop internal orchestration / gate keys from client SearchView payloads.
_INTERNAL_CLIENT_KEYS = {
    "leo_blocked",
    "sif_blocked",
    "architecture_status",
    "concept_ids",
    "concepts_influencing_answer",
    "must_have_missing",
    "missing_leo",
    "missing_items",
    "missing_evidence",
    "ecp_version",
    "yfp_version",
    "provider_id",
    "winning_provider",
}

# Never expose market-data vendor / API / Yahoo-native terms in client answers.
_PROVIDER_RE = re.compile(
    r"(?i)\b("
    r"yahoo(?:\s*finance)?|yfinance|quotesummary|quoteSummary|"
    r"indianapi|indian\s*api|finnhub|fmp|"
    r"financialmodelingprep|financial\s*modeling\s*prep|"
    r"provider_id|provider\s*confidence|winning_provider|"
    r"api\s*key|x-api-key"
    r")\b"
)

_SOURCE_PUBLIC = {
    "KIP": "knowledge",
    "RSP": "research_committee",
    "RMS": "research_desk",
    "CRE": "evaluation",
    "IOC": "operations",
    "AWS": "workspace",
    "Replay": "historical_replay",
    "L4": "composite_view",
    "E01": "market_regime",
    "E02": "factor_context",
    "E03": "technical",
    "E04": "relative_value",
    "E05": "events",
    "E08": "volatility",
    "E09": "trend",
    "E10": "model_portfolio",
    "E11": "sentiment",
    "E13": "fundamentals",
    "E14": "market_risk",
    "yahoo": "institutional",
    "Yahoo": "institutional",
    "Yahoo Finance": "institutional",
    "yfinance": "institutional",
    "indianapi": "institutional",
    "finnhub": "institutional",
    "fmp": "institutional",
    "YFP": "institutional",
}


def public_source(name: str | None) -> str:
    if not name:
        return "institutional"
    return _SOURCE_PUBLIC.get(str(name), _SOURCE_PUBLIC.get(str(name).upper(), "institutional"))


def public_label(key: str | None) -> str:
    if not key:
        return "signal"
    return _ENGINE_LABELS.get(str(key), _ENGINE_LABELS.get(str(key).upper(), str(key)))


def scrub_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = _ENGINE_RE.sub("institutional research", str(value))
    text = _PROVIDER_RE.sub("institutional data", text)
    # Soften leftover checklist phrasing that can still reach clients
    text = re.sub(r"(?i)\bIRP\s*V1\b", "Institutional Research", text)
    return text


def scrub(obj: Any) -> Any:
    """Recursively rename engine keys and scrub strings for client responses."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in _INTERNAL_CLIENT_KEYS:
                continue
            # Strip provider-native / enrichment provenance keys from client payloads
            if lk in {
                "provider_id",
                "provider",
                "winning_provider",
                "winning_provider_summary",
                "provider_confidence",
                "yfp_version",
                "enrichment",
                "yahoo",
                "quoteSummary",
                "quotesummary",
                "yfinance",
            }:
                continue
            if k in {"sources", "meta", "engine_versions", "formula_versions", "engines"}:
                # Drop or rewrite later by caller
                if k == "sources" and isinstance(v, list):
                    out["sources"] = sorted({public_source(x) for x in v})
                elif k == "engines" and isinstance(v, dict):
                    out["model_evidence"] = {
                        public_label(ek): scrub(ev) for ek, ev in v.items()
                    }
                elif k == "meta" and isinstance(v, dict):
                    meta = dict(v)
                    if isinstance(meta.get("sources"), list):
                        meta["sources"] = sorted(
                            {public_source(x) for x in meta["sources"]}
                        )
                    meta.pop("workspace", None)
                    out["meta"] = scrub(meta)
                continue
            pk = public_label(k) if k in _ENGINE_LABELS or k.upper() in _ENGINE_LABELS else k
            # Also map nested e01/l4 style keys and compound keys like E03_xs_momentum
            if re.fullmatch(r"[eE]\d{2}|[lL]4", str(k) or ""):
                pk = public_label(k)
            elif re.match(r"^(E0[1-9]|E1[0-4]|L4|e0[1-9]|e1[0-4]|l4)([_\-.].*)?$", str(k) or ""):
                m = re.match(r"^(E0[1-9]|E1[0-4]|L4|e0[1-9]|e1[0-4]|l4)([_\-.].*)?$", str(k))
                base = public_label(m.group(1)) if m else str(k)
                suffix = m.group(2) or ""
                pk = f"{base}{suffix}"
            out[pk] = scrub(v)
        return out
    return obj


def pick_label(state: dict[str, Any] | None, *keys: str) -> str | None:
    if not state:
        return None
    for k in keys:
        v = state.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            for nested in ("label", "regime", "risk_level", "side", "name", "status"):
                if nested in v and v[nested] is not None:
                    return scrub_text(str(v[nested]))
            continue
        return scrub_text(str(v))
    return None


def pick_number(state: dict[str, Any] | None, *keys: str) -> float | None:
    if not state:
        return None
    for k in keys:
        v = state.get(k)
        if v is None:
            continue
        if isinstance(v, dict):
            for nested in ("value", "score", "composite_score", "confidence"):
                if nested in v:
                    try:
                        return float(v[nested])
                    except (TypeError, ValueError):
                        continue
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None
