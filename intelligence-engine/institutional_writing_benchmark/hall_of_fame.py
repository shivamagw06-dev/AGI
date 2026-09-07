"""Hall of Fame — 100 best responses, version comparison, regression guard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_writing_benchmark.schema import HALL_OF_FAME_COUNT

_ROOT = Path(__file__).resolve().parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def hall_of_fame_ids() -> list[str]:
    """Hall of Fame — 100 universal questions on TCS anchor."""
    from institutional_investor_curriculum.benchmarks import hall_of_fame_benchmark_ids

    return hall_of_fame_benchmark_ids()


def _hof_path() -> Path:
    return _ROOT / "hall_of_fame" / "entries.json"


def load_hall_of_fame() -> dict[str, Any]:
    path = _hof_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": "1.0", "updated_at": None, "entries": {}}


def save_hall_of_fame(data: dict[str, Any]) -> None:
    path = _hof_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def compare_and_maybe_update(
    benchmark_id: str,
    *,
    question: str,
    response_text: str,
    editorial_score: float,
    forward_rating: str,
) -> dict[str, Any]:
    """Keep new version only if objectively better than hall of fame entry."""
    hof = load_hall_of_fame()
    entries = hof.setdefault("entries", {})
    prev = entries.get(benchmark_id)
    prev_score = (prev or {}).get("editorial_score") or 0.0

    improved = editorial_score > prev_score or prev is None
    if improved:
        history = list((prev or {}).get("revision_history") or [])
        if prev:
            history.append({
                "archived_at": _now(),
                "editorial_score": prev_score,
                "forward_rating": prev.get("forward_rating"),
                "response_excerpt": (prev.get("response_text") or "")[:500],
            })
        entries[benchmark_id] = {
            "benchmark_id": benchmark_id,
            "question": question,
            "response_text": response_text,
            "editorial_score": editorial_score,
            "forward_rating": forward_rating,
            "updated_at": _now(),
            "revision_history": history[-5:],
        }
        save_hall_of_fame(hof)

    return {
        "benchmark_id": benchmark_id,
        "improved": improved,
        "previous_score": prev_score if prev else None,
        "new_score": editorial_score,
        "kept": improved,
    }
