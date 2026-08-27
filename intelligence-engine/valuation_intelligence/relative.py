"""Relative valuation vs peer medians (premium/discount + reasons)."""

from __future__ import annotations

from statistics import median
from typing import Any

from valuation_intelligence.schema import PeerSnapshot, RelativeMetric, SubjectMultiples
from valuation_intelligence.conditioning import percentile_rank


def _median(vals: list[float | None]) -> float | None:
    clean = [float(v) for v in vals if isinstance(v, (int, float))]
    if not clean:
        return None
    return round(float(median(clean)), 2)


def _premium(current: float | None, peer_med: float | None) -> float | None:
    if current is None or peer_med is None or peer_med == 0:
        return None
    return round((current / peer_med - 1.0) * 100.0, 1)


def _reasons(
    *,
    subject_roe: float | None,
    peer_roe: float | None,
    subject_eps_cagr: float | None,
    peer_eps_cagr: float | None,
    subject_leverage: float | None,
    peer_leverage: float | None,
    premium_pct: float | None,
) -> list[str]:
    reasons: list[str] = []
    if subject_roe is not None and peer_roe is not None:
        if subject_roe > peer_roe * 1.05:
            reasons.append("Higher ROE")
        elif subject_roe < peer_roe * 0.95:
            reasons.append("Lower ROE")
    if subject_eps_cagr is not None and peer_eps_cagr is not None:
        if subject_eps_cagr > peer_eps_cagr + 1.0:
            reasons.append("Higher EPS CAGR")
        elif subject_eps_cagr < peer_eps_cagr - 1.0:
            reasons.append("Lower EPS CAGR")
    if subject_leverage is not None and peer_leverage is not None:
        if subject_leverage < peer_leverage * 0.9:
            reasons.append("Lower leverage")
        elif subject_leverage > peer_leverage * 1.1:
            reasons.append("Higher leverage")
    if premium_pct is not None and not reasons:
        if premium_pct > 5:
            reasons.append("Trading above peer median")
        elif premium_pct < -5:
            reasons.append("Trading below peer median")
        else:
            reasons.append("In line with peer median")
    return reasons


def build_relative(
    subject: SubjectMultiples,
    peers: list[PeerSnapshot],
    *,
    subject_roe: float | None = None,
    subject_eps_cagr: float | None = None,
    subject_net_debt: float | None = None,
    subject_equity: float | None = None,
) -> dict[str, RelativeMetric]:
    peer_pe = _median([p.pe for p in peers])
    peer_pb = _median([p.pb for p in peers])
    peer_ev = _median([p.ev_ebitda for p in peers])
    peer_roe = _median([p.roe for p in peers])
    peer_eps = _median([p.eps_cagr_3y for p in peers])
    peer_nd = _median([p.net_debt for p in peers if p.net_debt is not None])

    subj_lev = None
    if isinstance(subject_net_debt, (int, float)) and isinstance(subject_equity, (int, float)) and subject_equity:
        subj_lev = float(subject_net_debt) / float(subject_equity)

    out: dict[str, RelativeMetric] = {}
    for key, cur, med in (
        ("pe", subject.pe, peer_pe),
        ("pb", subject.pb, peer_pb),
        ("ev_ebitda", subject.ev_ebitda, peer_ev),
        ("roe", subject_roe, peer_roe),
    ):
        prem = _premium(cur, med)
        out[key] = RelativeMetric(
            metric=key,
            current=cur,
            peer_median=med,
            premium_pct=prem,
            peer_percentile=percentile_rank(cur, [
                getattr(p, {"pe": "pe", "pb": "pb", "ev_ebitda": "ev_ebitda", "roe": "roe"}[key])
                for p in peers
            ]),
            reasons=_reasons(
                subject_roe=subject_roe,
                peer_roe=peer_roe,
                subject_eps_cagr=subject_eps_cagr,
                peer_eps_cagr=peer_eps,
                subject_leverage=subj_lev,
                peer_leverage=peer_nd,  # coarse proxy when equity missing
                premium_pct=prem,
            )
            if key in {"pe", "pb", "ev_ebitda"}
            else (
                ["Higher than peers"]
                if prem is not None and prem > 5
                else ["Lower than peers"]
                if prem is not None and prem < -5
                else ["In line with peers"]
                if prem is not None
                else []
            ),
        )

    # Margins / growth relative stubs filled by caller if needed
    out["eps_cagr_3y"] = RelativeMetric(
        metric="eps_cagr_3y",
        current=subject_eps_cagr,
        peer_median=peer_eps,
        premium_pct=_premium(subject_eps_cagr, peer_eps),
        reasons=[],
    )
    return out


def peer_medians(peers: list[PeerSnapshot]) -> dict[str, float | None]:
    return {
        "median_pe": _median([p.pe for p in peers]),
        "median_pb": _median([p.pb for p in peers]),
        "median_ev_ebitda": _median([p.ev_ebitda for p in peers]),
        "median_roe": _median([p.roe for p in peers]),
        "median_eps_cagr_3y": _median([p.eps_cagr_3y for p in peers]),
    }
