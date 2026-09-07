"""PRE-01 correlation engine — Phase 1 proxies + CorrelationProvider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio_risk.models import CorrelationRisk


class CorrelationProvider(ABC):
    """Future: historical covariance / vendor risk models."""

    name: str = "base"

    @abstractmethod
    def pair_correlation(self, a: HoldingRecord, b: HoldingRecord) -> float:
        raise NotImplementedError


class ProxyCorrelationProvider(CorrelationProvider):
    """Deterministic proxies: common sector / industry / macro drivers."""

    name = "proxy_v1"

    def pair_correlation(self, a: HoldingRecord, b: HoldingRecord) -> float:
        if a.ticker == b.ticker:
            return 1.0
        sa = (a.sector or "").strip().lower()
        sb = (b.sector or "").strip().lower()
        ia = (a.industry or "").strip().lower()
        ib = (b.industry or "").strip().lower()
        if ia and ib and ia == ib:
            return 0.85
        if sa and sb and sa == sb:
            return 0.72
        # Shared India macro driver baseline
        ca = (a.country or "IN").upper()
        cb = (b.country or "IN").upper()
        if ca == cb == "IN":
            return 0.35
        return 0.20


def evaluate_correlation(
    holdings: Sequence[HoldingRecord],
    *,
    provider: CorrelationProvider | None = None,
) -> CorrelationRisk:
    prov = provider or ProxyCorrelationProvider()
    rows = list(holdings)
    pairs: list[dict] = []
    corrs: list[float] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            c = float(prov.pair_correlation(rows[i], rows[j]))
            w = float(rows[i].weight or 0.0) * float(rows[j].weight or 0.0)
            pairs.append(
                {
                    "a": rows[i].ticker,
                    "b": rows[j].ticker,
                    "correlation": round(c, 4),
                    "weight_product": round(w, 6),
                    "same_sector": (rows[i].sector or "") == (rows[j].sector or ""),
                }
            )
            corrs.append(c)

    avg = sum(corrs) / len(corrs) if corrs else 0.0
    mx = max(corrs) if corrs else 0.0

    if avg >= 0.75 or mx >= 0.90:
        level = "Critical"
    elif avg >= 0.60 or mx >= 0.80:
        level = "High"
    elif avg >= 0.45:
        level = "Moderate"
    else:
        level = "Low"

    # Keep top pairs by correlation
    pairs_sorted = sorted(pairs, key=lambda p: float(p["correlation"]), reverse=True)[:12]
    return CorrelationRisk(
        level=level,
        average_correlation=round(avg, 4),
        max_pair_correlation=round(mx, 4),
        pairs=tuple(pairs_sorted),
        provider=prov.name,
    )
