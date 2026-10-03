"""Quality engine — cash conversion, leverage, profitability signals (evidence-backed)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.schema import SEV_NEGATIVE, SEV_POSITIVE, SEV_WARNING


def _latest(series: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [p for p in series if isinstance(p.get("value"), (int, float))]
    if not rows:
        return None
    return sorted(rows, key=lambda r: str(r.get("period") or r.get("reporting_period") or ""))[-1]


def _val_at(series_map: dict[str, list[dict[str, Any]]], metric: str) -> tuple[float | None, dict[str, Any] | None]:
    row = _latest(series_map.get(metric) or [])
    if not row:
        return None, None
    return float(row["value"]), row


def quality_signals(series_map: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Return quality findings candidates with evidence (no unsupported claims)."""
    out: list[dict[str, Any]] = []

    ocf, ocf_row = _val_at(series_map, "operating_cash_flow")
    ni, ni_row = _val_at(series_map, "net_income")
    if ocf is not None and ni is not None and ni != 0 and ocf_row and ni_row:
        ratio = ocf / ni
        if ratio >= 1.0:
            code, sev = "strong_cash_conversion", SEV_POSITIVE
            detail = f"Operating cash flow ({ocf:.2f}) covers net income ({ni:.2f}); conversion ratio {ratio:.2f}."
        elif ratio >= 0.7:
            code, sev = "adequate_cash_conversion", SEV_WARNING
            detail = f"Operating cash flow ({ocf:.2f}) is below net income ({ni:.2f}); conversion ratio {ratio:.2f}."
        else:
            code, sev = "weak_cash_conversion", SEV_NEGATIVE
            detail = f"Operating cash flow ({ocf:.2f}) lags net income ({ni:.2f}); conversion ratio {ratio:.2f}."
        out.append(
            {
                "code": code,
                "category": "cash_flow_quality",
                "severity": sev,
                "detail": detail,
                "evidence": {
                    "metrics": [
                        {"metric": "operating_cash_flow", "period": ocf_row.get("period") or ocf_row.get("reporting_period"), "value": ocf},
                        {"metric": "net_income", "period": ni_row.get("period") or ni_row.get("reporting_period"), "value": ni},
                    ],
                    "conversion_ratio": round(ratio, 4),
                    "warehouse_version": ocf_row.get("warehouse_version") or ni_row.get("warehouse_version"),
                    "validation_id": ocf_row.get("validation_id") or ni_row.get("validation_id"),
                },
            }
        )

    debt, debt_row = _val_at(series_map, "total_debt")
    equity_series = series_map.get("total_equity") or series_map.get("equity") or []
    equity, equity_row = _val_at({"total_equity": equity_series}, "total_equity")
    de_series = series_map.get("debt_to_equity") or []
    de, de_row = _val_at({"debt_to_equity": de_series}, "debt_to_equity")
    if de is not None and de_row:
        if de >= 1.5:
            out.append(
                {
                    "code": "high_leverage",
                    "category": "balance_sheet_strength",
                    "severity": SEV_WARNING,
                    "detail": f"Debt-to-equity is {de:.2f}.",
                    "evidence": {
                        "metrics": [{"metric": "debt_to_equity", "period": de_row.get("period") or de_row.get("reporting_period"), "value": de}],
                        "warehouse_version": de_row.get("warehouse_version"),
                        "validation_id": de_row.get("validation_id"),
                    },
                }
            )
        elif de <= 0.5:
            out.append(
                {
                    "code": "low_leverage",
                    "category": "balance_sheet_strength",
                    "severity": SEV_POSITIVE,
                    "detail": f"Debt-to-equity is {de:.2f}.",
                    "evidence": {
                        "metrics": [{"metric": "debt_to_equity", "period": de_row.get("period") or de_row.get("reporting_period"), "value": de}],
                        "warehouse_version": de_row.get("warehouse_version"),
                        "validation_id": de_row.get("validation_id"),
                    },
                }
            )
    elif debt is not None and equity is not None and equity != 0 and debt_row and equity_row:
        ratio = debt / equity
        code = "high_leverage" if ratio >= 1.5 else ("low_leverage" if ratio <= 0.5 else "moderate_leverage")
        sev = SEV_WARNING if ratio >= 1.5 else (SEV_POSITIVE if ratio <= 0.5 else SEV_WARNING)
        out.append(
            {
                "code": code,
                "category": "balance_sheet_strength",
                "severity": sev,
                "detail": f"Debt/equity proxy is {ratio:.2f} (debt {debt:.2f} / equity {equity:.2f}).",
                "evidence": {
                    "metrics": [
                        {"metric": "total_debt", "period": debt_row.get("period") or debt_row.get("reporting_period"), "value": debt},
                        {"metric": "total_equity", "period": equity_row.get("period") or equity_row.get("reporting_period"), "value": equity},
                    ],
                    "warehouse_version": debt_row.get("warehouse_version"),
                    "validation_id": debt_row.get("validation_id"),
                },
            }
        )

    # Profitability direction from net_income YoY-like: last two annual-ish points
    ni_series = sorted(
        [p for p in (series_map.get("net_income") or []) if isinstance(p.get("value"), (int, float))],
        key=lambda r: str(r.get("period") or r.get("reporting_period") or ""),
    )
    if len(ni_series) >= 2:
        a, b = ni_series[-2], ni_series[-1]
        av, bv = float(a["value"]), float(b["value"])
        if bv > av:
            out.append(
                {
                    "code": "improving_profitability",
                    "category": "profitability",
                    "severity": SEV_POSITIVE,
                    "detail": f"Net income rose from {av:.2f} ({a.get('period') or a.get('reporting_period')}) to {bv:.2f} ({b.get('period') or b.get('reporting_period')}).",
                    "evidence": {
                        "metrics": [
                            {"metric": "net_income", "period": a.get("period") or a.get("reporting_period"), "value": av},
                            {"metric": "net_income", "period": b.get("period") or b.get("reporting_period"), "value": bv},
                        ],
                        "warehouse_version": b.get("warehouse_version"),
                        "validation_id": b.get("validation_id"),
                    },
                }
            )
        elif bv < av:
            out.append(
                {
                    "code": "declining_profitability",
                    "category": "profitability",
                    "severity": SEV_NEGATIVE,
                    "detail": f"Net income fell from {av:.2f} ({a.get('period') or a.get('reporting_period')}) to {bv:.2f} ({b.get('period') or b.get('reporting_period')}).",
                    "evidence": {
                        "metrics": [
                            {"metric": "net_income", "period": a.get("period") or a.get("reporting_period"), "value": av},
                            {"metric": "net_income", "period": b.get("period") or b.get("reporting_period"), "value": bv},
                        ],
                        "warehouse_version": b.get("warehouse_version"),
                        "validation_id": b.get("validation_id"),
                    },
                }
            )

    roce, roce_row = _val_at(series_map, "roce")
    if roce is not None and roce_row:
        if roce >= 15:
            out.append(
                {
                    "code": "capital_efficiency",
                    "category": "growth_quality",
                    "severity": SEV_POSITIVE,
                    "detail": f"ROCE is {roce:.2f}%.",
                    "evidence": {
                        "metrics": [{"metric": "roce", "period": roce_row.get("period") or roce_row.get("reporting_period"), "value": roce}],
                        "warehouse_version": roce_row.get("warehouse_version"),
                        "validation_id": roce_row.get("validation_id"),
                    },
                }
            )

    # Earnings quality: OCF vs NI already covered; flag low if weak conversion + rising NI
    codes = {s["code"] for s in out}
    if "weak_cash_conversion" in codes and "improving_profitability" in codes:
        out.append(
            {
                "code": "low_earnings_quality",
                "category": "cash_flow_quality",
                "severity": SEV_WARNING,
                "detail": "Profitability improved while cash conversion is weak — earnings quality warrants monitoring.",
                "evidence": {
                    "supporting_codes": ["weak_cash_conversion", "improving_profitability"],
                    "metrics": [],
                },
            }
        )
    elif "strong_cash_conversion" in codes:
        out.append(
            {
                "code": "high_earnings_quality",
                "category": "cash_flow_quality",
                "severity": SEV_POSITIVE,
                "detail": "Cash conversion supports reported earnings.",
                "evidence": {"supporting_codes": ["strong_cash_conversion"], "metrics": []},
            }
        )

    return out
