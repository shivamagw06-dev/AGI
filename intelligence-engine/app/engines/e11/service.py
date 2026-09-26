"""E11 service — FeatureSnapshot + E01/E14 + SENT/NEWS → E11State soft voter."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e11.entity_map import EntityMap
from app.engines.e11.features.builder import SentimentFeatureBuilder
from app.engines.e11.flags import E11Flags
from app.engines.e11.mapping import FORMULA_ID, MODEL_VERSION, SOCIAL_WEIGHT_CAP
from app.engines.e11.metrics import E11Metrics, Timer
from app.engines.e11.models.state import compute_universe_states
from app.engines.e11.sentiment_state import E11State, e11_from_row
from app.engines.e11.soft_voter import soft_voter_contribution
from app.engines.e11.state_builder import build_e11_engine_state
from app.engines.e11.store import E11StateStore
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E11Service:
    """Passive soft-voter consumer. No MarketDataClient. News P0 only."""

    NODE_ID = "E11_SENT"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        e01: E01Service | None = None,
        e14: E14Service | None = None,
        store: E11StateStore | None = None,
        entity_map: EntityMap | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E11Flags | None = None,
        default_universe_id: str = "NSE_INVESTABLE_L1",
    ) -> None:
        self.registry = registry
        self.e01 = e01
        self.e14 = e14
        self.entity_map = entity_map or EntityMap()
        self.builder = SentimentFeatureBuilder(registry, entity_map=self.entity_map)
        self.store = store or E11StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E11Flags.from_settings()
        self.metrics = E11Metrics()
        self.default_universe_id = default_universe_id
        self._panels: dict[str, dict[str, Any]] = {}

    def run_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
        e01_state: EngineState | None = None,
        e14_state: EngineState | None = None,
        universe_id: str | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> dict[str, E11State]:
        timer = Timer()
        if not self.flags.e11_p0:
            raise RuntimeError("E11_P0 is disabled")
        self._gate_placeholders()

        try:
            if e01_state is None and self.e01 is not None:
                e01_state = self.e01.get_state(as_of=as_of) or self.e01.get_state()
            if e14_state is None and self.e14 is not None:
                e14_state = self.e14.get_state(as_of=as_of) or self.e14.get_state()

            merged_panels = dict(self._panels)
            if panels:
                for sym, meta in panels.items():
                    merged_panels[sym.upper()] = {
                        **(merged_panels.get(sym.upper()) or {}),
                        **meta,
                    }
            built = self.builder.build_universe(
                as_of=as_of,
                panels=merged_panels or None,
                snapshots=snapshots,
            )
            if not built:
                self.metrics.record_run(timer.ms(), ok=True)
                return {}

            for sym, panel in built.items():
                self._panels[sym] = {
                    "sector_id": panel.sector_id,
                    "news_tone": panel.news_tone,
                    "news_volume": panel.news_volume,
                    "news_recency_hours": panel.news_recency_hours,
                    "news_source": panel.news_source,
                    "news_docs": [
                        {
                            "doc_id": d.doc_id,
                            "tone": d.tone,
                            "age_hours": d.age_hours,
                            "source_class": d.source_class,
                            "entity_link": d.entity_link,
                            "headline": d.headline,
                        }
                        for d in panel.docs
                    ],
                }

            rows = compute_universe_states(built)
            e01_ref = _ref_e01(e01_state)
            e14_ref = _ref_e14(e14_state)
            uid = universe_id or self.default_universe_id
            conf_adj = 1.0
            if e14_state is not None:
                conf_adj = float((e14_state.metadata or {}).get("confidence_adjustment") or 1.0)
                if (e14_state.metadata or {}).get("playbook") == "hard_derisk":
                    conf_adj *= 0.85

            out: dict[str, E11State] = {}
            for sym, row in rows.items():
                digest = _sha(
                    {
                        "symbol": sym,
                        "as_of": as_of,
                        "entity_id": row.entity_id,
                        "news_score": row.news_score,
                        "composite_score": row.composite_score,
                        "reliability_weight": row.reliability_weight,
                        "decay_weight": row.decay_weight,
                        "soft_voter_weight": row.soft_voter_weight,
                        "model_version": MODEL_VERSION,
                        "formula_id": FORMULA_ID,
                    }
                )
                sent = e11_from_row(
                    row,
                    universe_id=uid,
                    e01_ref=e01_ref,
                    e14_ref=e14_ref,
                    digest=digest,
                )
                state = build_e11_engine_state(
                    sent,
                    generated_at=generated_at or datetime.now(timezone.utc),
                    flags=self._flag_map(),
                    confidence_value=min(1.0, sent.confidence * conf_adj),
                )
                errors = validate_engine_state(state.model_dump(mode="json"))
                if errors:
                    raise ValueError(f"E11State schema invalid for {sym}: {errors[:3]}")
                if persist:
                    self.store.put(sent, state)
                out[sym] = sent

            self._record_orch(as_of=as_of, n=len(out), latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return out
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, n=0, latency_ms=timer.ms(), ok=False)
            raise

    def get_sentiment_state(self, symbol: str, as_of: str | None = None) -> E11State | None:
        timer = Timer()
        sent = self.store.get_sentiment_state(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=sent is not None)
        return sent

    def get_state(self, symbol: str, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, symbol: str, limit: int = 50) -> list[EngineState]:
        return self.store.history(symbol, limit=limit)

    def soft_voter(self, symbol: str, as_of: str | None = None) -> dict[str, Any]:
        """E11-005 — contribution for L4; absent ⇒ weight 0."""
        return soft_voter_contribution(self.get_sentiment_state(symbol, as_of=as_of))

    def on_feature_ready(
        self,
        *,
        as_of: str,
        symbol: str | None = None,
        snapshot: FeatureSnapshot | None = None,
    ) -> dict[str, E11State] | None:
        if not self.flags.e11_p0:
            return None
        snapshots = None
        panels = None
        if symbol and snapshot is not None:
            snapshots = {symbol.upper(): snapshot}
        elif symbol and symbol.upper() in self._panels:
            panels = {symbol.upper(): self._panels[symbol.upper()]}
        elif not self._panels and snapshot is None:
            return None
        log.info("e11_consume_feature_ready", extra={"extra": {"as_of": as_of, "symbol": symbol}})
        return self.run_universe(as_of=as_of, panels=panels, snapshots=snapshots)

    def on_e01_ready(self, e01_state: EngineState) -> dict[str, E11State] | None:
        if not self.flags.e11_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e01_state.as_of, e01_state=e01_state)

    def on_e14_ready(self, e14_state: EngineState) -> dict[str, E11State] | None:
        if not self.flags.e11_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e14_state.as_of, e14_state=e14_state)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e11_p0,
            "service": "e11-sentiment-alternative-data",
            "engine": "E11",
            "node_id": self.NODE_ID,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "entity_map": self.entity_map.stats(),
            "metrics": self.metrics.snapshot(),
            "social_weight_cap": SOCIAL_WEIGHT_CAP,
            "consumes": [
                "FeatureSnapshot",
                "E01State",
                "E14State",
                "NEWS_*",
                "SENT_*",
            ],
            "market_data_access": False,
            "polling": False,
            "formula_id": FORMULA_ID,
            "ml": False,
            "social": False,
            "transcripts": False,
            "llm": False,
            "altdata": False,
            "soft_voter": True,
            "execution": False,
        }

    def _flag_map(self) -> dict[str, bool]:
        return {
            "E11_P0": self.flags.e11_p0,
            "E11_SOCIAL": self.flags.e11_social,
            "E11_TRANSCRIPTS": self.flags.e11_transcripts,
            "E11_LLM": self.flags.e11_llm,
            "E11_ML": self.flags.e11_ml,
            "E11_ALTDATA": self.flags.e11_altdata,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.e11_social:
            from app.engines.e11.models import social as _s

            _s.social_disabled()
        if self.flags.e11_transcripts:
            from app.engines.e11.models import transcripts as _t

            _t.transcripts_disabled()
        if self.flags.e11_llm:
            from app.engines.e11.models import llm as _l

            _l.llm_disabled()
        if self.flags.e11_ml:
            from app.engines.e11.models import ml as _m

            _m.ml_disabled()
        if self.flags.e11_altdata:
            from app.engines.e11.models import altdata as _a

            _a.altdata_disabled()

    def _record_orch(self, *, as_of: str, n: int, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e11_sentiment",
            as_of=as_of,
            trigger_reason="feature_e01_e14_ready",
            allow_parallel=True,
        )
        try:
            if "E11_SENT" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "E11_SENT",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"symbols": n},
                )
            elif "SPEC_PARALLEL" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "SPEC_PARALLEL",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"engine": "E11", "symbols": n},
                )
        except KeyError:
            pass
        self.orch_ledger.finish(run.run_id, "succeeded" if ok else "failed")


def _ref_e01(state: EngineState | None) -> dict[str, Any]:
    if state is None:
        return {}
    meta = state.metadata or {}
    return {
        "as_of": state.as_of,
        "primary_regime": meta.get("primary_regime"),
        "hash": state.hash,
    }


def _ref_e14(state: EngineState | None) -> dict[str, Any]:
    if state is None:
        return {}
    meta = state.metadata or {}
    return {
        "as_of": state.as_of,
        "playbook": meta.get("playbook"),
        "risk_level": meta.get("risk_level"),
        "confidence_adjustment": meta.get("confidence_adjustment"),
        "hash": state.hash,
    }


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
