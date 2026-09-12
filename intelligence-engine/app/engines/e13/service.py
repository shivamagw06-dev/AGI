"""E13 service — FeatureSnapshot + E01/E14 → E13Fundamental → EngineState."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e13.features.builder import FundamentalFeatureBuilder
from app.engines.e13.flags import E13Flags
from app.engines.e13.fundamental import E13Fundamental, fundamental_from_row
from app.engines.e13.mapping import FORMULA_ID, MODEL_VERSION, P0_PILLARS
from app.engines.e13.metrics import E13Metrics, Timer
from app.engines.e13.models.scorer import compute_universe_scores
from app.engines.e13.state_builder import build_e13_state
from app.engines.e13.store import E13StateStore
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E13Service:
    """Passive consumer. No MarketDataClient. No polling. No ML / NLP / moat."""

    NODE_ID = "E13_FUND"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        e01: E01Service | None = None,
        e14: E14Service | None = None,
        store: E13StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E13Flags | None = None,
        default_universe_id: str = "NSE_INVESTABLE_L1",
    ) -> None:
        self.registry = registry
        self.e01 = e01
        self.e14 = e14
        self.builder = FundamentalFeatureBuilder(registry)
        self.store = store or E13StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E13Flags.from_settings()
        self.metrics = E13Metrics()
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
    ) -> dict[str, E13Fundamental]:
        timer = Timer()
        if not self.flags.e13_p0:
            raise RuntimeError("E13_P0 is disabled")
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
                    **panel.metrics,
                }

            rows = compute_universe_scores(built)
            e01_ref = _ref_e01(e01_state)
            e14_ref = _ref_e14(e14_state)
            uid = universe_id or self.default_universe_id
            conf_adj = 1.0
            if e14_state is not None:
                conf_adj = float((e14_state.metadata or {}).get("confidence_adjustment") or 1.0)

            out: dict[str, E13Fundamental] = {}
            for sym, row in rows.items():
                digest = _sha(
                    {
                        "symbol": sym,
                        "as_of": as_of,
                        "composite_score": row.composite_score,
                        "pillar_scores": row.pillar_scores,
                        "model_version": MODEL_VERSION,
                        "formula_id": FORMULA_ID,
                    }
                )
                fund = fundamental_from_row(
                    row,
                    universe_id=uid,
                    e01_ref=e01_ref,
                    e14_ref=e14_ref,
                    digest=digest,
                )
                state = build_e13_state(
                    fund,
                    generated_at=generated_at or datetime.now(timezone.utc),
                    flags=self._flag_map(),
                    confidence_value=min(1.0, fund.confidence * conf_adj),
                )
                errors = validate_engine_state(state.model_dump(mode="json"))
                if errors:
                    raise ValueError(f"E13State schema invalid for {sym}: {errors[:3]}")
                if persist:
                    self.store.put(fund, state)
                out[sym] = fund

            self._record_orch(as_of=as_of, n=len(out), latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return out
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, n=0, latency_ms=timer.ms(), ok=False)
            raise

    def get_fundamental(self, symbol: str, as_of: str | None = None) -> E13Fundamental | None:
        timer = Timer()
        fund = self.store.get_fundamental(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=fund is not None)
        return fund

    def get_state(self, symbol: str, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, symbol: str, limit: int = 50) -> list[EngineState]:
        return self.store.history(symbol, limit=limit)

    def on_feature_ready(
        self,
        *,
        as_of: str,
        symbol: str | None = None,
        snapshot: FeatureSnapshot | None = None,
    ) -> dict[str, E13Fundamental] | None:
        if not self.flags.e13_p0:
            return None
        snapshots = None
        panels = None
        if symbol and snapshot is not None:
            snapshots = {symbol.upper(): snapshot}
        elif symbol and symbol.upper() in self._panels:
            panels = {symbol.upper(): self._panels[symbol.upper()]}
        elif not self._panels and snapshot is None:
            return None
        log.info("e13_consume_feature_ready", extra={"extra": {"as_of": as_of, "symbol": symbol}})
        return self.run_universe(as_of=as_of, panels=panels, snapshots=snapshots)

    def on_e01_ready(self, e01_state: EngineState) -> dict[str, E13Fundamental] | None:
        if not self.flags.e13_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e01_state.as_of, e01_state=e01_state)

    def on_e14_ready(self, e14_state: EngineState) -> dict[str, E13Fundamental] | None:
        if not self.flags.e13_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e14_state.as_of, e14_state=e14_state)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e13_p0,
            "service": "e13-equity-fundamental-ls",
            "engine": "E13",
            "node_id": self.NODE_ID,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": ["FeatureSnapshot", "E01State", "E14State"],
            "market_data_access": False,
            "polling": False,
            "pillars": list(P0_PILLARS),
            "formula_id": FORMULA_ID,
            "ml": False,
            "analyst_nlp": False,
            "moat_classifier": False,
        }

    def _flag_map(self) -> dict[str, bool]:
        return {
            "E13_P0": self.flags.e13_p0,
            "E13_REVISIONS": self.flags.e13_revisions,
            "E13_MOAT": self.flags.e13_moat,
            "E13_ML": self.flags.e13_ml,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.e13_revisions:
            from app.engines.e13.models import revisions as _r

            _r.revisions_disabled()
        if self.flags.e13_moat:
            from app.engines.e13.models import moat as _m

            _m.moat_disabled()
        if self.flags.e13_ml:
            from app.engines.e13.models import ml as _ml

            _ml.ml_disabled()

    def _record_orch(self, *, as_of: str, n: int, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e13_fundamental",
            as_of=as_of,
            trigger_reason="feature_e01_e14_ready",
            allow_parallel=True,
        )
        try:
            if "E13_FUND" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "E13_FUND",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"symbols": n},
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
