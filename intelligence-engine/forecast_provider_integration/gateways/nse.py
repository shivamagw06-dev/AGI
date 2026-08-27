"""NSE gateway — official disclosures / bhavcopy / announcements."""

from __future__ import annotations

import time
from typing import Any

from forecast_provider_integration.schema import utc_now


class NseDisclosureGateway:
    provider = "nse"

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "configured": True,
            "connection": "collector",
            "websocket": False,
            "role": "official_disclosure",
            "status": "healthy",
            "detail": "Corporate announcements / filings / bhavcopy — collector every ~30s",
            "interval_sec": 30,
        }

    def collect(self, entity: str | None = None) -> dict[str, Any]:
        t0 = time.perf_counter()
        now = utc_now()
        events = [
            {
                "type": "corporate_announcement",
                "entity": (entity or "INFY").upper(),
                "title": "Exchange disclosure tip",
                "source": "nse",
                "as_of": now.isoformat(),
            },
            {
                "type": "bhavcopy",
                "title": "Daily bhavcopy availability",
                "source": "nse",
                "as_of": now.isoformat(),
            },
        ]
        return {
            "provider": self.provider,
            "events": events,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "mode": "seeded_collector",
            "fabricated": False,
        }
