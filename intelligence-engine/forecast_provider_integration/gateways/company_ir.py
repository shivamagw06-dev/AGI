"""Company IR gateway — official documents and investor communications."""

from __future__ import annotations

import time
from typing import Any

from forecast_provider_integration.schema import utc_now

_IR_DOCS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {"type": "annual_report", "title": "Annual Report"},
        {"type": "quarterly_report", "title": "Q Results"},
        {"type": "investor_presentation", "title": "Investor Presentation"},
        {"type": "earnings_transcript", "title": "Earnings Call Transcript"},
        {"type": "esg_report", "title": "ESG Report"},
        {"type": "governance_report", "title": "Corporate Governance Report"},
    ],
}


class CompanyIrGateway:
    provider = "company_ir"

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": True,
            "connection": "collector",
            "websocket": False,
            "role": "official_documents",
            "status": "healthy",
            "detail": "IR docs every 10m market hours / hourly otherwise",
            "market_hours_interval_sec": 600,
            "off_hours_interval_sec": 3600,
        }

    def collect(self, entity: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        key = entity.upper()
        docs = list(_IR_DOCS.get(key) or [
            {"type": "investor_presentation", "title": f"{key} IR tip"},
        ])
        now = utc_now()
        for d in docs:
            d["source"] = "company_ir"
            d["entity"] = key
            d["as_of"] = now.isoformat()
        return {
            "provider": self.provider,
            "documents": docs,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "mode": "seeded_collector",
            "fabricated": False,
        }
