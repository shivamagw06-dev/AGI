"""VE pipeline — assemble valuation objects from structured engine inputs."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.ve.config import PRIMARY_MODELS, SUGGESTED_MOS, SUPPORTED_MODELS
from app.ve.engines import (
    MODEL_PLUGINS,
    build_peer_rows,
    dcf_fcff,
    run_model,
    sensitivity_grid,
)
from app.ve.inputs import gather_inputs
from app.ve.models import MarginOfSafety, ScenarioCase, ValuationObject, new_id
from app.ve.store import VeStore


def _fiscal_year() -> str:
    now = datetime.now(timezone.utc)
    # Indian FY Apr-Mar
    year = now.year + 1 if now.month >= 4 else now.year
    return f"FY{year}"


def _mos(market_price: float, intrinsic: float, history_ivs: list[float]) -> MarginOfSafety:
    if intrinsic <= 0:
        disc = 0.0
    else:
        disc = ((intrinsic - market_price) / intrinsic) * 100.0
    # Historical percentile of current IV among prior IVs
    if history_ivs:
        below = sum(1 for x in history_ivs if x <= intrinsic)
        pct = below / len(history_ivs)
    else:
        pct = 0.5
    undervalued = market_price < intrinsic * (1.0 - SUGGESTED_MOS * 0.5)
    if disc >= SUGGESTED_MOS * 100:
        label = "deep_discount"
    elif disc >= 10:
        label = "undervalued"
    elif disc <= -10:
        label = "premium"
    else:
        label = "fair"
    return MarginOfSafety(
        market_price=round(market_price, 2),
        intrinsic_value=round(intrinsic, 2),
        discount_premium_pct=round(disc, 2),
        suggested_mos_pct=round(SUGGESTED_MOS * 100, 2),
        historical_percentile=round(pct, 4),
        undervalued=undervalued,
        label=label,
    )


def _scenarios(assumptions: dict[str, float], base_revenue_cr: float) -> list[ScenarioCase]:
    specs = [
        ("bull", 0.25, 1.25, 1.15, 0.9),
        ("base", 0.50, 1.0, 1.0, 1.0),
        ("bear", 0.25, 0.7, 0.85, 1.15),
    ]
    out: list[ScenarioCase] = []
    for name, prob, g_mult, m_mult, w_mult in specs:
        adj = dict(assumptions)
        adj["revenue_growth"] = max(0.0, assumptions["revenue_growth"] * g_mult)
        adj["ebit_margin"] = max(0.01, min(0.5, assumptions["ebit_margin"] * m_mult))
        adj["wacc"] = max(0.01, assumptions["wacc"] * w_mult)
        iv = dcf_fcff(adj, base_revenue_cr=base_revenue_cr).intrinsic_value
        out.append(
            ScenarioCase(
                name=name,
                intrinsic_value=round(iv, 2),
                probability=prob,
                confidence=0.7 if name == "base" else 0.55,
                notes=f"{name} case DCF FCFF",
            )
        )
    return out


class VePipeline:
    def __init__(
        self,
        store: VeStore,
        *,
        eve: Any = None,
        iie: Any = None,
        fle: Any = None,
        mee: Any = None,
        aoi: Any = None,
        ib: Any = None,
        scenarios: bool = True,
        sensitivity: bool = True,
        relative: bool = True,
    ) -> None:
        self.store = store
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.mee = mee
        self.aoi = aoi
        self.ib = ib
        self.scenarios_enabled = scenarios
        self.sensitivity_enabled = sensitivity
        self.relative_enabled = relative

    def value_company(
        self,
        key: str,
        *,
        models: list[str] | None = None,
        market_price: float | None = None,
        trigger: str = "manual",
        fiscal_year: str | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        gathered = gather_inputs(
            key,
            eve=self.eve,
            iie=self.iie,
            fle=self.fle,
            mee=self.mee,
            aoi=self.aoi,
            market_price=market_price,
        )
        company_id = gathered["company_id"]
        symbol = gathered["company_symbol"]
        assumptions = gathered["assumptions"]
        base_revenue = float(gathered["base_revenue_cr"])
        price = float(gathered["market_price"])
        peer_mult = gathered["peer_multiples"]

        history = self.store.history_for_company(company_id) or self.store.history_for_company(symbol)
        version = (history[-1].version + 1) if history else 1
        parent_id = history[-1].valuation_id if history else ""
        fy = fiscal_year or _fiscal_year()

        selected = list(models or list(PRIMARY_MODELS) + ["dcf_fcfe", "relative_pb", "relative_peg", "relative_pcf", "relative_ev_sales", "residual_income", "asset_based", "replacement_cost", "ddm"])
        # Deduplicate preserve order
        seen = set()
        ordered = []
        for m in selected:
            if m in MODEL_PLUGINS and m not in seen:
                ordered.append(m)
                seen.add(m)

        results = []
        for name in ordered:
            kwargs: dict[str, Any] = {}
            if name.startswith("dcf") or name in {"relative_pe", "relative_peg", "relative_pcf", "ddm"}:
                kwargs["base_revenue_cr"] = base_revenue
            if name == "relative_pe":
                kwargs["peer_pe"] = peer_mult["pe"]
            if name == "relative_ev_ebitda":
                kwargs["base_revenue_cr"] = base_revenue
                kwargs["peer_mult"] = peer_mult["ev_ebitda"]
            if name == "relative_ev_sales":
                kwargs["base_revenue_cr"] = base_revenue
                kwargs["peer_mult"] = peer_mult["ev_sales"]
            if name == "relative_pb":
                kwargs["peer_pb"] = peer_mult["pb"]
            if name == "relative_peg":
                kwargs["peer_pe"] = peer_mult["pe"]
            if not self.relative_enabled and name.startswith("relative_"):
                continue
            results.append(run_model(name, assumptions, **kwargs))

        # Blend: weight DCF higher
        weights = []
        for r in results:
            w = 0.35 if r.model.startswith("dcf") else 0.15 if r.model == "sotp" else 0.08
            weights.append(w)
        wsum = sum(weights) or 1.0
        blended = sum(r.intrinsic_value * w for r, w in zip(results, weights)) / wsum
        primary = next((r for r in results if r.model == "dcf_fcff"), results[0] if results else None)
        intrinsic = primary.intrinsic_value if primary else blended
        fair = blended

        scenarios = _scenarios(assumptions, base_revenue) if self.scenarios_enabled else []
        if scenarios:
            # Probability-weighted intrinsic
            pw = sum(s.intrinsic_value * s.probability for s in scenarios)
            intrinsic = round(0.6 * intrinsic + 0.4 * pw, 2)

        sens = (
            sensitivity_grid(assumptions, base_revenue_cr=base_revenue)
            if self.sensitivity_enabled
            else []
        )
        peers = build_peer_rows(symbol, list(gathered["peers"])) if self.relative_enabled else []
        hist_ivs = [h.intrinsic_value for h in history if h.intrinsic_value]
        mos = _mos(price, intrinsic, hist_ivs)

        # Key assumption drivers by sensitivity magnitude
        drivers = sorted(sens, key=lambda s: abs(s.change_pct), reverse=True)[:5]
        explain = {
            "why": (
                f"Intrinsic value ₹{intrinsic:.2f} vs market ₹{price:.2f} "
                f"({mos.label}, discount/premium {mos.discount_premium_pct:.1f}%)."
            ),
            "assumptions": [a.to_dict() for a in gathered["assumption_meta"][:20]],
            "evidence_ids": gathered["evidence_ids"],
            "forecast_ids": gathered["forecast_ids"],
            "event_ids": gathered["event_ids"],
            "risks": gathered["risks"],
            "key_drivers": [d.to_dict() for d in drivers],
            "models_used": [r.model for r in results],
            "events_that_changed_valuation": gathered["event_ids"],
        }

        obj = ValuationObject(
            valuation_id=new_id("val"),
            company_id=company_id,
            company_symbol=symbol,
            fiscal_year=fy,
            version=version,
            models=results,
            primary_model=primary.model if primary else "dcf_fcff",
            intrinsic_value=round(intrinsic, 2),
            fair_value=round(fair, 2),
            market_price=round(price, 2),
            blended_value=round(blended, 2),
            assumptions=gathered["assumption_meta"],
            scenarios=scenarios,
            margin_of_safety=mos,
            sensitivity=sens,
            peers=peers,
            evidence_ids=gathered["evidence_ids"],
            forecast_ids=gathered["forecast_ids"],
            event_ids=gathered["event_ids"],
            risks=gathered["risks"],
            explainability=explain,
            confidence=round(min(0.95, 0.45 + 0.4 * float(gathered["input_confidence"])), 4),
            parent_valuation_id=parent_id,
            trigger=trigger,
            metadata={"supported_models": list(SUPPORTED_MODELS)},
        )
        latency = (time.perf_counter() - t0) * 1000
        self.store.add(obj, recalc=bool(history), latency_ms=latency)

        # Soft IB publish — never required
        if self.ib is not None:
            try:
                self.ib.emit(
                    "CacheInvalidated",
                    producer="ve",
                    aggregate_type="company",
                    aggregate_id=symbol,
                    payload={
                        "scopes": ["cae", "company", "valuation"],
                        "company_symbol": symbol,
                        "valuation_id": obj.valuation_id,
                        "intrinsic_value": obj.intrinsic_value,
                    },
                    priority="normal",
                )
            except Exception:
                pass

        return {
            "valuation": obj.to_dict(),
            "latency_ms": round(latency, 2),
            "company_id": company_id,
            "company_symbol": symbol,
        }
