"""Deterministic gates applied after Ask AGI synthesis."""

from __future__ import annotations

import re
from typing import Any

_FULL_COMPANY_ANALYSIS_RE = re.compile(
    r"^\s*(?:please\s+)?(?:analyse|analyze|review|evaluate|assess)\b",
    re.I,
)

CONGLOMERATE_FRAMEWORK_GUARDS: dict[str, tuple[re.Pattern[str], ...]] = {
    "RELIANCE": (
        re.compile(r"\bindustry\s+dna\s*:\s*metals?\b", re.I),
        re.compile(r"\bore\s+linkages?\b", re.I),
        re.compile(r"\bindustry\s+dna\s*\([^)]*metals?[^)]*\)", re.I),
    ),
}


def requires_full_company_analysis(question: str, ticker: str | None) -> bool:
    """Resolved broad company analyses must run the complete research desk."""
    return bool(ticker and _FULL_COMPANY_ANALYSIS_RE.search(str(question or "")))


def dedupe_research_text(value: Any) -> str:
    """Remove repeated synthesis fragments without inventing replacement text."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    chunks = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    kept: list[str] = []
    for chunk in chunks:
        clean = chunk.strip()
        fingerprint = re.sub(r"[^a-z0-9]+", " ", clean.lower()).strip()
        key = fingerprint[:180]
        duplicate = bool(
            key
            and any(
                key == prior
                or (min(len(key), len(prior)) >= 40 and (key.startswith(prior) or prior.startswith(key)))
                for prior in seen
            )
        )
        if not clean or duplicate:
            continue
        seen.add(key)
        kept.append(clean)
    return " ".join(kept)


def filter_company_framework_text(values: list[Any], ticker: str | None) -> list[Any]:
    guards = CONGLOMERATE_FRAMEWORK_GUARDS.get(str(ticker or "").upper(), ())
    if not guards:
        return values
    return [
        value for value in values
        if not any(pattern.search(str(value or "")) for pattern in guards)
    ]


def has_numeric_valuation_evidence(value: Any) -> bool:
    """Require an actual price/multiple/value—not a score or adjective."""
    valuation_keys = {
        "share_price", "current_price", "enterprise_value", "market_cap",
        "ev_ebitda", "current_pe", "forward_pe", "pb", "peg",
        "fair_value", "target_price", "intrinsic_value", "sotp",
        "upside_pct", "downside_pct", "margin_of_safety",
    }
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        if str(key).lower() in valuation_keys and isinstance(item, (int, float)):
            return True
        if isinstance(item, dict) and has_numeric_valuation_evidence(item):
            return True
    return False


def _keys_recursive(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key).lower())
            keys.update(_keys_recursive(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_keys_recursive(item))
    return keys


def has_supported_valuation_evidence(value: Any) -> bool:
    """A valuation label requires numeric evidence, provenance and an as-of date."""
    keys = _keys_recursive(value)
    return bool(
        has_numeric_valuation_evidence(value)
        and keys.intersection({"source", "sources", "provenance", "source_url"})
        and keys.intersection({"as_of", "as_of_date", "date", "updated_at", "price_date"})
    )


def has_supported_financial_evidence(value: Any) -> bool:
    """Financial figures need metric, period, units/currency and provenance."""
    if not isinstance(value, dict):
        return False
    keys = _keys_recursive(value)
    financial_metrics = {
        "revenue", "sales", "ebitda", "ebit", "pat", "net_income",
        "free_cash_flow", "fcf", "net_debt", "operating_cash_flow",
        "ebitda_margin", "operating_margin",
    }
    has_numeric_metric = False

    def visit(item: Any) -> None:
        nonlocal has_numeric_metric
        if isinstance(item, dict):
            for key, nested in item.items():
                if str(key).lower() in financial_metrics and isinstance(nested, (int, float)):
                    has_numeric_metric = True
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return bool(
        has_numeric_metric
        and keys.intersection({"period", "fiscal_period", "fiscal_year", "as_of", "date"})
        and keys.intersection({"unit", "units", "currency", "currency_code"})
        and keys.intersection({"source", "sources", "provenance", "source_url"})
    )
