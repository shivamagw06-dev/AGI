"""Validation & quality gates — only valid events continue."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.contracts.models import RawEvent, Source, ValidationStatus
from app.storage.db import KaipStore

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.&-]{0,31}$")


class ValidationGate:
    def __init__(self, store: KaipStore, *, duplicate_window_seconds: int = 300) -> None:
        self.store = store
        self.duplicate_window_seconds = duplicate_window_seconds

    def validate(self, event: RawEvent) -> RawEvent:
        errors: list[str] = []

        # Schema / required envelope
        if not event.event_id:
            errors.append("missing_event_id")
        if not event.source:
            errors.append("missing_source")
        if not event.collector_id:
            errors.append("missing_collector_id")
        if not event.endpoint:
            errors.append("missing_endpoint")
        if not event.checksum:
            errors.append("missing_checksum")
        if not isinstance(event.payload, dict) or not event.payload:
            errors.append("empty_payload")

        # Timestamp
        if not isinstance(event.timestamp, datetime):
            errors.append("invalid_timestamp")

        # Source-specific required fields
        errors.extend(self._source_required(event))

        # Ticker validation (when present)
        if event.company_symbol:
            symbol = event.company_symbol.upper()
            event.company_symbol = symbol
            if not TICKER_RE.match(symbol):
                errors.append("invalid_ticker")
        elif event.source in {Source.YAHOO, Source.COMPANY_IR}:
            errors.append("missing_company_symbol")

        # Attachment / URL validation
        errors.extend(self._attachment_errors(event.payload))

        if errors:
            event.validation_status = ValidationStatus.REJECTED
            event.validation_errors = errors
            return event

        # Duplicate detection (still stored; not published)
        if self.store.find_duplicate(
            source=event.source.value,
            company_symbol=event.company_symbol,
            checksum=event.checksum,
            window_seconds=self.duplicate_window_seconds,
            now=event.timestamp if isinstance(event.timestamp, datetime) else None,
        ):
            event.validation_status = ValidationStatus.DUPLICATE
            event.validation_errors = ["duplicate_checksum_in_window"]
            return event

        event.validation_status = ValidationStatus.ACCEPTED
        event.validation_errors = []
        return event

    def _source_required(self, event: RawEvent) -> list[str]:
        payload = event.payload
        if event.source == Source.YAHOO:
            if "chart" not in payload and "quote_summary" not in payload and "marketCap" not in payload:
                # allow compact fixtures that already look like quote blobs
                if not any(k in payload for k in ("price", "regularMarketPrice", "info")):
                    return ["yahoo_missing_market_payload"]
        if event.source == Source.NSE and event.collector_id == "NSEAnnouncementCollector":
            if not (payload.get("symbol") or payload.get("company_symbol") or event.company_symbol):
                return ["nse_announcement_missing_symbol"]
            if not (payload.get("desc") or payload.get("subject") or payload.get("event_title") or payload.get("attchmntText")):
                return ["nse_announcement_missing_title"]
        if event.source == Source.BSE:
            if not (payload.get("action_type") or payload.get("PURPOSE") or payload.get("purpose")):
                return ["bse_missing_action_type"]
        if event.source == Source.COMPANY_IR:
            if not (payload.get("ir_url") or event.endpoint):
                return ["company_ir_missing_url"]
        return []

    def _attachment_errors(self, payload: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for key in ("attchmntFile", "attachment_url", "ir_url", "url", "document_url"):
            url = payload.get(key)
            if not url:
                continue
            if not isinstance(url, str):
                errors.append(f"invalid_attachment_type:{key}")
                continue
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"invalid_attachment_url:{key}")
        docs = payload.get("documents")
        if isinstance(docs, list):
            for i, doc in enumerate(docs):
                if isinstance(doc, dict) and doc.get("url"):
                    parsed = urlparse(str(doc["url"]))
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        errors.append(f"invalid_document_url:{i}")
        return errors
