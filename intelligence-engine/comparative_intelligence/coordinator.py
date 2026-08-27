"""ComparisonCoordinator — multi-company collect → side-by-side ICR."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from comparative_intelligence.collectors import collect_universe
from comparative_intelligence.dimensions import modules_for_comparison_type, normalize_comparison_type
from comparative_intelligence.report import build_icr
from comparative_intelligence.routing import extract_tickers, route_comparison
from comparative_intelligence.schema import CIO01_PRODUCT, CIO01_VERSION


class ComparisonCoordinator:
    """Cross-company orchestration. Never recalculates FIRE outputs."""

    product = CIO01_PRODUCT
    version = CIO01_VERSION

    def compare(
        self,
        *,
        tickers: Optional[List[str]] = None,
        question: Optional[str] = None,
        comparison_type: Optional[str] = None,
        modules: Optional[List[str]] = None,
        series_maps: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None,
        documents_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        prebuilt_map: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        resolved = extract_tickers(question, explicit=tickers)
        if len(resolved) < 2:
            raise ValueError("at least two tickers are required for comparison")

        routing = route_comparison(question, comparison_type=comparison_type, modules=modules)
        ctype = normalize_comparison_type(routing.get("comparison_type") or comparison_type)
        mods = list(routing.get("modules") or modules_for_comparison_type(ctype))

        universe = collect_universe(
            resolved,
            mods,
            series_maps=series_maps,
            documents_map=documents_map,
            prebuilt_map=prebuilt_map,
        )
        assembly_ms = (time.perf_counter() - t0) * 1000.0
        icr = build_icr(
            tickers=resolved,
            comparison_type=ctype,
            question=question,
            modules=mods,
            universe=universe,
            routing=routing,
            assembly_ms=assembly_ms,
        )
        icr["product"] = self.product
        icr["version"] = self.version
        icr["company_payloads"] = {
            ticker: {
                mod: {
                    "ok": wrap.get("ok"),
                    "error": wrap.get("error"),
                    "source": wrap.get("source"),
                    "payload": wrap.get("payload") if wrap.get("ok") else {},
                }
                for mod, wrap in mods_map.items()
            }
            for ticker, mods_map in universe.items()
        }
        return icr


def compare(
    *,
    tickers: Optional[List[str]] = None,
    question: Optional[str] = None,
    comparison_type: Optional[str] = None,
    modules: Optional[List[str]] = None,
    series_maps: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]] = None,
    documents_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    prebuilt_map: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    return ComparisonCoordinator().compare(
        tickers=tickers,
        question=question,
        comparison_type=comparison_type,
        modules=modules,
        series_maps=series_maps,
        documents_map=documents_map,
        prebuilt_map=prebuilt_map,
    )
