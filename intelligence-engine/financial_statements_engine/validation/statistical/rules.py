"""Statistical anomaly detection — warnings only; never auto-fail publication."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import extract_metrics, finding, metric_value
from financial_statements_engine.validation.schema import STAT_THRESHOLDS


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    metrics = extract_metrics(draft)
    thr = dict(STAT_THRESHOLDS)
    if context and context.get("stat_thresholds"):
        thr.update(context["stat_thresholds"])
    out: list[dict[str, Any]] = []

    def warn_neg(rule_id: str, name: str, key: str, enabled_key: str) -> None:
        if not thr.get(enabled_key, True):
            out.append(finding(rule_id=rule_id, rule_name=name, status="SKIP", severity="INFO"))
            return
        v = metric_value(metrics, key)
        if v is None:
            out.append(
                finding(
                    rule_id=rule_id,
                    rule_name=name,
                    status="SKIP",
                    severity="INFO",
                    affected_metrics=[key],
                )
            )
            return
        bad = v < 0
        out.append(
            finding(
                rule_id=rule_id,
                rule_name=name,
                status="WARN" if bad else "PASS",
                severity="WARNING" if bad else "INFO",
                affected_metrics=[key],
                evidence={"value": v},
                detail=f"Negative {key}" if bad else None,
            )
        )

    warn_neg("STAT_NEG_DEP", "negative_depreciation", "depreciation", "forbid_negative_depreciation")
    warn_neg("STAT_NEG_INV", "negative_inventory", "inventory", "forbid_negative_inventory")
    warn_neg("STAT_NEG_SC", "negative_share_capital", "share_capital", "forbid_negative_share_capital")

    # Extreme margin if revenue + net_income
    rev = metric_value(metrics, "revenue")
    ni = metric_value(metrics, "net_income")
    if rev is not None and rev != 0 and ni is not None:
        margin = (ni / rev) * 100.0
        extreme = abs(margin) > 80.0
        out.append(
            finding(
                rule_id="STAT_MARGIN",
                rule_name="extreme_margin_shift",
                status="WARN" if extreme else "PASS",
                severity="WARNING" if extreme else "INFO",
                affected_metrics=["revenue", "net_income"],
                evidence={"net_margin_pct": margin},
                detail="Extreme net margin" if extreme else None,
            )
        )
    else:
        out.append(
            finding(
                rule_id="STAT_MARGIN",
                rule_name="extreme_margin_shift",
                status="SKIP",
                severity="INFO",
                affected_metrics=["revenue", "net_income"],
            )
        )

    # Growth vs prior (warning only)
    prior = (context or {}).get("prior_metrics") or {}
    prior_rev = None
    if isinstance(prior, dict):
        prow = prior.get("revenue")
        if isinstance(prow, dict):
            prior_rev = prow.get("value")
        elif isinstance(prow, (int, float)):
            prior_rev = float(prow)
    if rev is not None and prior_rev not in (None, 0):
        growth = ((rev - float(prior_rev)) / abs(float(prior_rev))) * 100.0
        limit = float(thr.get("revenue_growth_abs_pct") or 200.0)
        bad = abs(growth) > limit
        out.append(
            finding(
                rule_id="STAT_REV_GROWTH",
                rule_name="revenue_growth_anomaly",
                status="WARN" if bad else "PASS",
                severity="WARNING" if bad else "INFO",
                affected_metrics=["revenue"],
                evidence={"growth_pct": growth, "limit_pct": limit},
            )
        )
    else:
        out.append(
            finding(
                rule_id="STAT_REV_GROWTH",
                rule_name="revenue_growth_anomaly",
                status="SKIP",
                severity="INFO",
                affected_metrics=["revenue"],
            )
        )

    return out
