"""Universe membership features (WBS FEAT-002)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.models import FeatureMetadata, FeatureValue


class UniverseMembershipCalculator(FeatureCalculator):
    def __init__(self, universe_id: str) -> None:
        self.universe_id = universe_id
        self.metadata = FeatureMetadata(
            feature_id=f"UNIV_MEMBER_{universe_id}",
            category="UNIV_",
            description=f"1 if symbol is a member of {universe_id} as-of, else 0",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["universe.membership"],
            refresh_frequency="1d",
            source="feature_registry",
        )

    def compute(
        self,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        available_at: datetime,
        ctx: FeatureContext,
        dep_values: dict[str, FeatureValue],
    ) -> FeatureValue:
        membership = ctx.get("universe_membership") or {}
        members = set(membership.get(self.universe_id) or [])
        is_member = bool(symbol and symbol.upper() in {m.upper() for m in members})
        return FeatureValue(
            feature_id=self.metadata.feature_id,
            formula_version=self.metadata.formula_version,
            symbol=symbol,
            as_of=as_of,
            available_at=available_at,
            value=1 if is_member else 0,
            confidence=1.0,
            quality_flag="ok",
            source=self.metadata.source,
            metadata={"universe_id": self.universe_id},
        )


def register_universe_calculators(service: Any) -> None:
    service.register_calculator(UniverseMembershipCalculator("NIFTY500"))
    service.register_calculator(UniverseMembershipCalculator("NIFTY50"))
