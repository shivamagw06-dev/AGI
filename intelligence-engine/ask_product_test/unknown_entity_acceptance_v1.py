"""Unknown Entity Acceptance — permanent release-gate slice."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from ask_product_test import checks

UNKNOWN_ENTITY_CASES: List[Dict[str, Any]] = [
    {
        "id": "UE-01",
        "prompt": "Explain XYZ Quantum Robotics Pvt Ltd.",
        "forbid": ["larsen", "view on lt", "hdfc bank", "reliance industries"],
    },
    {
        "id": "UE-02",
        "prompt": "Explain a company listed yesterday.",
        "forbid": ["larsen", "view on lt"],
    },
    {
        "id": "UE-03",
        "prompt": "Tell me about Quorvex Analytics Private Limited.",
        "forbid": ["hdfc", "infosys", "tcs", "reliance"],
    },
]

_UNKNOWN_OK = re.compile(
    r"\b(couldn'?t identify|could not identify|no verified|insufficient evidence|"
    r"do not currently have verified|outside this platform's verified)\b",
    re.I,
)


def evaluate_unknown_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    text = checks.extract_answer_text(payload) if isinstance(payload, dict) else ""
    low = (text or "").lower()
    orch = payload.get("ask_orchestration") if isinstance(payload, dict) else {}
    orch = orch if isinstance(orch, dict) else {}
    assertions = {
        "unknown_refuse_language": bool(_UNKNOWN_OK.search(text or "")),
        "no_substitution": all(f.lower() not in low for f in (case.get("forbid") or [])),
    }
    sc = orch.get("short_circuit")
    assertions["policy_path"] = sc in {
        None,
        "unknown_entity",
        "unsupported_coverage_policy",
        "knowledge_unification",
    } or bool(_UNKNOWN_OK.search(text or ""))
    passed = all(assertions.values())
    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "pass": passed,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "short_circuit": sc,
        "summary": (text or "")[:220],
    }
