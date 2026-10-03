"""E01 service — FeatureSnapshot → threshold classify → EngineState → ledger/cache."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.features.builder import E01FeatureBuilder, FeatureVector
from app.engines.e01.flags import E01Flags
from app.engines.e01.metrics import E01Metrics, Timer
from app.engines.e01.state_builder import build_e01_state
from app.engines.e01.store import E01StateStore
from app.features.models import FeatureSnapshot, FeatureValue, utcnow
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E01Service:
    """Passive FeatureSnapshot consumer. No market-data access. No polling."""

    NODE_ID = "E01_MACRO"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        store: E01StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E01Flags | None = None,
    ) -> None:
        self.registry = registry
        self.builder = E01FeatureBuilder(registry)
        self.store = store or E01StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E01Flags.from_settings()
        self.metrics = E01Metrics()
        self._prior_cycle: str | None = None

    def run(
        self,
        *,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> EngineState:
        timer = Timer()
        if not self.flags.e01_p0:
            raise RuntimeError("E01_P0 is disabled")

        # Hard-gate non-P0 paths
        if self.flags.e01_hmm:
            from app.engines.e01.models import hmm_regime

            _ = hmm_regime  # pragma: no cover — flag default false
        if self.flags.e01_ml:
            from app.engines.e01.models import ml

            _ = ml  # pragma: no cover

        try:
            fv = self.builder.build(as_of=as_of, snapshot=snapshot)
            state = build_e01_state(
                fv,
                prior_cycle=self._prior_cycle,
                generated_at=generated_at or datetime.now(timezone.utc),
                flags={
                    "E01_P0": self.flags.e01_p0,
                    "E01_HMM": self.flags.e01_hmm,
                    "E01_ML": self.flags.e01_ml,
                },
            )
            errors = validate_engine_state(state.model_dump(mode="json"))
            if errors:
                raise ValueError(f"E01State schema invalid: {errors[:3]}")

            if persist:
                self.store.put(state)
            self._prior_cycle = state.metadata.get("axes", {}).get("R_CYCLE", {}).get("state")
            self._record_orch(state, latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return state
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch_failed(as_of=as_of, latency_ms=timer.ms())
            raise

    def get_state(self, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        if as_of:
            state = self.store.get(as_of)
        else:
            state = self.store.current()
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, limit: int = 50) -> list[EngineState]:
        return self.store.history(limit=limit)

    def on_feature_ready(self, ready: Any, snapshot: FeatureSnapshot | None = None) -> EngineState | None:
        """ORCH L2 ready-event handler — passive consumer, no polling."""
        if not self.flags.e01_p0:
            return None
        # Prefer snapshot from caller; else rebuild empty and rely on registry PIT
        as_of = getattr(ready, "as_of", None) or (snapshot.as_of if snapshot else None)
        if as_of is None:
            return None
        as_of_s = str(as_of)[:10]
        # Only react when macro-relevant features present or snapshot provided
        feature_ids = set(getattr(ready, "feature_ids", []) or [])
        macro_hit = any(fid.startswith("MACRO_") or fid.startswith("VOL_") for fid in feature_ids)
        if snapshot is None and not macro_hit and feature_ids:
            return None
        log.info(
            "e01_consume_feature_ready",
            extra={"extra": {"as_of": as_of_s, "batch_id": getattr(ready, "batch_id", None)}},
        )
        return self.run(as_of=as_of_s, snapshot=snapshot)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e01_p0,
            "service": "e01-macro-regime",
            "engine": "E01",
            "node_id": self.NODE_ID,
            "flags": {
                "E01_P0": self.flags.e01_p0,
                "E01_HMM": self.flags.e01_hmm,
                "E01_ML": self.flags.e01_ml,
            },
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": "FeatureSnapshot",
            "market_data_access": False,
            "polling": False,
        }

    def _record_orch(self, state: EngineState, *, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e01_macro",
            as_of=state.as_of,
            trigger_reason="feature_ready",
            allow_parallel=True,
        )
        self.orch_ledger.complete_node(
            run.run_id,
            self.NODE_ID,
            "succeeded" if ok else "failed",
            latency_ms=int(latency_ms),
            input_hash=state.input_hash,
            output_hash=state.hash,
            detail={
                "primary_regime": state.metadata.get("primary_regime"),
                "macro_score": state.metadata.get("macro_score"),
            },
        )
        self.orch_ledger.finish(run.run_id, "succeeded" if ok else "failed")

    def _record_orch_failed(self, *, as_of: str, latency_ms: float) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e01_macro",
            as_of=as_of,
            trigger_reason="feature_ready_error",
            allow_parallel=True,
        )
        self.orch_ledger.complete_node(
            run.run_id,
            self.NODE_ID,
            "failed",
            latency_ms=int(latency_ms),
            error_code="E01_RUN_FAILED",
        )
        self.orch_ledger.finish(run.run_id, "failed")


def snapshot_from_macro_dict(as_of: str, values: dict[str, float]) -> FeatureSnapshot:
    """Test/helper: build a FeatureSnapshot of E01 feature_ids (Feature Registry shape)."""
    fvs: dict[str, FeatureValue] = {}
    available = utcnow()
    for fid, val in values.items():
        fvs[fid] = FeatureValue(
            feature_id=fid,
            formula_version="1.0.0",
            symbol=None,
            as_of=as_of,
            available_at=available,
            value=val,
            source="feature_registry",
            quality_flag="ok",
        )
    return FeatureSnapshot(snapshot_id="fixture", as_of=as_of, values=fvs)
