"""Legacy KIP retrieval — fallback provider, never the default."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class LegacyKipProvider:
    spec = ProviderSpec(
        id="legacy_kip",
        label="Legacy KIP Retrieval",
        coverage="Historical document/chunk retrieval (fallback only)",
        priority=90,
        supported_question_types=("company", "news", "industry", "macro", "unknown"),
        typical_latency_ms=120,
        confidence_ceiling=0.55,
    )

    def health_check(self) -> str:
        try:
            from pathlib import Path

            snap = Path(__file__).resolve().parents[2] / "data" / "kip" / "kip_snapshot.json"
            return "ok" if snap.exists() else "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        # Explicitly a fallback: only contribute when the planner selected us
        # (knowledge_planner includes legacy_kip last for company/news).
        try:
            # Soft probe — do not construct the full UiService graph here.
            from pathlib import Path
            import json

            snap = Path(__file__).resolve().parents[2] / "data" / "kip" / "kip_snapshot.json"
            if not snap.exists():
                return empty_result(self.spec.id, t0, "kip_snapshot_missing")
            # Cheap keyword match over a capped document list — proves the
            # provider is reachable without pulling the entire Ask stack.
            body = json.loads(snap.read_text(encoding="utf-8"))
            docs = body.get("documents") or body.get("docs") or []
            if not isinstance(docs, list) or not docs:
                return empty_result(self.spec.id, t0, "kip_empty")
            q = (plan.question or "").lower()
            tokens = [t for t in q.replace("?", " ").split() if len(t) >= 4][:6]
            hits = []
            for doc in docs[:400]:
                if not isinstance(doc, dict):
                    continue
                blob = " ".join(
                    str(doc.get(k) or "") for k in ("title", "summary", "ticker", "company", "text")
                ).lower()
                if tokens and sum(1 for t in tokens if t in blob) >= max(1, min(2, len(tokens))):
                    hits.append(doc)
                if len(hits) >= 3:
                    break
            if not hits:
                return empty_result(self.spec.id, t0, "kip_no_match")
            titles = [str(h.get("title") or h.get("id") or "doc")[:80] for h in hits]
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.45,
                t0=t0,
                summary=f"Legacy KIP matched {len(hits)} document(s) (fallback).",
                why=[f"KIP doc: {t}" for t in titles],
                evidence=[{"source": "legacy_kip", "title": t} for t in titles],
                facts=[{"field": "kip_hit_count", "value": len(hits)}],
                raw={"hits": [{"title": h.get("title"), "ticker": h.get("ticker")} for h in hits]},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
