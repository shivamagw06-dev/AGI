"""Change detection — material deltas become institutional Learning Events."""

from __future__ import annotations

from typing import Any

from app.config.settings import Settings
from app.contracts.models import (
    Importance,
    KnowledgeObject,
    KnowledgeObjectType,
    LearningCategory,
    LearningEvent,
)
from app.storage.db import KaipStore


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


class ChangeDetector:
    def __init__(self, store: KaipStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def detect(self, ko: KnowledgeObject, previous: KnowledgeObject | None) -> list[LearningEvent]:
        cur = ko.knowledge or ko.payload
        if previous is None:
            if ko.object_type in {
                KnowledgeObjectType.CORPORATE_ACTION,
                KnowledgeObjectType.CORPORATE_EVENT,
                KnowledgeObjectType.NEWS_EVENT,
            }:
                return [
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.CORPORATE
                        if ko.object_type != KnowledgeObjectType.NEWS_EVENT
                        else LearningCategory.NEWS,
                        importance=Importance.MEDIUM,
                        field_name="object_created",
                        previous_value=None,
                        new_value=ko.object_type.value,
                        delta=1,
                        reason=f"New {ko.object_type.value} observed",
                        affected=["Company", "Corporate"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                ]
            return []

        prev = previous.knowledge or previous.payload
        events: list[LearningEvent] = []

        if ko.object_type == KnowledgeObjectType.MARKET_SNAPSHOT:
            events.extend(self._market_changes(ko, prev, cur))
        elif ko.object_type == KnowledgeObjectType.FINANCIAL_STATEMENT:
            events.extend(self._financial_changes(ko, prev, cur))
        elif ko.object_type == KnowledgeObjectType.COMPANY_PROFILE:
            events.extend(self._profile_changes(ko, prev, cur))
        elif ko.object_type == KnowledgeObjectType.CORPORATE_ACTION:
            if prev.get("action_type") != cur.get("action_type") or prev.get("ex_date") != cur.get("ex_date"):
                events.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.CORPORATE,
                        importance=Importance.HIGH,
                        field_name="corporate_action",
                        previous_value=prev.get("action_type"),
                        new_value=cur.get("action_type"),
                        reason="Corporate action changed",
                        affected=["Company", "Ownership", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )
        elif ko.object_type == KnowledgeObjectType.OWNERSHIP:
            for field in ("promoters_pct", "fii_pct", "dii_pct", "mutual_funds_pct"):
                if prev.get(field) != cur.get(field) and cur.get(field) is not None:
                    events.append(
                        LearningEvent(
                            company_symbol=ko.company_symbol,
                            category=LearningCategory.OWNERSHIP,
                            importance=Importance.MEDIUM,
                            field_name=field,
                            previous_value=prev.get(field),
                            new_value=cur.get(field),
                            reason=f"{field} changed",
                            affected=["Company", "Ownership"],
                            object_type=ko.object_type,
                            object_id=ko.object_id,
                            source_event_ids=list(ko.source_event_ids),
                        )
                    )
        return events

    def _profile_changes(
        self, ko: KnowledgeObject, prev: dict[str, Any], cur: dict[str, Any]
    ) -> list[LearningEvent]:
        out: list[LearningEvent] = []
        prev_sector = _nested(prev, "business", "sector") or prev.get("sector")
        cur_sector = _nested(cur, "business", "sector") or cur.get("sector")
        prev_industry = _nested(prev, "business", "industry") or prev.get("industry")
        cur_industry = _nested(cur, "business", "industry") or cur.get("industry")
        if prev_sector and cur_sector and prev_sector != cur_sector:
            out.append(
                LearningEvent(
                    company_symbol=ko.company_symbol,
                    category=LearningCategory.BUSINESS,
                    importance=Importance.HIGH,
                    field_name="sector",
                    previous_value=prev_sector,
                    new_value=cur_sector,
                    reason="Sector classification changed",
                    affected=["Company", "Sector"],
                    object_type=ko.object_type,
                    object_id=ko.object_id,
                    source_event_ids=list(ko.source_event_ids),
                )
            )
        if prev_industry and cur_industry and prev_industry != cur_industry:
            out.append(
                LearningEvent(
                    company_symbol=ko.company_symbol,
                    category=LearningCategory.BUSINESS,
                    importance=Importance.MEDIUM,
                    field_name="industry",
                    previous_value=prev_industry,
                    new_value=cur_industry,
                    reason="Industry classification changed",
                    affected=["Company", "Sector"],
                    object_type=ko.object_type,
                    object_id=ko.object_id,
                    source_event_ids=list(ko.source_event_ids),
                )
            )

        # Valuation / growth embedded on company knowledge
        prev_pe = _num(_nested(prev, "valuation", "pe") or prev.get("pe_ratio"))
        cur_pe = _num(_nested(cur, "valuation", "pe") or cur.get("pe_ratio"))
        if prev_pe is not None and cur_pe is not None:
            delta = abs(cur_pe - prev_pe)
            if delta >= self.settings.pe_material_abs:
                out.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.VALUATION,
                        importance=Importance.MEDIUM,
                        field_name="pe",
                        previous_value=prev_pe,
                        new_value=cur_pe,
                        delta=round(cur_pe - prev_pe, 6),
                        reason=f"PE moved by {delta:.2f}",
                        affected=["Company", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )

        prev_g = _num(_nested(prev, "growth", "revenue_growth_pct"))
        cur_g = _num(_nested(cur, "growth", "revenue_growth_pct"))
        if prev_g is not None and cur_g is not None:
            delta_pp = abs(cur_g - prev_g)
            if delta_pp >= self.settings.revenue_growth_material_pp:
                direction = "accelerated" if cur_g > prev_g else "decelerated"
                out.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.FINANCIAL,
                        importance=Importance.HIGH,
                        field_name="revenue_growth",
                        previous_value=prev_g,
                        new_value=cur_g,
                        delta=round(cur_g - prev_g, 4),
                        reason=f"Revenue growth {direction}",
                        affected=["Company", "Sector", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )
        return out

    def _market_changes(
        self, ko: KnowledgeObject, prev: dict[str, Any], cur: dict[str, Any]
    ) -> list[LearningEvent]:
        out: list[LearningEvent] = []
        prev_pe = _num(prev.get("pe_ratio") or _nested(prev, "valuation", "pe"))
        cur_pe = _num(cur.get("pe_ratio") or _nested(cur, "valuation", "pe"))
        if prev_pe is not None and cur_pe is not None:
            delta = abs(cur_pe - prev_pe)
            if delta >= self.settings.pe_material_abs:
                out.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.VALUATION,
                        importance=Importance.MEDIUM,
                        field_name="pe_ratio",
                        previous_value=prev_pe,
                        new_value=cur_pe,
                        delta=round(cur_pe - prev_pe, 6),
                        reason=f"PE moved by {delta:.2f}",
                        affected=["Company", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )

        prev_px = _num(prev.get("price") or prev.get("last_price"))
        cur_px = _num(cur.get("price") or cur.get("last_price"))
        if prev_px and cur_px and prev_px != 0:
            pct = abs((cur_px - prev_px) / prev_px) * 100.0
            if pct >= self.settings.price_material_pct:
                out.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.MARKET,
                        importance=Importance.HIGH if pct >= 5 else Importance.MEDIUM,
                        field_name="price",
                        previous_value=prev_px,
                        new_value=cur_px,
                        delta=round(pct, 4),
                        reason=f"Price moved {pct:.2f}%",
                        affected=["Company", "Market", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )
        return out

    def _financial_changes(
        self, ko: KnowledgeObject, prev: dict[str, Any], cur: dict[str, Any]
    ) -> list[LearningEvent]:
        out: list[LearningEvent] = []

        def as_pct(v: float | None) -> float | None:
            if v is None:
                return None
            return v * 100.0 if abs(v) <= 1.5 else v

        prev_g = as_pct(_num(prev.get("revenue_growth_pct") if prev.get("revenue_growth_pct") is not None else prev.get("revenue_growth")))
        cur_g = as_pct(_num(cur.get("revenue_growth_pct") if cur.get("revenue_growth_pct") is not None else cur.get("revenue_growth")))
        if prev_g is not None and cur_g is not None:
            delta_pp = abs(cur_g - prev_g)
            if delta_pp >= self.settings.revenue_growth_material_pp:
                direction = "accelerated" if cur_g > prev_g else "decelerated"
                out.append(
                    LearningEvent(
                        company_symbol=ko.company_symbol,
                        category=LearningCategory.FINANCIAL,
                        importance=Importance.HIGH,
                        field_name="revenue_growth",
                        previous_value=prev_g,
                        new_value=cur_g,
                        delta=round(cur_g - prev_g, 4),
                        reason=f"Revenue growth {direction}",
                        affected=["Company", "Sector", "Valuation"],
                        object_type=ko.object_type,
                        object_id=ko.object_id,
                        source_event_ids=list(ko.source_event_ids),
                    )
                )
        return out
