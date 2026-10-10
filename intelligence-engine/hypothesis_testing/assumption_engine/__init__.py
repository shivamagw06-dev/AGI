"""Assumption engine — expose explicit / implicit / weak / untested assumptions."""

from __future__ import annotations

from typing import Any

_TYPE_ASSUMPTIONS: dict[str, dict[str, list[str]]] = {
    "Business": {
        "explicit": ["Deposit franchise remains strong", "Competition stays rational", "Switching costs persist"],
        "implicit": ["No abrupt digital disintermediation", "Customer behaviour remains sticky"],
        "weak": ["Peer competitive response stays measured"],
        "untested": ["No structural regulatory change to deposit pricing"],
    },
    "Valuation": {
        "explicit": ["Consensus growth path is a fair base case", "Historical multiples remain relevant anchors"],
        "implicit": ["Discount rates stay roughly stable", "Accounting quality comparable across history"],
        "weak": ["No regime shift in market risk premia"],
        "untested": ["Scenario DCF triangulation confirms street multiples"],
    },
    "Financial": {
        "explicit": ["Underwriting standards remain intact", "Secured mix does not deteriorate sharply"],
        "implicit": ["Recovery rates stay near historical norms"],
        "weak": ["Macro credit impulse does not cliff"],
        "untested": ["Segment vintage curves confirm benign steady-state losses"],
    },
    "Macro": {
        "explicit": ["Policy path transmits via NIM and volumes", "Sector beta remains the dominant channel"],
        "implicit": ["No sudden external shock overrides local policy"],
        "weak": ["Fiscal impulse does not fully offset monetary easing"],
        "untested": ["High-frequency demand nowcasts confirm transmission"],
    },
    "Risk": {
        "explicit": ["Identified risk factors remain material", "Capital buffers are the binding constraint"],
        "implicit": ["Disclosure captures the main contingent exposures"],
        "weak": ["Stress scenarios are severe enough"],
        "untested": ["Full contingent liability schedule"],
    },
}


def build_assumptions(hypothesis: dict[str, Any]) -> dict[str, Any]:
    t = str(hypothesis.get("type") or "Business")
    base = _TYPE_ASSUMPTIONS.get(t) or _TYPE_ASSUMPTIONS["Business"]
    # Merge any assumptions already on the hypothesis (from IHG)
    prior = hypothesis.get("assumptions") if isinstance(hypothesis.get("assumptions"), dict) else {}
    return {
        "explicit": list(dict.fromkeys(list(base["explicit"]) + list(prior.get("known") or []))),
        "implicit": list(dict.fromkeys(list(base["implicit"]) + list(prior.get("unknown") or []))),
        "weak": list(dict.fromkeys(list(base["weak"]) + list(prior.get("weak") or []))),
        "untested": list(dict.fromkeys(list(base["untested"]) + list(prior.get("evidence_gaps") or []))),
    }
