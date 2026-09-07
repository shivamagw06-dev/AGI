"""Company Identity Service — the canonical identity every engine must query.

Resolution order (Capital IQ always wins):
  1. valuation_consensus store  (CapIQ Broker Estimates master)
  2. institutional_knowledge_tables (CapIQ screener exports)

Nothing here infers classification from a business description.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Optional

from company_identity.schema import (
    PRIMARY_SECTORS,
    SOURCE_CAPIQ_CONSENSUS,
    SOURCE_CAPIQ_IKT,
    SOURCE_NONE,
    CompanyIdentity,
)
from company_identity.taxonomy import classify, forbidden_for, framework_for

_LOCK = threading.RLock()
_CACHE: dict[str, CompanyIdentity] = {}
_NAME_INDEX: dict[str, str] | None = None
_SHORT_NAME_INDEX: dict[str, str] | None = None
_SECTOR_LOOKUP = {s.lower(): s for s in PRIMARY_SECTORS}

_LEGAL_TAIL_RE = re.compile(r"\b(limited|ltd|plc|inc|incorporated)\b\.?", re.I)


def _short_name_key(raw_name: Any) -> str:
    """Company name with only the legal suffix removed.

    Distinguishes "ITC Limited" (genuinely one word) from "Birla Corporation
    Limited", whose single-word form only appears because "Corporation" is a
    stripped suffix and which reads as a group name, not a company.
    """
    text = _LEGAL_TAIL_RE.sub(" ", str(raw_name or ""))
    text = re.sub(r"[^\w&\- ]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _normalize_name(name: Any) -> str:
    try:
        from institutional_knowledge_tables.bulk_sheet import normalize_company_name

        return normalize_company_name(name)
    except Exception:
        import re

        return re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()


def _name_index() -> dict[str, str]:
    """Exact normalized company name → ticker, built from the CapIQ master.

    Exact match only. A partial or fuzzy match could bind the wrong company,
    which the Entity Intelligence contract forbids.
    """
    global _NAME_INDEX
    with _LOCK:
        if _NAME_INDEX is not None:
            return _NAME_INDEX
    global _SHORT_NAME_INDEX
    index: dict[str, str] = {}
    short_index: dict[str, str] = {}
    short_ambiguous: set[str] = set()
    ambiguous: set[str] = set()
    try:
        from valuation_consensus.store import load_live

        for ticker, row in (load_live().get("rows") or {}).items():
            # NAME* keys are synthetic row ids minted during import for
            # companies with no exchange ticker. They identify a dashboard
            # row, not a tradable entity, so they must never bind a question.
            if str(ticker).startswith("NAME"):
                continue
            name = _normalize_name(row.get("company_name"))
            if not name:
                continue
            if name in index and index[name] != ticker:
                ambiguous.add(name)
                continue
            index[name] = ticker
            short = _short_name_key(row.get("company_name"))
            if short and " " not in short:
                if short in short_index and short_index[short] != ticker:
                    short_ambiguous.add(short)
                else:
                    short_index[short] = ticker
    except Exception:
        pass
    for name in ambiguous:
        index.pop(name, None)
    for name in short_ambiguous:
        short_index.pop(name, None)
    with _LOCK:
        _NAME_INDEX = index
        _SHORT_NAME_INDEX = short_index
    return index


def _short_name_index() -> dict[str, str]:
    """Single-word company names that are genuinely the whole name."""
    if _SHORT_NAME_INDEX is None:
        _name_index()
    return _SHORT_NAME_INDEX or {}


def ticker_for_name(name: Optional[str]) -> Optional[str]:
    """Resolve an exact company name to its canonical CapIQ ticker."""
    key = _normalize_name(name)
    if not key:
        return None
    return _name_index().get(key)


_MAX_NAME_TOKENS = 12


def prefix_is_unambiguous(key: str, chosen: str, index: dict[str, str]) -> bool:
    """Reject a prefix bind when the stem also abbreviates a different company.

    "Sun Pharma" prefixes Sun Pharma Advanced Research, but it is equally the
    common abbreviation of Sun Pharmaceutical Industries — a different
    company — so neither may be bound from that mention alone.
    """
    tokens = key.split()
    if not tokens:
        return False
    head, last = tokens[:-1], tokens[-1]
    for name in index:
        if name == chosen:
            continue
        parts = name.split()
        if len(parts) <= len(head):
            continue
        if (
            parts[: len(head)] == head
            and parts[len(head)] != last
            and parts[len(head)].startswith(last)
        ):
            return False
    return True

# Single-token company names (ITC, Infosys) are matchable, but only when the
# token cannot be ordinary question vocabulary — otherwise "advance" or
# "value" would bind a namesake company.
_MENTION_STOPWORDS = frozenset(
    {
        "advance", "value", "growth", "income", "credit", "capital", "premium", "future",
        "modern", "global", "national", "international", "india", "indian", "prime", "supreme",
        "sector", "industry", "market", "company", "business", "model", "share", "stock",
        "target", "price", "sales", "profit", "revenue", "margin", "quality", "risk", "report",
        "best", "first", "next", "star", "sun", "moon", "orient", "eco", "wonder", "hi", "tech",
    }
)


def resolve_company_mention(text: Optional[str]) -> tuple[Optional[str], str]:
    """Bind a company mention to a canonical ticker, or refuse.

    Matching is longest-name-first over the question's word windows, so
    "Oil and Natural Gas Corporation Limited's business model?" binds ONGC
    rather than letting a loose keyword match pick Oil India. A mention that
    is not a full name binds only when exactly one CapIQ company name starts
    with it — "Apollo Hospitals" resolves to Apollo Hospitals Enterprise,
    while bare "Apollo" stays ambiguous across Apollo Micro / Tyres / Pipes.
    """
    key = _normalize_name(text)
    if not key:
        return None, "no_mention"
    index = _name_index()

    exact = index.get(key)
    if exact:
        return exact, "exact_name"

    tokens = key.split()
    if len(tokens) < 2:
        # Single generic token is never enough to pick between namesakes.
        return None, "mention_too_short"

    # Longest contiguous window that is exactly a canonical company name.
    for size in range(min(len(tokens), _MAX_NAME_TOKENS), 1, -1):
        hits = {
            index[window]
            for start in range(0, len(tokens) - size + 1)
            if (window := " ".join(tokens[start : start + size])) in index
        }
        if len(hits) == 1:
            return hits.pop(), "name_in_question"
        if len(hits) > 1:
            return None, "ambiguous_mention"

    prefix = f"{key} "
    matched = {
        name: ticker for name, ticker in index.items() if name == key or name.startswith(prefix)
    }
    if len(set(matched.values())) == 1:
        name = next(iter(matched))
        if not prefix_is_unambiguous(key, name, index):
            return None, "abbreviation_collision"
        return matched[name], "unique_prefix"
    if len(matched) > 1:
        return None, "ambiguous_mention"

    # Longest window that uniquely prefixes exactly one canonical name.
    for size in range(min(len(tokens), _MAX_NAME_TOKENS), 1, -1):
        for start in range(0, len(tokens) - size + 1):
            window = " ".join(tokens[start : start + size])
            window_prefix = f"{window} "
            hits = {
                name: ticker
                for name, ticker in index.items()
                if name == window or name.startswith(window_prefix)
            }
            if len(set(hits.values())) == 1:
                name = next(iter(hits))
                if prefix_is_unambiguous(window, name, index):
                    return hits[name], "unique_prefix_in_question"

    # Single-token canonical names, guarded against ordinary vocabulary and
    # against group names whose one-word form is only a stripped suffix.
    short_index = _short_name_index()
    from company_identity.core_aliases import exact_core_alias_ticker
    from entity_intelligence.registry import AMBIGUOUS

    single: list[str] = []
    for tok in tokens:
        if len(tok) < 3 or tok in _MENTION_STOPWORDS:
            continue
        # Ambiguity must hold inside a sentence exactly as it does for a bare
        # mention. Previously bare "Tata" refused, while "What sector is Tata
        # in?" reached this later index and could bind one Tata company.
        if AMBIGUOUS.get(tok):
            continue
        curated = exact_core_alias_ticker(tok)
        if curated:
            single.append(curated)
            continue
        prefix = f"{tok} "
        prefix_tickers = {
            ticker for name, ticker in index.items()
            if name == tok or name.startswith(prefix)
        }
        if len(prefix_tickers) > 1:
            continue
        if tok in short_index:
            single.append(short_index[tok])
    if len(set(single)) == 1:
        return single[0], "single_token_name"
    if len(set(single)) > 1:
        return None, "ambiguous_mention"
    return None, "no_capiq_match"


def _canonical_sector(value: Any) -> Optional[str]:
    """Only ever emit one of the 11 canonical CapIQ Primary Sectors."""
    s = str(value or "").strip()
    if not s:
        return None
    return _SECTOR_LOOKUP.get(s.lower())


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _from_consensus(ticker: str) -> Optional[dict[str, Any]]:
    try:
        from valuation_consensus.store import get_row

        return get_row(ticker)
    except Exception:
        return None


def _from_ikt(ticker: str) -> Optional[dict[str, Any]]:
    try:
        from institutional_knowledge_tables.store import get_table

        master = get_table(ticker, "company_master").get("row") or {}
        biz = get_table(ticker, "business_model").get("row") or {}
        if not master and not biz:
            return None

        def v(row: dict[str, Any], key: str) -> Any:
            cell = row.get(key)
            return cell.get("value") if isinstance(cell, dict) else None

        return {
            "ticker": ticker,
            "company_name": v(master, "company_name"),
            "sector": v(master, "sector"),
            "industry": v(master, "industry"),
            "industry_classification": v(biz, "industry_classifications"),
            "exchange": v(master, "exchange"),
            "country": v(master, "country"),
            "website": v(master, "website"),
            "parent": v(master, "parent_company"),
            "description": v(biz, "description") or v(biz, "description_short"),
            "products": v(biz, "products"),
        }
    except Exception:
        return None


def _build(ticker: str, row: dict[str, Any], source: str) -> CompanyIdentity:
    sector = _canonical_sector(row.get("sector"))
    industry = _clean(row.get("industry"))
    business_type, dna = classify(industry, sector)
    allowed, kpis = framework_for(dna)
    forbidden_val, forbidden_kpi = forbidden_for(dna)
    return CompanyIdentity(
        ticker=ticker,
        company_name=_clean(row.get("company_name")) or ticker,
        primary_sector=sector,
        primary_industry=industry,
        business_type=business_type,
        industry_dna=dna,
        industry_classification=_clean(row.get("industry_classification")),
        exchange=_clean(row.get("exchange") or row.get("primary_exchange")),
        country=_clean(row.get("country")),
        website=_clean(row.get("website")),
        parent=_clean(row.get("parent")),
        products=_clean(row.get("products")),
        competitors=_clean(row.get("competitors")),
        business_description=_clean(row.get("description")),
        market_cap=_clean(row.get("market_cap")),
        enterprise_value=_clean(row.get("enterprise_value")),
        company_type=_clean(row.get("company_type")),
        currency=_clean(row.get("currency")),
        trading_status=_clean(row.get("trading_status") or row.get("status")),
        isin=_clean(row.get("isin")),
        allowed_valuation=allowed,
        forbidden_valuation=forbidden_val,
        kpis=kpis,
        forbidden_kpis=forbidden_kpi,
        source=source,
        resolved=True,
    )


def _unresolved(ticker: str) -> CompanyIdentity:
    return CompanyIdentity(
        ticker=str(ticker or "").strip().upper(),
        company_name=str(ticker or "").strip().upper(),
        primary_sector=None,
        primary_industry=None,
        business_type=None,
        industry_dna=None,
        source=SOURCE_NONE,
        resolved=False,
    )


def invalidate_cache() -> None:
    global _NAME_INDEX
    with _LOCK:
        _CACHE.clear()
        _NAME_INDEX = None


def identity_for(ticker: Optional[str]) -> CompanyIdentity:
    """Canonical, immutable identity for a ticker. Never infers, never guesses."""
    t = str(ticker or "").strip().upper()
    if not t:
        return _unresolved("")
    with _LOCK:
        cached = _CACHE.get(t)
    if cached is not None:
        return cached

    row = _from_consensus(t)
    source = SOURCE_CAPIQ_CONSENSUS
    # Both stores are Capital IQ exports with different column sets: the
    # Broker Estimates master carries consensus and classification, the
    # screener export carries website / country / currency / company type.
    # Merge them, filling only fields the primary row does not already have.
    ikt = _from_ikt(t)
    if ikt:
        merged = dict(row or {})
        for key, value in ikt.items():
            if value is not None and not merged.get(key):
                merged[key] = value
        if not row:
            source = SOURCE_CAPIQ_IKT
        row = merged

    if not row:
        return _unresolved(t)

    ident = _build(t, row, source)
    if not ident.primary_sector and not ident.primary_industry:
        ident = _unresolved(t)
    with _LOCK:
        _CACHE[t] = ident
    return ident


def ambiguous_company_candidates(question: Optional[str], limit: int = 6) -> list[dict[str, Any]]:
    """Capitalised stems in a question that name several Capital IQ companies.

    "Explain Apollo" could mean Apollo Hospitals, Apollo Tyres, Apollo Micro
    Systems or Apollo Pipes. Rather than pick one, the caller should ask which.
    Returns [] when the question names no such stem.
    """
    text = str(question or "")
    if not text.strip():
        return []
    # If the registry can already identify one company from this question,
    # nothing is ambiguous — "Axis Bank" resolves even though "Bank" alone
    # prefixes dozens of names.
    if resolve_company_mention(text)[0]:
        return []
    index = _name_index()
    short_index = _short_name_index()
    for raw in re.findall(r"\b[A-Z][A-Za-z&.\-]{2,}\b", text):
        token = _normalize_name(raw)
        if not token or " " in token or len(token) < 3:
            continue
        if token in _MENTION_STOPWORDS or token in short_index:
            continue
        prefix = f"{token} "
        matches = sorted({name for name in index if name.startswith(prefix)})
        if len(matches) < 2:
            continue
        return [
            {"company_name": name.title(), "ticker": index[name]} for name in matches[:limit]
        ]
    return []


def resolve(ticker_or_name: Optional[str]) -> CompanyIdentity:
    """Identity by ticker, falling back to an exact company-name match."""
    raw = str(ticker_or_name or "").strip()
    if not raw:
        return _unresolved("")
    direct = identity_for(raw)
    if direct.resolved:
        return direct
    mapped = ticker_for_name(raw)
    return identity_for(mapped) if mapped else direct


def context_for(ticker: Optional[str]) -> dict[str, Any]:
    """Compact immutable context for downstream engines."""
    return identity_for(ticker).context()


def health() -> dict[str, Any]:
    try:
        from valuation_consensus.store import load_live

        rows = load_live().get("rows") or {}
        total = len(rows)
        classified = 0
        unmapped: list[str] = []
        for tk, row in rows.items():
            sector = _canonical_sector(row.get("sector"))
            industry = _clean(row.get("industry"))
            business_type, dna = classify(industry, sector)
            if business_type and dna:
                classified += 1
            elif industry:
                unmapped.append(industry)
        pct = round((classified / total) * 100.0, 2) if total else 0.0
        return {
            "ok": True,
            "engine": "company_identity",
            "status": "ok" if pct >= 99.0 else ("degraded" if total else "empty"),
            "companies": total,
            "classified": classified,
            "classification_pct": pct,
            "unmapped_industries": sorted(set(unmapped))[:20],
            "canonical_source": "capital_iq",
        }
    except Exception as exc:
        return {"ok": False, "engine": "company_identity", "error": str(exc)[:200]}
