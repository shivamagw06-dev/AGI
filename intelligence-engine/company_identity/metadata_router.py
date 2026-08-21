"""Company Metadata Router — direct lookups, ahead of the reasoning stack.

"Axis Bank primary sector" is a metadata lookup, not a research question. It
must never reach Entity Intelligence, KUL, fusion or the composer: the answer
is a stored Capital IQ field.

    Question → Metadata Router → Company Identity Service → Capital IQ → answer
"""

from __future__ import annotations

import re
from typing import Any, Optional

# field key → (display label, regex of question phrasings)
_FIELD_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("primary_sector", "Primary Sector", r"\b(primary\s+)?sectors?\b"),
    ("primary_industry", "Primary Industry", r"\b(primary\s+)?industry\b|\bindustries\b"),
    (
        "industry_classification",
        "Industry Classification",
        r"\bindustry\s+classificat\w*\b|\bgics\b",
    ),
    ("ticker", "Ticker", r"\btickers?\b|\bsymbols?\b|\bscrip\s*code\b"),
    ("exchange", "Exchange", r"\bexchanges?\b|\blisted\s+(?:on|where)\b|\blisting\b"),
    ("website", "Website", r"\bwebsites?\b|\bweb\s*site\b|\burls?\b|\bdomain\b|\bhomepage\b"),
    ("currency", "Currency", r"\bcurrenc(?:y|ies)\b|\breporting\s+currency\b"),
    ("country", "Country", r"\bcountry\b|\bdomicile\b|\bbased\s+in\b|\bnationality\b"),
    ("parent", "Parent", r"\bparent(?:\s+company)?\b|\bultimate\s+(?:corporate\s+)?parent\b|\bowner\b"),
    ("company_type", "Company Type", r"\bcompany\s+type\b|\bentity\s+type\b"),
    ("business_type", "Business Type", r"\bbusiness\s+type\b|\barchetype\b"),
    ("trading_status", "Trading Status", r"\b(trading\s+)?status\b|\bactive(?:ly)?\s+traded\b"),
    ("products", "Products", r"\bproducts?\b(?!\s+company)"),
    ("competitors", "Competitors", r"\bcompetitors?\b|\bpeers?\b|\brivals?\b"),
    ("industry_dna", "Industry DNA", r"\bindustry\s+dna\b"),
    ("headquarters", "Headquarters", r"\bheadquarters?\b|\bhead\s+office\b|\bhq\b"),
    ("employees", "Employees", r"\bemployees?\b|\bheadcount\b|\bstaff\s+strength\b"),
    ("founded", "Founded", r"\bfounded\b|\bincorporat\w+\b|\bestablished\b|\byear\s+of\s+founding\b"),
    ("isin", "ISIN", r"\bisin\b"),
    (
        "market_cap",
        "Market Cap",
        r"\bmarket\s*cap(?:itali[sz]ation)?\b|\bmkt\s*cap\b",
    ),
    (
        "enterprise_value",
        "Enterprise Value",
        r"\benterprise\s+value\b|\bev\b(?!\s*/)",
    ),
)

_COMPILED = tuple((key, label, re.compile(rx, re.I)) for key, label, rx in _FIELD_PATTERNS)

# Phrasings that look like metadata words but are analytical questions —
# these belong to the reasoning stack, not a field lookup.
_ANALYTICAL_RE = re.compile(
    r"\b(why|how does|how do|compar\w+|versus|\bvs\b|explain|thesis|outlook|forecast|"
    r"should i|risk|risks|moat|valuation|valued|target price|consensus|upside|"
    r"expensive|cheap|overvalued|undervalued|discount|premium|multiple|multiples|"
    r"screen|scanner|re-?rating|de-?rating|trading at|trades at|"
    r"drivers?|economics|business model|invest|attractive|opportunit\w+|"
    r"strategy|competitive advantage|deep dive|analys|assess|evaluate)\b",
    re.I,
)

# Fields the canonical registry does not carry from the Capital IQ export.
# ISIN / market_cap / EV are answered when present on CompanyIdentity.
_UNAVAILABLE_FIELDS = {"headquarters", "employees", "founded"}

MAX_METADATA_WORDS = 12


def detect_fields(question: str) -> list[tuple[str, str]]:
    """Return [(field_key, label)] the question is asking for."""
    q = str(question or "")
    if not q.strip():
        return []
    hits: list[tuple[str, str]] = []
    for key, label, pattern in _COMPILED:
        if pattern.search(q):
            hits.append((key, label))
    # "primary industry" also matches the generic sector pattern via "industry
    # classification"; keep the most specific single field when both fire.
    if len(hits) > 1:
        keys = {k for k, _ in hits}
        if "industry_classification" in keys and "primary_industry" in keys:
            hits = [h for h in hits if h[0] != "primary_industry"]
        if "business_type" in keys and "company_type" in keys:
            hits = [h for h in hits if h[0] != "company_type"]
    return hits


def is_metadata_question(question: str) -> bool:
    """Short, factual, field-shaped question about one company."""
    q = str(question or "").strip()
    if not q or len(q.split()) > MAX_METADATA_WORDS:
        return False
    if _ANALYTICAL_RE.search(q):
        return False
    return bool(detect_fields(q))


_FIELD_WORDS_RE = re.compile(
    r"\b(primary|sector|sectors|industry|industries|classification|classifications|gics|"
    r"ticker|tickers|symbol|symbols|scrip|code|exchange|exchanges|listed|listing|"
    r"website|web|site|url|urls|domain|homepage|currency|currencies|reporting|"
    r"country|domicile|nationality|parent|ultimate|corporate|owner|company|entity|type|"
    r"business|archetype|trading|status|products|product|competitors|competitor|peers|"
    r"peer|rivals|dna|headquarters|head|office|hq|employees|headcount|staff|strength|"
    r"founded|incorporated|incorporation|established|year|isin|of|the|for|what|is|whats|"
    r"which|show|me|tell|give|please|and|in|on|at|"
    r"market|cap|capitalization|capitalisation|mkt|enterprise|value|ev)\b",
    re.I,
)


def _company_stem(question: str) -> str:
    """Question minus metadata field vocabulary — what remains names the company."""
    stem = _FIELD_WORDS_RE.sub(" ", str(question or ""))
    stem = re.sub(r"[^\w&.\- ]+", " ", stem)
    return re.sub(r"\s+", " ", stem).strip()


def _resolve_short_name(stem: str) -> tuple[Optional[str], str]:
    """Bind a short company reference ("Titan", "Reliance") when unambiguous."""
    from company_identity.service import _name_index, _normalize_name, prefix_is_unambiguous

    key = _normalize_name(stem)
    if not key or len(key) < 3:
        return None, "mention_too_short"
    index = _name_index()
    exact = index.get(key)
    if exact:
        return exact, "exact_name"
    prefix = f"{key} "
    matched = {name: t for name, t in index.items() if name.startswith(prefix)}
    if len(set(matched.values())) == 1:
        name = next(iter(matched))
        if not prefix_is_unambiguous(key, name, index):
            return None, "abbreviation_collision"
        return matched[name], "unique_prefix_stem"
    return None, "ambiguous_mention" if matched else "no_capiq_match"


def _resolve_ticker_mention(stem: str) -> tuple[Optional[str], str]:
    """Bind a ticker written as a ticker — ONGC, BPCL, HCLTech.

    Requires the mention to look like a symbol (single token, multiple capital
    letters), so a name-cased word such as "Apollo" can never pick up the
    unrelated APOLLO listing.
    """
    token = str(stem or "").strip()
    if not token or " " in token or len(token) < 2:
        return None, "not_ticker_shaped"
    if sum(1 for ch in token if ch.isupper()) < 2:
        return None, "not_ticker_shaped"
    from company_identity.service import identity_for

    identity = identity_for(token.upper())
    return (identity.ticker, "ticker_mention") if identity.resolved else (None, "unknown_ticker")


def _resolve_curated_alias(stem: str) -> tuple[Optional[str], str]:
    """Market shorthand ("Reliance", "TCS", "DMart") via Entity Intelligence.

    Only a verified, planner-allowed entity is accepted, so ambiguous stems
    still fall through to clarification and private names still refuse.
    """
    from company_identity.core_aliases import exact_core_alias_ticker
    from entity_intelligence.registry import ambiguity_candidates

    if ambiguity_candidates(stem):
        return None, "ambiguous_curated_alias"
    ticker = exact_core_alias_ticker(stem)
    if not ticker:
        return None, "not_a_curated_alias"
    from company_identity.service import identity_for

    return (str(ticker).upper(), "curated_alias") if identity_for(ticker).resolved else (None, "not_in_registry")


def _value_for(identity: Any, field: str) -> Optional[Any]:
    if field == "industry_dna":
        return identity.industry_dna
    if field == "business_type":
        return identity.business_type
    return getattr(identity, field, None)


def _fields_outside_company_name(question: str, company_name: str) -> list[tuple[str, str]]:
    """Detect field words only in the part of the question that is not the name.

    "Reliance Industries" and "Sun Pharmaceutical Industries" contain the word
    "Industries"; without this, an annual-report question about Reliance was
    treated as a request for its primary industry.
    """
    residue = str(question or "")
    for token in str(company_name or "").split():
        cleaned = re.sub(r"[^\w&]", "", token)
        if len(cleaned) < 3:
            continue
        residue = re.sub(rf"\b{re.escape(cleaned)}\w*\b", " ", residue, flags=re.I)
    return detect_fields(residue)


def route(question: str) -> Optional[dict[str, Any]]:
    """Answer a company metadata question directly, or return None.

    None means "not a metadata question" — the caller continues to the normal
    pipeline. A dict is a complete answer that must bypass KUL entirely.
    """
    q = str(question or "").strip()
    if not is_metadata_question(q):
        return None

    from company_identity.service import resolve_company_mention, identity_for

    ticker, how = resolve_company_mention(q)
    if not ticker:
        # Strip the field words so only the company mention remains, then let
        # a short name like "Titan" resolve against the canonical registry.
        stem = _company_stem(q)
        if stem:
            ticker, how = resolve_company_mention(stem)
            if not ticker:
                ticker, how = _resolve_short_name(stem)
            if not ticker:
                ticker, how = _resolve_ticker_mention(stem)
            if not ticker:
                ticker, how = _resolve_curated_alias(stem)
    if not ticker:
        # No unambiguous company → let Entity Intelligence handle it, so
        # ambiguous stems still get clarification and unknown names refusal.
        return None
    identity = identity_for(ticker)
    if not identity.resolved:
        return None

    fields = _fields_outside_company_name(q, identity.company_name)
    if not fields:
        # Every field word came from the company's own name — this is not a
        # metadata question at all.
        return None
    answered: list[dict[str, Any]] = []
    missing: list[str] = []
    for key, label in fields:
        value = _value_for(identity, key)
        if value in (None, "") or key in _UNAVAILABLE_FIELDS:
            missing.append(label)
            continue
        answered.append({"field": key, "label": label, "value": value})

    # Market-data fields with empty registry values should fall through to KUL /
    # CapIQ engines rather than short-circuit with an empty metadata answer.
    if not answered and fields and all(k in {"market_cap", "enterprise_value", "isin"} for k, _ in fields):
        return None

    if not answered and not missing:
        return None

    name = identity.company_name
    if answered:
        parts = [f"{a['label']}: {a['value']}" for a in answered]
        summary = f"{name} — " + "; ".join(parts) + "."
    else:
        summary = (
            f"{name} is covered in the Capital IQ registry, but "
            + ", ".join(missing)
            + " is not carried in the current export."
        )

    why = [f"Capital IQ registry record for {name} ({identity.ticker})."]
    for a in answered:
        why.append(f"{a['label']}: {a['value']}.")
    if missing:
        why.append("Not in the Capital IQ export: " + ", ".join(missing) + ".")
    why.append("Stored company metadata — no reasoning stack, no inference.")

    return {
        "ok": True,
        "route": "company_metadata",
        "ticker": identity.ticker,
        "company_name": name,
        "resolution": how,
        "fields": answered,
        "missing_fields": missing,
        "summary": summary,
        "why": why,
        "identity": identity.context(),
        "source": identity.source,
        "evidence": [
            {
                "source": "company_identity",
                "title": f"{identity.ticker}.capital_iq_registry",
                "layer": "company_metadata",
            }
        ],
    }
