"""Environment configuration for official source adapters (FSE-02.3)."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = "true") -> bool:
    return str(os.environ.get(name, default)).strip().lower() not in {"0", "false", "no", "off"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


def enable_mca() -> bool:
    return _truthy("ENABLE_MCA", "true")


def enable_nse() -> bool:
    return _truthy("ENABLE_NSE", "true")


def enable_bse() -> bool:
    return _truthy("ENABLE_BSE", "true")


def enable_ir() -> bool:
    return _truthy("ENABLE_IR", "true")


def source_timeout_s() -> float:
    return max(1.0, _float("SOURCE_TIMEOUT", 30.0))


def max_download_retries() -> int:
    return max(0, _int("MAX_DOWNLOAD_RETRIES", 3))
