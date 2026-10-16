"""Prediction Engine (PE) — probabilistic distributions; immutable prediction versions."""

from __future__ import annotations

import random
import statistics
from datetime import timedelta
from typing import Any

from app.ail.catalog import COMPANIES
from app.ail.models import ForecastDistribution, PredictionRecord, ThesisVersion, utc_now
from app.ail.store import AilStore


class PredictionEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def forecast(
        self,
        ticker: str,
        *,
        company: str | None = None,
        evidence_ids: list[str] | None = None,
        thesis: ThesisVersion | None = None,
        force_new: bool = False,
    ) -> PredictionRecord:
        t = ticker.upper()
        prior = self.store.active_prediction(t)
        profile = COMPANIES.get(t) or {}
        seed = dict(profile.get("financial_seed") or {})
        name = company or profile.get("company") or t

        bull_p = thesis.bull.probability if thesis else 0.30
        base_p = thesis.base.probability if thesis else 0.45
        bear_p = thesis.bear.probability if thesis else 0.25

        rev = float(seed.get("revenue_inr_cr_p50") or 100000.0)
        ebitda_m = float(seed.get("ebitda_margin_p50") or 0.18)
        eps = float(seed.get("eps_p50") or 50.0)
        debt = float(seed.get("net_debt_p50") or 0.0)
        roe = float(seed.get("roe_p50") or 0.15)
        roce = roe * 0.9
        mult = float(seed.get("target_multiple_p50") or 20.0)

        scenarios = {
            "bull": _scenario(rev, ebitda_m, eps, debt, roe, roce, mult, scale=1.12, margin_delta=0.02),
            "base": _scenario(rev, ebitda_m, eps, debt, roe, roce, mult, scale=1.0, margin_delta=0.0),
            "bear": _scenario(rev, ebitda_m, eps, debt, roe, roce, mult, scale=0.90, margin_delta=-0.025),
        }
        scenarios["bull"]["probability"] = bull_p
        scenarios["base"]["probability"] = base_p
        scenarios["bear"]["probability"] = bear_p

        distributions = [
            _dist("revenue", "INR_cr", scenarios, "revenue"),
            _dist("ebitda", "INR_cr", scenarios, "ebitda"),
            _dist("eps", "INR", scenarios, "eps"),
            _dist("fcf", "INR_cr", scenarios, "fcf"),
            _dist("roe", "ratio", scenarios, "roe"),
            _dist("roce", "ratio", scenarios, "roce"),
            _dist("ebitda_margin", "ratio", scenarios, "ebitda_margin"),
            _dist("net_debt", "INR_cr", scenarios, "net_debt"),
            _dist("cash", "INR_cr", scenarios, "cash"),
            _dist("dividend", "INR", scenarios, "dividend"),
            _dist("target_price", "INR", scenarios, "target_price"),
            _dist("valuation_multiple", "x", scenarios, "valuation_multiple"),
        ]

        # Monte Carlo blend using scenario probabilities
        for d in distributions:
            d.samples = _monte_carlo(scenarios, d.metric, n=200)
            if d.samples:
                xs = sorted(d.samples)
                d.p10 = xs[int(0.10 * (len(xs) - 1))]
                d.p50 = xs[int(0.50 * (len(xs) - 1))]
                d.p90 = xs[int(0.90 * (len(xs) - 1))]
                d.mean = statistics.fmean(xs)

        sensitivity = {
            "revenue_to_eps": "EPS ≈ linear to revenue at constant margins",
            "margin_to_target_price": "±100bps EBITDA margin ≈ ±multiple-adjusted price impact",
            "multiple_to_target_price": "Target price scales ~1:1 with valuation multiple",
        }

        conf = 0.55
        if thesis:
            conf = round((thesis.base.confidence + thesis.bull.confidence + thesis.bear.confidence) / 3.0, 4)

        pred = PredictionRecord(
            ticker=t,
            company=str(name),
            model_version="ail-pe-v1.0",
            prediction_date=utc_now(),
            review_date=(utc_now() + timedelta(days=90)).date().isoformat(),
            scenario=scenarios,
            distributions=distributions,
            sensitivity=sensitivity,
            inputs={
                "financial_seed": seed,
                "thesis_probabilities": {"bull": bull_p, "base": base_p, "bear": bear_p},
                "monte_carlo_paths": 200,
            },
            evidence_ids=list(evidence_ids or []),
            confidence=conf,
            outcome=None,
        )

        if prior and not force_new:
            # immutable: only append if thesis probs or evidence set changed materially
            same_ev = set(prior.evidence_ids) == set(pred.evidence_ids)
            same_p = (
                abs((prior.scenario.get("bull") or {}).get("probability", 0) - bull_p) < 1e-9
                and abs((prior.scenario.get("bear") or {}).get("probability", 0) - bear_p) < 1e-9
            )
            if same_ev and same_p:
                return prior
        return self.store.put_prediction(pred)

    def get(self, ticker: str) -> dict[str, Any]:
        pred = self.store.active_prediction(ticker)
        if not pred:
            pred = self.forecast(ticker, force_new=True)
        return {
            "programme": "PE",
            **pred.to_dict(),
            "history_versions": len(self.store.predictions_by_ticker.get(ticker.upper(), [])),
            "immutable": True,
        }

    def get_by_id(self, prediction_id: str) -> dict[str, Any] | None:
        p = self.store.get_prediction(prediction_id)
        return p.to_dict() if p else None


def _scenario(
    rev: float,
    ebitda_m: float,
    eps: float,
    debt: float,
    roe: float,
    roce: float,
    mult: float,
    *,
    scale: float,
    margin_delta: float,
) -> dict[str, Any]:
    margin = max(0.01, ebitda_m + margin_delta)
    revenue = rev * scale
    ebitda = revenue * margin
    eps_v = eps * scale * (1 + margin_delta)
    fcf = ebitda * 0.55
    cash = max(0.0, -min(0.0, debt) + ebitda * 0.2)
    dividend = max(0.0, eps_v * 0.35)
    target = max(1.0, eps_v * mult * (1 + margin_delta))
    return {
        "revenue": round(revenue, 2),
        "ebitda": round(ebitda, 2),
        "eps": round(eps_v, 2),
        "fcf": round(fcf, 2),
        "roe": round(roe * (1 + margin_delta), 4),
        "roce": round(roce * (1 + margin_delta), 4),
        "ebitda_margin": round(margin, 4),
        "net_debt": round(debt * (1.05 if scale < 1 else 0.95), 2),
        "cash": round(cash, 2),
        "dividend": round(dividend, 2),
        "target_price": round(target, 2),
        "valuation_multiple": round(mult * (1 + margin_delta * 2), 2),
    }


def _dist(metric: str, unit: str, scenarios: dict[str, dict[str, Any]], key: str) -> ForecastDistribution:
    vals = [float(scenarios[s][key]) for s in ("bear", "base", "bull")]
    vals_sorted = sorted(vals)
    return ForecastDistribution(
        metric=metric,
        unit=unit,
        p10=vals_sorted[0],
        p50=vals_sorted[1],
        p90=vals_sorted[2],
        mean=statistics.fmean(vals),
    )


def _monte_carlo(scenarios: dict[str, dict[str, Any]], metric: str, *, n: int = 200) -> list[float]:
    keys = ["bull", "base", "bear"]
    weights = [float(scenarios[k].get("probability") or 0.33) for k in keys]
    s = sum(weights) or 1.0
    weights = [w / s for w in weights]
    out: list[float] = []
    rng = random.Random(42 + hash(metric) % 1000)
    for _ in range(n):
        pick = rng.choices(keys, weights=weights, k=1)[0]
        base = float(scenarios[pick][metric])
        # local noise
        noise = rng.gauss(0, abs(base) * 0.04 + 1e-6)
        out.append(base + noise)
    return out
