"""Company IR historical collector — reports, presentations, transcripts, ESG, governance."""

from __future__ import annotations

from typing import Any

from app.collectors.base import BaseHistoricalCollector
from app.contracts.models import RawHistoricalEvent, Source


def default_ir_fixture(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    reports = []
    for y in range(2015, 2026):
        reports.append(
            {
                "date": f"{y}-05-20",
                "report_type": "annual_report",
                "title": f"{symbol} Annual Report FY{y}",
                "url": f"https://ir.example/{symbol.lower()}/ar-{y}.pdf",
            }
        )
        reports.append(
            {
                "date": f"{y}-07-25",
                "report_type": "quarterly_report",
                "title": f"{symbol} Q1 FY{y} Results",
                "url": f"https://ir.example/{symbol.lower()}/q1-{y}.pdf",
            }
        )
        if y >= 2018:
            reports.append(
                {
                    "date": f"{y}-07-26",
                    "report_type": "earnings_presentation",
                    "title": f"{symbol} Earnings Presentation FY{y}",
                    "url": f"https://ir.example/{symbol.lower()}/ep-{y}.pdf",
                }
            )
            reports.append(
                {
                    "date": f"{y}-07-27",
                    "report_type": "earnings_transcript",
                    "title": f"{symbol} Earnings Transcript FY{y}",
                    "url": f"https://ir.example/{symbol.lower()}/et-{y}.pdf",
                }
            )
    reports.append(
        {
            "date": "2024-03-31",
            "report_type": "esg_report",
            "title": f"{symbol} ESG Report 2024",
            "url": f"https://ir.example/{symbol.lower()}/esg-2024.pdf",
        }
    )
    reports.append(
        {
            "date": "2024-03-31",
            "report_type": "governance_report",
            "title": f"{symbol} Corporate Governance Report 2024",
            "url": f"https://ir.example/{symbol.lower()}/gov-2024.pdf",
        }
    )
    return {"reports": reports}


class CompanyIRHistoricalCollector(BaseHistoricalCollector):
    collector_id = "CompanyIRHistoricalCollector"
    source = Source.COMPANY_IR
    categories = ("company_ir_reports",)

    def __init__(
        self,
        *,
        symbols: list[str],
        live: bool = False,
        fixture_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.live = live
        self.fixture_payloads = fixture_payloads or {}

    def collect(self, *, ingestion_run_id: str | None = None) -> list[RawHistoricalEvent]:
        _ = self.live
        events: list[RawHistoricalEvent] = []
        for symbol in self.symbols:
            payload = self.fixture_payloads.get(symbol) or default_ir_fixture(symbol)
            events.append(
                self.make_event(
                    endpoint=f"company_ir://historical/{symbol}",
                    category="company_ir_reports",
                    payload=payload,
                    company_symbol=symbol,
                    effective_start="2015-01-01",
                    ingestion_run_id=ingestion_run_id,
                )
            )
        return events
