"""Deterministic 10–20y historical fixtures for offline Historical Depth.

Institutional reference shapes — not live feeds. INFY and HDFCBANK carry
richer crisis-era detail for acceptance tests. Other Nifty names get
parametric panels so Decision Coverage depth expands without inventing APIs.
"""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.historical_depth.schema import pit_record, regime_record, timeline_event

# FY07..FY26 → 20 years
FISCAL_YEARS: tuple[str, ...] = tuple(f"FY{y:02d}" for y in range(7, 27))

# Period end / earnings availability (India FY ends Mar 31; AR typically Jul).
_FY_END = {f"FY{y:02d}": f"20{y:02d}-03-31" for y in range(7, 27)}
_FY_AVAILABLE = {f"FY{y:02d}": f"20{y:02d}-07-15" for y in range(7, 27)}


def _fy_end(fy: str) -> str:
    return _FY_END[fy]


def _fy_available(fy: str) -> str:
    return _FY_AVAILABLE[fy]


def _scale(base: float, years: int, growth: float, shocks: dict[int, float] | None = None) -> list[float]:
    out = []
    v = float(base)
    shocks = shocks or {}
    for i in range(years):
        if i in shocks:
            v = v * (1.0 + shocks[i])
        elif i > 0:
            v = v * (1.0 + growth)
        out.append(round(v, 4))
    return out


def _infy_panel() -> dict[str, list[float]]:
    """Infosys FY07–FY26 shaped around GFC / COVID / recovery."""
    n = len(FISCAL_YEARS)
    # index: 0=FY07 ... 1=FY08(GFC) ... 13=FY20(COVID) ...
    price = _scale(450, n, 0.12, {1: -0.45, 2: 0.35, 13: -0.25, 14: 0.55})
    eps = _scale(22, n, 0.10, {1: -0.15, 13: -0.08, 14: 0.18})
    bvps = _scale(80, n, 0.08, {1: 0.02})
    revenue = _scale(14000, n, 0.12, {1: 0.05, 13: 0.02, 14: 0.14})
    ebitda = _scale(4000, n, 0.11, {1: -0.05, 13: 0.05})
    ebit = _scale(3500, n, 0.11, {1: -0.08, 13: 0.04})
    ni = _scale(3200, n, 0.10, {1: -0.12, 13: -0.05, 14: 0.15})
    ocf = _scale(3500, n, 0.10, {1: -0.10})
    capex = _scale(800, n, 0.06, {13: -0.20})
    debt = _scale(0, n, 0.0)  # mostly lease later — keep small late
    debt = [0.0] * 10 + _scale(2000, n - 10, 0.08)
    cash = _scale(5000, n, 0.08, {1: -0.10, 14: 0.20})
    shares = [230.0] * 10 + [420.0] * (n - 10)  # split-like jump
    equity = _scale(18000, n, 0.08)
    gp = [round(r * 0.32, 2) for r in revenue]
    fcf = [round(o - c, 2) for o, c in zip(ocf, capex)]
    return {
        "price": price,
        "eps": eps,
        "bvps": bvps,
        "revenue": revenue,
        "gross_profit": gp,
        "ebitda": ebitda,
        "ebit": ebit,
        "net_income": ni,
        "ocf": ocf,
        "fcf": fcf,
        "capex": capex,
        "total_debt": debt,
        "cash": cash,
        "shares": shares,
        "equity": equity,
    }


def _hdfc_panel() -> dict[str, list[float]]:
    n = len(FISCAL_YEARS)
    price = _scale(200, n, 0.14, {1: -0.40, 13: -0.30, 14: 0.40})
    eps = _scale(12, n, 0.14, {1: -0.10, 13: 0.05})
    bvps = _scale(80, n, 0.12)
    revenue = _scale(20000, n, 0.14, {1: 0.08})
    ebitda = _scale(8000, n, 0.13)
    ebit = list(ebitda)
    ni = _scale(4000, n, 0.14, {1: -0.08})
    ocf = _scale(4500, n, 0.12)
    capex = _scale(400, n, 0.05)
    debt = _scale(80000, n, 0.10)
    cash = _scale(15000, n, 0.10)
    shares = [550.0] * n
    equity = _scale(40000, n, 0.12)
    gp = [round(r * 0.55, 2) for r in revenue]
    fcf = [round(o - c, 2) for o, c in zip(ocf, capex)]
    return {
        "price": price,
        "eps": eps,
        "bvps": bvps,
        "revenue": revenue,
        "gross_profit": gp,
        "ebitda": ebitda,
        "ebit": ebit,
        "net_income": ni,
        "ocf": ocf,
        "fcf": fcf,
        "capex": capex,
        "total_debt": debt,
        "cash": cash,
        "shares": shares,
        "equity": equity,
    }


def _parametric_panel(entity: str) -> dict[str, list[float]]:
    h = hashlib.md5(entity.encode()).digest()
    base_price = 100 + (h[0] % 90) * 10
    base_eps = 5 + (h[1] % 40)
    n = len(FISCAL_YEARS)
    g = 0.08 + (h[2] % 8) / 100.0
    shocks = {1: -0.25 - (h[3] % 20) / 100.0, 13: -0.15, 14: 0.25}
    price = _scale(base_price, n, g, shocks)
    eps = _scale(base_eps, n, g * 0.9, {1: -0.12, 13: -0.05, 14: 0.15})
    bvps = _scale(base_eps * 8, n, 0.08)
    revenue = _scale(5000 + h[4] * 100, n, g, {1: -0.05, 13: 0.0})
    ebitda = [round(r * 0.22, 2) for r in revenue]
    ebit = [round(r * 0.18, 2) for r in revenue]
    ni = [round(e * 0.7, 2) for e in ebit]
    ocf = [round(n_ * 1.1, 2) for n_ in ni]
    capex = [round(r * 0.04, 2) for r in revenue]
    debt = _scale(2000 + h[5] * 50, n, 0.03)
    cash = _scale(1000 + h[6] * 20, n, 0.07)
    shares = [50.0 + (h[7] % 40)] * n
    equity = _scale(8000 + h[8] * 100, n, 0.08)
    gp = [round(r * 0.35, 2) for r in revenue]
    fcf = [round(o - c, 2) for o, c in zip(ocf, capex)]
    return {
        "price": price,
        "eps": eps,
        "bvps": bvps,
        "revenue": revenue,
        "gross_profit": gp,
        "ebitda": ebitda,
        "ebit": ebit,
        "net_income": ni,
        "ocf": ocf,
        "fcf": fcf,
        "capex": capex,
        "total_debt": debt,
        "cash": cash,
        "shares": shares,
        "equity": equity,
    }


def annual_panel(entity: str) -> dict[str, list[float]]:
    e = entity.upper()
    if e == "INFY":
        return _infy_panel()
    if e == "HDFCBANK":
        return _hdfc_panel()
    return _parametric_panel(e)


def annual_records(entity: str) -> list[dict[str, Any]]:
    panel = annual_panel(entity)
    records = []
    for i, fy in enumerate(FISCAL_YEARS):
        payload = {f: float(panel[f][i]) for f in panel}
        records.append(
            pit_record(
                entity=entity,
                kind="financials_annual",
                period=fy,
                period_end=_fy_end(fy),
                available_from=_fy_available(fy),
                payload=payload,
                source="fixture",
            )
        )
    return records


def monthly_prices(entity: str) -> list[dict[str, Any]]:
    """Monthly adjusted closes from FY07 → FY26 (240 months) with crisis drawdowns."""
    e = entity.upper()
    h = hashlib.md5(e.encode()).digest()
    # Start ~2007-04
    px = 100.0 + (h[0] % 50)
    if e == "INFY":
        px = 450.0
    elif e == "HDFCBANK":
        px = 200.0
    records = []
    # Deterministic monthly returns with regime shocks
    for yi, year in enumerate(range(2007, 2027)):
        for month in range(1, 13):
            if year == 2007 and month < 4:
                continue
            if year == 2026 and month > 3:
                break
            # base drift
            r = 0.008 + ((h[(yi + month) % 16] % 9) - 4) / 1000.0
            # GFC late 2008
            if year == 2008 and month >= 9:
                r = -0.12 + (month % 3) * 0.01
            elif year == 2009 and month <= 3:
                r = -0.06
            elif year == 2009 and month >= 4:
                r = 0.04
            # COVID Mar 2020
            if year == 2020 and month == 3:
                r = -0.22
            elif year == 2020 and month in (4, 5):
                r = -0.05
            elif year == 2020 and month >= 6:
                r = 0.06
            # Rate hiking stress 2022
            if year == 2022 and month in (5, 6, 9, 10):
                r = -0.04
            px = max(1.0, round(px * (1.0 + r), 4))
            # month-end date
            day = 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31
            if month == 2:
                day = 28
            date = f"{year:04d}-{month:02d}-{day:02d}"
            records.append(
                pit_record(
                    entity=entity,
                    kind="price_monthly",
                    period=f"{year:04d}-{month:02d}",
                    period_end=date,
                    available_from=date,  # prices available same day
                    payload={
                        "adj_close": px,
                        "close": px,
                        "volume": 1_000_000 + h[month % 16] * 1000,
                        "return_pct": round(r * 100.0, 4),
                    },
                    source="fixture",
                )
            )
    return records


def quarterly_records(entity: str) -> list[dict[str, Any]]:
    """Approximate quarterly from annual (4 equal slices) with lag available_from."""
    annual = {r["period"]: r for r in annual_records(entity)}
    out = []
    for fy, rec in annual.items():
        year = int("20" + fy[2:4])
        payload_a = rec["payload"]
        for qi, (month, avail_month) in enumerate(((6, 7), (9, 10), (12, 1), (3, 4)), start=1):
            # Q1=Jun, Q2=Sep, Q3=Dec, Q4=Mar of next calendar for FY
            if qi < 4:
                period_end = f"{year - 1}-{month:02d}-30" if month != 12 else f"{year - 1}-12-31"
                # FY07 Q1 ends 2006-06-30
                y = year - 1
                if month == 6:
                    period_end = f"{y}-06-30"
                elif month == 9:
                    period_end = f"{y}-09-30"
                else:
                    period_end = f"{y}-12-31"
                available_from = f"{y}-{avail_month:02d}-20"
            else:
                period_end = f"{year}-03-31"
                available_from = f"{year}-04-20"  # results typically mid/late April — PIT critical
            q_payload = {
                k: round(float(payload_a[k]) / 4.0, 4)
                for k in ("revenue", "gross_profit", "ebit", "ebitda", "net_income", "eps", "fcf", "capex")
                if k in payload_a
            }
            q_payload["cash"] = float(payload_a.get("cash") or 0)
            q_payload["total_debt"] = float(payload_a.get("total_debt") or 0)
            q_payload["shares"] = float(payload_a.get("shares") or 0)
            out.append(
                pit_record(
                    entity=entity,
                    kind="financials_quarterly",
                    period=f"{fy}Q{qi}",
                    period_end=period_end,
                    available_from=available_from,
                    payload=q_payload,
                    source="fixture",
                )
            )
    return out


def timeline_records(entity: str) -> list[dict[str, Any]]:
    e = entity.upper()
    events = [
        timeline_event(
            entity=e,
            date="2008-10-15",
            event_type="guidance",
            title="Guidance cut during GFC",
            source="fixture",
            evidence=f"{e}-GFC-GUIDANCE",
            confidence=0.8,
        ),
        timeline_event(
            entity=e,
            date="2015-06-20",
            event_type="dividend",
            title="Dividend declaration",
            source="fixture",
            evidence=f"{e}-DIV-2015",
        ),
        timeline_event(
            entity=e,
            date="2020-03-25",
            event_type="regulatory",
            title="COVID lockdown impact note",
            source="fixture",
            evidence=f"{e}-COVID-NOTE",
        ),
        timeline_event(
            entity=e,
            date="2020-04-20",
            event_type="earnings",
            title="Q4 results post COVID shock",
            source="fixture",
            evidence=f"{e}-Q4-2020",
            available_from="2020-04-20",
        ),
        timeline_event(
            entity=e,
            date="2022-06-10",
            event_type="capital_raise",
            title="Capital allocation update",
            source="fixture",
            evidence=f"{e}-CAP-2022",
        ),
    ]
    if e == "INFY":
        events.append(
            timeline_event(
                entity=e,
                date="2014-08-01",
                event_type="ceo_change",
                title="CEO transition",
                source="fixture",
                evidence="INFY-CEO-2014",
                confidence=0.95,
            )
        )
    return events


def corporate_action_records(entity: str) -> list[dict[str, Any]]:
    e = entity.upper()
    return [
        pit_record(
            entity=e,
            kind="corporate_action",
            period="2015-06-20",
            period_end="2015-06-20",
            available_from="2015-06-20",
            payload={"action": "dividend", "amount": 20.0, "currency": "INR"},
        ),
        pit_record(
            entity=e,
            kind="corporate_action",
            period="2018-09-15",
            period_end="2018-09-15",
            available_from="2018-09-15",
            payload={"action": "bonus", "ratio": "1:1"},
        ),
        pit_record(
            entity=e,
            kind="corporate_action",
            period="2021-11-01",
            period_end="2021-11-01",
            available_from="2021-11-01",
            payload={"action": "buyback", "amount_cr": 500.0},
        ),
    ]


def shareholding_records(entity: str) -> list[dict[str, Any]]:
    """Offline/dev fixture only — never used in production APP_ENV."""
    e = entity.upper()
    # Deterministic synthetic ownership panel for tests
    h = abs(hash(e)) % 7
    promoter = 20.0 + h
    fii = 25.0 + (h % 5)
    dii = 20.0
    mf = 15.0
    public = max(5.0, 100.0 - promoter - fii - dii - mf)
    out = []
    for year, month in ((2022, 3), (2023, 3), (2024, 3), (2025, 3)):
        pe = f"{year}-{month:02d}-31" if month != 3 else f"{year}-03-31"
        out.append(
            pit_record(
                entity=e,
                kind="shareholding",
                period=pe,
                period_end=pe,
                available_from=pe,
                payload={
                    "promoter": promoter,
                    "fii": fii,
                    "dii": dii,
                    "mutual_funds": mf,
                    "public": round(public, 2),
                    "pledged": float(h % 3),
                },
                source="fixture",
                confidence=0.7,
            )
        )
    return out


def market_regimes() -> list[dict[str, Any]]:
    return [
        regime_record(
            regime_id="gfc_2008",
            name="Global Financial Crisis",
            start="2008-09-01",
            end="2009-03-31",
            macro_state={"inflation": "falling", "rates": "cutting", "liquidity": "stressed"},
            affected_sectors=["banks", "it_services", "metals"],
            tags=["crisis", "bear", "GFC"],
        ),
        regime_record(
            regime_id="taper_2013",
            name="Taper Tantrum",
            start="2013-05-01",
            end="2013-09-30",
            macro_state={"fx": "usd_inr_spike", "rates": "hiking"},
            affected_sectors=["banks", "nbfc", "real_estate"],
            tags=["correction", "taper"],
        ),
        regime_record(
            regime_id="covid_2020",
            name="COVID Shock",
            start="2020-02-01",
            end="2020-05-31",
            macro_state={"gdp": "collapse", "liquidity": "emergency", "oil": "crash"},
            affected_sectors=["aviation", "auto", "banks", "it_services"],
            tags=["crisis", "COVID", "bear"],
        ),
        regime_record(
            regime_id="rate_hike_2010_11",
            name="Rate Hiking Cycle 2010-11",
            start="2010-03-01",
            end="2011-12-31",
            macro_state={"rates": "hiking", "inflation": "high"},
            affected_sectors=["banks", "nbfc", "real_estate"],
            tags=["rate_hiking"],
        ),
        regime_record(
            regime_id="rate_hike_2013_14",
            name="Rate Hiking Cycle 2013-14",
            start="2013-07-01",
            end="2014-06-30",
            macro_state={"rates": "hiking", "fx": "weak"},
            affected_sectors=["banks", "nbfc"],
            tags=["rate_hiking"],
        ),
        regime_record(
            regime_id="rate_hike_2022_23",
            name="Rate Hiking Cycle 2022-23",
            start="2022-05-01",
            end="2023-06-30",
            macro_state={"rates": "hiking", "inflation": "high", "oil": "elevated"},
            affected_sectors=["banks", "nbfc", "auto", "real_estate"],
            tags=["rate_hiking"],
        ),
        regime_record(
            regime_id="ai_boom_2023_25",
            name="AI Boom",
            start="2023-01-01",
            end="2025-12-31",
            macro_state={"growth": "tech_led", "liquidity": "ample"},
            affected_sectors=["it_services"],
            tags=["bull", "AI"],
        ),
        regime_record(
            regime_id="recovery_2009_10",
            name="Post-GFC Recovery",
            start="2009-04-01",
            end="2010-12-31",
            macro_state={"rates": "low", "liquidity": "improving"},
            affected_sectors=["it_services", "banks", "auto"],
            tags=["recovery", "bull"],
        ),
    ]


def macro_history() -> list[dict[str, Any]]:
    """Annual macro snapshots FY07–FY26 with PIT available_from."""
    rows = []
    # Approximate India/US macro path
    repo = 6.0
    cpi = 5.0
    usd_inr = 40.0
    oil = 70.0
    for i, fy in enumerate(FISCAL_YEARS):
        year = 2006 + i  # FY07 ~ 2006-07
        if fy == "FY09":  # GFC
            repo, cpi, oil = 5.0, 8.0, 45.0
        elif fy == "FY14":  # taper
            repo, usd_inr = 8.0, 68.0
        elif fy == "FY21":  # COVID year
            repo, cpi, oil = 4.0, 6.2, 40.0
        elif fy in {"FY23", "FY24"}:
            repo, cpi, oil = 6.5, 5.5, 85.0
        else:
            repo = min(8.0, max(4.0, repo + (0.1 if i % 3 == 0 else -0.05)))
            cpi = min(9.0, max(3.0, cpi + (0.2 if i % 4 == 0 else -0.1)))
            usd_inr = min(85.0, usd_inr + 1.2)
            oil = max(35.0, min(110.0, oil + (3 if i % 2 else -2)))
        period = fy
        rows.append(
            {
                "period": period,
                "period_end": _fy_end(fy),
                "available_from": _fy_end(fy),  # macro prints roughly period-end
                "payload": {
                    "repo_rate": round(repo / 100.0, 4),
                    "cpi": round(cpi / 100.0, 4),
                    "usd_inr": round(usd_inr, 2),
                    "oil_brent": round(oil, 2),
                    "gdp_india_growth": 0.08 if fy not in {"FY09", "FY21"} else (-0.02 if fy == "FY21" else 0.03),
                    "pmi_india": 54.0 if fy not in {"FY09", "FY21"} else 42.0,
                    "credit_growth": 0.12 if fy not in {"FY09", "FY21"} else 0.04,
                    "liquidity": "ample" if repo < 0.055 else "tight",
                },
                "source": "fixture",
            }
        )
    return rows


def seed_universe() -> list[str]:
    try:
        from knowledge_factory.coverage import NIFTY_500

        return list(NIFTY_500)
    except Exception:
        try:
            from knowledge_factory.coverage import NIFTY_100

            return list(NIFTY_100)
        except Exception:
            return ["INFY", "HDFCBANK", "TCS", "RELIANCE", "ICICIBANK"]
