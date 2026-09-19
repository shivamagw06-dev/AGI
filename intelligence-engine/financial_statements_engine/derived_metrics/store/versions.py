"""Immutable Derived Metric Store — never overwrite prior calculation versions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from financial_statements_engine.derived_metrics.schema import DerivedMetricRecord, utc_now
from financial_statements_engine.derived_metrics.store.roots import dme_root
from financial_statements_engine.util import write_json_atomic


def _metric_dir(root: Path, company_id: str, period: str, metric_name: str) -> Path:
    safe_co = company_id.replace(":", "_")
    safe_period = period.replace("/", "_").replace(":", "_")
    return root / "metrics" / safe_co / safe_period / metric_name


def next_metric_version(company_id: str, period: str, metric_name: str, *, root: Path | None = None) -> int:
    r = root or dme_root()
    d = _metric_dir(r, company_id, period, metric_name)
    if not d.is_dir():
        return 1
    versions = [int(p.name[1:]) for p in d.iterdir() if p.is_dir() and p.name.startswith("v") and p.name[1:].isdigit()]
    return (max(versions) + 1) if versions else 1


def store_metric(record: DerivedMetricRecord, *, root: Path | None = None) -> Path:
    """Write-once store of a derived metric version."""
    r = root or dme_root()
    d = _metric_dir(r, record.company_id, record.period, record.metric_name) / f"v{record.metric_version}"
    if d.exists():
        raise FileExistsError(f"derived metric already exists (immutable): {d}")
    d.mkdir(parents=True, exist_ok=False)
    payload = record.to_dict()
    payload["content_hash"] = hashlib.sha256(
        json.dumps({k: v for k, v in payload.items() if k != "content_hash"}, sort_keys=True, default=str).encode()
    ).hexdigest()
    path = d / "metric.json"
    write_json_atomic(path, payload)
    _update_latest_pointer(r, record)
    _index_metric(r, record)
    return path


def _update_latest_pointer(root: Path, record: DerivedMetricRecord) -> None:
    ptr = _metric_dir(root, record.company_id, record.period, record.metric_name) / "LATEST"
    if ptr.exists():
        try:
            prev = json.loads(ptr.read_text(encoding="utf-8"))
            prev_version = prev.get("metric_version")
            if prev_version is not None:
                side = (
                    _metric_dir(root, record.company_id, record.period, record.metric_name)
                    / f"v{prev_version}"
                    / "superseded.json"
                )
                write_json_atomic(
                    side,
                    {
                        "superseded_by": record.metric_version,
                        "superseded_at": utc_now(),
                        "previous_metric_id": prev.get("metric_id"),
                    },
                )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    write_json_atomic(
        ptr,
        {
            "metric_id": record.metric_id,
            "metric_version": record.metric_version,
            "formula_version": record.formula_version,
            "value": record.value,
            "quality_status": record.quality_status,
            "updated_at": utc_now(),
        },
    )


def _index_metric(root: Path, record: DerivedMetricRecord) -> None:
    idx = root / "indexes" / "by_company" / f"{record.company_id.replace(':', '_')}.jsonl"
    idx.parent.mkdir(parents=True, exist_ok=True)
    with idx.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "metric_id": record.metric_id,
                    "metric_name": record.metric_name,
                    "period": record.period,
                    "metric_version": record.metric_version,
                    "formula_version": record.formula_version,
                    "value": record.value,
                    "quality_status": record.quality_status,
                },
                sort_keys=True,
            )
            + "\n"
        )


def load_latest(company_id: str, period: str, metric_name: str, *, root: Path | None = None) -> dict[str, Any] | None:
    r = root or dme_root()
    ptr = _metric_dir(r, company_id, period, metric_name) / "LATEST"
    if not ptr.exists():
        return None
    meta = json.loads(ptr.read_text(encoding="utf-8"))
    path = _metric_dir(r, company_id, period, metric_name) / f"v{meta['metric_version']}" / "metric.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_version(
    company_id: str, period: str, metric_name: str, version: int, *, root: Path | None = None
) -> dict[str, Any] | None:
    r = root or dme_root()
    path = _metric_dir(r, company_id, period, metric_name) / f"v{version}" / "metric.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_company_metrics(company_id: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    r = root or dme_root()
    idx = r / "indexes" / "by_company" / f"{company_id.replace(':', '_')}.jsonl"
    if not idx.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def store_failure_report(report: dict[str, Any], *, root: Path | None = None) -> Path:
    r = root or dme_root()
    d = r / "failures" / str(report.get("company_id", "UNKNOWN")).replace(":", "_") / str(
        report.get("period", "UNKNOWN")
    ).replace("/", "_")
    d.mkdir(parents=True, exist_ok=True)
    ts = str(report.get("calculation_timestamp") or utc_now()).replace(":", "")
    path = d / f"{report.get('metric_name', 'metric')}_{ts}.json"
    write_json_atomic(path, report)
    return path


def count_stored_metrics(*, root: Path | None = None) -> int:
    r = root or dme_root()
    return sum(1 for _ in (r / "metrics").rglob("metric.json")) if (r / "metrics").exists() else 0


def count_failures(*, root: Path | None = None) -> int:
    r = root or dme_root()
    return sum(1 for _ in (r / "failures").rglob("*.json")) if (r / "failures").exists() else 0
