"""LIDI validators — reject invalid live payloads before knowledge publish."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from live_data import store

VALIDATOR_VERSION = "lidi-validator-v1.0.0"
_TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.&-]{0,20}$")


def validate_live_dataset(
    dataset: dict[str, Any],
    *,
    required_payload_fields: tuple[str, ...] = (),
    row_ticker_field: str | None = "symbol",
    allow_empty_rows: bool = False,
) -> dict[str, Any]:
    failures: list[str] = []
    payload = dataset.get("payload") or {}

    if not dataset.get("collector_id"):
        failures.append("missing_collector")
    if not dataset.get("source_id"):
        failures.append("missing_source")
    if not dataset.get("official_source"):
        failures.append("source_integrity")
    if not (dataset.get("provenance") or {}).get("official_source"):
        failures.append("provenance_missing")
    if dataset.get("fixture") is True:
        failures.append("fixture_not_allowed_in_lidi_publish")
    if dataset.get("fabricated") is True:
        failures.append("fabricated_payload")

    for f in required_payload_fields:
        if payload.get(f) in (None, "", [], {}):
            failures.append(f"missing_field:{f}")

    # Date / effective
    eff = dataset.get("effective_date") or payload.get("effective_date")
    if eff:
        try:
            datetime.fromisoformat(str(eff)[:10])
        except Exception:
            failures.append("invalid_date")
    else:
        failures.append("missing_effective_date")

    if not dataset.get("checksum") and dataset.get("mode") == "live":
        failures.append("missing_checksum")

    rows = (
        payload.get("rows")
        or payload.get("events")
        or payload.get("actions")
        or payload.get("series")
        or payload.get("documents")
        or []
    )
    if not rows and not allow_empty_rows:
        failures.append("missing_fields:rows")

    # Duplicate + ticker checks for row payloads
    seen = set()
    outliers = 0
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            failures.append("schema_row")
            continue
        if row_ticker_field:
            sym = str(row.get(row_ticker_field) or "").upper()
            if sym and not _TICKER.match(sym):
                failures.append("invalid_ticker")
            # Events may share ticker+date; include headline/purpose for uniqueness.
            key = (
                sym,
                row.get("date") or row.get("effective_date") or row.get("ex_date") or row.get("series"),
                row.get("headline") or row.get("purpose") or row.get("action_type") or row.get("metric"),
            )
            if key in seen:
                failures.append("duplicate")
            seen.add(key)
        # soft per-row date check (do not hard-fail whole batch on one bad row)
        row_date = row.get("date") or row.get("effective_date") or row.get("ex_date") or row.get("as_of")
        if row_date:
            try:
                datetime.fromisoformat(str(row_date)[:10])
            except Exception:
                failures.append("invalid_date")
        # price outlier guard
        for px in ("close", "open", "high", "low", "prev_close"):
            if px in row and row[px] is not None:
                try:
                    v = float(row[px])
                    if v <= 0 or v > 1_000_000:
                        outliers += 1
                except Exception:
                    failures.append("schema_price")
    if outliers > max(5, int(0.05 * max(len(rows), 1))):
        failures.append("outliers")

    # Historical consistency soft: if snapshot exists, effective_date shouldn't go backwards silently
    # (warning only — not hard fail)
    warnings: list[str] = []
    prev = store.get_latest_snapshot(str(dataset.get("source_id") or ""), "LATEST")
    if prev and eff and prev.get("effective_date"):
        if str(eff)[:10] < str(prev.get("effective_date"))[:10] and not dataset.get("fallback"):
            warnings.append("historical_date_regression")

    failures = sorted(set(failures))
    ok = not failures
    verdict = {
        "ok": ok,
        "validator_version": VALIDATOR_VERSION,
        "failures": failures,
        "warnings": warnings,
        "validated_at": store.utc_now(),
    }
    store.log_validation(
        {
            "source_id": dataset.get("source_id"),
            "collector_id": dataset.get("collector_id"),
            "ok": ok,
            "failures": failures,
            "warnings": warnings,
        }
    )
    return verdict
