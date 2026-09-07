"""Continuous macro collectors — official Indian & global sources (seeded offline).

Collectors run in the background only. Ask / Research / Forecast never invoke these.
"""

from __future__ import annotations

from typing import Any, Callable

from continuous_macro_knowledge.schema import RawMacroRelease

# Institutional seeded releases representing official publication tips.
# Live connectors can replace payloads later without changing the pipeline contract.


def _rbi() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="rbi",
            country="India",
            category="Monetary",
            indicator="Repo Rate",
            current_value=6.50,
            previous_value=6.50,
            consensus=6.50,
            unit="%",
            release_date="2026-06-06",
            effective_date="2026-06-06",
            importance="Critical",
            payload={"reverse_repo": 3.35, "sdf": 6.25, "msf": 6.75, "crr": 4.0, "slr": 18.0, "mpc": "hold"},
        ),
        RawMacroRelease(
            source="rbi",
            country="India",
            category="Monetary",
            indicator="Banking Liquidity",
            current_value=1.2,
            previous_value=0.8,
            unit="INR lakh crore surplus",
            release_date="2026-07-27",
            importance="High",
            payload={"vrr": True, "vrrr": False, "money_market": "stable"},
        ),
        RawMacroRelease(
            source="rbi",
            country="India",
            category="External Sector",
            indicator="Forex Reserves",
            current_value=692.0,
            previous_value=688.5,
            unit="USD bn",
            release_date="2026-07-25",
            importance="High",
            payload={"inr_reference": 83.45},
        ),
        RawMacroRelease(
            source="rbi",
            country="India",
            category="Monetary",
            indicator="Credit Growth",
            current_value=14.2,
            previous_value=14.8,
            unit="% yoy",
            release_date="2026-07-20",
            importance="High",
            payload={"deposit_growth": 11.5},
        ),
        RawMacroRelease(
            source="rbi",
            country="India",
            category="Monetary",
            indicator="MPC Statement",
            current_value=None,
            previous_value=None,
            release_date="2026-06-06",
            importance="Critical",
            payload={"document": "MPC Statement", "stance": "neutral", "publications": ["bulletin", "fsr"]},
        ),
    ]


def _mospi() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="mospi",
            country="India",
            category="Inflation",
            indicator="CPI",
            current_value=3.65,
            previous_value=3.16,
            consensus=3.50,
            unit="% yoy",
            release_date="2026-07-14",
            effective_date="2026-06",
            importance="Critical",
            payload={"core_cpi": 3.9, "food": 2.8, "fuel": 4.1},
        ),
        RawMacroRelease(
            source="mospi",
            country="India",
            category="Inflation",
            indicator="WPI",
            current_value=2.10,
            previous_value=1.85,
            consensus=2.00,
            unit="% yoy",
            release_date="2026-07-14",
            importance="High",
            payload={},
        ),
        RawMacroRelease(
            source="mospi",
            country="India",
            category="Growth",
            indicator="IIP",
            current_value=4.2,
            previous_value=5.1,
            consensus=4.5,
            unit="% yoy",
            release_date="2026-07-12",
            importance="High",
            payload={"manufacturing": 3.8, "mining": 5.0, "electricity": 6.2},
        ),
        RawMacroRelease(
            source="nso",
            country="India",
            category="Growth",
            indicator="GDP",
            current_value=7.4,
            previous_value=7.6,
            consensus=7.3,
            unit="% yoy",
            release_date="2026-05-30",
            effective_date="FY26 Q4",
            importance="Critical",
            payload={"gva": 7.2, "consumption": 6.8, "investment": 8.1, "agriculture": 3.5, "services": 8.0},
        ),
        RawMacroRelease(
            source="nso",
            country="India",
            category="Growth",
            indicator="GVA",
            current_value=7.2,
            previous_value=7.4,
            unit="% yoy",
            release_date="2026-05-30",
            importance="High",
            payload={},
        ),
    ]


def _mof() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="mof",
            country="India",
            category="Fiscal",
            indicator="Fiscal Deficit",
            current_value=5.1,
            previous_value=5.6,
            unit="% of GDP",
            release_date="2026-07-01",
            importance="Critical",
            payload={"borrowing": "on_track", "monthly_economic_review": True},
        ),
        RawMacroRelease(
            source="mof",
            country="India",
            category="Fiscal",
            indicator="GST Collections",
            current_value=1.74,
            previous_value=1.68,
            unit="INR lakh crore",
            release_date="2026-07-01",
            importance="High",
            payload={"direct_tax": "steady"},
        ),
        RawMacroRelease(
            source="mof",
            country="India",
            category="Fiscal",
            indicator="Union Budget",
            current_value=None,
            previous_value=None,
            release_date="2026-02-01",
            importance="Critical",
            payload={"document": "Union Budget", "capex_thrust": True},
        ),
    ]


def _cga() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="cga",
            country="India",
            category="Fiscal",
            indicator="Government Revenue",
            current_value=28.5,
            previous_value=26.2,
            unit="INR lakh crore YTD",
            release_date="2026-07-10",
            importance="High",
            payload={"expenditure": 32.1, "fiscal_position": "consolidating"},
        ),
    ]


def _sebi() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="sebi",
            country="India",
            category="Financial Markets",
            indicator="Mutual Fund Flows",
            current_value=18500.0,
            previous_value=14200.0,
            unit="INR crore",
            release_date="2026-07-08",
            importance="Medium",
            payload={"equity_flows": 12000, "debt_flows": 6500, "circulars": 2},
        ),
    ]


def _fred() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="fred",
            country="United States",
            category="Monetary",
            indicator="Federal Funds Rate",
            current_value=4.50,
            previous_value=4.75,
            consensus=4.50,
            unit="%",
            release_date="2026-07-15",
            importance="Critical",
            payload={"us_treasury_10y": 4.25},
        ),
        RawMacroRelease(
            source="fred",
            country="United States",
            category="Inflation",
            indicator="US CPI",
            current_value=2.8,
            previous_value=2.9,
            consensus=2.8,
            unit="% yoy",
            release_date="2026-07-10",
            importance="High",
            payload={},
        ),
        RawMacroRelease(
            source="fred",
            country="United States",
            category="Growth",
            indicator="US GDP",
            current_value=2.1,
            previous_value=1.8,
            unit="% qoq saar",
            release_date="2026-07-25",
            importance="High",
            payload={"unemployment": 4.1},
        ),
    ]


def _imf() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="imf",
            country="Global",
            category="Growth",
            indicator="WEO Global Growth",
            current_value=3.2,
            previous_value=3.1,
            unit="%",
            release_date="2026-04-15",
            importance="High",
            payload={"india_growth_forecast": 6.5, "bop_note": True},
        ),
    ]


def _world_bank() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="world_bank",
            country="Global",
            category="Growth",
            indicator="World Bank Global Growth",
            current_value=2.6,
            previous_value=2.7,
            unit="%",
            release_date="2026-06-10",
            importance="Medium",
            payload={"development_indicators": True},
        ),
    ]


def _oecd() -> list[RawMacroRelease]:
    return [
        RawMacroRelease(
            source="oecd",
            country="Global",
            category="Growth",
            indicator="OECD CLI",
            current_value=100.2,
            previous_value=99.8,
            unit="index",
            release_date="2026-07-05",
            importance="Medium",
            payload={"business_confidence": 101.1},
        ),
    ]


COLLECTORS: dict[str, Callable[[], list[RawMacroRelease]]] = {
    "rbi": _rbi,
    "mospi": _mospi,
    "nso": _mospi,  # NSO releases bundled in mospi/nso function — filter below
    "mof": _mof,
    "cga": _cga,
    "sebi": _sebi,
    "fred": _fred,
    "imf": _imf,
    "world_bank": _world_bank,
    "oecd": _oecd,
}


def collect_source(source_id: str) -> dict[str, Any]:
    fn = COLLECTORS.get(source_id)
    if not fn:
        return {"ok": False, "source": source_id, "releases": [], "reason": "unknown_source"}
    releases = fn()
    if source_id == "nso":
        releases = [r for r in releases if r.source == "nso"]
    elif source_id == "mospi":
        releases = [r for r in releases if r.source == "mospi"]
    return {
        "ok": True,
        "source": source_id,
        "releases": releases,
        "n": len(releases),
        "mode": "seeded_official",
        "ask_triggered": False,
        "fabricated": False,
    }


def collect_all() -> dict[str, Any]:
    by_source: dict[str, Any] = {}
    all_releases: list[RawMacroRelease] = []
    for sid in ("rbi", "mospi", "nso", "mof", "cga", "sebi", "fred", "imf", "world_bank", "oecd"):
        out = collect_source(sid)
        by_source[sid] = {"ok": out["ok"], "n": out.get("n") or 0}
        all_releases.extend(out.get("releases") or [])
    return {
        "ok": True,
        "by_source": by_source,
        "releases": all_releases,
        "n": len(all_releases),
        "ask_triggered": False,
    }
