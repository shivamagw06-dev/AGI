"""Forensic Accounting Engine — Beneish M, Piotroski F, Altman Z (evidence-backed)."""

from __future__ import annotations

from typing import Any


def _beneish_m(f: dict[str, Any]) -> dict[str, Any]:
    """Beneish M-Score approximation (higher / less negative → more manipulation risk)."""
    dsri = float(f.get("dsri") or 1.0)
    gmi = float(f.get("gmi") or 1.0)
    aqi = float(f.get("aqi") or 1.0)
    sgi = float(f.get("sgi") or 1.0)
    depi = float(f.get("depi") or 1.0)
    sgai = float(f.get("sgai") or 1.0)
    lvgi = float(f.get("lvgi") or 1.0)
    tata = float(f.get("tata") or 0.0)
    # Classic Beneish coefficients
    m = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )
    # Threshold ≈ -1.78 (above → higher risk)
    risk = "elevated" if m > -1.78 else "low"
    # Map to 0-100 quality (higher = safer)
    quality = max(0.0, min(100.0, 70.0 - (m + 2.5) * 25.0))
    return {
        "beneish_m": round(m, 3),
        "beneish_risk": risk,
        "beneish_quality": round(quality, 1),
        "components": {
            "DSRI": dsri,
            "GMI": gmi,
            "AQI": aqi,
            "SGI": sgi,
            "DEPI": depi,
            "SGAI": sgai,
            "LVGI": lvgi,
            "TATA": tata,
        },
    }


def _piotroski_f(f: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "f_roa_pos",
        "f_cfo_pos",
        "f_roa_up",
        "f_accrual_ok",
        "f_leverage_down",
        "f_current_up",
        "f_no_dilution",
        "f_gross_margin_up",
        "f_asset_turnover_up",
    ]
    bits = {k: int(f.get(k) or 0) for k in keys}
    total = sum(bits.values())
    quality = round(total / 9.0 * 100.0, 1)
    return {
        "piotroski_f": total,
        "piotroski_quality": quality,
        "signals": bits,
        "label": "strong" if total >= 7 else "average" if total >= 4 else "weak",
    }


def _altman_z(f: dict[str, Any]) -> dict[str, Any]:
    if f.get("bank_mode"):
        return {
            "altman_z": None,
            "altman_quality": None,
            "zone": "n/a_bank",
            "note": "Classic Altman Z not applied to banks — capital / GNPA used instead",
        }
    x1 = float(f.get("z_wc_ta") or 0)
    x2 = float(f.get("z_re_ta") or 0)
    x3 = float(f.get("z_ebit_ta") or 0)
    x4 = float(f.get("z_me_tl") or 0)
    x5 = float(f.get("z_sales_ta") or 0)
    z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    if z > 2.99:
        zone = "safe"
        quality = 85.0
    elif z > 1.81:
        zone = "grey"
        quality = 55.0
    else:
        zone = "distress"
        quality = 25.0
    return {
        "altman_z": round(z, 3),
        "altman_quality": quality,
        "zone": zone,
        "components": {"X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5},
    }


def forensic_score(inputs: dict[str, Any] | None) -> dict[str, Any]:
    f = inputs or {}
    beneish = _beneish_m(f)
    piot = _piotroski_f(f)
    altman = _altman_z(f)

    parts = [beneish["beneish_quality"], piot["piotroski_quality"]]
    if altman.get("altman_quality") is not None:
        parts.append(float(altman["altman_quality"]))
    composite = round(sum(parts) / len(parts), 1) if parts else 50.0

    return {
        "forensic": composite,
        "beneish": beneish,
        "piotroski": piot,
        "altman": altman,
        "indexes": {
            "asset_quality_index": float(f.get("aqi") or 1.0),
            "sales_growth_index": float(f.get("sgi") or 1.0),
            "depreciation_index": float(f.get("depi") or 1.0),
            "leverage_index": float(f.get("lvgi") or 1.0),
        },
        "cash_flow_adequacy": "adequate" if int(f.get("f_cfo_pos") or 0) == 1 else "weak",
        "interest_coverage_proxy": "bank_or_net_cash" if f.get("bank_mode") else "modelled_via_z",
    }
