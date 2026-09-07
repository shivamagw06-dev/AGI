"""E14 service — FeatureSnapshot + E01State → rules → EngineState / Assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, validate_engine_state
from app.core.logging import get_logger
from app.engines.e01.service import E01Service
from app.engines.e14.assessment import E14Assessment, TargetType, build_assessment
from app.engines.e14.features.builder import E14FeatureBuilder
from app.engines.e14.flags import E14Flags
from app.engines.e14.metrics import E14Metrics, Timer
from app.engines.e14.models.rules import classify
from app.engines.e14.state_builder import build_e14_state
from app.engines.e14.store import E14StateStore
from app.features.models import FeatureSnapshot, FeatureValue, utcnow
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E14Service:
    """Passive consumer of FeatureSnapshot + E01State. No MarketDataClient. No polling."""

    NODE_ID = "E14_FIRM_PRIOR"
    ASSESS_NODE_ID = "E14_ASSESS"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        e01: E01Service | None = None,
        store: E14StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E14Flags | None = None,
    ) -> None:
        self.registry = registry
        self.e01 = e01
        self.builder = E14FeatureBuilder(registry)
        self.store = store or E14StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E14Flags.from_settings()
        self.metrics = E14Metrics()

    def run(
        self,
        *,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        e01_state: EngineState | None = None,
        book: dict[str, float] | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
    ) -> EngineState:
        timer = Timer()
        if not self.flags.e14_p0:
            raise RuntimeError("E14_P0 is disabled")
        if self.flags.e14_ml:
            from app.engines.e14.models import ml as _ml

            _ = _ml
        if self.flags.e14_bayes:
            from app.engines.e14.models import bayes as _bayes

            _ = _bayes

        try:
            if e01_state is None and self.e01 is not None:
                e01_state = self.e01.get_state(as_of=as_of) or self.e01.get_state()

            fv = self.builder.build(
                as_of=as_of,
                snapshot=snapshot,
                e01_state=e01_state,
                book=book,
            )
            classification = classify(fv, e01_state=e01_state)
            state = build_e14_state(
                fv,
                classification,
                generated_at=generated_at or datetime.now(timezone.utc),
                flags={
                    "E14_P0": self.flags.e14_p0,
                    "E14_ML": self.flags.e14_ml,
                    "E14_BAYES": self.flags.e14_bayes,
                },
            )
            errors = validate_engine_state(state.model_dump(mode="json"))
            if errors:
                raise ValueError(f"E14State schema invalid: {errors[:3]}")
            if persist:
                self.store.put(state)
            self._record_orch(state, latency_ms=timer.ms(), ok=True, node_id=self.NODE_ID)
            self.metrics.record_run(timer.ms(), ok=True)
            return state
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch_failed(as_of=as_of, latency_ms=timer.ms(), node_id=self.NODE_ID)
            raise

    def assess(
        self,
        *,
        target_type: TargetType,
        target_id: str,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        e01_state: EngineState | None = None,
        target_features: dict[str, float] | None = None,
        book: dict[str, float] | None = None,
    ) -> E14Assessment:
        """Produce E14Assessment. Fail-closed when E01 missing (gate != allow for promotion)."""
        if not self.flags.e14_p0:
            raise RuntimeError("E14_P0 is disabled")
        firm = self.get_state(as_of=as_of)
        if firm is None:
            firm = self.run(
                as_of=as_of,
                snapshot=snapshot,
                e01_state=e01_state,
                book=book,
                persist=True,
            )
        if e01_state is None and self.e01 is not None:
            e01_state = self.e01.get_state(as_of=as_of) or self.e01.get_state()
        fv = self.builder.build(
            as_of=as_of,
            snapshot=snapshot,
            e01_state=e01_state,
            book=book,
        )
        classification = classify(fv, e01_state=e01_state)
        assessment = build_assessment(
            target_type=target_type,
            target_id=target_id,
            as_of=as_of,
            fv=fv,
            classification=classification,
            e14_state_hash=firm.hash,
            target_features=target_features,
        )
        # Fail-closed promotion: without E01, gate must not be allow
        if not fv.e01_present and assessment.gate == "allow":
            assessment = assessment.model_copy(update={"gate": "allow_with_haircut"})
        self.store.put_assessment(assessment)
        self.metrics.record_assessment()
        if self.orch_ledger is not None:
            run = self.orch_ledger.trigger(
                "e14_assess",
                as_of=as_of,
                trigger_reason=f"assess:{target_type}",
                allow_parallel=True,
            )
            self.orch_ledger.complete_node(
                run.run_id,
                self.ASSESS_NODE_ID,
                "succeeded",
                detail={"gate": assessment.gate, "target_id": target_id},
            )
            self.orch_ledger.finish(run.run_id, "succeeded")
        return assessment

    def get_state(self, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get(as_of) if as_of else self.store.current()
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, limit: int = 50) -> list[EngineState]:
        return self.store.history(limit=limit)

    def on_inputs_ready(
        self,
        *,
        as_of: str,
        snapshot: FeatureSnapshot | None = None,
        e01_state: EngineState | None = None,
    ) -> EngineState | None:
        """ORCH callback — passive; no polling."""
        if not self.flags.e14_p0:
            return None
        log.info("e14_consume_inputs", extra={"extra": {"as_of": as_of}})
        return self.run(as_of=as_of, snapshot=snapshot, e01_state=e01_state)

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.e14_p0,
            "service": "e14-risk-crowding",
            "engine": "E14",
            "node_id": self.NODE_ID,
            "flags": {
                "E14_P0": self.flags.e14_p0,
                "E14_ML": self.flags.e14_ml,
                "E14_BAYES": self.flags.e14_bayes,
            },
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": ["FeatureSnapshot", "E01State"],
            "market_data_access": False,
            "polling": False,
        }

    def _record_orch(self, state: EngineState, *, latency_ms: float, ok: bool, node_id: str) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e14_firm",
            as_of=state.as_of,
            trigger_reason="feature_e01_ready",
            allow_parallel=True,
        )
        self.orch_ledger.complete_node(
            run.run_id,
            node_id,
            "succeeded" if ok else "failed",
            latency_ms=int(latency_ms),
            input_hash=state.input_hash,
            output_hash=state.hash,
            detail={
                "risk_level": state.metadata.get("risk_level"),
                "playbook": state.metadata.get("playbook"),
                "gate": state.metadata.get("gate"),
            },
        )
        self.orch_ledger.finish(run.run_id, "succeeded" if ok else "failed")

    def _record_orch_failed(self, *, as_of: str, latency_ms: float, node_id: str) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e14_firm",
            as_of=as_of,
            trigger_reason="e14_error",
            allow_parallel=True,
        )
        self.orch_ledger.complete_node(
            run.run_id,
            node_id,
            "failed",
            latency_ms=int(latency_ms),
            error_code="E14_RUN_FAILED",
        )
        self.orch_ledger.finish(run.run_id, "failed")


def snapshot_from_risk_dict(as_of: str, values: dict[str, float]) -> FeatureSnapshot:
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
    return FeatureSnapshot(snapshot_id="e14-fixture", as_of=as_of, values=fvs)
