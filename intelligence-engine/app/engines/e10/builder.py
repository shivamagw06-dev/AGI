"""E10-001 Portfolio Builder — inv-vol + top-N + caps + cash + vol target."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from app.contracts.engine_state import EngineState
from app.engines.e02.exposure import E02Exposure
from app.engines.e10.construction.cash import cash_floor_from_e14
from app.engines.e10.construction.inv_vol import inverse_volatility_weights
from app.engines.e10.construction.risk_caps import apply_risk_caps
from app.engines.e10.construction.select import Candidate, select_top_n
from app.engines.e10.construction.validate import validate_portfolio
from app.engines.e10.construction.vol_target import (
    apply_vol_target,
    portfolio_volatility,
    resolve_vol_target,
)
from app.engines.e10.mapping import (
    BOOK_ID,
    MANDATE_ID,
    MODEL_VERSION,
    NAME_CAP,
    PORTFOLIO_TYPE,
    SECTOR_CAP,
    SOLVER_ID,
    TOP_N_DEFAULT,
)
from app.engines.e10.portfolio import E10Portfolio
from app.engines.l4.opinion import L4Opinion


def build_portfolio(
    *,
    as_of: str,
    opinions: dict[str, L4Opinion],
    exposures: dict[str, E02Exposure],
    e14: EngineState | None,
    universe_id: str = "NIFTY500",
    top_n: int = TOP_N_DEFAULT,
    sigma_overrides: dict[str, float] | None = None,
) -> E10Portfolio:
    selected, rejected = select_top_n(
        opinions,
        exposures,
        top_n=top_n,
        sigma_overrides=sigma_overrides,
    )
    cash_floor, cash_source = cash_floor_from_e14(e14)
    vol_target = resolve_vol_target(e14)
    binding: list[str] = [f"C_CASH:{cash_source}"]

    if not selected:
        return _finalize(
            as_of=as_of,
            universe_id=universe_id,
            weights={},
            cash=1.0,
            selected=[],
            rejected=rejected,
            binding=binding + ["C_EMPTY_BOOK"],
            expected_vol=0.0,
            vol_target=vol_target,
            e14=e14,
            opinions=opinions,
            exposures=exposures,
            cash_source=cash_source,
            scale=0.0,
        )

    seed = inverse_volatility_weights(selected)
    equity_budget = max(0.0, 1.0 - cash_floor)
    capped, cap_binding = apply_risk_caps(
        seed,
        selected,
        name_cap=NAME_CAP,
        sector_cap=SECTOR_CAP,
        equity_budget=equity_budget,
    )
    binding.extend(cap_binding)

    scaled, _exp_vol_pre, scale, vol_binding = apply_vol_target(
        capped,
        selected,
        vol_target=vol_target,
        e14=e14,
    )
    binding.extend(vol_binding)

    # Hard re-clip after size/vol scale (never exceed name/sector caps)
    if scaled:
        unit = {s: w / max(sum(scaled.values()), 1e-12) for s, w in scaled.items()}
        scaled, cap2 = apply_risk_caps(
            unit,
            selected,
            name_cap=NAME_CAP,
            sector_cap=SECTOR_CAP,
            equity_budget=sum(scaled.values()),
        )
        for b in cap2:
            if b not in binding:
                binding.append(b)

    equity = sum(scaled.values())
    if equity > 1.0 - cash_floor + 1e-9:
        allow = max(0.0, 1.0 - cash_floor)
        if equity > 0 and allow >= 0:
            factor = allow / equity
            scaled = {s: w * factor for s, w in scaled.items()}
            binding.append("C_CASH_FLOOR")
            equity = sum(scaled.values())

    cash = round(max(cash_floor, 1.0 - equity), 8)
    # Exact residual to 1.0
    equity = sum(scaled.values())
    cash = round(1.0 - equity, 8)
    if cash < 0 and abs(cash) < 1e-8:
        cash = 0.0

    weights = {s: round(w, 8) for s, w in scaled.items() if w > 1e-10}
    expected_vol = portfolio_volatility(weights, selected)
    return _finalize(
        as_of=as_of,
        universe_id=universe_id,
        weights=weights,
        cash=float(cash),
        selected=selected,
        rejected=rejected,
        binding=binding,
        expected_vol=round(expected_vol, 6),
        vol_target=vol_target,
        e14=e14,
        opinions=opinions,
        exposures=exposures,
        cash_source=cash_source,
        scale=scale,
    )


def _finalize(
    *,
    as_of: str,
    universe_id: str,
    weights: dict[str, float],
    cash: float,
    selected: list[Candidate],
    rejected: list[dict[str, str]],
    binding: list[str],
    expected_vol: float,
    vol_target: float,
    e14: EngineState | None,
    opinions: dict[str, L4Opinion],
    exposures: dict[str, E02Exposure],
    cash_source: str,
    scale: float,
) -> E10Portfolio:
    validation = validate_portfolio(weights, cash, selected)
    sector_alloc: dict[str, float] = defaultdict(float)
    positions: list[dict[str, Any]] = []
    cand_map = {c.symbol: c for c in selected}
    for sym, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        c = cand_map.get(sym)
        sector = c.sector_id if c else None
        if sector:
            sector_alloc[sector] += w
        positions.append(
            {
                "symbol": sym,
                "side": "long",
                "weight": w,
                "sector_id": sector,
                "alpha_score": c.score if c else None,
                "sigma": c.sigma if c else None,
                "cap_source": [b for b in binding if sym in b],
            }
        )

    confs = [opinions[s].confidence for s in weights if s in opinions]
    base_conf = sum(confs) / len(confs) if confs else 0.4
    e14_adj = 1.0
    e14_ref: dict[str, Any] = {}
    if e14 is not None:
        meta = e14.metadata or {}
        e14_adj = float(meta.get("confidence_adjustment") or 1.0)
        e14_ref = {
            "as_of": e14.as_of,
            "playbook": meta.get("playbook"),
            "risk_level": meta.get("risk_level"),
            "gate": meta.get("gate"),
            "size_multiplier": meta.get("size_multiplier"),
            "confidence_adjustment": e14_adj,
            "hash": e14.hash,
        }
    portfolio_confidence = float(max(0.05, min(0.95, base_conf * e14_adj)))

    digest = _sha(
        {
            "as_of": as_of,
            "weights": weights,
            "cash": cash,
            "model_version": MODEL_VERSION,
            "binding": binding,
            "selected": [c.symbol for c in selected],
        }
    )

    return E10Portfolio(
        as_of=as_of,
        universe_id=universe_id,
        mandate_id=MANDATE_ID,
        portfolio_type=PORTFOLIO_TYPE,
        book_id=BOOK_ID,
        weights=weights,
        cash_allocation=round(cash, 8),
        target_positions=positions,
        risk_budget={
            "name_cap": NAME_CAP,
            "sector_cap": SECTOR_CAP,
            "cash_floor_policy": cash_source,
            "cash_allocation": round(cash, 8),
            "vol_target": vol_target,
            "scale": scale,
            "equity_gross": round(sum(weights.values()), 8),
        },
        expected_volatility=float(expected_vol),
        vol_target=float(vol_target),
        portfolio_confidence=portfolio_confidence,
        gross=round(sum(weights.values()), 8),
        net=round(sum(weights.values()), 8),
        sector_allocation={k: round(v, 8) for k, v in sector_alloc.items()},
        validation=validation,
        binding_constraints=binding,
        solver={
            "model_id": SOLVER_ID,
            "status": "feasible" if validation.get("ok") else "violations",
            "binding_constraints": binding,
        },
        e14_ref=e14_ref,
        l4_refs={s: opinions[s].hash for s in weights if s in opinions},
        e02_refs={s: exposures[s].hash for s in weights if s in exposures},
        selected_symbols=[c.symbol for c in selected],
        rejected_symbols=rejected,
        model_version=MODEL_VERSION,
        research_only=True,
        execution=False,
        hash=digest,
    )


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
