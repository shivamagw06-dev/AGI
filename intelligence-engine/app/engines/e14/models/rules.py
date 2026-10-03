"""Rule-based risk classification — P0 (spec §3.2–3.3, §7.7–7.8). No ML."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e14.features.builder import RiskFeatureVector
from app.engines.e14.mapping import TAXONOMY_IDS


@dataclass(frozen=True)
class RiskClassification:
    risk_score: float
    risk_level: str
    taxonomy_scores: dict[str, float]
    risk_flags: list[dict[str, Any]]
    playbook: str
    gate: str
    size_multiplier: float
    confidence_adjustment: float
    crowding_score: float
    liquidity_score: float
    tail_risk_score: float
    top_risk_drivers: list[str]
    engine_weight_adjustments: dict[str, float]
    suggested_hedging: list[dict[str, Any]]
    vol_target_suggested: float
    degraded: bool


def severity_band(score: float) -> str:
    if score < 25:
        return "S0"
    if score < 50:
        return "S1"
    if score < 75:
        return "S2"
    if score < 90:
        return "S3"
    return "S4"


def risk_level_from_score(score: float) -> str:
    if score < 30:
        return "low"
    if score < 50:
        return "moderate"
    if score < 70:
        return "elevated"
    if score < 85:
        return "severe"
    return "critical"


def classify(
    fv: RiskFeatureVector,
    *,
    e01_state: EngineState | None = None,
) -> RiskClassification:
    tax = _taxonomy_scores(fv, e01_state)
    risk_score = _fuse_risk_score(tax)

    # Hard override: any S4 or E01 crisis → max(score, 90), hedge-only gate
    e01_crisis = False
    if e01_state is not None:
        axes = (e01_state.metadata or {}).get("axes") or {}
        e01_crisis = (axes.get("R_STRESS") or {}).get("state") == "crisis"
        if (axes.get("R_VOL") or {}).get("state") == "crisis_vol":
            e01_crisis = True

    if e01_crisis or any(severity_band(s) == "S4" for s in tax.values()):
        risk_score = max(risk_score, 90.0)

    crowding = fv.get("crowding_index", tax["RK_CROWD"]) or tax["RK_CROWD"]
    liquidity = fv.get("liquidity_index", 100.0 - tax["RK_LIQUIDITY"]) or (100.0 - tax["RK_LIQUIDITY"])
    tail = fv.get("tail_risk_score", tax["RK_TAIL"]) or tax["RK_TAIL"]
    fragility = fv.get("fragility_index", 50.0) or 50.0
    days_exit = fv.get("days_to_exit_stress", 0.0) or 0.0
    gap_mult = fv.get("gap_buffer_mult", 1.0) or 1.0

    playbook = _playbook(risk_score, tax, e01_crisis)
    size_mult = _size_mult(
        risk_score=risk_score,
        playbook=playbook,
        crowding=crowding,
        fragility=fragility,
        liquidity=liquidity,
        days_exit=days_exit,
        gap_mult=gap_mult,
    )
    stale_ratio = len(fv.stale_inputs) / max(1, len(fv.stale_inputs) + len(fv.values))
    e01_risk = None
    if e01_state is not None:
        e01_risk = (e01_state.metadata or {}).get("risk_level")
    conf_adj = _conf_adj(
        crowding=crowding,
        liquidity=liquidity,
        tail=tail,
        e01_risk_level=e01_risk,
        stale_ratio=stale_ratio,
        e01_present=fv.e01_present,
    )
    gate = _gate(risk_score, playbook, e01_crisis)
    flags = _flags(tax, fv)
    drivers = _top_drivers(tax, fv)
    weights = _engine_weights(playbook, risk_score, size_mult)
    hedges = _hedges(tax, fv, risk_score)
    vol_tgt = _vol_target(playbook, e01_state)
    degraded = (not fv.e01_present) or stale_ratio > 0.40

    return RiskClassification(
        risk_score=float(round(risk_score, 4)),
        risk_level=risk_level_from_score(risk_score),
        taxonomy_scores={k: float(round(v, 2)) for k, v in tax.items()},
        risk_flags=flags,
        playbook=playbook,
        gate=gate,
        size_multiplier=float(round(size_mult, 4)),
        confidence_adjustment=float(round(conf_adj, 4)),
        crowding_score=float(round(crowding, 2)),
        liquidity_score=float(round(liquidity, 2)),
        tail_risk_score=float(round(tail, 2)),
        top_risk_drivers=drivers,
        engine_weight_adjustments=weights,
        suggested_hedging=hedges,
        vol_target_suggested=vol_tgt,
        degraded=degraded,
    )


def _taxonomy_scores(fv: RiskFeatureVector, e01: EngineState | None) -> dict[str, float]:
    vix = fv.get("vix_pctile_5y", 0.5) or 0.5
    corr = fv.get("corr_avg_20d", 0.35) or 0.35
    spike = fv.get("corr_spike", 0.0) or 0.0
    liq = fv.get("liquidity_index", 60.0) or 60.0
    crowd = fv.get("crowding_index", 40.0) or 40.0
    frag = fv.get("fragility_index", 40.0) or 40.0
    tail = fv.get("tail_risk_score", 40.0) or 40.0
    hhi = fv.get("name_hhi", 0.05) or 0.05
    beta = fv.get("portfolio_beta", 1.0) or 1.0
    macro = fv.get("macro_risk_bridge", 50.0) or 50.0
    hy = fv.get("credit_stress", fv.get("hy_oas", 0.0) or 0.0) or 0.0
    dd = fv.get("expected_dd_3m_p95", 0.10) or 0.10
    exec_bps = fv.get("exec_impact_bps", 10.0) or 10.0
    worst = fv.get("stress_worst_pnl", -5.0) or -5.0

    # Regime-aware crowding threshold scale (spec §8): high_vol lowers S2 bar
    crowd_adj = crowd
    if e01 is not None:
        vol_state = ((e01.metadata or {}).get("axes") or {}).get("R_VOL", {}).get("state")
        if vol_state in {"high_vol", "crisis_vol"}:
            crowd_adj = min(100.0, crowd + 10.0)

    scores = {
        "RK_MARKET": _clip(30 + abs(beta - 1.0) * 40 + vix * 40),
        "RK_LIQUIDITY": _clip(100.0 - liq),
        "RK_CREDIT": _clip(40 + (hy if abs(hy) <= 5 else hy / 20.0) * 15),
        "RK_VOL": _clip(vix * 100.0),
        "RK_CORR": _clip(corr * 80.0 + max(0.0, spike) * 100.0),
        "RK_TAIL": _clip(tail),
        "RK_GAP": _clip(40 + (1.0 - (fv.get("gap_buffer_mult", 1.0) or 1.0)) * 80),
        "RK_FACTOR": _clip(0.5 * crowd_adj + 0.5 * frag),
        "RK_CROWD": _clip(crowd_adj),
        "RK_EXEC": _clip(min(100.0, exec_bps * 1.2)),
        "RK_MACRO": _clip(macro),
        "RK_EVENT": _clip(35 + (1.0 - (fv.get("gap_buffer_mult", 1.0) or 1.0)) * 50),
        "RK_GEO": 20.0,
        "RK_FX": _clip(30 + abs(fv.get("usd_mom_63d", 0.0) or 0.0) * 200),
        "RK_REG": 25.0,
        "RK_CONC": _clip(hhi * 400.0),
        "RK_DD": _clip(dd * 100.0 / 0.40 * 0.9),
        "RK_SYSTEMIC": _clip(0.5 * macro + 0.3 * (vix * 100) + 0.2 * max(0.0, -worst * 3)),
    }
    for tid in TAXONOMY_IDS:
        scores.setdefault(tid, 25.0)
    return scores


def _fuse_risk_score(tax: dict[str, float]) -> float:
    """Spec §3.3 logistic fusion of standardised risk impulses."""

    def z(score: float) -> float:
        # Map 0–100 score to approx z impulse centered at 40
        return (score - 40.0) / 20.0

    x = (
        0.18 * z(tax["RK_MARKET"])
        + 0.14 * z(tax["RK_CROWD"])
        + 0.14 * z(tax["RK_LIQUIDITY"])
        + 0.12 * z(tax["RK_TAIL"])
        + 0.10 * z(tax["RK_CORR"])
        + 0.10 * z(tax["RK_FACTOR"])
        + 0.08 * z(tax["RK_DD"])
        + 0.08 * z(tax["RK_MACRO"])
        + 0.06 * z(tax["RK_EVENT"])
    )
    # Scale so benign ~0.3 and crisis ~0.9
    phi = 1.0 / (1.0 + math.exp(-x))
    return float(max(0.0, min(100.0, 100.0 * phi)))


def _playbook(risk_score: float, tax: dict[str, float], e01_crisis: bool) -> str:
    if e01_crisis or risk_score >= 90 or tax["RK_SYSTEMIC"] >= 90:
        return "hard_derisk"
    if risk_score >= 60 or tax["RK_CROWD"] >= 70 or tax["RK_CORR"] >= 70:
        return "elevated"
    return "normal"


def _size_mult(
    *,
    risk_score: float,
    playbook: str,
    crowding: float,
    fragility: float,
    liquidity: float,
    days_exit: float,
    gap_mult: float,
) -> float:
    # Spec §7.8
    if playbook == "hard_derisk" or risk_score >= 90:
        base = 0.25
    elif risk_score >= 75 or crowding >= 80 or days_exit > 15:
        base = 0.40
    elif risk_score >= 60 or fragility >= 70:
        base = 0.55
    elif risk_score >= 45:
        base = 0.75
    elif liquidity >= 75 and crowding <= 30 and risk_score < 30:
        base = 1.00
    else:
        base = 0.90
    base *= max(0.5, min(1.0, gap_mult))
    return float(max(0.25, min(1.00, base)))


def _conf_adj(
    *,
    crowding: float,
    liquidity: float,
    tail: float,
    e01_risk_level: str | None,
    stale_ratio: float,
    e01_present: bool,
) -> float:
    conf_adj = 1.0
    if crowding >= 70:
        conf_adj *= 0.85
    if liquidity <= 40:
        conf_adj *= 0.80
    if tail >= 70:
        conf_adj *= 0.80
    if e01_risk_level == "critical":
        conf_adj *= 0.70
    if stale_ratio > 0.40:
        conf_adj *= 0.75
    if not e01_present:
        # Fail closed: confidence_adjustment ≤ 0.7
        conf_adj = min(conf_adj, 0.70)
    return float(max(0.40, min(1.00, conf_adj)))


def _gate(risk_score: float, playbook: str, e01_crisis: bool) -> str:
    if e01_crisis or playbook == "hard_derisk" or risk_score >= 90:
        return "research_hedge_only"
    if risk_score >= 75:
        return "block_promotion"
    if risk_score >= 45 or playbook == "elevated":
        return "allow_with_haircut"
    return "allow"


def _flags(tax: dict[str, float], fv: RiskFeatureVector) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for tid, score in sorted(tax.items(), key=lambda kv: kv[1], reverse=True):
        sev = severity_band(score)
        if sev in {"S2", "S3", "S4"}:
            flags.append(
                {
                    "taxonomy_id": tid,
                    "severity": sev,
                    "message": f"{tid} score {score:.0f} ({sev})",
                }
            )
    if (fv.get("liquidity_index") or 100) < 40:
        flags.append(
            {
                "taxonomy_id": "RK_LIQUIDITY",
                "severity": severity_band(tax["RK_LIQUIDITY"]),
                "message": "Liquidity index below 40",
            }
        )
    # Dedupe by taxonomy keep highest severity
    best: dict[str, dict[str, Any]] = {}
    order = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4}
    for fl in flags:
        tid = fl["taxonomy_id"]
        if tid not in best or order[fl["severity"]] > order[best[tid]["severity"]]:
            best[tid] = fl
    return list(best.values())[:12]


def _top_drivers(tax: dict[str, float], fv: RiskFeatureVector) -> list[str]:
    ranked = sorted(tax.items(), key=lambda kv: kv[1], reverse=True)
    return [tid for tid, _ in ranked[:5]]


def _engine_weights(playbook: str, risk_score: float, size_mult: float) -> dict[str, float]:
    if playbook == "hard_derisk":
        return {
            "E01": 1.00,
            "E02": 0.70,
            "E03": 0.40,
            "E04": 0.50,
            "E05": 0.60,
            "E08": 1.30,
            "E09": 0.35,
            "E10": 1.00,
            "E11": 0.70,
            "E12": 0.20,
            "E13": 0.40,
        }
    if playbook == "elevated":
        return {
            "E01": 1.00,
            "E02": 0.95,
            "E03": 0.85,
            "E04": 0.80,
            "E05": 0.90,
            "E08": 1.10,
            "E09": 0.85,
            "E10": 1.00,
            "E11": 0.90,
            "E12": 0.70,
            "E13": 0.85,
        }
    # mild haircut scaled by size_mult
    s = size_mult
    return {
        "E01": 1.00,
        "E02": round(0.95 + 0.05 * s, 2),
        "E03": round(0.90 + 0.10 * s, 2),
        "E04": round(0.90 + 0.10 * s, 2),
        "E05": 1.00,
        "E08": 1.00,
        "E09": round(0.90 + 0.10 * s, 2),
        "E10": 1.00,
        "E11": 1.00,
        "E12": round(0.85 + 0.15 * s, 2),
        "E13": round(0.90 + 0.10 * s, 2),
    }


def _hedges(tax: dict[str, float], fv: RiskFeatureVector, risk_score: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    beta = fv.get("portfolio_beta", 1.0) or 1.0
    if beta > 1.1 and tax["RK_VOL"] >= 50:
        out.append(
            {
                "taxonomy_id": "RK_MARKET",
                "action": "research_index_put_overlay",
                "urgency": "medium" if risk_score < 75 else "high",
                "rationale": f"Portfolio beta {beta:.2f} with elevated vol risk",
            }
        )
    if tax["RK_CROWD"] >= 65:
        out.append(
            {
                "taxonomy_id": "RK_CROWD",
                "action": "research_factor_neutral_overlay",
                "urgency": "medium",
                "rationale": "Crowding elevated — reduce concentrated consensus exposure in research",
            }
        )
    if tax["RK_CORR"] >= 65 and tax["RK_SYSTEMIC"] >= 50:
        out.append(
            {
                "taxonomy_id": "RK_SYSTEMIC",
                "action": "increase_cash_hedge_sleeve_research",
                "urgency": "high",
                "rationale": "Correlation spike with systemic pressure",
            }
        )
    return out


def _vol_target(playbook: str, e01: EngineState | None) -> float:
    e01_vol = 0.10
    if e01 is not None:
        vt = (e01.metadata or {}).get("vol_target")
        if isinstance(vt, (int, float)):
            e01_vol = float(vt)
    if playbook == "hard_derisk":
        return min(e01_vol, 0.06)
    if playbook == "elevated":
        return min(e01_vol, 0.09)
    return min(e01_vol, 0.10)


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(max(lo, min(hi, x)))
