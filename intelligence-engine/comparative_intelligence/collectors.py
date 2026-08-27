"""Collect FIRE packs per company — reuse IO-01 collectors; never recalculate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def collect_company(
    ticker: str,
    modules: List[str],
    *,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    prebuilt: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Soft-call FIRE façades via Investment Office collectors (orchestration reuse)."""
    from investment_office.irp.collectors import collect_modules

    return collect_modules(
        ticker,
        modules,
        series_map=series_map,
        documents=documents,
        prebuilt=prebuilt,
    )


def collect_universe(
    tickers: List[str],
    modules: List[str],
    *,
    series_maps: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None,
    documents_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    prebuilt_map: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Returns {ticker: {module: wrap}}.
    prebuilt_map: {ticker: {module: payload}} for deterministic tests.
    """
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    sm = series_maps or {}
    dm = documents_map or {}
    pm = prebuilt_map or {}
    for t in tickers:
        out[t] = collect_company(
            t,
            modules,
            series_map=sm.get(t),
            documents=dm.get(t),
            prebuilt=pm.get(t),
        )
    return out
