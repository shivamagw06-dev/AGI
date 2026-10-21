"""Continuous Gather Learn (CGL) structured-extracts provider."""

from __future__ import annotations

import json
import time
from pathlib import Path

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class ContinuousGatherProvider:
    spec = ProviderSpec(
        id="cgl",
        label="Continuous Gather Learn",
        coverage="Structured extracts from continuous gather/learn cycles",
        priority=35,
        supported_question_types=("company", "market", "macro", "news", "industry"),
        typical_latency_ms=30,
        confidence_ceiling=0.7,
    )

    def _knowledge_dir(self) -> Path:
        try:
            from continuous_gather_learn.persist import store_root

            return store_root() / "knowledge"
        except Exception:
            return Path(__file__).resolve().parents[2] / "data" / "continuous_gather_learn" / "knowledge"

    def health_check(self) -> str:
        try:
            d = self._knowledge_dir()
            if not d.exists():
                return "empty"
            n = sum(1 for _ in d.glob("*.json"))
            if n >= 50:
                return "ok"
            if n > 0:
                return "degraded"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        ticker = (plan.ticker_hint or "").upper()
        needle = (plan.company_hint or ticker or "").lower()
        if not needle and not ticker:
            return empty_result(self.spec.id, t0, "no_entity_for_cgl")
        try:
            d = self._knowledge_dir()
            if not d.exists():
                return empty_result(self.spec.id, t0, "cgl_dir_missing")
            hits = []
            # Prefer filename/ticker-prefixed extracts before scanning bodies.
            paths = sorted(d.glob("*.json"))
            if ticker:
                preferred = [p for p in paths if ticker.lower() in p.stem.lower()]
                rest = [p for p in paths if p not in preferred]
                paths = preferred + rest
            for path in paths[:200]:
                try:
                    body = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(body, dict):
                    continue
                entity = str(body.get("entity") or body.get("ticker") or body.get("symbol") or "").upper()
                if ticker and entity == ticker:
                    hits.append(body)
                elif ticker and ticker.lower() in path.stem.lower():
                    hits.append(body)
                elif needle and needle in json.dumps(
                    {k: body.get(k) for k in ("entity", "ticker", "symbol", "title", "summary") if k in body},
                    default=str,
                ).lower():
                    hits.append(body)
                if len(hits) >= 5:
                    break
            if not hits:
                return empty_result(self.spec.id, t0, "cgl_no_match")
            why = []
            for h in hits[:3]:
                ent = h.get("entity") or h.get("ticker") or "extract"
                kind = h.get("kind") or h.get("type") or "knowledge"
                why.append(f"CGL {kind} for {ent}.")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.65,
                t0=t0,
                summary=f"Continuous Gather has {len(hits)} structured extract(s) for this entity.",
                why=why,
                evidence=[{"source": "continuous_gather_learn", "title": f"extracts:{len(hits)}"}],
                facts=[{"field": "cgl_extract_count", "value": len(hits)}],
                raw={"extracts": hits[:5]},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
