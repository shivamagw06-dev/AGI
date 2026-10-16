"""Frozen benchmark universe v1 — permanent. Do not mutate entries; add v2 instead."""

from __future__ import annotations

from typing import Any

# Named anchors (real institutional coverage)
_NAMED: list[dict[str, Any]] = [
    # Banks (India)
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "region": "india", "bucket": "banks"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "region": "india", "bucket": "banks"},
    {"ticker": "SBIN", "name": "SBI", "region": "india", "bucket": "banks"},
    {"ticker": "AXISBANK", "name": "Axis Bank", "region": "india", "bucket": "banks"},
    {"ticker": "KOTAKBANK", "name": "Kotak Bank", "region": "india", "bucket": "banks"},
    # FMCG
    {"ticker": "NESTLEIND", "name": "Nestlé India", "region": "india", "bucket": "fmcg"},
    {"ticker": "HINDUNILVR", "name": "HUL", "region": "india", "bucket": "fmcg"},
    {"ticker": "ITC", "name": "ITC", "region": "india", "bucket": "fmcg"},
    {"ticker": "BRITANNIA", "name": "Britannia", "region": "india", "bucket": "fmcg"},
    {"ticker": "DABUR", "name": "Dabur", "region": "india", "bucket": "fmcg"},
    # IT
    {"ticker": "TCS", "name": "TCS", "region": "india", "bucket": "it"},
    {"ticker": "INFY", "name": "Infosys", "region": "india", "bucket": "it"},
    {"ticker": "TECHM", "name": "Tech Mahindra", "region": "india", "bucket": "it"},
    {"ticker": "WIPRO", "name": "Wipro", "region": "india", "bucket": "it"},
    {"ticker": "HCLTECH", "name": "HCL Tech", "region": "india", "bucket": "it"},
    # Industrials
    {"ticker": "LT", "name": "L&T", "region": "india", "bucket": "industrials"},
    {"ticker": "SIEMENS", "name": "Siemens", "region": "india", "bucket": "industrials"},
    {"ticker": "ULTRACEMCO", "name": "UltraTech", "region": "india", "bucket": "industrials"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "region": "india", "bucket": "industrials"},
    {"ticker": "ABB", "name": "ABB India", "region": "india", "bucket": "industrials"},
    # Consumer
    {"ticker": "MARUTI", "name": "Maruti", "region": "india", "bucket": "consumer"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors", "region": "india", "bucket": "consumer"},
    {"ticker": "ETERNAL", "name": "Eternal", "region": "india", "bucket": "consumer"},
    {"ticker": "NYKAA", "name": "Nykaa", "region": "india", "bucket": "consumer"},
    {"ticker": "TITAN", "name": "Titan", "region": "india", "bucket": "consumer"},
    # Global
    {"ticker": "AAPL", "name": "Apple", "region": "global", "bucket": "global"},
    {"ticker": "MSFT", "name": "Microsoft", "region": "global", "bucket": "global"},
    {"ticker": "AMZN", "name": "Amazon", "region": "global", "bucket": "global"},
    {"ticker": "GOOGL", "name": "Alphabet", "region": "global", "bucket": "global"},
    {"ticker": "META", "name": "Meta", "region": "global", "bucket": "global"},
    {"ticker": "NVDA", "name": "Nvidia", "region": "global", "bucket": "global"},
    {"ticker": "BRK.B", "name": "Berkshire", "region": "global", "bucket": "global"},
    {"ticker": "JPM", "name": "JPMorgan", "region": "global", "bucket": "global"},
    {"ticker": "COST", "name": "Costco", "region": "global", "bucket": "global"},
    {"ticker": "KO", "name": "Coca-Cola", "region": "global", "bucket": "global"},
    # Failures / special
    {"ticker": "NOKIA", "name": "Nokia", "region": "global", "bucket": "historical_failures"},
    {"ticker": "YESBANK", "name": "Yes Bank", "region": "india", "bucket": "historical_failures"},
    {"ticker": "WIRECARD", "name": "Wirecard", "region": "global", "bucket": "historical_failures"},
    {"ticker": "GE", "name": "GE", "region": "global", "bucket": "historical_failures"},
    {"ticker": "LEHMAN", "name": "Lehman", "region": "global", "bucket": "historical_failures"},
]

# Target counts from ACS/IRS spec
_TARGETS: dict[str, int] = {
    "banks": 20,
    "fmcg": 20,
    "it": 20,
    "industrials": 20,
    "consumer": 20,
    "global": 50,
    "historical_failures": 30,
    "turnarounds": 20,
    "cyclicals": 20,
    "platform": 20,
    "capital_allocators": 20,
    "high_roic_compounders": 20,
    "deep_value": 20,
    "utilities": 10,
    "healthcare": 10,
    "energy": 10,
}


def _pad(bucket: str, region: str, target: int, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [c for c in existing if c["bucket"] == bucket]
    i = 1
    while len(out) < target:
        out.append(
            {
                "ticker": f"{bucket[:4].upper()}{i:03d}",
                "name": f"{bucket.replace('_', ' ').title()} Benchmark {i}",
                "region": region,
                "bucket": bucket,
                "synthetic": True,
            }
        )
        i += 1
    return out[:target]


def build_universe() -> list[dict[str, Any]]:
    """Build permanent v1 universe with required bucket sizes."""
    by_bucket: dict[str, list[dict[str, Any]]] = {}
    for c in _NAMED:
        by_bucket.setdefault(c["bucket"], []).append(dict(c))

    region_for = {
        "banks": "india",
        "fmcg": "india",
        "it": "india",
        "industrials": "india",
        "consumer": "india",
        "global": "global",
        "historical_failures": "global",
        "turnarounds": "india",
        "cyclicals": "india",
        "platform": "global",
        "capital_allocators": "global",
        "high_roic_compounders": "india",
        "deep_value": "india",
        "utilities": "india",
        "healthcare": "india",
        "energy": "india",
    }
    universe: list[dict[str, Any]] = []
    for bucket, target in _TARGETS.items():
        region = region_for[bucket]
        universe.extend(_pad(bucket, region, target, by_bucket.get(bucket, [])))

    # India total should be >= 100 across india region buckets
    india = [c for c in universe if c["region"] == "india"]
    n = 1
    while len(india) < 100:
        extra = {
            "ticker": f"IND{n:03d}",
            "name": f"India Benchmark {n}",
            "region": "india",
            "bucket": "consumer",
            "synthetic": True,
        }
        universe.append(extra)
        india.append(extra)
        n += 1
    return universe


BENCHMARK_UNIVERSE: list[dict[str, Any]] = build_universe()


def universe_counts() -> dict[str, Any]:
    buckets: dict[str, int] = {}
    regions: dict[str, int] = {}
    for c in BENCHMARK_UNIVERSE:
        buckets[c["bucket"]] = buckets.get(c["bucket"], 0) + 1
        regions[c["region"]] = regions.get(c["region"], 0) + 1
    return {
        "total": len(BENCHMARK_UNIVERSE),
        "buckets": buckets,
        "regions": regions,
        "targets_met": all(buckets.get(k, 0) >= v for k, v in _TARGETS.items()),
        "india_ge_100": regions.get("india", 0) >= 100,
        "global_ge_50": buckets.get("global", 0) >= 50,
    }
