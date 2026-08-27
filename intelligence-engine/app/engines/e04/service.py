"""E04 service — FeatureSnapshot + E01/E14/E02/E03 → E04State → EngineState."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.service import E02Service
from app.engines.e03.alpha import E03Alpha
from app.engines.e03.service import E03Service
from app.engines.e04.features.builder import RelativeValueFeatureBuilder
from app.engines.e04.flags import E04Flags
from app.engines.e04.mapping import FORMULA_ID, MODEL_VERSION
from app.engines.e04.metrics import E04Metrics, Timer
from app.engines.e04.models.state import compute_pair_states
from app.engines.e04.rv_state import E04State, e04_from_row
from app.engines.e04.state_builder import build_e04_engine_state
from app.engines.e04.store import E04StateStore
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E04Service:
    """Passive consumer. No MarketDataClient. No Kalman/ML/ETF basis/portfolio."""

    NODE_ID = "E04_RVAL"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        e01: E01Service | None = None,
        e14: E14Service | None = None,
        e02: E02Service | None = None,
        e03: E03Service | None = None,
        store: E04StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E04Flags | None = None,
        default_universe_id: str = "NSE_INVESTABLE_L1",
    ) -> None:
        self.registry = registry
        self.e01 = e01
        self.e14 = e14
        self.e02 = e02
        self.e03 = e03
        self.builder = RelativeValueFeatureBuilder(registry)
        self.store = store or E04StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E04Flags.from_settings()
        self.metrics = E04Metrics()
        self.default_universe_id = default_universe_id
        self._panels: dict[str, dict[str, Any]] = {}
        self._static_pairs: list[tuple[str, str]] = []
        self._user_pairs: list[tuple[str, str]] = []
        self._last_e02: dict[str, dict[str, Any]] = {}
        self._last_e03: dict[str, dict[str, Any]] = {}

    def set_static_pairs(self, pairs: list[tuple[str, str]]) -> None:
        self._static_pairs = [(a.upper(), b.upper()) for a, b in pairs]

    def set_user_pairs(self, pairs: list[tuple[str, str]]) -> None:
        self._user_pairs = [(a.upper(), b.upper()) for a, b in pairs]

    def run_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
        user_pairs: list[tuple[str, str]] | None = None,
        static_pairs: list[tuple[str, str]] | None = None,
        e01_state: EngineState | None = None,
        e14_state: EngineState | None = None,
        e02_exposures: dict[str, E02Exposure] | None = None,
        e03_alphas: dict[str, E03Alpha] | None = None,
        universe_id: str | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> dict[str, E04State]:
        timer = Timer()
        if not self.flags.e04_p0:
            raise RuntimeError("E04_P0 is disabled")
        self._gate_placeholders()

        try:
            if e01_state is None and self.e01 is not None:
                e01_state = self.e01.get_state(as_of=as_of) or self.e01.get_state()
            if e14_state is None and self.e14 is not None:
                e14_state = self.e14.get_state(as_of=as_of) or self.e14.get_state()

            merged = dict(self._panels)
            if panels:
                for sym, meta in panels.items():
                    merged[sym.upper()] = {**(merged.get(sym.upper()) or {}), **meta}
            # Enrich sector from E02 if available
            if e02_exposures:
                for sym, exp in e02_exposures.items():
                    self._last_e02[sym.upper()] = {
                        "dominant_factor": exp.dominant_factor,
                        "composite_score": exp.composite_score,
                        "hash": exp.hash,
                    }
                    merged.setdefault(sym.upper(), {})
                    if exp.sector_id:
                        merged[sym.upper()].setdefault("sector_id", exp.sector_id)
            elif self.e02 is not None:
                # Pull cached exposures when wired
                pass
            if e03_alphas:
                for sym, alpha in e03_alphas.items():
                    self._last_e03[sym.upper()] = {
                        "label": alpha.label,
                        "score": alpha.agi_tech_score,
                        "hash": alpha.hash,
                    }

            built = self.builder.build_pairs(
                as_of=as_of,
                symbol_panels=merged or None,
                snapshots=snapshots,
                user_pairs=user_pairs or self._user_pairs or None,
                static_pairs=static_pairs or self._static_pairs or None,
            )
            if not built:
                self.metrics.record_run(timer.ms(), ok=True)
                return {}

            for sym, panel_meta in merged.items():
                self._panels[sym] = dict(panel_meta)

            rows = compute_pair_states(built)
            e01_ref = _ref_e01(e01_state)
            e14_ref = _ref_e14(e14_state)
            uid = universe_id or self.default_universe_id
            conf_adj = 1.0
            if e14_state is not None:
                conf_adj = float((e14_state.metadata or {}).get("confidence_adjustment") or 1.0)

            out: dict[str, E04State] = {}
            for pid, row in rows.items():
                e02_ref = {
                    "legs": {
                        row.leg_a: self._last_e02.get(row.leg_a, {}),
                        row.leg_b: self._last_e02.get(row.leg_b, {}),
                    }
                }
                e03_ref = {
                    "legs": {
                        row.leg_a: self._last_e03.get(row.leg_a, {}),
                        row.leg_b: self._last_e03.get(row.leg_b, {}),
                    }
                }
                digest = _sha(
                    {
                        "pair_id": pid,
                        "as_of": as_of,
                        "hedge_beta": row.hedge_beta,
                        "z_score": row.z_score,
                        "cointegrated": row.cointegrated,
                        "half_life": row.half_life,
                        "composite_score": row.composite_score,
                        "model_version": MODEL_VERSION,
                        "formula_id": FORMULA_ID,
                    }
                )
                rv = e04_from_row(
                    row,
                    universe_id=uid,
                    e01_ref=e01_ref,
                    e14_ref=e14_ref,
                    e02_ref=e02_ref,
                    e03_ref=e03_ref,
                    digest=digest,
                )
                state = build_e04_engine_state(
                    rv,
                    generated_at=generated_at or datetime.now(timezone.utc),
                    flags=self._flag_map(),
                    confidence_value=min(1.0, rv.confidence * conf_adj),
                )
                errors = validate_engine_state(state.model_dump(mode="json"))
                if errors:
                    raise ValueError(f"E04State schema invalid for {pid}: {errors[:3]}")
                if persist:
                    self.store.put(rv, state)
                out[pid] = rv

            self._record_orch(as_of=as_of, n=len(out), latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return out
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, n=0, latency_ms=timer.ms(), ok=False)
            raise

    def get_rv_state(self, pair: str, as_of: str | None = None) -> E04State | None:
        timer = Timer()
        rv = self.store.get_rv_state(pair, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=rv is not None)
        return rv

    def get_state(self, pair: str, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(pair, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, pair: str, limit: int = 50) -> list[EngineState]:
        return self.store.history(pair, limit=limit)

    def on_feature_ready(
        self,
        *,
        as_of: str,
        symbol: str | None = None,
        snapshot: FeatureSnapshot | None = None,
    ) -> dict[str, E04State] | None:
        if not self.flags.e04_p0:
            return None
        snapshots = None
        panels = None
        if symbol and snapshot is not None:
            snapshots = {symbol.upper(): snapshot}
        elif symbol and symbol.upper() in self._panels:
            panels = {symbol.upper(): self._panels[symbol.upper()]}
        elif not self._panels and snapshot is None:
            return None
        log.info("e04_consume_feature_ready", extra={"extra": {"as_of": as_of, "symbol": symbol}})
        return self.run_universe(as_of=as_of, panels=panels, snapshots=snapshots)

    def on_e01_ready(self, e01_state: EngineState) -> dict[str, E04State] | None:
        if not self.flags.e04_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e01_state.as_of, e01_state=e01_state)

    def on_e14_ready(self, e14_state: EngineState) -> dict[str, E04State] | None:
        if not self.flags.e04_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e14_state.as_of, e14_state=e14_state)

    def on_e02_ready(self, exposures: dict[str, E02Exposure]) -> dict[str, E04State] | None:
        if not self.flags.e04_p0 or not exposures:
            return None
        as_of = next(iter(exposures.values())).as_of
        return self.run_universe(as_of=as_of, e02_exposures=exposures)

    def on_e03_ready(self, alphas: dict[str, E03Alpha]) -> dict[str, E04State] | None:
        if not self.flags.e04_p0 or not alphas:
            return None
        as_of = next(iter(alphas.values())).as_of
        # Need panels — seed from alpha symbols if empty
        if not self._panels:
            for sym in alphas:
                self._panels[sym.upper()] = {"sector_id": None}
        return self.run_universe(as_of=as_of, e03_alphas=alphas)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e04_p0,
            "service": "e04-stat-arb-relative-value",
            "engine": "E04",
            "node_id": self.NODE_ID,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": [
                "FeatureSnapshot",
                "E01State",
                "E14State",
                "E02Exposure",
                "E03Alpha",
                "RVAL_*",
            ],
            "market_data_access": False,
            "polling": False,
            "formula_id": FORMULA_ID,
            "ml": False,
            "kalman": False,
            "dynamic_hedge": False,
            "etf_basis": False,
            "portfolio_construction": False,
            "execution": False,
        }

    def _flag_map(self) -> dict[str, bool]:
        return {
            "E04_P0": self.flags.e04_p0,
            "E04_KALMAN": self.flags.e04_kalman,
            "E04_DYNAMIC_HEDGE": self.flags.e04_dynamic_hedge,
            "E04_ETF_BASIS": self.flags.e04_etf_basis,
            "E04_ML": self.flags.e04_ml,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.e04_kalman:
            from app.engines.e04.models import kalman as _k

            _k.kalman_disabled()
        if self.flags.e04_dynamic_hedge:
            from app.engines.e04.models import dynamic_hedge as _d

            _d.dynamic_hedge_disabled()
        if self.flags.e04_etf_basis:
            from app.engines.e04.models import etf_basis as _e

            _e.etf_basis_disabled()
        if self.flags.e04_ml:
            from app.engines.e04.models import ml as _m

            _m.ml_disabled()

    def _record_orch(self, *, as_of: str, n: int, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e04_relative_value",
            as_of=as_of,
            trigger_reason="feature_e01_e14_e02_e03_ready",
            allow_parallel=True,
        )
        try:
            if "E04_RVAL" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "E04_RVAL",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"pairs": n},
                )
            elif "SPEC_PARALLEL" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "SPEC_PARALLEL",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"engine": "E04", "pairs": n},
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
