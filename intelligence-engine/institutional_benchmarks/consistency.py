"""Consistency validation across related institutional questions."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def evaluate_consistency(
    primary_report: Mapping[str, Any],
    related_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Related questions must remain internally consistent.

    Detects:
    - BUY/SELL collapse on any related answer
    - Peer preference statements that invert without shared evidence
    - Missing counter-evidence on related answers while primary has it
    """
    failures: list[dict[str, str]] = []
    primary_ticker = str(primary_report.get("ticker") or "").upper()
    primary_contra = bool(
        ((primary_report.get("sections") or {}).get("evidence_contradicting") or {}).get("items")
    )
    primary_unk = bool(
        ((primary_report.get("sections") or {}).get("outstanding_unknowns") or {}).get("items")
    )

    for row in related_runs or []:
        q = str(row.get("question") or "")
        rep = row.get("report") or {}
        if rep.get("collapsed_to_buy_sell") or rep.get("buy_sell") in {"BUY", "SELL", "buy", "sell"}:
            failures.append(
                {
                    "code": "CONSISTENCY_FAILURE",
                    "detail": f"Related question collapsed to BUY/SELL: {q[:120]}",
                }
            )
        secs = rep.get("sections") or {}
        if primary_contra and not (secs.get("evidence_contradicting") or {}).get("items"):
            failures.append(
                {
                    "code": "CONSISTENCY_FAILURE",
                    "detail": f"Related answer dropped counter-evidence: {q[:120]}",
                }
            )
        if primary_unk and not (secs.get("outstanding_unknowns") or {}).get("items"):
            failures.append(
                {
                    "code": "CONSISTENCY_FAILURE",
                    "detail": f"Related answer dropped unknowns: {q[:120]}",
                }
            )
        # Crude inversion: if question asks "why not peer" but report has no peer section
        if "why not" in q.lower() or "instead" in q.lower():
            peer = secs.get("peer_comparison") or {}
            if not (peer.get("paragraphs") or peer.get("peers")):
                failures.append(
                    {
                        "code": "CONSISTENCY_FAILURE",
                        "detail": f"Peer-comparison question lacks peer section: {q[:120]}",
                    }
                )

    # Primary must not claim certainty while listing unknowns empty
    conf = (primary_report.get("sections") or {}).get("confidence_discussion") or {}
    mean_c = conf.get("confidence")
    if isinstance(mean_c, (int, float)) and mean_c >= 0.9 and not primary_unk:
        failures.append(
            {
                "code": "CONSISTENCY_FAILURE",
                "detail": f"High confidence ({mean_c}) without unknowns for {primary_ticker}.",
            }
        )

    codes = sorted({f["code"] for f in failures})
    return {
        "ok": not failures,
        "failures": failures,
        "failure_codes": codes,
        "related_n": len(list(related_runs or [])),
        "primary_ticker": primary_ticker,
    }
