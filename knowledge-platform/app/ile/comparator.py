"""Step 1 — Compare new knowledge object against previous version."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts.models import KnowledgeObject, KnowledgeObjectType


@dataclass
class FieldChange:
    field_name: str
    previous_value: Any
    new_value: Any
    path: str
    kind: str = "numeric"  # numeric | categorical | structural


@dataclass
class ComparisonResult:
    object_type: KnowledgeObjectType
    subject_key: str
    company_symbol: str | None
    is_first_version: bool
    changes: list[FieldChange] = field(default_factory=list)


TRACKED_NUMERIC_PATHS: dict[KnowledgeObjectType, list[tuple[str, tuple[str, ...]]]] = {
    KnowledgeObjectType.COMPANY_PROFILE: [
        ("pe", ("valuation", "pe")),
        ("pb", ("valuation", "pb")),
        ("market_cap", ("valuation", "market_cap")),
        ("revenue_growth", ("growth", "revenue_growth_pct")),
        ("earnings_growth", ("growth", "earnings_growth_pct")),
    ],
    KnowledgeObjectType.MARKET_SNAPSHOT: [
        ("price", ("price",)),
        ("pe_ratio", ("pe_ratio",)),
        ("market_cap", ("market_cap",)),
        ("volume", ("volume",)),
        ("daily_move_pct", ("daily_move_pct",)),
    ],
    KnowledgeObjectType.FINANCIAL_STATEMENT: [
        ("revenue_growth", ("revenue_growth_pct",)),
        ("earnings_growth", ("earnings_growth_pct",)),
        ("revenue", ("revenue",)),
        ("ebitda", ("ebitda",)),
        ("pat", ("pat",)),
        ("eps", ("eps",)),
        ("cash", ("cash",)),
        ("debt", ("debt",)),
        ("pat_margin", ("margins", "pat_margin_pct")),
        ("ebitda_margin", ("margins", "ebitda_margin_pct")),
    ],
    KnowledgeObjectType.OWNERSHIP: [
        ("promoters_pct", ("promoters_pct",)),
        ("fii_pct", ("fii_pct",)),
        ("dii_pct", ("dii_pct",)),
        ("mutual_funds_pct", ("mutual_funds_pct",)),
    ],
    KnowledgeObjectType.ANALYST_CONSENSUS: [
        ("target_price", ("target_price",)),
    ],
}

TRACKED_CATEGORICAL: dict[KnowledgeObjectType, list[tuple[str, tuple[str, ...]]]] = {
    KnowledgeObjectType.COMPANY_PROFILE: [
        ("sector", ("business", "sector")),
        ("industry", ("business", "industry")),
        ("company", ("company",)),
    ],
    KnowledgeObjectType.CORPORATE_ACTION: [
        ("action_type", ("action_type",)),
        ("ex_date", ("ex_date",)),
    ],
    KnowledgeObjectType.CORPORATE_EVENT: [
        ("event_type", ("event_type",)),
        ("event_title", ("event_title",)),
        ("category", ("category",)),
    ],
    KnowledgeObjectType.NEWS_EVENT: [
        ("headline", ("headline",)),
        ("importance", ("importance",)),
    ],
    KnowledgeObjectType.ANALYST_CONSENSUS: [
        ("recommendation", ("recommendation",)),
    ],
}


def _get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_pct_if_ratio(field_name: str, value: Any) -> Any:
    """Normalize growth ratios stored as 0.18 alongside percent 18."""
    if value is None:
        return None
    if field_name in {"revenue_growth", "earnings_growth", "pat_margin", "ebitda_margin"}:
        try:
            n = float(value)
        except (TypeError, ValueError):
            return value
        if abs(n) <= 1.5:
            return round(n * 100.0, 6)
        return n
    return value


class KnowledgeComparator:
    def compare(self, current: KnowledgeObject, previous: KnowledgeObject | None) -> ComparisonResult:
        cur = current.knowledge or current.payload
        result = ComparisonResult(
            object_type=current.object_type,
            subject_key=current.subject_key,
            company_symbol=current.company_symbol,
            is_first_version=previous is None,
        )
        if previous is None:
            if current.object_type in {
                KnowledgeObjectType.CORPORATE_ACTION,
                KnowledgeObjectType.CORPORATE_EVENT,
                KnowledgeObjectType.NEWS_EVENT,
            }:
                result.changes.append(
                    FieldChange(
                        field_name="object_created",
                        previous_value=None,
                        new_value=current.object_type.value,
                        path="object_created",
                        kind="categorical",
                    )
                )
            return result

        prev = previous.knowledge or previous.payload
        for field_name, path in TRACKED_NUMERIC_PATHS.get(current.object_type, []):
            pv = _as_pct_if_ratio(field_name, _get(prev, path))
            # also allow flat fallback
            if pv is None and len(path) == 1:
                pv = _as_pct_if_ratio(field_name, prev.get(path[0]))
            cv = _as_pct_if_ratio(field_name, _get(cur, path))
            if cv is None and len(path) == 1:
                cv = _as_pct_if_ratio(field_name, cur.get(path[0]))
            # financial statement may still store ratio on revenue_growth key
            if field_name == "revenue_growth" and pv is None:
                pv = _as_pct_if_ratio(field_name, prev.get("revenue_growth"))
            if field_name == "revenue_growth" and cv is None:
                cv = _as_pct_if_ratio(field_name, cur.get("revenue_growth"))
            if pv is None or cv is None:
                continue
            try:
                if float(pv) == float(cv):
                    continue
            except (TypeError, ValueError):
                if pv == cv:
                    continue
            result.changes.append(
                FieldChange(
                    field_name=field_name,
                    previous_value=pv,
                    new_value=cv,
                    path=".".join(path),
                    kind="numeric",
                )
            )

        for field_name, path in TRACKED_CATEGORICAL.get(current.object_type, []):
            pv = _get(prev, path)
            cv = _get(cur, path)
            if pv is None and cv is None:
                continue
            if pv == cv:
                continue
            if pv is None or cv is None:
                continue
            result.changes.append(
                FieldChange(
                    field_name=field_name,
                    previous_value=pv,
                    new_value=cv,
                    path=".".join(path),
                    kind="categorical",
                )
            )
        return result
