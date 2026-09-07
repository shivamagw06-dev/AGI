"""Canonical normalizer — raw historical payloads → typed historical records."""

from __future__ import annotations

from typing import Any

from app.contracts.models import HistoricalObjectType, PeriodKind, RawHistoricalEvent


class HistoricalNormalizer:
    def normalize(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        handlers = {
            "daily_ohlcv": self._prices,
            "annual_financials": self._annual_financials,
            "quarterly_financials": self._quarterly_financials,
            "balance_sheets": self._balance_sheets,
            "cash_flows": self._cash_flows,
            "dividends": self._dividends,
            "corporate_actions": self._actions,
            "corporate_events": self._events,
            "company_profile_history": self._profile,
            "news_metadata": self._news,
            "company_ir_reports": self._reports,
            "index_constituents": self._index,
        }
        fn = handlers.get(event.category)
        if not fn:
            return []
        return fn(event)

    def _prices(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        rows = event.payload.get("prices_daily") or event.payload.get("bhavcopy") or []
        out = []
        for row in rows:
            date = row.get("date")
            if not date:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.PRICE_HISTORY.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.DAILY.value,
                    "knowledge": {
                        "open": row.get("open"),
                        "high": row.get("high"),
                        "low": row.get("low"),
                        "close": row.get("close"),
                        "volume": row.get("volume"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _annual_financials(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        return self._financial_rows(event, event.payload.get("financials_annual") or [], PeriodKind.ANNUAL)

    def _quarterly_financials(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        return self._financial_rows(
            event, event.payload.get("financials_quarterly") or [], PeriodKind.QUARTERLY
        )

    def _financial_rows(
        self, event: RawHistoricalEvent, rows: list[dict[str, Any]], period_kind: PeriodKind
    ) -> list[dict[str, Any]]:
        out = []
        for row in rows:
            period = row.get("period")
            if not period:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.FINANCIAL_STATEMENT.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": period,
                    "period_kind": period_kind.value,
                    "time_period": period,
                    "knowledge": {
                        "statement_type": "income",
                        "revenue": row.get("revenue"),
                        "net_income": row.get("net_income"),
                        "pe": row.get("pe"),
                        "valuation": row.get("valuation") or {"pe": row.get("pe")},
                        "margins": row.get("margins")
                        or (
                            {
                                "pat_margin": round(
                                    float(row["net_income"]) / float(row["revenue"]), 4
                                )
                            }
                            if row.get("revenue") and row.get("net_income")
                            else {}
                        ),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _balance_sheets(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("balance_sheets") or []:
            period = row.get("period")
            if not period:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.BALANCE_SHEET.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": period,
                    "period_kind": row.get("period_kind") or PeriodKind.ANNUAL.value,
                    "time_period": period,
                    "knowledge": {
                        "total_assets": row.get("total_assets"),
                        "total_equity": row.get("total_equity"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _cash_flows(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("cash_flows") or []:
            period = row.get("period")
            if not period:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.CASH_FLOW.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": period,
                    "period_kind": row.get("period_kind") or PeriodKind.ANNUAL.value,
                    "time_period": period,
                    "knowledge": {
                        "operating_cf": row.get("operating_cf"),
                        "capex": row.get("capex"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _dividends(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("dividends") or []:
            date = row.get("date")
            if not date:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.DIVIDEND_HISTORY.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.EVENT.value,
                    "knowledge": {"amount": row.get("amount")},
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _actions(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        rows = event.payload.get("splits") or event.payload.get("corporate_actions") or []
        out = []
        for row in rows:
            date = row.get("date")
            if not date:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.CORPORATE_ACTION.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.EVENT.value,
                    "knowledge": {
                        "action_type": row.get("action_type") or row.get("ratio") or "action",
                        "details": row.get("details") or row.get("ratio"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _events(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("announcements") or []:
            date = row.get("date")
            if not date:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.CORPORATE_EVENT.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.EVENT.value,
                    "knowledge": {
                        "event_type": row.get("category") or "announcement",
                        "subject": row.get("subject"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _profile(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        profile = event.payload.get("profile") or {}
        if not profile:
            return []
        as_of = profile.get("as_of") or "1970-01-01"
        return [
            {
                "object_type": HistoricalObjectType.COMPANY_PROFILE.value,
                "company_symbol": event.company_symbol,
                "effective_date": as_of,
                "period_kind": PeriodKind.POINT_IN_TIME.value,
                "company_name": profile.get("longName"),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "index_membership": profile.get("index_membership") or [],
                "knowledge": {
                    "company": profile.get("longName"),
                    "sector": profile.get("sector"),
                    "industry": profile.get("industry"),
                    "index_membership": profile.get("index_membership") or [],
                },
                "source_event_id": event.event_id,
            }
        ]

    def _news(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("news") or []:
            date = row.get("date")
            if not date:
                continue
            out.append(
                {
                    "object_type": HistoricalObjectType.NEWS_EVENT.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.EVENT.value,
                    "knowledge": {
                        "title": row.get("title"),
                        "publisher": row.get("publisher"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _reports(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        out = []
        for row in event.payload.get("reports") or []:
            date = row.get("date")
            if not date:
                continue
            # Map IR docs onto corporate event family + reports mirror table via knowledge.report_type
            out.append(
                {
                    "object_type": HistoricalObjectType.CORPORATE_EVENT.value,
                    "company_symbol": event.company_symbol,
                    "effective_date": date,
                    "period_kind": PeriodKind.EVENT.value,
                    "knowledge": {
                        "event_type": "ir_document",
                        "report_type": row.get("report_type"),
                        "title": row.get("title"),
                        "url": row.get("url"),
                    },
                    "source_event_id": event.event_id,
                }
            )
        return out

    def _index(self, event: RawHistoricalEvent) -> list[dict[str, Any]]:
        # Index membership updates entity resolution; no KO required beyond profile tips.
        membership = []
        for row in event.payload.get("index_constituents") or []:
            if row.get("member") and row.get("index"):
                membership.append(row["index"])
        if not membership:
            return []
        return [
            {
                "object_type": HistoricalObjectType.COMPANY_PROFILE.value,
                "company_symbol": event.company_symbol,
                "effective_date": "2025-03-31",
                "period_kind": PeriodKind.POINT_IN_TIME.value,
                "index_membership": membership,
                "knowledge": {"index_membership": membership, "source": "nse_constituents"},
                "source_event_id": event.event_id,
            }
        ]
