"""MACRO_ feature calculators (WBS FEAT-004)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.models import FeatureMetadata, FeatureValue


class _MacroScalar(FeatureCalculator):
    def __init__(self, meta: FeatureMetadata, fn) -> None:
        self.metadata = meta
        self._fn = fn

    def compute(
        self,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        available_at: datetime,
        ctx: FeatureContext,
        dep_values: dict[str, FeatureValue],
    ) -> FeatureValue:
        value, quality = self._fn(ctx)
        return FeatureValue(
            feature_id=self.metadata.feature_id,
            formula_version=self.metadata.formula_version,
            symbol=None,
            as_of=as_of,
            available_at=available_at,
            value=value,
            confidence=self.metadata.confidence if value is not None else 0.0,
            quality_flag=quality,
            source=self.metadata.source,
        )


def register_macro_calculators(service: Any) -> None:
    def yield_curve(ctx: FeatureContext):
        # Expect ctx["macro"] = {"US10Y": x, "US2Y": y}
        macro = ctx.get("macro") or {}
        ten = macro.get("US10Y")
        two = macro.get("US2Y")
        if ten is None or two is None:
            return None, "missing"
        return float(ten) - float(two), "ok"

    def dollar_strength(ctx: FeatureContext):
        macro = ctx.get("macro") or {}
        dxy = macro.get("DXY")
        if dxy is None:
            return None, "missing"
        # Momentum proxy vs prior if provided
        prev = macro.get("DXY_PREV")
        if prev is None:
            return float(dxy), "partial"
        if float(prev) == 0:
            return None, "error"
        return (float(dxy) / float(prev) - 1.0) * 100.0, "ok"

    def oil_momentum(ctx: FeatureContext):
        macro = ctx.get("macro") or {}
        oil = macro.get("BRENT")
        oil_prev = macro.get("BRENT_PREV")
        if oil is None or oil_prev is None or float(oil_prev) == 0:
            return None, "missing"
        return (float(oil) / float(oil_prev) - 1.0) * 100.0, "ok"

    service.register_calculator(
        _MacroScalar(
            FeatureMetadata(
                feature_id="MACRO_YIELD_CURVE_10Y2Y",
                category="MACRO_",
                description="US 10Y-2Y yield curve slope",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=[],
                inputs=["macro.US10Y", "macro.US2Y"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            yield_curve,
        )
    )
    service.register_calculator(
        _MacroScalar(
            FeatureMetadata(
                feature_id="MACRO_DOLLAR_STRENGTH",
                category="MACRO_",
                description="DXY level or % change vs prior",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=[],
                inputs=["macro.DXY", "macro.DXY_PREV"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            dollar_strength,
        )
    )
    service.register_calculator(
        _MacroScalar(
            FeatureMetadata(
                feature_id="MACRO_OIL_MOMENTUM",
                category="MACRO_",
                description="Brent % change vs prior print",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=[],
                inputs=["macro.BRENT", "macro.BRENT_PREV"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            oil_momentum,
        )
    )
