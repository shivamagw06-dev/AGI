"""Deterministic historical macro series (FY07–FY26) with point-in-time fields."""

from __future__ import annotations

from typing import Any

FISCAL_YEARS = tuple(f"FY{y:02d}" for y in range(7, 27))


def _fy_end(fy: str) -> str:
    y = int("20" + fy[2:4])
    return f"{y}-03-31"


def _series() -> dict[str, list[float]]:
    """Key macro paths shaped around GFC / taper / COVID / 2022 hiking."""
    n = len(FISCAL_YEARS)
    repo = []
    cpi = []
    oil = []
    usd_inr = []
    gdp = []
    pmi = []
    credit = []
    dxy = []
    curve = []  # 10y-2y proxy (positive = steep)
    r, c, o, fx, g, p, cr, dx, yc = 6.0, 5.0, 70.0, 40.0, 0.08, 54.0, 0.14, 80.0, 1.0
    for i, fy in enumerate(FISCAL_YEARS):
        if fy == "FY09":  # GFC
            r, c, o, g, p, cr, dx, yc = 5.0, 8.0, 45.0, 0.03, 42.0, 0.05, 85.0, -0.5
        elif fy == "FY14":  # taper
            r, c, fx, dx, yc = 8.0, 7.0, 68.0, 84.0, -0.2
        elif fy == "FY21":  # COVID year
            r, c, o, g, p, cr, dx, yc = 4.0, 6.2, 40.0, -0.02, 35.0, 0.04, 95.0, 0.8
        elif fy in {"FY23", "FY24"}:  # hiking / high inflation aftermath
            r, c, o, g, p, cr, dx, yc = 6.5, 5.7, 85.0, 0.07, 56.0, 0.15, 104.0, -0.3
        else:
            r = min(8.5, max(4.0, r + (0.15 if i % 4 == 0 else -0.05)))
            c = min(9.0, max(3.0, c + (0.2 if i % 5 == 0 else -0.1)))
            o = max(35.0, min(110.0, o + (4 if i % 2 else -3)))
            fx = min(85.0, fx + 1.1)
            g = 0.075 if fy not in {"FY09", "FY21"} else g
            p = 54.0 if fy not in {"FY09", "FY21"} else p
            cr = 0.12 if fy not in {"FY09", "FY21"} else cr
            dx = min(110.0, max(75.0, dx + (1 if i % 3 == 0 else -0.5)))
            yc = 0.5 if fy not in {"FY09", "FY14", "FY23"} else yc
        repo.append(round(r / 100.0, 4))
        cpi.append(round(c / 100.0, 4))
        oil.append(round(o, 2))
        usd_inr.append(round(fx, 2))
        gdp.append(round(g, 4))
        pmi.append(round(p, 2))
        credit.append(round(cr, 4))
        dxy.append(round(dx, 2))
        curve.append(round(yc, 3))
    return {
        "interest_rates": repo,
        "inflation": cpi,
        "oil": oil,
        "usd_inr": usd_inr,
        "gdp": gdp,
        "pmi": pmi,
        "credit_growth": credit,
        "dxy": dxy,
        "yield_curve": curve,
        "liquidity": [0.02 if x < 0.055 else -0.01 for x in repo],
        "government_bond_yields": [round(x + 0.01, 4) for x in repo],
    }


def historical_macro_records() -> dict[str, list[dict[str, Any]]]:
    series = _series()
    out: dict[str, list[dict[str, Any]]] = {}
    for sid, vals in series.items():
        rows = []
        for fy, v in zip(FISCAL_YEARS, vals):
            pe = _fy_end(fy)
            rows.append(
                {
                    "period": fy,
                    "period_end": pe,
                    "available_from": pe,  # PIT: known at period end
                    "value": v,
                    "source": "fixture",
                }
            )
        out[sid] = rows
    return out


def snapshot_as_of(as_of: str) -> dict[str, Any]:
    """Latest available macro snapshot on or before as_of (PIT)."""
    hist = historical_macro_records()
    snap = {}
    for sid, rows in hist.items():
        avail = [r for r in rows if str(r["available_from"]) <= as_of]
        if avail:
            snap[sid] = avail[-1]["value"]
            snap[f"{sid}_period"] = avail[-1]["period"]
    snap["as_of"] = as_of
    snap["n_series"] = sum(1 for k in hist if k in snap)
    return snap


def current_snapshot() -> dict[str, Any]:
    return snapshot_as_of("2026-03-31")
