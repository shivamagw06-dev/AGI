"""Accounting Intelligence — earnings quality, cash conversion, red flags."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import AccountingAnalysis


class AccountingModel(DomainModel):
    """Teach AGI accounting quality, accruals and cash conversion."""

    domain = "accounting"
    version = "1.0.0"
    name = "Accounting Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)

        revenue_growth = num(p, "revenue_growth", 0.1)
        gross_margin = num(p, "gross_margin", 0.35)
        gross_margin_delta = num(p, "gross_margin_delta", 0.0)
        ebit_margin = num(p, "ebit_margin", 0.18)
        fcf_margin = num(p, "fcf_margin", 0.12)
        cash_conversion = num(p, "cash_conversion", fcf_margin / max(ebit_margin, 0.01))
        nwc_days = num(p, "nwc_days", 40.0)
        receivables_days = num(p, "receivables_days", 60.0)
        inventory_days = num(p, "inventory_days", 45.0)
        one_time_items = num(p, "one_time_items_pct_ebit", 0.0)
        capitalised_opex = num(p, "capitalised_opex_pct_sales", 0.0)
        goodwill_pct_assets = num(p, "goodwill_pct_assets", 0.1)
        pricing_vs_volume = str(p.get("revenue_driver") or "mixed").lower()

        red_flags: list[str] = []
        notes: list[str] = []
        strengths: list[str] = []
        weaknesses: list[str] = []

        # Accrual / earnings quality heuristics (deterministic)
        accrual_drag = 0.0
        if cash_conversion < 0.7:
            accrual_drag += 0.15
            red_flags.append("Cash conversion below 0.7 — earnings quality risk")
        if receivables_days > 90:
            accrual_drag += 0.1
            red_flags.append("Receivables days elevated")
        if inventory_days > 120:
            accrual_drag += 0.08
            red_flags.append("Inventory days elevated")
        if one_time_items > 0.15:
            accrual_drag += 0.12
            red_flags.append("Material one-time / exceptional items")
        if capitalised_opex > 0.05:
            accrual_drag += 0.1
            red_flags.append("Elevated capitalised expenses vs sales")
        if goodwill_pct_assets > 0.35:
            accrual_drag += 0.08
            red_flags.append("High goodwill intensity — impairment risk")

        if gross_margin_delta > 0 and pricing_vs_volume == "pricing":
            strengths.append("Gross margin expansion with pricing-led growth indicates pricing power")
            notes.append(
                f"Revenue growth {revenue_growth:.1%} appears pricing-led; gross margin Δ {gross_margin_delta:.1%} supports pricing power over temporary operating leverage"
            )
        elif revenue_growth > 0.15 and gross_margin_delta < 0:
            weaknesses.append("Growth with margin compression — volume/mix or cost pressure")
            notes.append("Revenue growth not accompanied by margin expansion")

        if cash_conversion >= 0.9:
            strengths.append("Strong cash conversion")
        if nwc_days < 30:
            strengths.append("Efficient working capital")
            notes.append("Working capital improvement supports higher earnings quality")

        accrual_quality = clamp(1.0 - accrual_drag)
        earnings_quality = clamp(0.55 * accrual_quality + 0.25 * clamp(cash_conversion) + 0.2 * clamp(gross_margin))
        cf_quality = clamp(0.7 * clamp(cash_conversion) + 0.3 * (1.0 if fcf_margin > 0 else 0.3))
        aq_score = clamp(0.45 * earnings_quality + 0.35 * cf_quality + 0.2 * accrual_quality)

        label = "high_quality" if aq_score >= 0.7 else "acceptable" if aq_score >= 0.5 else "weak"
        conf = clamp(0.5 + 0.1 * len(strengths) - 0.05 * len(red_flags), 0.35, 0.9)

        obj = AccountingAnalysis(
            subject_id=sid,
            accounting_quality_score=round(aq_score, 4),
            cash_flow_quality=round(cf_quality, 4),
            accrual_quality=round(accrual_quality, 4),
            earnings_quality=round(earnings_quality, 4),
            cash_conversion=round(cash_conversion, 4),
            red_flags=red_flags,
            notes=notes,
            evidence_links=list(p.get("evidence_links") or p.get("evidence_ids") or []),
            confidence=round(conf, 4),
            version=self.version,
        )

        summary = (
            f"Accounting quality {label.replace('_', ' ')} ({aq_score:.0%}). "
            + (notes[0] if notes else "Cash and accrual signals reviewed.")
        )
        return AnalysisResult(
            object_type="AccountingAnalysis",
            object_id=new_id("acc"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(aq_score, 4),
            label=label,
            confidence=round(conf, 4),
            summary=summary,
            outputs={"accounting": obj.to_dict(), "metrics": {
                "gross_margin": gross_margin,
                "ebit_margin": ebit_margin,
                "fcf_margin": fcf_margin,
                "nwc_days": nwc_days,
                "receivables_days": receivables_days,
                "inventory_days": inventory_days,
            }},
            red_flags=red_flags,
            strengths=strengths,
            weaknesses=weaknesses,
            evidence_links=obj.evidence_links,
            explainability={
                "why": summary,
                "components": {
                    "earnings_quality": earnings_quality,
                    "cash_flow_quality": cf_quality,
                    "accrual_quality": accrual_quality,
                },
                "concepts": [
                    "revenue_recognition",
                    "gross_margin",
                    "operating_leverage",
                    "free_cash_flow",
                    "working_capital",
                    "cash_conversion",
                    "accrual_quality",
                    "earnings_quality",
                ],
            },
        )
