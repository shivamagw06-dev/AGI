"""Validation & quality gates for historical raw archive events."""

from __future__ import annotations

from app.contracts.models import RawHistoricalEvent, ValidationStatus


class HistoricalValidationGate:
    """Content quality gates. Duplicate checksum handling is done pre-insert in the pipeline."""

    def validate(self, event: RawHistoricalEvent) -> RawHistoricalEvent:
        errors: list[str] = []
        if not event.company_symbol:
            errors.append("missing_company_symbol")
        if not event.category:
            errors.append("missing_category")
        if not event.payload:
            errors.append("empty_payload")
        if not event.checksum:
            errors.append("missing_checksum")

        # Category-specific minimal shape checks
        payload = event.payload or {}
        if event.category == "daily_ohlcv":
            if not (payload.get("prices_daily") or payload.get("bhavcopy")):
                errors.append("missing_price_series")
        if event.category in {"annual_financials", "quarterly_financials"}:
            key = "financials_annual" if "annual" in event.category else "financials_quarterly"
            if not payload.get(key):
                errors.append("missing_financial_series")
        if event.category == "company_ir_reports" and not payload.get("reports"):
            errors.append("missing_reports")

        if errors:
            event.validation_status = ValidationStatus.REJECTED
            event.validation_errors = errors
            return event

        event.validation_status = ValidationStatus.ACCEPTED
        event.validation_errors = []
        return event
