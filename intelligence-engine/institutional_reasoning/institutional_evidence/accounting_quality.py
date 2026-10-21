"""Module 9 — Accounting Quality producers.

Accruals, receivables, inventory, WC, cash-flow quality, leverage,
asset turnover, Piotroski, Altman, Beneish — when inputs exist.
Otherwise transparent insufficient.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.provenance import now_iso

AQ_VERSION = "accounting-quality-v1.0.0"


def _num(d: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)) and v != 0:
            return float(v)
    return None


def produce_accounting_quality(
    entity_id: str,
    *,
    financials: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce accounting quality metrics from supplied financials pack.

    Does not invent scores. Missing inputs → insufficient flags.
    """
    eid = str(entity_id or "").upper()
    fin = financials or {}
    missing: list[str] = []
    metrics: dict[str, Any] = {}

    # Soft extract from common CID / YFP shapes
    flat = dict(fin)
    if isinstance(fin.get("metrics"), dict):
        flat.update(fin["metrics"])
    if isinstance(fin.get("ratios"), dict):
        flat.update(fin["ratios"])

    mapping = {
        "accruals": ("accruals", "accrual_ratio"),
        "receivables": ("receivables", "accounts_receivable", "receivables_days"),
        "inventory": ("inventory", "inventory_days"),
        "working_capital": ("working_capital", "nwc"),
        "cash_flow_quality": ("cash_conversion", "ocf_to_ni", "fcf_conversion"),
        "leverage": ("net_debt_to_ebitda", "debt_equity", "leverage"),
        "asset_turnover": ("asset_turnover", "ato"),
        "piotroski": ("piotroski", "piotroski_f_score", "f_score"),
        "altman": ("altman", "altman_z", "z_score"),
        "beneish": ("beneish", "beneish_m", "m_score"),
    }
    for out_key, aliases in mapping.items():
        val = _num(flat, *aliases)
        if val is None:
            missing.append(out_key)
        else:
            metrics[out_key] = val

    return {
        "entity": eid,
        "as_of": now_iso(),
        "metrics": metrics,
        "missing": missing,
        "cash_conversion": metrics.get("cash_flow_quality"),
        "leverage": metrics.get("leverage"),
        "earnings_quality": metrics.get("accruals") or metrics.get("piotroski"),
        "validated": len(metrics) >= 3,
        "insufficient": len(metrics) < 3,
        "accounting_quality_version": AQ_VERSION,
        "note": "Scores only emitted when inputs exist; otherwise insufficient.",
    }
