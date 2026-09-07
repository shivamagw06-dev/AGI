"""Stress-test case registry."""

from __future__ import annotations

from typing import Any

from institutional_stress_tests.cases.ist_01_kotak_rbi import IST_01_CASE
from institutional_stress_tests.cases.ist_02_kotak_raw import IST_02_CASE


CASES: dict[str, dict[str, Any]] = {
    IST_01_CASE["case_id"]: IST_01_CASE,
    IST_02_CASE["case_id"]: IST_02_CASE,
}


def get_case(case_id: str) -> dict[str, Any]:
    key = str(case_id or "").strip().upper()
    if key not in CASES:
        raise KeyError(f"unknown stress-test case: {case_id}")
    return dict(CASES[key])


def list_cases() -> list[dict[str, Any]]:
    return [dict(c) for c in CASES.values()]
