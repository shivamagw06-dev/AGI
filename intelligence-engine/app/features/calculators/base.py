"""Calculator protocol for Feature Registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any

from app.features.models import FeatureMetadata, FeatureValue


class FeatureContext(dict[str, Any]):
    """Inputs for a calculation: bars, quotes, deps, fundamentals, macro series."""


class FeatureCalculator(ABC):
    metadata: FeatureMetadata

    @abstractmethod
    def compute(
        self,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        available_at: datetime,
        ctx: FeatureContext,
        dep_values: dict[str, FeatureValue],
    ) -> FeatureValue:
        raise NotImplementedError
