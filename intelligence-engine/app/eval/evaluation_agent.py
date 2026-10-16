from __future__ import annotations

from app.schemas.models import PredictionRecord
from app.memory.store import DISK_DIR
import json


class EvaluationAgent:
    """Skeleton: records predictions for later outcome scoring."""

    def __init__(self):
        self._path = DISK_DIR / "predictions.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, prediction: PredictionRecord) -> PredictionRecord:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(prediction.model_dump_json() + "\n")
        return prediction

    def list_pending(self, limit: int = 50) -> list[PredictionRecord]:
        if not self._path.exists():
            return []
        rows: list[PredictionRecord] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            pred = PredictionRecord.model_validate_json(line)
            if pred.actual_outcome is None:
                rows.append(pred)
            if len(rows) >= limit:
                break
        return rows
