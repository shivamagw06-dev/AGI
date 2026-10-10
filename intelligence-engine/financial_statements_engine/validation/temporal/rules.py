"""Temporal validation — prior-period comparisons when available."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import finding


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ctx = context or {}
    prior = ctx.get("prior_draft") or ctx.get("prior_period")
    out: list[dict[str, Any]] = []
    period = draft.get("period") or {}
    period_end = period.get("period_end") if isinstance(period, dict) else None
    period_kind = period.get("period_kind") if isinstance(period, dict) else None

    out.append(
        finding(
            rule_id="TMP_PERIOD_KIND",
            rule_name="period_kind_valid",
            status="PASS" if period_kind in ("annual", "quarter", "quarterly", "year", None) or period_kind else "WARN",
            severity="WARNING" if period_kind not in ("annual", "quarter", "quarterly", "year", None) and period_kind else "INFO",
            evidence={"period_kind": period_kind, "period_end": period_end},
        )
    )

    currency = (draft.get("currency") or {}).get("canonical_currency")
    prior_currency = None
    if isinstance(prior, dict):
        prior_currency = (prior.get("currency") or {}).get("canonical_currency")
        prior_end = (prior.get("period") or {}).get("period_end")
        if prior_end and period_end and prior_end == period_end:
            out.append(
                finding(
                    rule_id="TMP_OVERLAP",
                    rule_name="period_overlap",
                    status="FAIL",
                    severity="ERROR",
                    evidence={"period_end": period_end, "prior_end": prior_end},
                    detail="Period overlaps prior draft period_end",
                )
            )
        else:
            out.append(
                finding(
                    rule_id="TMP_OVERLAP",
                    rule_name="period_overlap",
                    status="PASS",
                    severity="INFO",
                )
            )
        if prior_currency and currency and prior_currency != currency:
            out.append(
                finding(
                    rule_id="TMP_CURRENCY",
                    rule_name="currency_continuity",
                    status="FAIL",
                    severity="ERROR",
                    evidence={"currency": currency, "prior_currency": prior_currency},
                )
            )
        else:
            out.append(
                finding(
                    rule_id="TMP_CURRENCY",
                    rule_name="currency_continuity",
                    status="PASS" if prior_currency else "SKIP",
                    severity="INFO",
                    evidence={"currency": currency, "prior_currency": prior_currency},
                )
            )
    else:
        out.append(
            finding(
                rule_id="TMP_PRIOR",
                rule_name="prior_period_available",
                status="SKIP",
                severity="INFO",
                detail="No prior period supplied — temporal continuity skipped",
            )
        )

    return out
