"""E03 service — FeatureSnapshot + E01/E14/E02 → SM_AGI_TECH → E03Alpha / EngineState."""

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
from app.engines.e03.features.adapter import TechnicalFeatureAdapter
from app.engines.e03.flags import E03Flags
from app.engines.e03.mapping import ALPHA_ID, MODEL_VERSION, SUBMODEL_ID
from app.engines.e03.metrics import E03Metrics, Timer
from app.engines.e03.parity.audit import ParityReport, run_parity_audit
from app.engines.e03.state_builder import build_e03_state
from app.engines.e03.store import E03StateStore
from app.engines.e03.submodels.agi_tech import run_sm_agi_tech
from app.engines.e14.service import E14Service
from app.features.models import FeatureSnapshot
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger

log = get_logger(__name__)


class E03Service:
    """Passive consumer. No MarketDataClient. No polling. P0 = SM_AGI_TECH parity only."""

    NODE_ID = "E03_XS_ALPHA"

    def __init__(
        self,
        registry: FeatureRegistryService,
        *,
        e01: E01Service | None = None,
        e14: E14Service | None = None,
        e02: E02Service | None = None,
        store: E03StateStore | None = None,
        orch_ledger: OrchLedger | None = None,
        flags: E03Flags | None = None,
        default_universe_id: str = "NIFTY500",
    ) -> None:
        self.registry = registry
        self.e01 = e01
        self.e14 = e14
        self.e02 = e02
        self.adapter = TechnicalFeatureAdapter(registry)
        self.store = store or E03StateStore()
        self.orch_ledger = orch_ledger
        self.flags = flags or E03Flags.from_settings()
        self.metrics = E03Metrics()
        self.default_universe_id = default_universe_id
        self._panels: dict[str, dict[str, Any]] = {}
        self._last_e01_ref: dict[str, Any] = {}
        self._last_e14_ref: dict[str, Any] = {}
        self._last_e02_by_symbol: dict[str, dict[str, Any]] = {}

    def run_universe(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        snapshots: dict[str, FeatureSnapshot] | None = None,
        e01_state: EngineState | None = None,
        e14_state: EngineState | None = None,
        e02_exposures: dict[str, E02Exposure] | None = None,
        universe_id: str | None = None,
        generated_at: datetime | None = None,
        persist: bool = True,
        run_parity: bool | None = None,
    ) -> dict[str, E03Alpha]:
        timer = Timer()
        if not self.flags.e03_p0:
            raise RuntimeError("E03_P0 is disabled")
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

            built = self.adapter.build_universe(
                as_of=as_of,
                panels=merged or None,
                snapshots=snapshots,
            )
            if not built:
                self.metrics.record_run(timer.ms(), ok=True)
                return {}

            for sym, panel in built.items():
                self._panels[sym] = dict(panel.indicators)

            e01_ref = _ref_e01(e01_state) or self._last_e01_ref
            e14_ref = _ref_e14(e14_state) or self._last_e14_ref
            if e01_ref:
                self._last_e01_ref = e01_ref
            if e14_ref:
                self._last_e14_ref = e14_ref
            uid = universe_id or self.default_universe_id
            conf_adj = 1.0
            if e14_ref.get("confidence_adjustment") is not None:
                conf_adj = float(e14_ref["confidence_adjustment"])
            elif e14_state is not None:
                conf_adj = float((e14_state.metadata or {}).get("confidence_adjustment") or 1.0)

            out: dict[str, E03Alpha] = {}
            for sym, panel in built.items():
                result = run_sm_agi_tech(panel.indicators)
                e02_exp = (e02_exposures or {}).get(sym) or (
                    self.e02.get_exposure(sym, as_of=as_of) if self.e02 else None
                )
                e02_ref = _ref_e02(e02_exp) or self._last_e02_by_symbol.get(sym, {})
                if e02_ref:
                    self._last_e02_by_symbol[sym] = e02_ref
                # P0: composite == agi_tech when E03_COMPOSITE=false
                # Keep production confidence_pct exact; E14 haircut applied in EngineState only.
                composite = result.agi_tech_score
                conf = min(1.0, result.confidence * conf_adj)
                digest = _sha(
                    {
                        "symbol": sym,
                        "as_of": as_of,
                        "agi_tech_score": result.agi_tech_score,
                        "model_version": MODEL_VERSION,
                        "indicators": panel.indicators,
                    }
                )
                alpha = E03Alpha(
                    as_of=as_of,
                    universe_id=uid,
                    symbol=sym,
                    sector_id=(e02_ref or {}).get("sector_id"),
                    agi_tech_score=result.agi_tech_score,
                    composite_alpha_score=composite,
                    technical_score=result.agi_tech_score,
                    label=result.label,
                    confidence=conf,
                    confidence_pct=result.confidence_pct,
                    alpha_attribution=[
                        {
                            "alpha_id": ALPHA_ID,
                            "weight": 1.0,
                            "score": result.agi_tech_score,
                            "contrib": result.agi_tech_score,
                        }
                    ],
                    family_scores={SUBMODEL_ID: result.agi_tech_score},
                    e01_ref=e01_ref,
                    e02_ref=e02_ref,
                    e14_ref=e14_ref,
                    e14_projection={
                        "confidence_adjustment": conf_adj,
                        "playbook": e14_ref.get("playbook"),
                    },
                    top_features=[
                        name
                        for name, _ in sorted(
                            result.contributions.items(),
                            key=lambda kv: abs(kv[1]),
                            reverse=True,
                        )[:5]
                    ],
                    contributions=result.contributions,
                    indicators=panel.indicators,
                    stale_inputs=list(panel.stale_inputs),
                    model_version=MODEL_VERSION,
                    submodel_id=SUBMODEL_ID,
                    hash=digest,
                )
                state = build_e03_state(
                    alpha,
                    generated_at=generated_at or datetime.now(timezone.utc),
                    flags=self._flag_map(),
                )
                errors = validate_engine_state(state.model_dump(mode="json"))
                if errors:
                    raise ValueError(f"E03State schema invalid for {sym}: {errors[:3]}")
                if persist:
                    self.store.put(alpha, state)
                out[sym] = alpha

            do_parity = self.flags.e03_parity if run_parity is None else run_parity
            if do_parity and out:
                self.run_parity_audit(as_of=as_of, generated_at=generated_at)

            self._record_orch(as_of=as_of, n=len(out), latency_ms=timer.ms(), ok=True)
            self.metrics.record_run(timer.ms(), ok=True)
            return out
        except Exception:
            self.metrics.record_run(timer.ms(), ok=False)
            self._record_orch(as_of=as_of, n=0, latency_ms=timer.ms(), ok=False)
            raise

    def run_parity_audit(
        self,
        *,
        as_of: str,
        panels: dict[str, dict[str, Any]] | None = None,
        generated_at: datetime | None = None,
    ) -> ParityReport:
        source = panels or self._panels
        report = run_parity_audit(source, as_of=as_of, generated_at=generated_at)
        self.store.put_parity(report)
        self.metrics.record_parity()
        return report

    def get_alpha(self, symbol: str, as_of: str | None = None) -> E03Alpha | None:
        timer = Timer()
        alpha = self.store.get_alpha(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=alpha is not None)
        return alpha

    def get_state(self, symbol: str, as_of: str | None = None) -> EngineState | None:
        timer = Timer()
        state = self.store.get_state(symbol, as_of=as_of)
        self.metrics.record_lookup(timer.ms(), cache_hit=state is not None)
        return state

    def history(self, symbol: str, limit: int = 50) -> list[EngineState]:
        return self.store.history(symbol, limit=limit)

    def get_parity(self) -> ParityReport | None:
        return self.store.get_parity()

    def on_feature_ready(
        self,
        *,
        as_of: str,
        symbol: str | None = None,
        snapshot: FeatureSnapshot | None = None,
    ) -> dict[str, E03Alpha] | None:
        if not self.flags.e03_p0:
            return None
        snapshots = None
        panels = None
        if symbol and snapshot is not None:
            snapshots = {symbol.upper(): snapshot}
        elif symbol and symbol.upper() in self._panels:
            panels = {symbol.upper(): self._panels[symbol.upper()]}
        elif not self._panels and snapshot is None:
            return None
        log.info("e03_consume_feature_ready", extra={"extra": {"as_of": as_of, "symbol": symbol}})
        return self.run_universe(as_of=as_of, panels=panels, snapshots=snapshots)

    def on_e01_ready(self, e01_state: EngineState) -> dict[str, E03Alpha] | None:
        if not self.flags.e03_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e01_state.as_of, e01_state=e01_state)

    def on_e14_ready(self, e14_state: EngineState) -> dict[str, E03Alpha] | None:
        if not self.flags.e03_p0 or not self._panels:
            return None
        return self.run_universe(as_of=e14_state.as_of, e14_state=e14_state)

    def on_e02_ready(self, exposures: dict[str, E02Exposure] | None) -> dict[str, E03Alpha] | None:
        if not self.flags.e03_p0 or not self._panels:
            return None
        as_of = None
        if exposures:
            for exp in exposures.values():
                as_of = exp.as_of
                break
        if as_of is None:
            # fall back to any stored panel run using latest e02
            return None
        return self.run_universe(as_of=as_of, e02_exposures=exposures)

    def health(self) -> dict[str, Any]:
        parity = self.store.get_parity()
        return {
            "ok": self.flags.e03_p0,
            "service": "e03-xs-quant",
            "engine": "E03",
            "node_id": self.NODE_ID,
            "flags": self._flag_map(),
            "store": self.store.stats(),
            "metrics": self.metrics.snapshot(),
            "consumes": ["FeatureSnapshot", "E01State", "E14State", "E02Exposure"],
            "market_data_access": False,
            "polling": False,
            "submodel": SUBMODEL_ID,
            "parity": {
                "enabled": self.flags.e03_parity,
                "passed": parity.passed if parity else None,
                "agreement_rate": parity.agreement_rate if parity else None,
                "max_drift": parity.max_drift if parity else None,
            },
        }

    def _flag_map(self) -> dict[str, bool]:
        return {
            "E03_P0": self.flags.e03_p0,
            "E03_PARITY": self.flags.e03_parity,
            "E03_COMPOSITE": self.flags.e03_composite,
            "E03_XS_MODE": self.flags.e03_xs_mode,
            "E03_ML": self.flags.e03_ml,
        }

    def _gate_placeholders(self) -> None:
        if self.flags.e03_composite:
            from app.engines.e03.submodels import composite as _c

            _ = _c
        if self.flags.e03_xs_mode:
            from app.engines.e03.submodels import xs_mode as _x

            _ = _x
        if self.flags.e03_ml:
            from app.engines.e03.submodels import ml as _m

            _ = _m

    def _record_orch(self, *, as_of: str, n: int, latency_ms: float, ok: bool) -> None:
        if self.orch_ledger is None:
            return
        run = self.orch_ledger.trigger(
            "e03_alpha",
            as_of=as_of,
            trigger_reason="feature_e01_e14_e02_ready",
            allow_parallel=True,
        )
        try:
            if "E03_XS_ALPHA" in self.orch_ledger.dag_node_ids():
                self.orch_ledger.complete_node(
                    run.run_id,
                    "E03_XS_ALPHA",
                    "succeeded" if ok else "failed",
                    latency_ms=int(latency_ms),
                    detail={"symbols": n, "submodel": SUBMODEL_ID},
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


def _ref_e02(exposure: E02Exposure | None) -> dict[str, Any]:
    if exposure is None:
        return {}
    return {
        "as_of": exposure.as_of,
        "dominant_factor": exposure.dominant_factor,
        "sector_id": exposure.sector_id,
        "composite_score": exposure.composite_score,
        "hash": exposure.hash,
    }


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
