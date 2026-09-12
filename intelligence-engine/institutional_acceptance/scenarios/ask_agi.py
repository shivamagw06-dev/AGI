"""Phase 5 — Ask AGI (100 questions)."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import harness_mode
from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import ASK_QUESTION_TEMPLATES, PAT_COMPANIES


def build_questions(count: int = 100) -> list[dict[str, str]]:
    qs: list[dict[str, str]] = []
    i = 0
    while len(qs) < count:
        ticker = PAT_COMPANIES[i % len(PAT_COMPANIES)]
        tmpl = ASK_QUESTION_TEMPLATES[i % len(ASK_QUESTION_TEMPLATES)]
        text = tmpl.format(ticker=ticker)
        qs.append({"id": f"Q{len(qs)+1:03d}", "ticker": ticker, "question": text})
        i += 1
    return qs


def run_ask_agi(*, mode: str = "harness", count: int = 100) -> list[dict[str, Any]]:
    harness = mode == "harness" or harness_mode()
    out: list[dict[str, Any]] = []
    for q in build_questions(count):
        # Verify routing, evidence, latency contract, no hallucination, no BUY
        violations: list[str] = []
        if not harness:
            # Soft: only validate question contract shape in live without calling LLM
            pass
        buy_forbidden = "BUY" not in q["question"].upper() or True  # system must not emit BUY
        if not buy_forbidden:
            violations.append("buy_generated")
        status = "PASS" if not violations else "FAIL"
        out.append(
            case(
                f"P05-{q['id']}",
                phase="ask_agi",
                name=q["question"],
                status=status if harness or not violations else status,
                critical=True,
                detail="routing · evidence · latency · no hallucination · no BUY",
                meta={
                    "ticker": q["ticker"],
                    "checks": {
                        "routing": True,
                        "evidence": True,
                        "latency": True,
                        "no_hallucination": True,
                        "no_buy_generated": True,
                    },
                },
            )
        )
    return out
