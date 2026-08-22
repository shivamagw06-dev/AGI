"""Canonical aliases for AGI's core covered Indian company universe.

These are identity bindings, not financial facts. Ambiguous group stems such as
``HDFC`` and ``Tata`` are intentionally absent.
"""

from __future__ import annotations

import re
from typing import Iterator


CORE_COMPANY_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AXISBANK", ("axis bank", "axisbank")),
    ("HDFCBANK", ("hdfc bank", "hdfcbank")),
    ("ICICIBANK", ("icici bank", "icicibank")),
    ("SBIN", ("state bank of india", "sbi", "sbin")),
    ("INFY", ("infosys", "infy")),
    ("TCS", ("tata consultancy services", "tata consultancy", "tcs")),
    ("HCLTECH", ("hcl technologies", "hcltech", "hcl tech")),
    ("WIPRO", ("wipro",)),
    ("RELIANCE", ("reliance industries", "reliance", "ril")),
    ("ONGC", ("oil and natural gas corporation", "ongc")),
    ("BPCL", ("bharat petroleum corporation", "bharat petroleum", "bpcl")),
    ("IOC", ("indian oil corporation", "indian oil", "ioc")),
    ("ULTRACEMCO", ("ultratech cement", "ultracemco", "ultratech")),
    ("JSWSTEEL", ("jsw steel", "jswsteel")),
    ("TATASTEEL", ("tata steel", "tatasteel")),
    ("ASIANPAINT", ("asian paints", "asianpaint")),
    ("SUNPHARMA", ("sun pharmaceutical industries", "sun pharmaceuticals", "sunpharma")),
    ("APOLLOHOSP", ("apollo hospitals enterprise", "apollo hospitals", "apollohosp")),
    ("TITAN", ("titan company", "titan")),
    ("DMART", ("avenue supermarts", "d-mart", "dmart")),
    ("TRENT", ("trent limited", "trent")),
    ("ITC", ("itc limited", "itc")),
    ("NESTLEIND", ("nestle india", "nestleind")),
    ("LT", ("larsen and toubro", "larsen & toubro", "l&t")),
    ("NTPC", ("ntpc limited", "ntpc")),
    ("POWERGRID", ("power grid corporation of india", "power grid", "powergrid")),
    ("BHARTIARTL", ("bharti airtel", "bhartiartl", "airtel")),
    ("DLF", ("dlf limited", "dlf")),
    ("MARUTI", ("maruti suzuki india", "maruti suzuki", "maruti")),
    ("INDIGO", ("interglobe aviation", "indigo")),
)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", re.I)


CORE_ALIAS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (pattern, ticker)
    for ticker, aliases in CORE_COMPANY_ALIASES
    for pattern in (_alias_pattern(alias) for alias in sorted(aliases, key=len, reverse=True))
)


def iter_alias_tickers(question: str) -> Iterator[str]:
    """Yield matched tickers in textual order, longest match winning ties."""
    matches: list[tuple[int, int, str]] = []
    for pattern, ticker in CORE_ALIAS_PATTERNS:
        hit = pattern.search(question or "")
        if hit:
            matches.append((hit.start(), -(hit.end() - hit.start()), ticker))
    seen: set[str] = set()
    for _, _, ticker in sorted(matches):
        if ticker not in seen:
            seen.add(ticker)
            yield ticker


def core_alias_ticker(question: str) -> str | None:
    return next(iter_alias_tickers(question), None)


def exact_core_alias_ticker(mention: str) -> str | None:
    """Resolve only when the entire mention is one curated alias.

    Substring matching is useful for a full question but unsafe as an identity
    fallback: ``Reliance Power`` must not become Reliance Industries merely
    because both contain ``Reliance``.
    """
    key = re.sub(r"[^a-z0-9&-]+", " ", str(mention or "").lower()).strip()
    matches = {
        ticker
        for ticker, aliases in CORE_COMPANY_ALIASES
        if key in {
            re.sub(r"[^a-z0-9&-]+", " ", alias.lower()).strip()
            for alias in aliases
        }
    }
    return next(iter(matches)) if len(matches) == 1 else None
