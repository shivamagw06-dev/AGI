"""In-memory Industry Intelligence store (soft, immutable industry objects)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_INDUSTRIES: dict[str, dict[str, Any]] = {}
_COMPANY_MAP: dict[str, str] = {}
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _INDUSTRIES.clear()
        _COMPANY_MAP.clear()
        _RUNS.clear()


def put_industry(obj: dict[str, Any]) -> dict[str, Any]:
    iid = str(obj.get("industry_id") or "")
    if not iid:
        raise ValueError("industry object requires industry_id")
    with _LOCK:
        if iid not in _INDUSTRIES:
            _INDUSTRIES[iid] = deepcopy(obj)
        return deepcopy(_INDUSTRIES[iid])


def get_industry(industry_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _INDUSTRIES.get(str(industry_id or "").lower())
        return deepcopy(row) if row else None


def list_industries() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_INDUSTRIES.items())]


def industry_count() -> int:
    with _LOCK:
        return len(_INDUSTRIES)


def put_company_map(mapping: dict[str, str]) -> None:
    with _LOCK:
        _COMPANY_MAP.update({k.upper(): v.lower() for k, v in mapping.items()})


def get_company_industry(ticker: str) -> str | None:
    with _LOCK:
        return _COMPANY_MAP.get(str(ticker or "").upper())


def list_company_map() -> dict[str, str]:
    with _LOCK:
        return dict(_COMPANY_MAP)


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
