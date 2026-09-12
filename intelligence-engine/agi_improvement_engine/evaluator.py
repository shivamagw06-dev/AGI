"""Bounded OpenAI evaluator. Ask AGI output is never accepted as ground truth."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from agi_improvement_engine.schema import CRITICAL_FAILURES, FAILURE_TAXONOMY, SCORE_WEIGHTS


def _text(value: Any, limit: int) -> str:
    if isinstance(value, str):
        raw = value
    elif isinstance(value, list):
        raw = "\n".join(str(item) for item in value if item is not None)
    elif isinstance(value, dict):
        raw = "\n".join(
            str(value.get(key) or "") for key in ("executive_summary", "summary", "prose", "why")
        )
    else:
        raw = str(value or "")
    return re.sub(r"\s+", " ", raw).strip()[:limit]


def _public_citations(answer: dict[str, Any]) -> list[dict[str, str]]:
    values = answer.get("sources") or answer.get("citations") or []
    rows: list[dict[str, str]] = []
    for value in values[:20] if isinstance(values, list) else []:
        if not isinstance(value, dict):
            continue
        rows.append({
            "title": _text(value.get("title"), 300),
            "source": _text(value.get("source") or value.get("provider"), 160),
            "date": _text(value.get("date") or value.get("as_of"), 80),
            "url": _text(value.get("url"), 500),
        })
    return rows


def evaluate_answer(question: dict[str, Any], answer: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for evaluator mode")
    from openai import OpenAI

    bounded = {
        "question": {
            "question_id": question.get("question_id"), "question": question.get("question"),
            "ticker": question.get("ticker"), "company": question.get("company"),
            "sector": question.get("sector"), "kind": question.get("kind"),
            "difficulty": question.get("difficulty"),
        },
        "answer": {
            "executive_summary": _text(answer.get("executive_summary"), 4000),
            "answer": _text(answer.get("answer"), 12_000),
            "why": _text(answer.get("why"), 4000),
            "as_of": _text(answer.get("as_of"), 80),
            "citations": _public_citations(answer),
        },
    }
    prompt = (
        "Independently grade this Indian-equity research answer. The answer is not truth. "
        "Use only evidence included in the payload; missing support must lose points. Return JSON with "
        f"dimensions (each 0-100, exactly {list(SCORE_WEIGHTS)}), root_causes from {list(FAILURE_TAXONOMY)}, "
        f"critical_failures from {list(CRITICAL_FAILURES)}, and concise notes.\nPAYLOAD\n"
        + json.dumps(bounded, ensure_ascii=False, default=str)[:45_000]
    )
    response = OpenAI(api_key=key, timeout=float(os.environ.get("AGI_EVAL_TIMEOUT_SEC", "45"))).responses.create(
        model=os.environ.get("AGI_EVAL_MODEL", "gpt-5.6-terra"),
        input=prompt,
        reasoning={"effort": os.environ.get("AGI_EVAL_REASONING", "low")},
        store=False,
    )
    raw = (response.output_text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    payload = json.loads(raw)
    usage = getattr(response, "usage", None)
    return payload, {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "model_calls": 1,
    }
