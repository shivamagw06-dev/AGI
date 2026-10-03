"""IMAI quality gates — fail closed on leakage / invention / no evidence."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.schema import REGIMES


def evaluate_memory_pack(pack: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    failures: list[str] = []
    memories = list(pack.get("memories") or [])

    if pack.get("invented_analogues") is True:
        failures.append("invented_historical_analogues")

    for m in memories:
        mid = m.get("memory_id") or "?"
        eids = m.get("evidence_ids") or []
        if not eids:
            failures.append(f"memory_without_evidence:{mid}")
        if m.get("fabricated") is True or m.get("validated_historical") is False:
            failures.append(f"invented_historical_analogues:{mid}")
        conf = m.get("confidence")
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            failures.append(f"confidence_impossible:{mid}")
        sim = m.get("similarity_score")
        if sim is not None and (
            not isinstance(sim, (int, float)) or float(sim) < 0 or float(sim) > 100.0
        ):
            failures.append(f"unsupported_similarity:{mid}")
        avail = str(m.get("available_from") or "")[:10]
        if as_of and avail and avail > str(as_of)[:10]:
            failures.append(f"future_leakage:{mid}")
        # Outcome redaction consistency under replay
        if as_of:
            ko = str(m.get("known_outcome_as_of") or avail)[:10]
            if ko and ko > str(as_of)[:10] and not m.get("outcome_redacted"):
                failures.append(f"replay_mismatch:{mid}")

        for r in m.get("macro_regime") or []:
            if r and r not in REGIMES:
                failures.append(f"incorrect_regime:{mid}:{r}")
        mr = m.get("market_regime")
        if mr and mr not in REGIMES:
            failures.append(f"incorrect_regime:{mid}:{mr}")

    status = "fail" if failures else "pass"
    return {
        "status": status,
        "failures": failures,
        "memory_count": len(memories),
        "gates": [
            "future_leakage",
            "invented_historical_analogues",
            "unsupported_similarity",
            "incorrect_regime",
            "replay_mismatch",
            "memory_without_evidence",
            "confidence_impossible",
        ],
    }
