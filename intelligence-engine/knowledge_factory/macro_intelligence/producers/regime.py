"""Macro regime classification from institutional snapshot rules."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence.decision_matrix import decision_matrix_for_regimes
from knowledge_factory.macro_intelligence.fixtures.seed_macro import current_snapshot, snapshot_as_of
from knowledge_factory.macro_intelligence.playbooks.catalog import regime_playbook


def classify_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    rates = float(snap.get("interest_rates") or 0)
    infl = float(snap.get("inflation") or 0)
    gdp = float(snap.get("gdp") or 0)
    pmi = float(snap.get("pmi") or 50)
    oil = float(snap.get("oil") or 70)
    credit = float(snap.get("credit_growth") or 0)
    liq = float(snap.get("liquidity") or 0)
    curve = float(snap.get("yield_curve") or 0)
    dxy = float(snap.get("dxy") or 90)

    labels: list[str] = []
    if rates >= 0.06:
        labels.append("high_rates")
    else:
        labels.append("low_rates")
    if infl >= 0.055:
        labels.append("high_inflation")
    else:
        labels.append("low_inflation")
    if gdp < 0.02 or pmi < 45:
        labels.append("contraction")
    elif gdp >= 0.07 and pmi >= 53:
        labels.append("expansion")
    elif 0.02 <= gdp < 0.05:
        labels.append("recovery")
    else:
        labels.append("peak" if rates >= 0.06 else "expansion")
    if curve < 0:
        labels.append("yield_curve_inversion")
    if credit >= 0.12:
        labels.append("credit_expansion")
    elif credit <= 0.06:
        labels.append("credit_contraction")
    if liq >= 0.015:
        labels.append("liquidity_expansion")
    elif liq <= 0:
        labels.append("liquidity_tightening")
    if oil >= 80:
        labels.append("commodity_boom")
    elif oil <= 50:
        labels.append("commodity_bust")
    if dxy >= 100 or (gdp < 0.02 and pmi < 45):
        labels.append("risk_off")
    else:
        labels.append("risk_on")

    # Primary regime for playbook
    if "contraction" in labels or "risk_off" in labels:
        primary = "contraction" if "contraction" in labels else "risk_off"
    elif "high_rates" in labels and "high_inflation" in labels:
        primary = "high_rates"
    elif "commodity_boom" in labels and "high_rates" not in labels:
        primary = "commodity_boom"
    elif "expansion" in labels:
        primary = "expansion"
    else:
        primary = labels[0]

    matrix = decision_matrix_for_regimes(labels)
    playbook = regime_playbook(primary)
    return {
        "as_of": snap.get("as_of"),
        "snapshot": {k: v for k, v in snap.items() if not str(k).endswith("_period")},
        "active_regimes": labels,
        "primary_regime": primary,
        "playbook": playbook,
        "decision_matrix": matrix,
        "found": True,
        "fabricated": False,
    }


def classify_current() -> dict[str, Any]:
    return classify_snapshot(current_snapshot())


def classify_as_of(as_of: str) -> dict[str, Any]:
    snap = snapshot_as_of(as_of)
    if snap.get("n_series", 0) == 0:
        return {
            "found": False,
            "as_of": as_of,
            "reason": "macro_history_unavailable",
            "insufficient": True,
            "fabricated": False,
        }
    out = classify_snapshot(snap)
    out["point_in_time_integrity"] = True
    return out
