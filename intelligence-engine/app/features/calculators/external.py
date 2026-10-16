"""Category stubs for externally materialized features (OPTIONS_/SENT_/EVENT_/RVAL_).

No research logic. Calculators are registered later or values are ingested into the
Feature Store; engines still consume only Feature Registry outputs.
"""

from __future__ import annotations

from typing import Any

from app.features.models import FeatureMetadata


def register_external_category_stubs(service: Any) -> None:
    stubs = [
        FeatureMetadata(
            feature_id="OPTIONS_IV_RANK",
            category="OPTIONS_",
            description="Implied volatility rank (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["options.iv_history"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="OPTIONS_PCR",
            category="OPTIONS_",
            description="Put/call ratio (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["options.volume"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="OPTIONS_GAMMA_EXPOSURE",
            category="OPTIONS_",
            description="Aggregate gamma exposure (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["options.greeks"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="SENT_NEWS",
            category="SENT_",
            description="News sentiment score (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["alt.news"],
            refresh_frequency="1h",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="SENT_OWNERSHIP_TREND",
            category="SENT_",
            description="Institutional ownership trend (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["alt.ownership"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="EVENT_EPS_SURPRISE",
            category="EVENT_",
            description="EPS surprise vs consensus (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["fundamentals.eps", "fundamentals.consensus"],
            refresh_frequency="event",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="EVENT_GUIDANCE_DELTA",
            category="EVENT_",
            description="Guidance delta vs prior (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["fundamentals.guidance"],
            refresh_frequency="event",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="RVAL_SPREAD",
            category="RVAL_",
            description="Relative-value spread (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close", "pair.benchmark"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="RVAL_COINTEGRATION",
            category="RVAL_",
            description="Pair cointegration statistic (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=[],
            inputs=["ohlcv.close", "pair.benchmark"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
        FeatureMetadata(
            feature_id="RVAL_HALF_LIFE",
            category="RVAL_",
            description="Mean-reversion half-life (external/materialized)",
            owner="feature-registry",
            formula_version="1.0.0",
            dependencies=["RVAL_SPREAD"],
            inputs=["ohlcv.close"],
            refresh_frequency="1d",
            source="external",
            confidence=0.0,
        ),
    ]
    for meta in stubs:
        service.register_metadata(meta)
