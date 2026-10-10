"""VE store — immutable valuation append log; soft-delete only; never overwrite."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ve.models import ValuationObject


@dataclass
class VeMetrics:
    valuations_created: int = 0
    recalculations: int = 0
    companies_covered: int = 0
    avg_confidence: float = 0.0
    avg_mos_pct: float = 0.0
    undervalued_count: int = 0
    overvalued_count: int = 0
    bus_triggered: int = 0
    last_latency_ms: float = 0.0

    _conf_sum: float = field(default=0.0, repr=False)
    _mos_sum: float = field(default=0.0, repr=False)

    def observe(self, obj: ValuationObject, *, recalc: bool = False, latency_ms: float = 0.0) -> None:
        if recalc:
            self.recalculations += 1
        self.last_latency_ms = latency_ms
        self._conf_sum += float(obj.confidence or 0)
        mos = float((obj.margin_of_safety.discount_premium_pct if obj.margin_of_safety else 0) or 0)
        self._mos_sum += mos
        if obj.margin_of_safety:
            if obj.margin_of_safety.undervalued:
                self.undervalued_count += 1
            else:
                self.overvalued_count += 1

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        n = max(1, self.valuations_created)
        return {
            "valuations_created": self.valuations_created,
            "recalculations": self.recalculations,
            "companies_covered": self.companies_covered,
            "avg_confidence": round(self._conf_sum / n, 4),
            "avg_mos_pct": round(self._mos_sum / n, 2),
            "undervalued_count": self.undervalued_count,
            "overvalued_count": self.overvalued_count,
            "bus_triggered": self.bus_triggered,
            "last_latency_ms": self.last_latency_ms,
        }


class VeStore:
    def __init__(self) -> None:
        self.valuations: dict[str, ValuationObject] = {}
        self.version_order: list[str] = []
        self.latest_by_company: dict[str, str] = {}  # company_id -> valuation_id
        self.audit: list[dict[str, Any]] = []
        self.metrics = VeMetrics()

    def add(self, obj: ValuationObject, *, recalc: bool = False, latency_ms: float = 0.0) -> ValuationObject:
        if obj.valuation_id in self.valuations:
            return self.valuations[obj.valuation_id]
        # Supersede previous latest for company
        prev_id = self.latest_by_company.get(obj.company_id)
        if prev_id and prev_id in self.valuations:
            prev = self.valuations[prev_id]
            prev.superseded = True
        self.valuations[obj.valuation_id] = obj
        self.version_order.append(obj.valuation_id)
        self.latest_by_company[obj.company_id] = obj.valuation_id
        self.metrics.valuations_created = len(self.valuations)
        self.metrics.companies_covered = len(self.latest_by_company)
        self.metrics.observe(obj, recalc=recalc, latency_ms=latency_ms)
        self.audit.append(
            {
                "action": "add_valuation",
                "valuation_id": obj.valuation_id,
                "company_id": obj.company_id,
                "version": obj.version,
                "trigger": obj.trigger,
            }
        )
        self.audit = self.audit[-500:]
        return obj

    def get(self, valuation_id: str) -> ValuationObject | None:
        return self.valuations.get(valuation_id)

    def latest(self, company_id: str) -> ValuationObject | None:
        vid = self.latest_by_company.get(company_id)
        if vid:
            return self.valuations.get(vid)
        # fallback by symbol match
        for cid, vidd in self.latest_by_company.items():
            obj = self.valuations.get(vidd)
            if obj and (obj.company_symbol == company_id.upper() or obj.company_id == company_id):
                return obj
        return None

    def history_for_company(self, company_id: str) -> list[ValuationObject]:
        rows = [
            v
            for v in self.valuations.values()
            if v.company_id == company_id or v.company_symbol == company_id.upper()
        ]
        rows.sort(key=lambda v: (v.created_at, v.version))
        return rows

    def active_valuations(self) -> list[ValuationObject]:
        return [
            self.valuations[vid]
            for vid in self.latest_by_company.values()
            if vid in self.valuations and not self.valuations[vid].soft_deleted
        ]

    def snapshot(self) -> dict[str, Any]:
        return {
            "valuations": len(self.valuations),
            "companies": len(self.latest_by_company),
            "audit": len(self.audit),
        }
