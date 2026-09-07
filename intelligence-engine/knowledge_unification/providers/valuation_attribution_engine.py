"""KUL provider — Valuation Attribution / Research Intelligence Engine (VARIE)."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MARKERS = (
    "premium",
    "discount",
    "attribute",
    "attribution",
    "why",
    "explain",
    "expensive",
    "cheap",
    "driver",
    "decompose",
    "break down",
    "relative to",
    "sector",
    "industry",
    "history",
    "compare",
    "valuation",
    "analyze",
    "institutional",
    "compounder",
    "outlook",
)


class ValuationAttributionEngineProvider:
    spec = ProviderSpec(
        id="valuation_attribution_engine",
        label="Valuation Attribution Engine",
        coverage=(
            "Decomposes valuation premium/discount into quality, growth, ownership, "
            "macro and history factors from warehouse + HVIE — descriptive only"
        ),
        priority=6,
        supported_question_types=(
            "valuation", "attribution", "company", "investment", "comparison", "historical",
        ),
        typical_latency_ms=220,
        confidence_ceiling=0.88,
    )

    def health_check(self) -> str:
        try:
            from valuation_attribution_engine.production import company  # noqa: F401

            return "ok"
        except Exception:
            return "degraded"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        qlow = (plan.question or "").lower()
        if not any(m in qlow for m in _MARKERS):
            return empty_result(self.spec.id, t0, "not_an_attribution_question")
        ticker = (plan.ticker_hint or "").strip().upper()
        if not ticker:
            return empty_result(self.spec.id, t0, "no_company_for_varie")
        try:
            from valuation_attribution_engine.production import company as varie_company
            from valuation_attribution_engine.production import peer as varie_peer

            pack = varie_company(ticker) or {}
            peer_tk = None
            # Soft peer for comparison questions: second alias if present.
            if "compare" in qlow or " versus " in qlow or " vs " in qlow:
                for name, tk in (("tcs", "TCS"), ("infosys", "INFY"), ("wipro", "WIPRO")):
                    if name in qlow and tk != ticker:
                        peer_tk = tk
                        break
            peer_pack = None
            if peer_tk:
                try:
                    peer_pack = varie_peer(ticker, peer_symbol=peer_tk)
                except Exception:
                    peer_pack = None
                if not isinstance(peer_pack, dict):
                    peer_pack = None
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not isinstance(pack, dict) or not pack.get("ok"):
            err = pack.get("error") if isinstance(pack, dict) else "varie_empty"
            return empty_result(self.spec.id, t0, str(err or "varie_empty"))

        snap = pack.get("snapshot") if isinstance(pack.get("snapshot"), dict) else {}
        note = pack.get("research_note") or pack.get("summary") or ""
        if not isinstance(note, str):
            note = str(note or "")
        summary = note or (
            f"{ticker} valuation attribution — premium {snap.get('premium_pct')}% "
            f"vs history (percentile {snap.get('historical_percentile')})."
        )
        why_raw = pack.get("why") or []
        why = [str(w) for w in why_raw if w][:8] if isinstance(why_raw, list) else []
        expl_raw = pack.get("explainability")
        expl = expl_raw if isinstance(expl_raw, dict) else {
            "observed": why[:3],
            "derived": [f"premium_pct={snap.get('premium_pct')}"],
            "inferred": [note[:240]] if note else [],
        }
        conf_raw = pack.get("confidence")
        if isinstance(conf_raw, dict):
            conf_score = float(conf_raw.get("score") or 0.7)
        else:
            try:
                conf_score = float(conf_raw or 0.7)
            except (TypeError, ValueError):
                conf_score = 0.7
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=conf_score,
            t0=t0,
            summary=str(summary)[:1200],
            why=why,
            evidence=[{
                "source": "valuation_attribution_engine",
                "title": f"varie:{ticker}",
                "explainability": expl,
            }],
            facts=[
                {"field": "premium_pct", "value": snap.get("premium_pct"), "source": "varie"},
                {"field": "historical_percentile", "value": snap.get("historical_percentile"), "source": "varie"},
            ],
            raw={
                "engine": "valuation_attribution_engine",
                "symbol": ticker,
                "factors": (pack.get("factors") or [])[:8] if isinstance(pack.get("factors"), list) else [],
                "peer": peer_pack if isinstance(peer_pack, dict) and peer_pack.get("ok") else None,
            },
        )
