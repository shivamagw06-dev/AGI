"""Deterministic calculation engine — warehouse facts in, derived metrics out."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from financial_statements_engine.derived_metrics.dependency.graph import dependency_lineage
from financial_statements_engine.derived_metrics.formula_registry.registry import (
    get_formula_by_metric,
    resolve_order,
)
from financial_statements_engine.derived_metrics.schema import DME_VERSION
from financial_statements_engine.financial_warehouse.production import get_latest
from financial_statements_engine.util import now_iso


class CalculationError(Exception):
    def __init__(self, code: str, detail: str, *, formula_id: str | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.formula_id = formula_id


def evaluate_expression(expr: Any, env: dict[str, float], *, forbid_neg_denom: bool = True) -> float:
    """Safe AST evaluator. No Python eval."""
    if isinstance(expr, (int, float)):
        return float(expr)
    if isinstance(expr, str):
        if expr not in env:
            raise CalculationError("MISSING_INPUT", f"missing:{expr}")
        return float(env[expr])
    if not isinstance(expr, dict) or len(expr) != 1:
        raise CalculationError("BAD_EXPR", f"invalid_expression:{expr!r}")
    op, args = next(iter(expr.items()))
    if not isinstance(args, list):
        args = [args]
    vals = [evaluate_expression(a, env, forbid_neg_denom=forbid_neg_denom) for a in args]
    if op == "add":
        return sum(vals)
    if op == "sub":
        if len(vals) != 2:
            raise CalculationError("BAD_EXPR", "sub_arity")
        return vals[0] - vals[1]
    if op == "mul":
        out = 1.0
        for v in vals:
            out *= v
        return out
    if op == "div":
        if len(vals) != 2:
            raise CalculationError("BAD_EXPR", "div_arity")
        if vals[1] == 0:
            raise CalculationError("DIV_ZERO", "division_by_zero")
        if forbid_neg_denom and vals[1] < 0:
            raise CalculationError("NEG_DENOM", "negative_denominator_prohibited")
        return vals[0] / vals[1]
    if op == "neg":
        return -vals[0]
    if op == "abs":
        return abs(vals[0])
    raise CalculationError("BAD_EXPR", f"unknown_op:{op}")


def _facts_to_env(facts: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, str]]:
    env: dict[str, float] = {}
    fact_ids: dict[str, str] = {}
    for f in facts:
        m = str(f.get("canonical_metric") or f.get("metric") or "")
        if not m:
            continue
        v = f.get("value")
        if v is None:
            v = f.get("normalized_value")
        if isinstance(v, (int, float)):
            env[m] = float(v)
            if f.get("fact_id"):
                fact_ids[m] = str(f["fact_id"])
    return env, fact_ids


def calculate_company(
    ticker: str,
    *,
    metrics: list[str] | None = None,
    facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Batch/incremental calculation for one company from warehouse latest facts."""
    t = ticker.upper().strip()
    if facts is None:
        pack = get_latest(t)
        facts = list(pack.get("facts") or [])
    env, fact_ids = _facts_to_env(facts)
    order = resolve_order(metrics)
    calculated: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    ts = now_iso()

    for name in order:
        form = get_formula_by_metric(name)
        if not form:
            continue
        # Skip if required warehouse inputs missing and not already calculated deps
        missing = []
        for req in form.get("required_inputs") or []:
            if req not in env and req not in calculated:
                # required may be a derived dep
                if req in (form.get("dependencies") or []):
                    if req not in calculated:
                        missing.append(req)
                else:
                    missing.append(req)
        if missing:
            failures.append(
                {
                    "metric": name,
                    "formula_id": form["formula_id"],
                    "status": "FAILED",
                    "code": "MISSING_MANDATORY_INPUTS",
                    "missing": missing,
                }
            )
            continue
        # merge derived deps into local env
        local = dict(env)
        for d in form.get("dependencies") or []:
            if d in calculated and calculated[d].get("value") is not None:
                local[d] = float(calculated[d]["value"])
        try:
            value = evaluate_expression(
                form["expression"],
                local,
                forbid_neg_denom=bool(form.get("forbid_negative_denominator", True)),
            )
            # overflow guard
            if abs(value) > 1e15:
                raise CalculationError("OVERFLOW", "value_overflow", formula_id=form["formula_id"])
            lineage = dependency_lineage(name)
            source_ids = sorted(
                {
                    fact_ids[k]
                    for k in (form.get("required_inputs") or [])
                    if k in fact_ids
                }
            )
            fingerprint = hashlib.sha256(
                json.dumps(
                    {
                        "metric": name,
                        "formula_id": form["formula_id"],
                        "formula_version": form["version"],
                        "value": value,
                        "inputs": {k: local.get(k) for k in (form.get("required_inputs") or [])},
                    },
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ).hexdigest()
            calculated[name] = {
                "metric": name,
                "value": value,
                "formula_id": form["formula_id"],
                "formula_version": form["version"],
                "category": form.get("category"),
                "status": "OK",
                "source_fact_ids": source_ids,
                "lineage_path": lineage.get("path"),
                "calculation_timestamp": ts,
                "dme_version": DME_VERSION,
                "fingerprint": fingerprint,
                "quality_status": "calculated",
            }
            env[name] = value  # allow downstream formulas
        except CalculationError as exc:
            failures.append(
                {
                    "metric": name,
                    "formula_id": form["formula_id"],
                    "status": "FAILED",
                    "code": exc.code,
                    "detail": exc.detail,
                }
            )

    return {
        "ok": True,
        "ticker": t,
        "dme_version": DME_VERSION,
        "period": next((f.get("reporting_period") for f in facts if f.get("reporting_period")), None),
        "company_id": next((f.get("company_id") for f in facts if f.get("company_id")), f"nse:{t}"),
        "metrics": calculated,
        "failures": failures,
        "metrics_calculated": len(calculated),
        "failures_n": len(failures),
        "deterministic": True,
        "mutates_warehouse_facts": False,
        "as_of": ts,
        "issues_recommendations": False,
    }
