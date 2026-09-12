"""BT-003 Historical Engine Runner — isolated E01→E14→E02→E13→E08→E09→E05→E11→E03→E04→L4→E10 chain.

Creates fresh engine instances so replay never mutates production singletons.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.engines.e01.mapping import MODEL_VERSION as E01_MODEL
from app.engines.e01.service import E01Service, snapshot_from_macro_dict
from app.engines.e02.mapping import MODEL_VERSION as E02_MODEL
from app.engines.e02.service import E02Service
from app.engines.e03.mapping import MODEL_VERSION as E03_MODEL
from app.engines.e03.service import E03Service
from app.engines.e04.mapping import FORMULA_ID as E04_FORMULA
from app.engines.e04.mapping import MODEL_VERSION as E04_MODEL
from app.engines.e04.service import E04Service
from app.engines.e05.mapping import FORMULA_ID as E05_FORMULA
from app.engines.e05.mapping import MODEL_VERSION as E05_MODEL
from app.engines.e05.service import E05Service
from app.engines.e11.mapping import FORMULA_ID as E11_FORMULA
from app.engines.e11.mapping import MODEL_VERSION as E11_MODEL
from app.engines.e11.service import E11Service
from app.engines.e08.mapping import FORMULA_ID as E08_FORMULA
from app.engines.e08.mapping import MODEL_VERSION as E08_MODEL
from app.engines.e08.service import E08Service
from app.engines.e09.mapping import FORMULA_ID as E09_FORMULA
from app.engines.e09.mapping import MODEL_VERSION as E09_MODEL
from app.engines.e09.service import E09Service
from app.engines.e10.mapping import MODEL_VERSION as E10_MODEL
from app.engines.e10.service import E10Service
from app.engines.e13.mapping import FORMULA_ID as E13_FORMULA
from app.engines.e13.mapping import MODEL_VERSION as E13_MODEL
from app.engines.e13.service import E13Service
from app.engines.e14.mapping import MODEL_VERSION as E14_MODEL
from app.engines.e14.service import E14Service, snapshot_from_risk_dict
from app.engines.l4.mapping import MODEL_VERSION as L4_MODEL
from app.engines.l4.service import L4Service
from app.features.service import FeatureRegistryService
from app.orch.ledger import OrchLedger
from app.validation.golden.loader import GoldenDay
from app.validation.models import ReplayDaySlice

FIXED_TS = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


class HistoricalEngineRunner:
    """Run one as-of day through the frozen institutional DAG (replay kind)."""

    def __init__(self, *, universe_id: str = "NIFTY500") -> None:
        self.universe_id = universe_id
        self.registry = FeatureRegistryService()
        self.ledger = OrchLedger()
        self.e01 = E01Service(self.registry, orch_ledger=self.ledger)
        self.e14 = E14Service(self.registry, e01=self.e01, orch_ledger=self.ledger)
        self.e02 = E02Service(self.registry, e01=self.e01, e14=self.e14, orch_ledger=self.ledger)
        self.e13 = E13Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e08 = E08Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e09 = E09Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e05 = E05Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e11 = E11Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e03 = E03Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            e02=self.e02,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e04 = E04Service(
            self.registry,
            e01=self.e01,
            e14=self.e14,
            e02=self.e02,
            e03=self.e03,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.l4 = L4Service(
            e01=self.e01,
            e14=self.e14,
            e02=self.e02,
            e03=self.e03,
            e11=self.e11,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )
        self.e10 = E10Service(
            l4=self.l4,
            e14=self.e14,
            e02=self.e02,
            orch_ledger=self.ledger,
            default_universe_id=universe_id,
        )

    def engine_versions(self) -> dict[str, str]:
        return {
            "E01": E01_MODEL,
            "E14": E14_MODEL,
            "E02": E02_MODEL,
            "E13": E13_MODEL,
            "E08": E08_MODEL,
            "E09": E09_MODEL,
            "E05": E05_MODEL,
            "E11": E11_MODEL,
            "E03": E03_MODEL,
            "E04": E04_MODEL,
            "L4": L4_MODEL,
            "E10": E10_MODEL,
        }

    def formula_versions(self) -> dict[str, str]:
        # Feature registry formula versions for registered calculators
        out: dict[str, str] = {}
        for meta in self.registry.list_features():
            out[meta.feature_id] = meta.formula_version
        out["SM_AGI_TECH"] = E03_MODEL
        out["FM_AGI_FUND"] = E13_FORMULA
        out["VM_AGI_VOL"] = E08_FORMULA
        out["TM_AGI_CTA"] = E09_FORMULA
        out["EM_AGI_EVENT"] = E05_FORMULA
        out["SM_AGI_SENT"] = E11_FORMULA
        out["RV_AGI_PAIR"] = E04_FORMULA
        out["AM_INVVOL"] = E10_MODEL
        return out

    def run_day(self, day: GoldenDay, *, generated_at: datetime | None = None) -> ReplayDaySlice:
        ts = generated_at or FIXED_TS
        macro_snap = snapshot_from_macro_dict(day.as_of, day.macro_features)
        risk_snap = snapshot_from_risk_dict(day.as_of, day.risk_features)

        e01_state = self.e01.run(as_of=day.as_of, snapshot=macro_snap, generated_at=ts)
        e14_state = self.e14.run(
            as_of=day.as_of,
            snapshot=risk_snap,
            e01_state=e01_state,
            generated_at=ts,
        )
        e02_exps = self.e02.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e13_funds = self.e13.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e08_states = self.e08.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e09_states = self.e09.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e05_states = self.e05.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e11_states = self.e11.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )
        e03_alphas = self.e03.run_universe(
            as_of=day.as_of,
            panels=day.e03_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            e02_exposures=e02_exps,
            universe_id=self.universe_id,
            generated_at=ts,
            run_parity=False,
        )
        e04_states = self.e04.run_universe(
            as_of=day.as_of,
            panels=day.e02_panels,
            e01_state=e01_state,
            e14_state=e14_state,
            e02_exposures=e02_exps,
            e03_alphas=e03_alphas,
            universe_id=self.universe_id,
            generated_at=ts,
        )

        l4_opinions: dict[str, Any] = {}
        for sym, alpha in e03_alphas.items():
            op = self.l4.run(
                symbol=sym,
                as_of=day.as_of,
                e01_state=e01_state,
                e14_state=e14_state,
                e02_exposure=e02_exps.get(sym),
                e03_alpha=alpha,
                e11_state=e11_states.get(sym),
                universe_id=self.universe_id,
                generated_at=ts,
            )
            l4_opinions[sym] = op

        portfolio = self.e10.run(
            as_of=day.as_of,
            opinions=l4_opinions,
            exposures=e02_exps,
            e14_state=e14_state,
            universe_id=self.universe_id,
            generated_at=ts,
        )

        # Portfolio return uses next-day forward returns from golden day
        port_ret = 0.0
        for sym, w in portfolio.weights.items():
            port_ret += w * float(day.forward_returns.get(sym, 0.0))
        # Cash earns 0 in P0 research replay

        return ReplayDaySlice(
            as_of=day.as_of,
            e01_hash=e01_state.hash,
            e14_hash=e14_state.hash,
            e02_hashes={s: e.hash for s, e in e02_exps.items()},
            e13_hashes={s: f.hash for s, f in e13_funds.items()},
            e08_hashes={s: v.hash for s, v in e08_states.items()},
            e09_hashes={s: t.hash for s, t in e09_states.items()},
            e05_hashes={s: e.hash for s, e in e05_states.items()},
            e11_hashes={s: snt.hash for s, snt in e11_states.items()},
            e04_hashes={s: r.hash for s, r in e04_states.items()},
            e03_hashes={s: a.hash for s, a in e03_alphas.items()},
            l4_hashes={s: o.hash for s, o in l4_opinions.items()},
            e13_labels={s: f.label for s, f in e13_funds.items()},
            e08_labels={s: v.label for s, v in e08_states.items()},
            e09_labels={s: t.label for s, t in e09_states.items()},
            e05_labels={s: e.label for s, e in e05_states.items()},
            e11_labels={s: snt.label for s, snt in e11_states.items()},
            e04_labels={s: r.label for s, r in e04_states.items()},
            e03_labels={s: a.label for s, a in e03_alphas.items()},
            l4_labels={s: o.label for s, o in l4_opinions.items()},
            e13_scores={s: f.composite_score for s, f in e13_funds.items()},
            e08_scores={s: v.composite_score for s, v in e08_states.items()},
            e09_scores={s: t.composite_score for s, t in e09_states.items()},
            e05_scores={s: e.composite_score for s, e in e05_states.items()},
            e11_scores={s: snt.composite_score for s, snt in e11_states.items()},
            e04_scores={s: r.composite_score for s, r in e04_states.items()},
            e03_scores={s: a.agi_tech_score for s, a in e03_alphas.items()},
            l4_scores={s: o.composite_score for s, o in l4_opinions.items()},
            confidences={s: o.confidence for s, o in l4_opinions.items()},
            portfolio_weights=dict(portfolio.weights),
            cash_allocation=portfolio.cash_allocation,
            portfolio_hash=portfolio.hash,
            expected_volatility=portfolio.expected_volatility,
            e14_risk_level=str((e14_state.metadata or {}).get("risk_level")),
            e01_regime=str((e01_state.metadata or {}).get("primary_regime")),
            model_versions=self.engine_versions(),
            formula_versions={
                "SM_AGI_TECH": E03_MODEL,
                "FM_AGI_FUND": E13_FORMULA,
                "VM_AGI_VOL": E08_FORMULA,
                "TM_AGI_CTA": E09_FORMULA,
                "EM_AGI_EVENT": E05_FORMULA,
                "SM_AGI_SENT": E11_FORMULA,
                "RV_AGI_PAIR": E04_FORMULA,
                "AM_INVVOL": E10_MODEL,
            },
            portfolio_return=round(port_ret, 8),
            benchmark_return=day.benchmark_return,
        )
