"""TECH_ feature calculators (WBS FEAT-003)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.calculators.tech_math import (
    adx_wilder,
    atr_wilder,
    ema,
    roc,
    rsi_wilder,
    sma,
    stdev,
)
from app.features.models import FeatureMetadata, FeatureValue


def _closes(ctx: FeatureContext) -> list[float]:
    bars = ctx.get("bars") or []
    return [float(b["close"]) for b in bars]


def _series(ctx: FeatureContext) -> tuple[list[float], list[float], list[float], list[float]]:
    bars = ctx.get("bars") or []
    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    volumes = [float(b.get("volume") or 0.0) for b in bars]
    return closes, highs, lows, volumes


class _LastOfSeries(FeatureCalculator):
    def __init__(self, meta: FeatureMetadata, compute_series) -> None:
        self.metadata = meta
        self._compute_series = compute_series

    def compute(
        self,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        available_at: datetime,
        ctx: FeatureContext,
        dep_values: dict[str, FeatureValue],
    ) -> FeatureValue:
        series = self._compute_series(ctx, dep_values)
        value = None
        quality = "missing"
        for item in reversed(series):
            if item is not None:
                value = float(item)
                quality = "ok"
                break
        if value is None and (ctx.get("bars") or []):
            quality = "partial"
        return FeatureValue(
            feature_id=self.metadata.feature_id,
            formula_version=self.metadata.formula_version,
            symbol=symbol,
            as_of=as_of,
            available_at=available_at,
            value=value,
            confidence=self.metadata.confidence if value is not None else 0.0,
            quality_flag=quality,  # type: ignore[arg-type]
            source=self.metadata.source,
        )


def register_tech_calculators(service: Any) -> None:
    def add(meta: FeatureMetadata, fn) -> None:
        service.register_calculator(_LastOfSeries(meta, fn))

    add(
        FeatureMetadata(
            feature_id="TECH_EMA_12",
            category="TECH_",
            description="12-period EMA of close",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        lambda ctx, deps: ema(_closes(ctx), 12),
    )
    add(
        FeatureMetadata(
            feature_id="TECH_EMA_20",
            category="TECH_",
            description="20-period EMA of close",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        lambda ctx, deps: ema(_closes(ctx), 20),
    )
    add(
        FeatureMetadata(
            feature_id="TECH_EMA_26",
            category="TECH_",
            description="26-period EMA of close",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        lambda ctx, deps: ema(_closes(ctx), 26),
    )

    def macd_line(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        # Prefer dependency values when present (no duplicate EMA calc in graph consumers),
        # but compute from closes for series alignment in batch.
        e12 = ema(_closes(ctx), 12)
        e26 = ema(_closes(ctx), 26)
        out: list[float | None] = []
        for a, b in zip(e12, e26):
            out.append(None if a is None or b is None else a - b)
        return out

    add(
        FeatureMetadata(
            feature_id="TECH_MACD",
            category="TECH_",
            description="MACD line (EMA12 - EMA26)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=["TECH_EMA_12", "TECH_EMA_26"],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        macd_line,
    )

    add(
        FeatureMetadata(
            feature_id="TECH_RSI_14",
            category="TECH_",
            description="Wilder RSI(14)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        lambda ctx, deps: rsi_wilder(_closes(ctx), 14),
    )

    def atr14(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        c, h, l, _ = _series(ctx)
        return atr_wilder(h, l, c, 14)

    add(
        FeatureMetadata(
            feature_id="TECH_ATR_14",
            category="TECH_",
            description="Wilder ATR(14)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.high", "ohlcv.low", "ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        atr14,
    )

    def adx14(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        c, h, l, _ = _series(ctx)
        return adx_wilder(h, l, c, 14)

    add(
        FeatureMetadata(
            feature_id="TECH_ADX_14",
            category="TECH_",
            description="Wilder ADX(14)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=["TECH_ATR_14"],
            inputs=["ohlcv.high", "ohlcv.low", "ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        adx14,
    )

    add(
        FeatureMetadata(
            feature_id="TECH_ROC_10",
            category="TECH_",
            description="Rate of change 10 periods (%)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        lambda ctx, deps: roc(_closes(ctx), 10),
    )

    def bb_upper(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        closes = _closes(ctx)
        m = sma(closes, 20)
        s = stdev(closes, 20)
        return [None if a is None or b is None else a + 2 * b for a, b in zip(m, s)]

    def bb_lower(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        closes = _closes(ctx)
        m = sma(closes, 20)
        s = stdev(closes, 20)
        return [None if a is None or b is None else a - 2 * b for a, b in zip(m, s)]

    add(
        FeatureMetadata(
            feature_id="TECH_BBANDS_UPPER_20",
            category="TECH_",
            description="Bollinger upper band (20, 2)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        bb_upper,
    )
    add(
        FeatureMetadata(
            feature_id="TECH_BBANDS_LOWER_20",
            category="TECH_",
            description="Bollinger lower band (20, 2)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        bb_lower,
    )

    def vwap(ctx: FeatureContext, deps: dict[str, FeatureValue]) -> list[float | None]:
        bars = ctx.get("bars") or []
        out: list[float | None] = []
        cum_pv = 0.0
        cum_v = 0.0
        for b in bars:
            tp = (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3.0
            vol = float(b.get("volume") or 0.0)
            cum_pv += tp * vol
            cum_v += vol
            out.append(None if cum_v == 0 else cum_pv / cum_v)
        return out

    add(
        FeatureMetadata(
            feature_id="TECH_VWAP",
            category="TECH_",
            description="Cumulative VWAP from bar typical price",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.high", "ohlcv.low", "ohlcv.close", "ohlcv.volume"],
            refresh_frequency="1d",
            source="feature_registry",
        ),
        vwap,
    )
