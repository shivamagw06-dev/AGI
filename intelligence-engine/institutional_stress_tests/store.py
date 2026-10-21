"""Process-local IST result store + metrics."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
_RESULTS: list[dict[str, Any]] = []
_METRICS: dict[str, Any] = {
    "runs": 0,
    "passes": 0,
    "fails": 0,
    "single_module_failures": 0,
    "last_case_id": None,
    "last_passed": None,
}
_LIMIT = 50


def record(result: dict[str, Any]) -> None:
    with _LOCK:
        _RESULTS.append(deepcopy(result))
        if len(_RESULTS) > _LIMIT:
            del _RESULTS[: len(_RESULTS) - _LIMIT]
        _METRICS["runs"] = int(_METRICS["runs"]) + 1
        if result.get("score", {}).get("passed") or result.get("passed"):
            _METRICS["passes"] = int(_METRICS["passes"]) + 1
            _METRICS["last_passed"] = True
        else:
            _METRICS["fails"] = int(_METRICS["fails"]) + 1
            _METRICS["last_passed"] = False
        fails = result.get("score", {}).get("automatic_failures") or result.get("automatic_failures") or []
        if "SINGLE_MODULE_RESPONSE" in fails:
            _METRICS["single_module_failures"] = int(_METRICS["single_module_failures"]) + 1
        _METRICS["last_case_id"] = result.get("case_id")


def latest() -> Optional[dict[str, Any]]:
    with _LOCK:
        return deepcopy(_RESULTS[-1]) if _RESULTS else None


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
    return {
        **m,
        "panels": {
            "runs": m.get("runs"),
            "passes": m.get("passes"),
            "fails": m.get("fails"),
            "single_module_failures": m.get("single_module_failures"),
        },
    }


def reset_for_tests() -> None:
    global _RESULTS
    with _LOCK:
        _RESULTS = []
        for k in list(_METRICS.keys()):
            if k in {"last_case_id", "last_passed"}:
                _METRICS[k] = None
            else:
                _METRICS[k] = 0
