"""VOL_ feature calculators."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.calculators.tech_math import atr_wilder, realized_vol
from app.features.models import FeatureMetadata, FeatureValue


class _LastSeries(FeatureCalculator):
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
        series = self._fn(ctx)
        value = next((float(x) for x in reversed(series) if x is not None), None)
        return FeatureValue(
            feature_id=self.metadata.feature_id,
            formula_version=self.metadata.formula_version,
            symbol=symbol,
            as_of=as_of,
            available_at=available_at,
            value=value,
            confidence=self.metadata.confidence if value is not None else 0.0,
            quality_flag="ok" if value is not None else "missing",
            source=self.metadata.source,
        )


def register_vol_calculators(service: Any) -> None:
    def closes(ctx: FeatureContext) -> list[float]:
        return [float(b["close"]) for b in (ctx.get("bars") or [])]

    service.register_calculator(
        _LastSeries(
            FeatureMetadata(
                feature_id="VOL_REALIZED_20",
                category="VOL_",
                description="Annualized realized volatility (20d log returns)",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=[],
                inputs=["ohlcv.close"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            lambda ctx: realized_vol(closes(ctx), 20),
        )
    )

    service.register_calculator(
        _LastSeries(
            FeatureMetadata(
                feature_id="VOL_HIST_60",
                category="VOL_",
                description="Annualized historical volatility (60d log returns)",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=[],
                inputs=["ohlcv.close"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            lambda ctx: realized_vol(closes(ctx), 60),
        )
    )

    def atr(ctx: FeatureContext) -> list[float | None]:
        bars = ctx.get("bars") or []
        h = [float(b["high"]) for b in bars]
        l = [float(b["low"]) for b in bars]
        c = [float(b["close"]) for b in bars]
        return atr_wilder(h, l, c, 14)

    service.register_calculator(
        _LastSeries(
            FeatureMetadata(
                feature_id="VOL_ATR_14",
                category="VOL_",
                description="ATR(14) exposed under VOL_ category",
                owner="feature-registry",
                formula_version="1.0.0",
                dependencies=["TECH_ATR_14"],
                inputs=["ohlcv.high", "ohlcv.low", "ohlcv.close"],
                refresh_frequency="1d",
                source="feature_registry",
            ),
            atr,
        )
    )
