"""InvestmentCoordinator — intent → modules → collect → assemble IRP."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from investment_office.irp.collectors import collect_modules
from investment_office.irp.packages import modules_for_package, normalize_package_type
from investment_office.irp.report import build_irp
from investment_office.irp.routing import route_question
from investment_office.schema import IO01_PRODUCT, IO01_VERSION


class InvestmentCoordinator:
    """Orchestration façade. Never recalculates FIRE outputs."""

    product = IO01_PRODUCT
    version = IO01_VERSION

    def coordinate(
        self,
        *,
        ticker: str,
        question: Optional[str] = None,
        package_type: Optional[str] = None,
        series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None,
        prebuilt: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        ticker_u = (ticker or "").strip().upper()
        if not ticker_u:
            raise ValueError("ticker is required")

        routing = route_question(question, package_type=package_type)
        pkg = normalize_package_type(routing.get("package_type") or package_type or "Institutional Brief")
        modules = list(routing.get("modules") or modules_for_package(pkg))

        collected = collect_modules(
            ticker_u,
            modules,
            series_map=series_map,
            documents=documents,
            prebuilt=prebuilt,
        )
        assembly_ms = (time.perf_counter() - t0) * 1000.0
        irp = build_irp(
            ticker=ticker_u,
            package_type=pkg,
            question=question,
            modules=modules,
            collected=collected,
            routing=routing,
            assembly_ms=assembly_ms,
        )
        irp["product"] = self.product
        irp["version"] = self.version
        irp["module_payloads"] = {
            mod: {
                "ok": wrap.get("ok"),
                "error": wrap.get("error"),
                "source": wrap.get("source"),
                # Pass-through only — no mutation of FIRE fields
                "payload": wrap.get("payload") if wrap.get("ok") else {},
            }
            for mod, wrap in collected.items()
        }
        return irp


def coordinate(
    *,
    ticker: str,
    question: Optional[str] = None,
    package_type: Optional[str] = None,
    series_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    prebuilt: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return InvestmentCoordinator().coordinate(
        ticker=ticker,
        question=question,
        package_type=package_type,
        series_map=series_map,
        documents=documents,
        prebuilt=prebuilt,
    )
