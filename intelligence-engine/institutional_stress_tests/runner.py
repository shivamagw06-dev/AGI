"""Run IST cases — probe stack → assemble answer → score with orchestration gate."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from institutional_stress_tests.answer_contract import build_institutional_answer
from institutional_stress_tests.cases import get_case
from institutional_stress_tests.probes import probe_all
from institutional_stress_tests.scoring import score_case
from institutional_stress_tests import store as ist_store


def run_case(
    case_id: str = "IST-01",
    *,
    prebuilt: Optional[Mapping[str, Mapping[str, Any]]] = None,
    answers: Optional[Mapping[str, Any]] = None,
    final_view: Optional[Mapping[str, Any]] = None,
    modules_filter: Optional[Sequence[str]] = None,
    allow_external: bool = False,
) -> dict[str, Any]:
    """
    Execute one institutional stress test.

    `modules_filter` is for negative tests — restricting probes to prove
    that no individual module can pass alone.
    """
    case = get_case(case_id)
    ticker = str(case.get("primary_ticker") or "").upper()
    peers = [str(p).upper() for p in (case.get("peer_tickers") or [])]

    # First pass: build candidate view so AskAGI probe can see it
    draft_view = dict(final_view or {})
    if answers and isinstance(answers.get("final_institutional_view"), Mapping):
        draft_view = {**draft_view, **dict(answers["final_institutional_view"])}

    probes = probe_all(
        ticker,
        peers,
        prebuilt=dict(prebuilt or {}),
        institutional_view=draft_view,
        modules_filter=list(modules_filter) if modules_filter else None,
    )

    answer = build_institutional_answer(
        case,
        probes,
        answers=answers,
        final_view=draft_view,
        allow_external=allow_external,
    )

    # Re-probe AskAGI with the assembled view (full stack only)
    if modules_filter is None or any(str(m).upper() in {"ASKAGI", "ASK AGI"} for m in modules_filter):
        from institutional_stress_tests.probes import probe_ask_agi

        probes["AskAGI"] = probe_ask_agi(ticker, institutional_view=answer.get("final_institutional_view"))
        # Refresh provenance after AskAGI
        answer = build_institutional_answer(
            case,
            probes,
            answers=answers,
            final_view=answer.get("final_institutional_view"),
            allow_external=allow_external,
        )

    score = score_case(case, probes, answer)
    result = {
        "ok": True,
        "case_id": case.get("case_id"),
        "workstream_id": case.get("workstream_id"),
        "title": case.get("title"),
        "question": case.get("question"),
        "ticker": ticker,
        "peers": peers,
        "probes": {k: {"ok": v.get("ok"), "contributing": v.get("contributing"), "error": v.get("error")} for k, v in probes.items()},
        "answer": answer,
        "score": score,
        "passed": bool(score.get("passed")),
        "no_single_module_pass": True,
        "forbids_simple_verdict": bool(case.get("forbids_simple_verdict")),
    }
    ist_store.record(result)
    return result
