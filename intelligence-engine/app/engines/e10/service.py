"""E10 service — L4Opinion + E14State + E02Exposure → model E10Portfolio."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.service import E02Service
from app.engines.e10.builder import build_portfolio
from app.engines.e10.flags import E10Flags
from app.engines.e10.mapping import TOP_N_DEFAULT
from app.engines.e10.metrics import E10Metrics, Timer
from app.engines.e10.portfolio import E10Portfolio
from app.engines.e10.state_builder import build_e10_state
from app.engines.e10.store import E10StateStore
from app.engines.e14.service import E14Service
from app.engines.l4.opinion import L4Opinion
from app.engines.l4.service import L4Service
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E10Service:
    """Passive model-portfolio builder. No MarketDataClient. No execution."""

    NODE_ID = "E10_PORTFOLIO"

    def __init__(
        self,
        *,
        l4: L4Service | None = None,
        e14: E14Service | None = None,
        e02: E02Service | None = None,
        store: E10StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E10Flags | None = None,
        default_universe_id: str = "NIFTY500",
        top_n: int = TOP_N_DEFAULT,
    ) -> None:
        self.l4 = l4
        self.e14 = e14
        self.e02 = e02
        self.store = store or E10StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E10Flags.from_settings()
        self.metrics = E10Metrics()
        self.default_universe_id = default_universe_id
        self.top_n = top_n

    def run(
        self,
        *,
        as_of: str,
        opinions: dict[str, L4Opinion] | None = None,
        exposures: dict[str, E02Exposure] | None = None,
        e14_state: EngineState | None = None,
        universe_id: str | None = None,
        top_n: int | None = None,
        sigma_overrides: dict[str, float] | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> E10Portfolio:
        timer = Timer()
        if not self.flags.e10_p0:
            raise RuntimeError("E10_P0 is disabled")
        self._gate_placeholders()

        try:
            if e14_state is None and self.e14 is not None:
                e14_state = self.e14.get_state(as_of=as_of) or self.e14.get_state()
            if opinions is None:
                opinions = self.l4.list_opinions(as_of=as_of) if self.l4 is not None else {}
            if exposures is None:
                exposures = {}
                if self.e02 is not None:
                    for sym in opinions:
                        exp = self.e02.get_exposure(sym, as_of=as_of)
                        if exp is not None:
                            exposures[sym.upper()] = exp

            portfolio = build_portfolio(
                as_of=as_of,
                opinions=opinions,
                exposures=exposures,
                e14=e14_state,
                universe_id=universe_id or self.default_universe_id,
                top_n=top_n if top_n is not None else self.top_n,
                sigma_overrides=sigma_overrides,
            )
            state = build_e10_state(
                portfolio,
                generated_at=generated_at or datetime.now(timezone.utc),
                flags=self._flag_map(),
            )
            errors = validate_engine_state(state.model_dump(mode="json"))
            if errors:
                raise ValueError(f"E10State schema invalid: {errors[:3]}")
            if persist:
                self.store.put(portfolio, state)
            self._record_orch(as_of=as_of, n=len(portfolio.weights), latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return portfolio
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, n=0, latency_ms=timer.ms(), ok=False)
            raise

    def get_portfolio(self, as_of: str | None = None) -> E10Portfolio | None:
        timer = Timer()
        port = self.store.get_portfolio(as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=port is not None)
        return port

    def get_state(self, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, limit: int = 50) -> list[EngineState]:
        return self.store.history(limit=limit)

    def on_l4_ready(
        self,
        opinions: dict[str, L4Opinion] | L4Opinion | None,
        *,
        as_of: str | None = None,
    ) -> E10Portfolio | None:
        if not self.flags.e10_p0:
            return None
        if isinstance(opinions, L4Opinion):
            day = as_of or opinions.as_of
            # Rebuild from full L4 book when available
            book = self.l4.list_opinions(as_of=day) if self.l4 is not None else {opinions.symbol: opinions}
            if opinions.symbol.upper() not in book:
                book[opinions.symbol.upper()] = opinions
            log.info("e10_consume_l4_ready", extra={"extra": {"as_of": day, "n": len(book)}})
            return self.run(as_of=day, opinions=book)
        if not opinions:
            return None
        day = as_of or next(iter(opinions.values())).as_of
        log.info("e10_consume_l4_ready", extra={"extra": {"as_of": day, "n": len(opinions)}})
        return self.run(as_of=day, opinions=opinions)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e10_p0,
            "service": "e10-portfolio-construction",
            "engine": "E10",
            "node_id": self.NODE_ID,
            "mode": "model_portfolio",
            "execution": False,
            "broker_integration": False,
            "order_routing": False,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": ["L4Opinion", "E14State", "E02Exposure"],
            "market_data_access": False,
            "feature_snapshot_access": False,
            "polling": False,
            "solver": "AM_INVVOL",
        }

    def _flag_map(self) -> dict[str, bool]:
        return {
            "E10_P0": self.flags.e10_p0,
            "E10_OPTIMIZER": self.flags.e10_optimizer,
            "E10_HRP": self.flags.e10_hrp,
            "E10_MVO": self.flags.e10_mvo,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.e10_optimizer:
            from app.engines.e10.placeholders import optimizer as _o

            _ = _o
        if self.flags.e10_mvo:
            from app.engines.e10.placeholders import mvo as _m

            _ = _m
        if self.flags.e10_hrp:
            from app.engines.e10.placeholders import hrp as _h

            _ = _h

    def _record_orch(self, *, as_of: str, n: int, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e10_portfolio",
            as_of=as_of,
            trigger_reason="l4_ready",
            allow_parallel=True,
        )
        try:
            if "E10_PORTFOLIO" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "E10_PORTFOLIO",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"positions": n, "execution": False},
                )
        except KeyError:
            pass
        self.orch_ledger.finish(run.run_id, "succeeded" if ok else "failed")
