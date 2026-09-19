"""L4 service — shadow composite opinion from E01/E14/E02/E03 only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.service import E02Service
from app.engines.e03.alpha import E03Alpha
from app.engines.e03.service import E03Service
from app.engines.e11.sentiment_state import E11State
from app.engines.e11.service import E11Service
from app.engines.e14.service import E14Service
from app.engines.l4.builder import build_opinion
from app.engines.l4.collector import collect_inputs
from app.engines.l4.conflict import resolve_conflicts
from app.engines.l4.evidence import aggregate_evidence
from app.engines.l4.flags import L4Flags
from app.engines.l4.fusion.vote import fuse_shadow_vote
from app.engines.l4.metrics import L4Metrics, Timer
from app.engines.l4.opinion import L4Opinion
from app.engines.l4.shadow import ShadowComparison, build_shadow_comparison
from app.engines.l4.state_builder import build_l4_state
from app.engines.l4.store import L4StateStore
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class L4Service:
    """Passive shadow consumer. No MarketDataClient. No FeatureSnapshot. No production influence."""

    NODE_ID = "L4_COMPOSITE"

    def __init__(
        self,
        *,
        e01: E01Service | None = None,
        e14: E14Service | None = None,
        e02: E02Service | None = None,
        e03: E03Service | None = None,
        e11: E11Service | None = None,
        store: L4StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: L4Flags | None = None,
        default_universe_id: str = "NIFTY500",
    ) -> None:
        self.e01 = e01
        self.e14 = e14
        self.e02 = e02
        self.e03 = e03
        self.e11 = e11
        self.store = store or L4StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or L4Flags.from_settings()
        self.metrics = L4Metrics()
        self.default_universe_id = default_universe_id
        self._symbols: set[str] = set()

    def run(
        self,
        *,
        symbol: str,
        as_of: str,
        e01_state: EngineState | None = None,
        e14_state: EngineState | None = None,
        e02_exposure: E02Exposure | None = None,
        e03_alpha: E03Alpha | None = None,
        e11_state: E11State | None = None,
        universe_id: str | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> L4Opinion:
        timer = Timer()
        if not self.flags.l4_shadow:
            raise RuntimeError("L4_SHADOW is disabled")
        if self.flags.l4_primary:
            raise RuntimeError("L4_PRIMARY must remain false in P0 Shadow")
        self._gate_placeholders()

        try:
            sym = symbol.upper()
            if e01_state is None and self.e01 is not None:
                e01_state = self.e01.get_state(as_of=as_of) or self.e01.get_state()
            if e14_state is None and self.e14 is not None:
                e14_state = self.e14.get_state(as_of=as_of) or self.e14.get_state()
            if e02_exposure is None and self.e02 is not None:
                e02_exposure = self.e02.get_exposure(sym, as_of=as_of)
            if e03_alpha is None and self.e03 is not None:
                e03_alpha = self.e03.get_alpha(sym, as_of=as_of)
            if e11_state is None and self.e11 is not None:
                e11_state = self.e11.get_sentiment_state(sym, as_of=as_of)

            inputs = collect_inputs(
                symbol=sym,
                as_of=as_of,
                e01=e01_state,
                e14=e14_state,
                e02=e02_exposure,
                e03=e03_alpha,
                e11=e11_state,
            )
            if inputs.e03 is None and inputs.e01 is None and inputs.e14 is None:
                raise ValueError("L4 requires at least one of E03/E01/E14")

            evidence = aggregate_evidence(inputs)
            resolution = resolve_conflicts(inputs, evidence)
            fusion = fuse_shadow_vote(inputs, resolution, evidence=evidence)
            opinion = build_opinion(
                inputs,
                evidence=evidence,
                resolution=resolution,
                fusion=fusion,
                universe_id=universe_id or self.default_universe_id,
            )
            state = build_l4_state(
                opinion,
                generated_at=generated_at or datetime.now(timezone.utc),
                flags=self._flag_map(),
            )
            errors = validate_engine_state(state.model_dump(mode="json"))
            if errors:
                raise ValueError(f"L4State schema invalid: {errors[:3]}")

            shadow = build_shadow_comparison(
                opinion,
                inputs.e03,
                generated_at=generated_at or datetime.now(timezone.utc),
            )
            if persist:
                self.store.put(opinion, state, shadow)
                self.metrics.record_shadow()
            self._symbols.add(sym)
            self._record_orch(as_of=as_of, symbol=sym, latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return opinion
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, symbol=symbol, latency_ms=timer.ms(), ok=False)
            raise

    def run_symbols(
        self,
        *,
        as_of: str,
        symbols: list[str],
        **kwargs: Any,
    ) -> dict[str, L4Opinion]:
        out: dict[str, L4Opinion] = {}
        for sym in symbols:
            out[sym.upper()] = self.run(symbol=sym, as_of=as_of, **kwargs)
        return out

    def get_opinion(self, symbol: str, as_of: str | None = None) -> L4Opinion | None:
        timer = Timer()
        op = self.store.get_opinion(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=op is not None)
        return op

    def get_state(self, symbol: str, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, symbol: str, limit: int = 50) -> list[EngineState]:
        return self.store.history(symbol, limit=limit)

    def get_shadow(self, symbol: str, as_of: str | None = None) -> ShadowComparison | None:
        return self.store.get_shadow(symbol, as_of=as_of)

    def list_opinions(self, as_of: str | None = None) -> dict[str, L4Opinion]:
        """Expose latest shadow opinions for downstream model-portfolio builders (E10)."""
        return self.store.list_opinions(as_of=as_of)

    def on_e01_ready(self, e01_state: EngineState) -> dict[str, L4Opinion]:
        return self._refresh_known(as_of=e01_state.as_of, e01_state=e01_state)

    def on_e14_ready(self, e14_state: EngineState) -> dict[str, L4Opinion]:
        return self._refresh_known(as_of=e14_state.as_of, e14_state=e14_state)

    def on_e02_ready(self, exposures: dict[str, E02Exposure] | None) -> dict[str, L4Opinion]:
        if not exposures:
            return {}
        as_of = next(iter(exposures.values())).as_of
        out: dict[str, L4Opinion] = {}
        for sym, exp in exposures.items():
            self._symbols.add(sym.upper())
            out[sym.upper()] = self.run(symbol=sym, as_of=as_of, e02_exposure=exp)
        return out

    def on_e03_ready(self, alphas: dict[str, E03Alpha] | None) -> dict[str, L4Opinion]:
        if not alphas:
            return {}
        as_of = next(iter(alphas.values())).as_of
        out: dict[str, L4Opinion] = {}
        for sym, alpha in alphas.items():
            self._symbols.add(sym.upper())
            out[sym.upper()] = self.run(symbol=sym, as_of=as_of, e03_alpha=alpha)
        return out

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.l4_shadow and not self.flags.l4_primary,
            "service": "l4-composite-intelligence",
            "engine": "L4",
            "node_id": self.NODE_ID,
            "mode": "shadow",
            "production_influence": False,
            "replaces_e03": False,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": ["E01State", "E14State", "E02Exposure", "E03Alpha"],
            "market_data_access": False,
            "feature_snapshot_access": False,
            "polling": False,
        }

    def _refresh_known(self, *, as_of: str, **kwargs: Any) -> dict[str, L4Opinion]:
        if not self.flags.l4_shadow or not self._symbols:
            return {}
        out: dict[str, L4Opinion] = {}
        for sym in sorted(self._symbols):
            try:
                out[sym] = self.run(symbol=sym, as_of=as_of, **kwargs)
            except Exception as exc:
                log.warning("l4_refresh_failed", extra={"extra": {"symbol": sym, "error": str(exc)}})
        return out

    def _flag_map(self) -> dict[str, bool]:
        return {
            "L4_SHADOW": self.flags.l4_shadow,
            "L4_PRIMARY": self.flags.l4_primary,
            "L4_BAYES": self.flags.l4_bayes,
            "L4_ML": self.flags.l4_ml,
            "L4_PROBABILITY": self.flags.l4_probability,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.l4_bayes:
            from app.engines.l4.placeholders import bayes as _b

            _ = _b
        if self.flags.l4_ml:
            from app.engines.l4.placeholders import ml as _m

            _ = _m
        if self.flags.l4_probability:
            from app.engines.l4.placeholders import probability as _p

            _ = _p

    def _record_orch(self, *, as_of: str, symbol: str, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "l4_composite",
            as_of=as_of,
            trigger_reason="e01_e14_e02_e03_ready",
            allow_parallel=True,
        )
        try:
            if "L4_COMPOSITE" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "L4_COMPOSITE",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"symbol": symbol, "shadow": True},
                )
        except KeyError:
            pass
        self.orch_ledger.finish(run.run_id, "succeeded" if ok else "failed")
