"""E10 PortfolioState / EngineState builder — conf-1.0 + evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e10.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.e10.portfolio import E10Portfolio


def build_e10_state(
    portfolio: E10Portfolio,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E10_P0": True,
        "E10_OPTIMIZER": False,
        "E10_HRP": False,
        "E10_MVO": False,
    }
    c_views = float(portfolio.portfolio_confidence)
    c_e14 = float((portfolio.e14_ref or {}).get("confidence_adjustment") or 1.0)
    c_valid = 1.0 if portfolio.validation.get("ok") else 0.5
    conf_value = float(max(0.05, min(0.95, (c_views * max(0.2, c_e14) * c_valid) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e10_pos_model",
            "claim": f"Model portfolio via {portfolio.solver.get('model_id')} top-N inv-vol",
        }
    )
    if portfolio.cash_allocation >= 0.15:
        evidence["risks"].append(
            {
                "id": "e10_risk_cash",
                "claim": f"Elevated cash allocation {portfolio.cash_allocation:.0%}",
            }
        )
    for b in portfolio.binding_constraints[:5]:
        evidence["unknowns"].append({"id": f"e10_bind_{b}", "claim": f"Binding constraint {b}"})
    if not portfolio.validation.get("ok"):
        evidence["negative"].append(
            {"id": "e10_neg_validation", "claim": "Portfolio validation reported violations"}
        )
    evidence["risks"].append(
        {
            "id": "e10_research_only",
            "claim": "Research model portfolio only — no execution / OMS / broker routing",
        }
    )

    input_hash = _sha(
        {
            "as_of": portfolio.as_of,
            "weights": portfolio.weights,
            "cash": portfolio.cash_allocation,
            "model_version": MODEL_VERSION,
            "flags": flag_map,
            "l4_refs": portfolio.l4_refs,
            "e14_ref": portfolio.e14_ref,
        }
    )

    metadata: dict[str, Any] = {
        "e10_portfolio": portfolio.model_dump(mode="json"),
        "weights": portfolio.weights,
        "cash_allocation": portfolio.cash_allocation,
        "expected_volatility": portfolio.expected_volatility,
        "vol_target": portfolio.vol_target,
        "gross_exposure": portfolio.gross,
        "net_exposure": portfolio.net,
        "research_only": True,
        "execution": False,
        "flags": flag_map,
    }

    body = {
        "engine": "E10",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": portfolio.as_of,
        "universe_id": portfolio.universe_id,
        "symbol": None,
        "score": {
            "raw": portfolio.expected_volatility,
            "normalized_0_100": None,
            "normalized_signed": None,
            "unit": "other",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "views_confidence": round(c_views, 4),
                "e14_confidence_adjustment": round(c_e14, 4),
                "validation": round(c_valid, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(len(portfolio.weights)),
            "historical_accuracy": None,
            "stability": None,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"Illustrative long-only research portfolio ({len(portfolio.weights)} names, "
                f"cash={portfolio.cash_allocation:.0%}, σ≈{portfolio.expected_volatility:.1%}). "
                "Model portfolio only — not advice and not executable."
            ),
            "top_drivers": ["L4_views", "E14_caps", "AM_INVVOL"],
            "falsifiers": ["e14_hard_derisk", "validation_failure", "empty_l4_universe"],
        },
        "warnings": ["research_only_not_advice", "no_execution"],
        "stale_inputs": [],
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
