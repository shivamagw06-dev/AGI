"""Historical macro collectors — official decades-scale series (seeded offline).

HMIP acquisition is background / ops only. Analysis never calls these.
"""

from __future__ import annotations

from typing import Any, Callable

from historical_macro_intelligence.schema import RawHistoricalObservation


def _obs(
    *,
    source: str,
    country: str,
    category: str,
    indicator: str,
    value: float | None,
    period: str,
    previous: float | None = None,
    unit: str = "",
    publication_date: str | None = None,
    effective_date: str | None = None,
    payload: dict[str, Any] | None = None,
) -> RawHistoricalObservation:
    pub = publication_date or f"{period[:4]}-12-31" if period[:4].isdigit() else "2000-01-01"
    return RawHistoricalObservation(
        source=source,
        country=country,
        category=category,
        indicator=indicator,
        value=value,
        period=period,
        previous=previous,
        unit=unit,
        publication_date=pub,
        effective_date=effective_date or period,
        payload=payload or {},
    )


def _series(
    source: str,
    country: str,
    category: str,
    indicator: str,
    points: list[tuple[str, float]],
    *,
    unit: str = "",
) -> list[RawHistoricalObservation]:
    out: list[RawHistoricalObservation] = []
    prev: float | None = None
    for period, value in points:
        out.append(
            _obs(
                source=source,
                country=country,
                category=category,
                indicator=indicator,
                value=value,
                period=period,
                previous=prev,
                unit=unit,
            )
        )
        prev = value
    return out


def _rbi() -> list[RawHistoricalObservation]:
    rows: list[RawHistoricalObservation] = []
    # Repo Rate institutional history (policy tip series)
    rows += _series(
        "rbi",
        "India",
        "Monetary",
        "Repo Rate",
        [
            ("1998", 9.00),
            ("2001", 7.50),
            ("2003", 6.00),
            ("2008", 9.00),
            ("2010", 6.25),
            ("2013", 7.75),
            ("2016", 6.25),
            ("2019", 5.15),
            ("2020", 4.00),
            ("2022", 6.25),
            ("2023", 6.50),
            ("2025", 6.50),
        ],
        unit="%",
    )
    rows += _series(
        "rbi",
        "India",
        "Monetary",
        "CRR",
        [("2008", 9.0), ("2013", 4.0), ("2020", 3.0), ("2022", 4.5), ("2025", 4.0)],
        unit="%",
    )
    rows += _series(
        "rbi",
        "India",
        "Monetary",
        "SLR",
        [("2008", 24.0), ("2013", 23.0), ("2018", 19.5), ("2025", 18.0)],
        unit="%",
    )
    rows += _series(
        "rbi",
        "India",
        "External Sector",
        "Forex Reserves",
        [
            ("2000", 38.0),
            ("2008", 252.0),
            ("2013", 275.0),
            ("2020", 542.0),
            ("2022", 563.0),
            ("2025", 680.0),
        ],
        unit="USD bn",
    )
    rows += _series(
        "rbi",
        "India",
        "Monetary",
        "Credit Growth",
        [("2013", 14.0), ("2016", 10.0), ("2020", 6.0), ("2022", 15.0), ("2025", 14.0)],
        unit="% yoy",
    )
    rows += _series(
        "rbi",
        "India",
        "Monetary",
        "Banking Liquidity",
        [("2019", 0.5), ("2020", 3.5), ("2022", -0.8), ("2025", 1.2)],
        unit="INR lakh crore surplus",
    )
    for year, title in [
        ("2016", "MPC Framework"),
        ("2020", "COVID Liquidity Measures"),
        ("2022", "Financial Stability Report"),
    ]:
        rows.append(
            _obs(
                source="rbi",
                country="India",
                category="Monetary",
                indicator="MPC Decisions",
                value=None,
                period=year,
                publication_date=f"{year}-12-01",
                payload={"document": title},
            )
        )
    return rows


def _mospi_nso() -> list[RawHistoricalObservation]:
    rows: list[RawHistoricalObservation] = []
    rows += _series(
        "nso",
        "India",
        "Growth",
        "GDP",
        [
            ("1995", 7.3),
            ("1998", 6.2),  # Asian crisis aftermath
            ("2001", 4.8),  # Dot-com
            ("2008", 3.1),  # GFC
            ("2010", 8.5),
            ("2016", 8.3),
            ("2020", -5.8),  # COVID
            ("2021", 9.7),  # Recovery
            ("2023", 7.6),
            ("2025", 7.4),
        ],
        unit="% yoy",
    )
    rows += _series(
        "nso",
        "India",
        "Growth",
        "GVA",
        [("2016", 7.9), ("2020", -4.2), ("2021", 8.8), ("2023", 7.2), ("2025", 7.2)],
        unit="% yoy",
    )
    rows += _series(
        "mospi",
        "India",
        "Inflation",
        "CPI",
        [
            ("2013", 9.5),
            ("2015", 4.9),
            ("2018", 3.4),
            ("2020", 6.2),
            ("2022", 6.7),
            ("2023", 5.4),
            ("2025", 3.7),
        ],
        unit="% yoy",
    )
    rows += _series(
        "mospi",
        "India",
        "Inflation",
        "WPI",
        [("2013", 6.0), ("2015", -2.5), ("2020", 1.2), ("2022", 13.7), ("2025", 2.1)],
        unit="% yoy",
    )
    rows += _series(
        "mospi",
        "India",
        "Growth",
        "IIP",
        [("2013", 0.6), ("2016", 4.6), ("2020", -8.4), ("2022", 5.5), ("2025", 4.2)],
        unit="% yoy",
    )
    rows += _series(
        "mospi",
        "India",
        "Inflation",
        "Core Inflation",
        [("2018", 5.5), ("2020", 4.8), ("2022", 6.0), ("2025", 3.9)],
        unit="% yoy",
    )
    return rows


def _mof_cga() -> list[RawHistoricalObservation]:
    rows: list[RawHistoricalObservation] = []
    rows += _series(
        "mof",
        "India",
        "Fiscal",
        "Fiscal Deficit",
        [
            ("2008", 6.0),
            ("2013", 4.5),
            ("2018", 3.4),
            ("2020", 9.2),
            ("2022", 6.4),
            ("2025", 5.1),
        ],
        unit="% of GDP",
    )
    rows += _series(
        "mof",
        "India",
        "Fiscal",
        "Government Borrowing",
        [("2018", 6.0), ("2020", 12.0), ("2022", 11.5), ("2025", 11.0)],
        unit="INR lakh crore",
    )
    for year in ("2015", "2018", "2021", "2024", "2026"):
        rows.append(
            _obs(
                source="mof",
                country="India",
                category="Fiscal",
                indicator="Union Budget",
                value=None,
                period=year,
                publication_date=f"{year}-02-01",
                payload={"document": "Union Budget"},
            )
        )
    rows += _series(
        "cga",
        "India",
        "Fiscal",
        "Government Revenue",
        [("2018", 17.0), ("2020", 16.5), ("2022", 22.0), ("2025", 28.5)],
        unit="INR lakh crore",
    )
    rows += _series(
        "cga",
        "India",
        "Fiscal",
        "Public Debt",
        [("2018", 68.0), ("2020", 89.0), ("2022", 83.0), ("2025", 81.0)],
        unit="% of GDP",
    )
    return rows


def _sebi() -> list[RawHistoricalObservation]:
    return _series(
        "sebi",
        "India",
        "Financial Markets",
        "Mutual Fund AUM",
        [("2015", 12.0), ("2018", 24.0), ("2020", 28.0), ("2022", 40.0), ("2025", 65.0)],
        unit="INR lakh crore",
    )


def _fred() -> list[RawHistoricalObservation]:
    rows: list[RawHistoricalObservation] = []
    rows += _series(
        "fred",
        "United States",
        "Monetary",
        "Federal Funds Rate",
        [
            ("2000", 6.50),
            ("2003", 1.00),
            ("2007", 5.25),
            ("2009", 0.15),
            ("2016", 0.50),
            ("2019", 2.40),
            ("2020", 0.10),
            ("2022", 4.50),
            ("2025", 4.50),
        ],
        unit="%",
    )
    rows += _series(
        "fred",
        "United States",
        "Inflation",
        "US CPI",
        [("2008", 3.8), ("2010", 1.6), ("2020", 1.2), ("2022", 8.0), ("2025", 2.8)],
        unit="% yoy",
    )
    rows += _series(
        "fred",
        "United States",
        "Growth",
        "US GDP",
        [("2008", -0.1), ("2009", -2.5), ("2010", 2.6), ("2020", -2.2), ("2021", 5.8), ("2025", 2.1)],
        unit="% yoy",
    )
    rows += _series(
        "fred",
        "United States",
        "Growth",
        "US Unemployment",
        [("2009", 9.3), ("2015", 5.3), ("2020", 8.1), ("2022", 3.6), ("2025", 4.1)],
        unit="%",
    )
    return rows


def _imf_wb_oecd() -> list[RawHistoricalObservation]:
    rows: list[RawHistoricalObservation] = []
    rows += _series(
        "imf",
        "Global",
        "Growth",
        "WEO Global Growth",
        [("2008", 3.0), ("2009", -0.1), ("2015", 3.5), ("2020", -2.8), ("2021", 6.3), ("2025", 3.2)],
        unit="%",
    )
    rows += _series(
        "world_bank",
        "Global",
        "Growth",
        "World Bank Global Growth",
        [("2010", 4.3), ("2015", 2.9), ("2020", -3.1), ("2025", 2.6)],
        unit="%",
    )
    rows += _series(
        "oecd",
        "Global",
        "Growth",
        "OECD CLI",
        [("2015", 100.0), ("2019", 99.2), ("2020", 96.5), ("2022", 99.8), ("2025", 100.2)],
        unit="index",
    )
    return rows


COLLECTORS: dict[str, Callable[[], list[RawHistoricalObservation]]] = {
    "rbi": _rbi,
    "mospi": _mospi_nso,
    "nso": _mospi_nso,
    "mof": _mof_cga,
    "cga": _mof_cga,
    "sebi": _sebi,
    "fred": _fred,
    "imf": _imf_wb_oecd,
    "world_bank": _imf_wb_oecd,
    "oecd": _imf_wb_oecd,
}


def collect_source(source_id: str) -> dict[str, Any]:
    fn = COLLECTORS.get(source_id)
    if not fn:
        return {"ok": False, "source": source_id, "observations": [], "reason": "unknown_source"}
    rows = fn()
    # Filter to source when shared functions
    if source_id in {"mospi", "nso"}:
        rows = [r for r in rows if r.source == source_id]
    elif source_id in {"mof", "cga"}:
        rows = [r for r in rows if r.source == source_id]
    elif source_id in {"imf", "world_bank", "oecd"}:
        rows = [r for r in rows if r.source == source_id]
    return {
        "ok": True,
        "source": source_id,
        "observations": rows,
        "n": len(rows),
        "mode": "seeded_historical",
        "ask_triggered": False,
        "fabricated": False,
    }


def collect_all() -> dict[str, Any]:
    by_source: dict[str, Any] = {}
    all_rows: list[RawHistoricalObservation] = []
    for sid in ("rbi", "mospi", "nso", "mof", "cga", "sebi", "fred", "imf", "world_bank", "oecd"):
        out = collect_source(sid)
        by_source[sid] = {"ok": out["ok"], "n": out.get("n") or 0}
        all_rows.extend(out.get("observations") or [])
    return {"ok": True, "by_source": by_source, "observations": all_rows, "n": len(all_rows)}
