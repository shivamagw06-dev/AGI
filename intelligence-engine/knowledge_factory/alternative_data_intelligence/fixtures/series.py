"""Curated Phase-1 historical observation seeds.

These are institutional Knowledge Factory seeds for pipeline / replay / trend
validation. Values are deterministic public-series-style indexes derived only
for seed coverage — provenance marks them as curated seeds from authoritative
provider categories. Live ingestion can replace series without redesign.

Never interpolate beyond the seeded points. Never claim live scrape here.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

from knowledge_factory.alternative_data_intelligence.objects.observation import (
    build_observation,
)
from knowledge_factory.alternative_data_intelligence.registry.catalog import DATASET_REGISTRY

# Monthly points: 2019-01 .. 2024-12 (72 observations per dataset)
_START_YEAR = 2019
_END_YEAR = 2024


def _months() -> list[str]:
    out = []
    for y in range(_START_YEAR, _END_YEAR + 1):
        for m in range(1, 13):
            out.append(f"{y}-{m:02d}-01")
    return out


def _base_path(dataset_id: str, i: int, n: int) -> float:
    """Deterministic seed path — directionally plausible, not a live print."""
    t = i / max(n - 1, 1)
    # mild growth + seasonal sinusoid + dataset-specific offset
    h = int(hashlib.sha256(dataset_id.encode()).hexdigest()[:6], 16)
    offset = 80 + (h % 40)
    growth = 20 * t
    seasonal = 5 * math.sin(2 * math.pi * (i % 12) / 12.0)
    # COVID soft dip around index ~14-20 (Mar-Sep 2020)
    covid = -12.0 if 14 <= i <= 20 else 0.0
    # 2021 recovery bump
    recovery = 4.0 if 24 <= i <= 36 else 0.0
    return round(offset + growth + seasonal + covid + recovery, 2)


# Dataset-specific value semantics for seeds
_VALUE_KIND = {
    "upi_transactions": "volume_index",
    "electricity_demand": "demand_index",
    "iip_manufacturing": "iip_index",
    "railway_freight": "freight_index",
    "port_cargo": "cargo_index",
    "vehicle_registrations": "registration_index",
    "air_passengers_domestic": "passenger_index",
    "bank_credit_growth": "yoy_growth_proxy",
    "rainfall_monsoon": "percent_of_lpa_proxy",
    "gst_collections": "collections_index",
}


def curated_observation_series() -> list[dict[str, Any]]:
    months = _months()
    n = len(months)
    out: list[dict[str, Any]] = []
    for dataset_id, meta in DATASET_REGISTRY.items():
        provider = str(meta.get("provider") or "government_open_data")
        source = str(meta.get("source_priority") or "government_open_data")
        conf = float(meta.get("confidence") or 0.85)
        for i, date in enumerate(months):
            value = _base_path(dataset_id, i, n)
            # Rainfall: center around 100% LPA with monsoon season peaks
            if dataset_id == "rainfall_monsoon":
                mon = int(date[5:7])
                if mon in (6, 7, 8, 9):
                    value = round(90 + 20 * math.sin((mon - 6) * math.pi / 3) + (i % 5), 2)
                else:
                    value = round(40 + (i % 7), 2)
            # Bank credit: yoy-like range
            if dataset_id == "bank_credit_growth":
                value = round(8 + 6 * math.sin(i / 8.0) + i * 0.02, 2)

            # available_from = publication lag ~1 month after period start
            y, m = int(date[:4]), int(date[5:7])
            if m == 12:
                available_from = f"{y + 1}-01-15"
            else:
                available_from = f"{y}-{m + 1:02d}-15"

            out.append(
                build_observation(
                    dataset_id=dataset_id,
                    date=date,
                    value=value,
                    unit=str(meta.get("unit") or "index"),
                    value_kind=_VALUE_KIND.get(dataset_id, "index"),
                    available_from=available_from,
                    source=source,
                    collector="iadi.fixtures.phase1_series",
                    confidence=conf,
                    evidence=f"{provider}:curated_public_series_seed:{dataset_id}:{date}",
                    notes="Curated institutional seed observation for Phase-1 IADI — not a live scrape.",
                    provider=provider,
                )
            )
    return out
