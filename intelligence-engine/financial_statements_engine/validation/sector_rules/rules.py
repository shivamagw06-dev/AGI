"""Sector-specific rules — isolated from core accounting equations."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import extract_metrics, finding, metric_value


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    sector = str((context or {}).get("sector") or draft.get("industry") or "").lower()
    metrics = extract_metrics(draft)
    out: list[dict[str, Any]] = []

    if sector in ("banking", "bank", "nbfc"):
        # Banks often lack classic "inventory"; presence is a warning only
        inv = metric_value(metrics, "inventory")
        if inv is not None and inv > 0:
            out.append(
                finding(
                    rule_id="SEC_BANK_INV",
                    rule_name="banking_unexpected_inventory",
                    status="WARN",
                    severity="WARNING",
                    affected_metrics=["inventory"],
                    evidence={"sector": sector, "inventory": inv},
                    detail="Inventory unusual for banking/NBFC",
                )
            )
        else:
            out.append(
                finding(
                    rule_id="SEC_BANK_INV",
                    rule_name="banking_unexpected_inventory",
                    status="PASS",
                    severity="INFO",
                    evidence={"sector": sector},
                )
            )
    elif sector in ("insurance",):
        out.append(
            finding(
                rule_id="SEC_INS_PLACEHOLDER",
                rule_name="insurance_rules_placeholder",
                status="SKIP",
                severity="INFO",
                detail="Insurance-specific rules reserved for expansion",
            )
        )
    elif sector in ("utilities", "power"):
        out.append(
            finding(
                rule_id="SEC_UTIL_PLACEHOLDER",
                rule_name="utilities_rules_placeholder",
                status="SKIP",
                severity="INFO",
            )
        )
    else:
        out.append(
            finding(
                rule_id="SEC_GENERIC",
                rule_name="no_sector_specific_rules",
                status="SKIP",
                severity="INFO",
                evidence={"sector": sector or None},
            )
        )
    return out
