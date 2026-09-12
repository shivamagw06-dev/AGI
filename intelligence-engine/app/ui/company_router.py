"""IKT Company Router — routes company-shaped questions to Institutional
Knowledge Tables (IKT) once a company has real bulk-uploaded data.

Why this exists: `institutional_knowledge_tables/bulk_sheet.py` can ingest
a Capital IQ-style company screener export in full (all 40 columns, every
company resolved — see `institutional_knowledge_tables/PHASE_BULK_NOTES`
in the ingest run), but nothing in the live Ask pipeline ever read from
IKT — `entity_resolution`'s static seed registry only recognizes ~22
companies, so a freshly-bulk-loaded company (e.g. "HMT Limited") would
still hit the unknown-entity hard stop or generic retrieval even though
its real business model, sector, financials, and competitors are sitting
in IKT.

This module is the fix: build a name/ticker index directly from whatever
is actually in the IKT store (never a hardcoded list — grows automatically
as more companies are bulk-uploaded) and answer company-shaped questions
about basic company profile straight from that structured data, with full
evidence lineage (source, effective_date) per fact — no retrieval, no LLM.

Deliberately scoped to descriptive "what/tell me about/explain" company
profile questions (business model, sector, snapshot financials,
competitors) — NOT investment recommendations or narrative synthesis,
which stay with the existing Executive Composer / recommendation policy.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Optional

_INDEX_LOCK = threading.RLock()
_INDEX_CACHE: Optional[dict[str, str]] = None  # normalized_name -> ticker
_TICKER_SET_CACHE: Optional[set[str]] = None


def _normalize_name(name: str):
    from institutional_knowledge_tables.bulk_sheet import normalize_company_name

    return normalize_company_name(name)


def _build_index() -> tuple[dict[str, str], set[str]]:
    from institutional_knowledge_tables.store import get_table, list_companies

    name_index: dict[str, str] = {}
    tickers: set[str] = set()
    for ticker in list_companies():
        tickers.add(ticker)
        row = get_table(ticker, "company_master").get("row") or {}
        name_cell = row.get("company_name") or {}
        name = name_cell.get("value") if isinstance(name_cell, dict) else None
        if name:
            norm = _normalize_name(str(name))
            if norm and norm not in name_index:
                name_index[norm] = ticker
    return name_index, tickers


def _get_index(*, refresh: bool = False) -> tuple[dict[str, str], set[str]]:
    global _INDEX_CACHE, _TICKER_SET_CACHE
    with _INDEX_LOCK:
        if refresh or _INDEX_CACHE is None:
            _INDEX_CACHE, _TICKER_SET_CACHE = _build_index()
        return _INDEX_CACHE, _TICKER_SET_CACHE


def invalidate_index_cache() -> None:
    """Call after a fresh bulk upload so newly-ingested companies are
    immediately findable without a process restart."""

    global _INDEX_CACHE, _TICKER_SET_CACHE
    with _INDEX_LOCK:
        _INDEX_CACHE = None
        _TICKER_SET_CACHE = None


_TICKER_TOKEN_RE = re.compile(r"\b([A-Z]{2,15}\d{0,6})\b")
_QUESTION_WORDS = ("explain", "what", "describe", "tell", "about", "is", "the")
# Tickers that are also common English finance words — only bind when the
# original question contains the token in ticker casing (e.g. bare PREMIUM),
# never when it only appears as lowercase prose ("premium pricing").
_AMBIGUOUS_TICKER_TOKENS = frozenset(
    {
        "PREMIUM",
        "VALUE",
        "GROWTH",
        "INCOME",
        "CREDIT",
        "ADVANCE",
        "CAPITAL",
        "POWER",
        "ENERGY",
        "FINANCE",
        "GLOBAL",
    }
)


_STOPWORDS_FOR_MATCH = {
    "explain", "what", "describe", "tell", "about", "is", "the", "why", "how",
    "does", "of", "for", "give", "me", "a", "in", "on", "business", "model",
}

# Hard generics never count toward a company-name match.
_HARD_GENERIC_WORDS = frozenset(
    {
        "india", "indian", "limited", "ltd", "private", "public", "group",
        "company", "industries", "enterprise", "enterprises", "holdings",
        "international", "national", "global", "corp", "corporation",
        "services", "finance", "financial", "air", "tech", "technology",
        "market", "markets", "premium", "value", "growth", "income", "credit",
        "advance", "asset", "management", "insurance", "the",
    }
)
# Soft sector words may count only alongside a distinctive token
# (tata+power ✓, bare power ✗, hdfc+company ✗).
_SOFT_GENERIC_WORDS = frozenset(
    {
        "capital", "power", "energy", "steel", "bank", "motors", "life",
        "paint", "paints", "cement", "pharma",
    }
)
_GENERIC_OVERLAP_WORDS = _HARD_GENERIC_WORDS | _SOFT_GENERIC_WORDS

# Explicit non-binds for known uncovered names that fuzzy-match wrong IKT rows.
_EXPLICIT_NO_BIND = frozenset(
    {
        "air india",
        "airindia",
    }
)


def detect_ikt_company(question: str) -> Optional[str]:
    """Returns the resolved IKT ticker for a company mentioned in the
    question, or None. Three tiers, most-specific first:
    1. A bare ticker token already in the IKT store's ticker set.
    2. A full normalized company-name phrase appearing verbatim as a
       substring of the (normalized) question — handles both short names
       ("HMT") and full names asked about directly.
    3. Word-overlap scoring — handles partial/abbreviated company names
       ("Texmaco Infrastructure" for "Texmaco Infrastructure & Holdings
       Limited") by requiring most of the company name's own words to
       appear in the question, picking the best-covered, most-specific
       match rather than any single word in isolation.
    """

    q = (question or "").strip()
    if not q:
        return None
    low_q = q.lower()
    if any(blocked in low_q for blocked in _EXPLICIT_NO_BIND):
        # Still allow other tickers in the same question (e.g. IndiGo vs Air India).
        # Strip the blocked phrase before matching so Air India cannot bind IKT.
        for blocked in _EXPLICIT_NO_BIND:
            low_q = low_q.replace(blocked, " ")
        q = re.sub(r"(?i)\bair[\s-]?india\b", " ", q)
    name_index, tickers = _get_index()
    if not name_index:
        return None

    for token in _TICKER_TOKEN_RE.findall(q.upper()):
        if token not in tickers:
            continue
        if token in _AMBIGUOUS_TICKER_TOKENS and not re.search(rf"\b{token}\b", q):
            continue
        return token

    norm_q = _normalize_name(q)
    if not norm_q:
        return None

    if norm_q in name_index:
        return name_index[norm_q]

    # Tier 2: literal substring — longest company-name match wins. Single-
    # word normalized names need a higher length floor (avoids a short,
    # generic-word remnant of a legal-suffix strip causing false positives
    # in unrelated questions); multi-word phrases are inherently specific
    # enough at a lower floor.
    substring_hits: list[tuple[int, str]] = []
    for norm_name, ticker in name_index.items():
        # Single-token legal-suffix-stripped names (e.g. "jct") need len≥3.
        min_len = 3 if " " in norm_name else 3
        if len(norm_name) >= min_len and f" {norm_name} " in f" {norm_q} ":
            substring_hits.append((len(norm_name), ticker))
    if substring_hits:
        substring_hits.sort(key=lambda t: t[0], reverse=True)
        return substring_hits[0][1]

    # Tier 3: word-overlap — most of the company name's words present.
    # Single-character tokens are excluded: they are almost always a
    # normalization artifact (e.g. an "&"-joined name like "S&S Power
    # Switchgear Limited" -> "s s power switchgear") rather than a real,
    # distinguishing word, and would otherwise let unrelated questions
    # spuriously match on a bare "s" or "a".
    words = {w for w in norm_q.split() if len(w) >= 2} - _STOPWORDS_FOR_MATCH
    if not words:
        return None
    best: Optional[tuple[float, int, int, str]] = None  # (hits, coverage_milli, name_len, ticker)
    for norm_name, ticker in name_index.items():
        name_words = [
            w
            for w in norm_name.split()
            if len(w) >= 2 and w not in _STOPWORDS_FOR_MATCH
        ]
        if not name_words:
            continue
        matched = [w for w in name_words if w in words]
        if not matched:
            continue
        distinctive = [w for w in matched if w not in _GENERIC_OVERLAP_WORDS]
        soft_hits = [w for w in matched if w in _SOFT_GENERIC_WORDS]
        # Pure hard/soft generic matches are never enough.
        if not distinctive:
            continue
        if len(name_words) == 1:
            if len(name_words[0]) < 3:
                continue
        else:
            # Multi-word: need distinctive + another token (distinctive or soft).
            if len(distinctive) + len(soft_hits) < 2:
                continue
        hits = len(matched)
        coverage = hits / len(name_words)
        if coverage < 0.45:
            continue
        candidate = (len(distinctive), hits, int(coverage * 1000), len(norm_name), ticker)
        if best is None or candidate[:4] > best[:4]:
            best = candidate
    return best[4] if best else None


def _field(row: dict[str, Any], name: str) -> Optional[Any]:
    cell = row.get(name)
    if isinstance(cell, dict):
        return cell.get("value")
    return None


def _evidence_entry(table: str, field: str, cell: Any) -> Optional[dict[str, Any]]:
    if not isinstance(cell, dict):
        return None
    return {
        "source": cell.get("source") or f"institutional_knowledge_tables.{table}",
        "title": f"{table}.{field}",
        "effective_date": cell.get("effective_date"),
    }


def answer_company_profile(ticker: str, question: str) -> Optional[dict[str, Any]]:
    """Builds a company-profile answer from IKT data alone. Returns None if
    the company has no usable business_model/company_master content."""

    from institutional_knowledge_tables.store import get_table

    master = get_table(ticker, "company_master")
    biz = get_table(ticker, "business_model")
    market = get_table(ticker, "market_data")
    financials = get_table(ticker, "financial_statements")
    competitors = get_table(ticker, "competitors")

    master_row = master.get("row") or {}
    biz_row = biz.get("row") or {}
    company_name = _field(master_row, "company_name") or ticker
    description = _field(biz_row, "description") or _field(biz_row, "description_short")
    if not description and not _field(master_row, "sector"):
        return None  # nothing real to say — do not fabricate a profile

    sector = _field(master_row, "sector")
    industry = _field(master_row, "industry")
    country = _field(master_row, "country")
    company_type = _field(master_row, "company_type")

    parts = []
    if description:
        # Use only the first 2-3 sentences of a (often very long) CapIQ
        # business description for the direct answer — full text stays
        # available via the IKT API, this is a summary lead, not a
        # regenerated/paraphrased narrative.
        sentences = re.split(r"(?<=[.!?])\s+", description.strip())
        parts.append(" ".join(sentences[:3]))
    elif sector or industry:
        parts.append(
            f"{company_name} operates in the {industry or sector} industry within the {sector} sector."
        )

    why: list[str] = []
    evidence: list[dict[str, Any]] = []

    if sector or industry:
        why.append(f"Sector: {sector or 'n/a'}; Industry: {industry or 'n/a'}.")
        ev = _evidence_entry("company_master", "sector", master_row.get("sector"))
        if ev:
            evidence.append(ev)

    if company_type or country:
        why.append(f"{company_type or 'Company'} based in {country or 'n/a'}.")

    market_row = None
    for row in market.get("rows") or []:
        market_row = row
        break
    if market_row:
        mc = _field(market_row, "market_cap")
        ev_val = _field(market_row, "enterprise_value")
        if mc:
            why.append(f"Market Capitalization ({market_row.get('period')}): ${mc}mm (USD, Capital IQ export).")
        if ev_val:
            why.append(f"Enterprise Value ({market_row.get('period')}): ${ev_val}mm (USD, Capital IQ export).")

    fin_row = None
    for row in financials.get("rows") or []:
        fin_row = row
        break
    if fin_row:
        revenue = _field(fin_row, "revenue")
        ebitda = _field(fin_row, "ebitda")
        if revenue:
            why.append(f"Total Revenue ({fin_row.get('period')}): ${revenue}mm (USD, LTM).")
        if ebitda:
            why.append(f"EBITDA ({fin_row.get('period')}): ${ebitda}mm (USD, LTM).")

    comp_row = competitors.get("row") or {}
    peer_cell = comp_row.get("peer")
    peer_val = _field(comp_row, "peer") if isinstance(peer_cell, dict) else None
    if peer_val:
        names = [p.strip().split(" (")[0] for p in str(peer_val).split(";") if p.strip()][:5]
        if names:
            why.append(f"Named competitors: {', '.join(names)}.")

    ev = _evidence_entry("business_model", "description", biz_row.get("description") or biz_row.get("description_short"))
    if ev:
        evidence.append(ev)
    if not evidence:
        evidence.append({"source": "institutional_knowledge_tables", "title": f"company_master:{ticker}"})

    summary = " ".join(p for p in parts if p) or f"{company_name} is a {company_type or 'company'} in the {sector or 'unclassified'} sector."

    return {
        "summary": summary.strip(),
        "why": why or [summary.strip()],
        "evidence": evidence,
        "engine": "institutional_knowledge_tables",
        "key": ticker,
        "company_name": company_name,
    }


def route(question: str) -> Optional[dict[str, Any]]:
    """Single public entry point, mirroring app/ui/financial_router.py's
    contract: returns None when no IKT-covered company is recognized."""

    ticker = detect_ikt_company(question)
    if not ticker:
        return None
    try:
        return answer_company_profile(ticker, question)
    except Exception:
        return None
