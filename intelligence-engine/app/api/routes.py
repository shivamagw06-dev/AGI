from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi import Body
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from options_lab import price_option_snapshot

from app.agents.registry import list_agents
from app.core.config import Settings, get_settings
from app.engines.e01.consumer import register_e01_with_orch_l2
from app.engines.e01.service import E01Service
from app.engines.e02.consumer import register_e02_with_orch
from app.engines.e02.service import E02Service
from app.engines.e03.consumer import register_e03_with_orch
from app.engines.e03.service import E03Service
from app.engines.e04.consumer import register_e04_with_orch
from app.engines.e04.service import E04Service
from app.engines.e05.consumer import register_e05_with_orch
from app.engines.e05.service import E05Service
from app.engines.e11.consumer import register_e11_with_orch
from app.engines.e11.service import E11Service
from app.engines.e14.consumer import register_e14_with_orch
from app.engines.e14.service import E14Service
from app.engines.e10.consumer import register_e10_with_orch
from app.engines.e10.service import E10Service
from app.engines.e08.consumer import register_e08_with_orch
from app.engines.e08.service import E08Service
from app.engines.e09.consumer import register_e09_with_orch
from app.engines.e09.service import E09Service
from app.engines.e13.consumer import register_e13_with_orch
from app.engines.e13.service import E13Service
from app.engines.l4.consumer import register_l4_with_orch
from app.engines.l4.service import L4Service
from app.eval.evaluation_agent import EvaluationAgent
from app.cre.service import CREService
from app.kip.models import (
    BulkIngestRequest,
    ChannelIngestRequest,
    ClientSearchRequest,
    IngestRequest,
    PredictionEvalRequest,
)
from app.kip.service import KipService
from app.rsp.models import CommitteeRequest, ReasonRequest, SynthesizeRequest
from app.rsp.service import RspService
from app.rms.models import (
    ApproveRequest,
    DraftRequest,
    PublishRequest,
    ResearchRequestCreate,
    ReviewRequest,
)
from app.rms.service import RmsService
from app.rms.workflow import WorkflowError
from app.aws.service import AwsService
from app.ioc.service import IocService
from app.aip.models import ExperimentHypothesis, ExperimentRequest
from app.aip.service import AipService
from app.irp.service import IrpService
from app.kf.service import KfService
from app.kc.service import KcService
from app.aoi.service import AoiService
from app.eve.service import EveService
from app.iie.service import IieService
from app.fle.service import FleService
from app.fre.service import FreService
from app.faa.service import FaaService
from app.mee.service import MeeService
from app.cae.service import CaeService
from app.ib.service import IbService
from app.ve.service import VeService
from app.ail.service import AilService
from app.fiml.service import FimlService
from app.academy.service import AcademyService
from app.ui.service import UiService
from app.validation.service import ValidationService
from app.features.models import FeatureMetadata
from app.features.service import FeatureRegistryService
from app.market_data.client import MarketDataClient
from app.memory.store import ResearchStore
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import BuildBatchRequest, MarketDataUpdateEvent
from app.orch.ledger import OrchLedger
from app.orchestration.director import ResearchDirector
from app.portfolio.normalize import MODEL_PORTFOLIOS
from app.portfolio.pack import build_portfolio_package, evaluate_scenario
from app.investment_office.pack import (
    build_investment_office_package,
    evaluate_office_scenario,
)
from app.investment_office.playbooks import list_playbooks
from app.schemas.models import (
    DeskType,
    InvestmentOfficePackage,
    InvestmentOfficeRequest,
    PortfolioIngestRequest,
    PortfolioPackage,
    PredictionRecord,
    ResearchRun,
    ResearchRunCreate,
)

router = APIRouter(prefix="/v1")
_store = ResearchStore()
_director = ResearchDirector(store=_store)
_eval = EvaluationAgent()
_market_data = MarketDataClient.from_settings(get_settings())
_features = FeatureRegistryService()
_orch_ledger = OrchLedger()
_l2 = L2FeatureBuildService(_features, orch_ledger=_orch_ledger)
_l2_drain_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="orch-l2-drain")
_e01 = E01Service(_features, orch_ledger=_orch_ledger)
_e14 = E14Service(_features, e01=_e01, orch_ledger=_orch_ledger)
_e02 = E02Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_e13 = E13Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_e08 = E08Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_e09 = E09Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_e03 = E03Service(_features, e01=_e01, e14=_e14, e02=_e02, orch_ledger=_orch_ledger)
_e04 = E04Service(
    _features, e01=_e01, e14=_e14, e02=_e02, e03=_e03, orch_ledger=_orch_ledger
)
_e05 = E05Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_e11 = E11Service(_features, e01=_e01, e14=_e14, orch_ledger=_orch_ledger)
_l4 = L4Service(
    e01=_e01, e14=_e14, e02=_e02, e03=_e03, e11=_e11, orch_ledger=_orch_ledger
)
_e10 = E10Service(l4=_l4, e14=_e14, e02=_e02, orch_ledger=_orch_ledger)
_validation = ValidationService()


def _engine_health(service: Any) -> dict[str, Any]:
    """Separate process availability from evidence that an engine has run."""
    payload = service.health()
    metrics = payload.get("metrics") or {}
    store = payload.get("store") or {}
    runs = int(metrics.get("runs") or 0)
    stored_outputs = sum(
        int(value or 0)
        for value in store.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    operational = runs > 0 and stored_outputs > 0
    return {
        **payload,
        "available": bool(payload.get("ok")),
        "operational": operational,
        "operational_status": (
            "operational" if operational
            else "ready_no_outputs" if payload.get("ok")
            else "disabled"
        ),
        "last_run_verified": runs > 0,
    }
_cre = CREService()
_kip = KipService()
_rsp = RspService(kip=_kip)
_rms = RmsService(kip=_kip, rsp=_rsp)
_aws = AwsService(
    kip=_kip,
    rsp=_rsp,
    rms=_rms,
    cre=_cre,
    validation=_validation,
    e01=_e01,
    e02=_e02,
    e03=_e03,
    e04=_e04,
    e05=_e05,
    e08=_e08,
    e09=_e09,
    e10=_e10,
    e11=_e11,
    e13=_e13,
    e14=_e14,
    l4=_l4,
)
_ioc = IocService(
    market_data=_market_data,
    features=_features,
    orch_l2=_l2,
    orch_ledger=_orch_ledger,
    e01=_e01,
    e02=_e02,
    e03=_e03,
    e04=_e04,
    e05=_e05,
    e08=_e08,
    e09=_e09,
    e10=_e10,
    e11=_e11,
    e13=_e13,
    e14=_e14,
    l4=_l4,
    validation=_validation,
    cre=_cre,
    kip=_kip,
    rsp=_rsp,
    rms=_rms,
    aws=_aws,
)
_aip = AipService()
_irp = IrpService(kip=_kip, rsp=_rsp)
_kf = KfService(kip=_kip)
_kc = KcService(kf=_kf, kip=_kip)
_aoi = AoiService(kip=_kip, kc=_kc, kf=_kf)
_eve = EveService(aoi=_aoi, kc=_kc, kf=_kf)
_aoi.bind_eve(_eve)
_fre = FreService(aoi=_aoi, kip=_kip, eve=_eve)
_faa = FaaService(fre=_fre, aoi=_aoi)
_fre.bind(faa=_faa)
_iie = IieService(eve=_eve, kc=_kc, kf=_kf, aoi=_aoi)
_fle = FleService(iie=_iie, eve=_eve, kc=_kc, kf=_kf, aoi=_aoi)
_mee = MeeService(eve=_eve, iie=_iie, fle=_fle, aoi=_aoi, kf=_kf, kc=_kc)
_cae = CaeService(kf=_kf, kc=_kc, aoi=_aoi, eve=_eve, iie=_iie, fle=_fle, mee=_mee, fre=_fre)
_ail = AilService(cae=_cae, fre=_fre, faa=_faa)
_ib = IbService(aoi=_aoi, eve=_eve, iie=_iie, fle=_fle, mee=_mee, cae=_cae)
_ve = VeService(eve=_eve, iie=_iie, fle=_fle, mee=_mee, aoi=_aoi, ib=_ib)
# Soft IB subscriber for valuation recalculation (additive; engines unchanged).
try:
    _ib.subscribe(
        {
            "subscriber": "ve",
            "event_types": [
                "EvidenceVerified",
                "ForecastUpdated",
                "ForecastResolved",
                "InvestmentThesisUpdated",
                "CorporateEventDetected",
                "CompanyUpdated",
            ],
            "priority": "normal",
            "retry_max": 2,
        }
    )
    _ib.delivery.register_handler("ve", _ve.on_bus_event)
except Exception:
    pass
# FIML — shared domain model library (not an engine; engines consume via models.consumers).
_fiml = FimlService()
# Finance Academy — curriculum knowledge library (not an engine; soft consumers only).
_academy = AcademyService()
_ui = UiService(
    aws=_aws,
    ioc=_ioc,
    kip=_kip,
    rsp=_rsp,
    rms=_rms,
    cre=_cre,
    validation=_validation,
    aip=_aip,
    irp=_irp,
    kf=_kf,
    kc=_kc,
    aoi=_aoi,
    eve=_eve,
    iie=_iie,
    fle=_fle,
    mee=_mee,
    fre=_fre,
    cae=_cae,
    ib=_ib,
    ve=_ve,
    ail=_ail,
)
# Soft-wire KIP retrieve → RSP reason into Research Director (no engine redesign).
_director.kip = _kip
_director.rsp = _rsp
# Soft-bind FAA/FRE/CAE into AIL (no redesign).
try:
    _ail.bind(cae=_cae, fre=_fre, faa=_faa)
except Exception:
    pass


def _wire_market_data_to_l2() -> None:
    """MarketData publishes updates; ORCH L2 marks dirty + schedules builds."""

    def _drain_queued_updates() -> None:
        while _l2.drain(parallel=True, max_workers=4) is not None:
            pass

    def _on_update(event: MarketDataUpdateEvent) -> None:
        _l2.on_market_data_update(event, drain=False)
        _l2_drain_pool.submit(_drain_queued_updates)

    _market_data.on_update(_on_update)


def _wire_e01_passive_consumer() -> None:
    """E01 registers as passive FeatureSnapshot consumer on ORCH L2 ready events."""
    register_e01_with_orch_l2(_l2, _e01)


def _wire_e14_passive_consumer() -> None:
    """E14 registers as passive consumer of FeatureSnapshot + E01State."""
    register_e14_with_orch(_l2, _e14, _e01)


def _wire_e02_passive_consumer() -> None:
    """E02 registers as passive consumer of FeatureSnapshot + E01State + E14State."""
    register_e02_with_orch(_l2, _e02, _e01, _e14)


def _wire_e13_passive_consumer() -> None:
    """E13 registers as passive consumer of FeatureSnapshot + E01State + E14State."""
    register_e13_with_orch(_l2, _e13, _e01, _e14)


def _wire_e08_passive_consumer() -> None:
    """E08 registers as passive consumer of FeatureSnapshot + E01State + E14State."""
    register_e08_with_orch(_l2, _e08, _e01, _e14)


def _wire_e09_passive_consumer() -> None:
    """E09 registers as passive consumer of FeatureSnapshot + E01State + E14State."""
    register_e09_with_orch(_l2, _e09, _e01, _e14)


def _wire_e05_passive_consumer() -> None:
    """E05 registers as passive consumer of FeatureSnapshot + E01State + E14State."""
    register_e05_with_orch(_l2, _e05, _e01, _e14)


def _wire_e11_passive_consumer() -> None:
    """E11 registers as passive soft voter after Feature Ready + E01 + E14 Ready."""
    register_e11_with_orch(_l2, _e11, _e01, _e14)


def _wire_e03_passive_consumer() -> None:
    """E03 registers as passive consumer of FeatureSnapshot + E01/E14/E02 Ready."""
    register_e03_with_orch(_l2, _e03, _e01, _e14, _e02)


def _wire_e04_passive_consumer() -> None:
    """E04 registers as passive consumer of Feature/E01/E14/E02/E03 Ready."""
    register_e04_with_orch(_l2, _e04, _e01, _e14, _e02, _e03)


def _wire_l4_passive_consumer() -> None:
    """L4 shadow registers as passive consumer of E01/E14/E02/E03 Ready only."""
    register_l4_with_orch(_l4, _e01, _e14, _e02, _e03)


def _wire_e10_passive_consumer() -> None:
    """E10 registers as passive model-portfolio builder after L4 Ready."""
    register_e10_with_orch(_e10, _l4)


_wire_market_data_to_l2()
_wire_e01_passive_consumer()
_wire_e14_passive_consumer()
_wire_e02_passive_consumer()
_wire_e13_passive_consumer()
_wire_e08_passive_consumer()
_wire_e09_passive_consumer()
_wire_e05_passive_consumer()
_wire_e11_passive_consumer()
_wire_e03_passive_consumer()
_wire_e04_passive_consumer()
_wire_l4_passive_consumer()
_wire_e10_passive_consumer()


#: A census walks every row for each company named. Bounded so one request
#: cannot become a full-tab scan.
MAX_CENSUS_SYMBOLS = 25


def require_token(
    authorization: str | None = Header(default=None),
    x_agi_token: str | None = Header(default=None, alias="X-AGI-Intelligence-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.intelligence_engine_token
    provided = None
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization.split(" ", 1)[1].strip()
    elif x_agi_token:
        provided = x_agi_token.strip()
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid intelligence engine token")


@router.get("/health")
async def health():
    return {
        "ok": True,
        "service": "agi-intelligence-engine",
        "deployment": {
            "commit": os.environ.get("RENDER_GIT_COMMIT"),
            "service_id": os.environ.get("RENDER_SERVICE_ID"),
            "instance_id": os.environ.get("RENDER_INSTANCE_ID"),
        },
        "agents": list_agents(),
    }


@router.get("/orch/status")
async def orch_status():
    """ORCH control-plane status (Document ID ORCH; not E00 Layer 5 / E10)."""
    summary = _orch_ledger.status_summary()
    summary["l2"] = _l2.health()
    return summary


@router.get("/orch/l2/health")
async def orch_l2_health():
    """ORCH Layer 2 Feature Build health (ORCH-003–005)."""
    return _l2.health()


@router.get("/e01/health")
async def e01_health():
    """E01 Macro & Regime Engine health (E01-001–005 P0)."""
    return _engine_health(_e01)


@router.get("/e01/state")
async def e01_state(as_of: str | None = None):
    """Frontend-ready E01 EngineState (warm cache)."""
    state = _e01.get_state(as_of=as_of)
    if state is None:
        raise HTTPException(status_code=404, detail="E01 state not available")
    return state.model_dump(mode="json")


@router.get("/e01/history")
async def e01_history(limit: int = 50):
    """E01 regime history (newest first)."""
    return [s.model_dump(mode="json") for s in _e01.history(limit=min(limit, 200))]


@router.get("/e14/health")
async def e14_health():
    """E14 Risk & Crowding Overlay health (E14-001–005 P0)."""
    return _engine_health(_e14)


@router.get("/e14/state")
async def e14_state(as_of: str | None = None):
    """Frontend-ready E14 EngineState (warm cache)."""
    state = _e14.get_state(as_of=as_of)
    if state is None:
        raise HTTPException(status_code=404, detail="E14 state not available")
    return state.model_dump(mode="json")


@router.get("/e14/history")
async def e14_history(limit: int = 50):
    """E14 firm risk history (newest first)."""
    return [s.model_dump(mode="json") for s in _e14.history(limit=min(limit, 200))]


@router.get("/e02/health")
async def e02_health():
    """E02 Factor & Style Engine health (E02-001–005 P0)."""
    return _engine_health(_e02)


@router.get("/e02/exposure/{symbol}")
async def e02_exposure(symbol: str, as_of: str | None = None):
    """Frontend-ready E02Exposure (warm cache)."""
    exp = _e02.get_exposure(symbol, as_of=as_of)
    if exp is None:
        raise HTTPException(status_code=404, detail="E02 exposure not available")
    return exp.model_dump(mode="json")


@router.get("/e02/history/{symbol}")
async def e02_history(symbol: str, limit: int = 50):
    """E02 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e02.history(symbol, limit=min(limit, 200))]


@router.get("/e13/health")
async def e13_health():
    """E13 Equity Fundamental L/S Engine health (E13-001–005 P0)."""
    return _engine_health(_e13)


@router.get("/e13/fundamental/{symbol}")
async def e13_fundamental(symbol: str, as_of: str | None = None):
    """Frontend-ready E13Fundamental (warm cache)."""
    fund = _e13.get_fundamental(symbol, as_of=as_of)
    if fund is None:
        raise HTTPException(status_code=404, detail="E13 fundamental not available")
    return fund.model_dump(mode="json")


@router.get("/e13/history/{symbol}")
async def e13_history(symbol: str, limit: int = 50):
    """E13 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e13.history(symbol, limit=min(limit, 200))]


@router.get("/e08/health")
async def e08_health():
    """E08 Volatility & Options Intelligence health (E08-001–005 P0)."""
    return _engine_health(_e08)


@router.get("/e08/state/{symbol}")
async def e08_state(symbol: str, as_of: str | None = None):
    """Frontend-ready E08State (warm cache)."""
    vol = _e08.get_vol_state(symbol, as_of=as_of)
    if vol is None:
        raise HTTPException(status_code=404, detail="E08 state not available")
    return vol.model_dump(mode="json")


@router.get("/e08/history/{symbol}")
async def e08_history(symbol: str, limit: int = 50):
    """E08 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e08.history(symbol, limit=min(limit, 200))]


@router.get("/e09/health")
async def e09_health():
    """E09 CTA Trend Engine health (E09-001–005 P0)."""
    return _engine_health(_e09)


@router.get("/e09/state/{symbol}")
async def e09_state(symbol: str, as_of: str | None = None):
    """Frontend-ready E09State (warm cache)."""
    trend = _e09.get_trend_state(symbol, as_of=as_of)
    if trend is None:
        raise HTTPException(status_code=404, detail="E09 state not available")
    return trend.model_dump(mode="json")


@router.get("/e09/history/{symbol}")
async def e09_history(symbol: str, limit: int = 50):
    """E09 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e09.history(symbol, limit=min(limit, 200))]


@router.get("/e04/health")
async def e04_health():
    """E04 Statistical Arbitrage & Relative Value health (E04-001–005 P0)."""
    return _engine_health(_e04)


@router.get("/e04/state/{pair}")
async def e04_state(pair: str, as_of: str | None = None):
    """Frontend-ready E04State for a pair id (warm cache)."""
    rv = _e04.get_rv_state(pair, as_of=as_of)
    if rv is None:
        raise HTTPException(status_code=404, detail="E04 state not available")
    return rv.model_dump(mode="json")


@router.get("/e04/history/{pair}")
async def e04_history(pair: str, limit: int = 50):
    """E04 EngineState history for a pair (newest first)."""
    return [s.model_dump(mode="json") for s in _e04.history(pair, limit=min(limit, 200))]


@router.get("/e05/health")
async def e05_health():
    """E05 Event-Driven & Special Situations health (E05-001–005 P0)."""
    return _engine_health(_e05)


@router.get("/e05/events/{symbol}")
async def e05_events(symbol: str, as_of: str | None = None):
    """Frontend-ready E05EventState (warm cache)."""
    evt = _e05.get_event_state(symbol, as_of=as_of)
    if evt is None:
        raise HTTPException(status_code=404, detail="E05 event state not available")
    return evt.model_dump(mode="json")


@router.get("/e05/history/{symbol}")
async def e05_history(symbol: str, limit: int = 50):
    """E05 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e05.history(symbol, limit=min(limit, 200))]


@router.get("/e11/health")
async def e11_health():
    """E11 Sentiment & Alternative Data health (E11-001–005 P0)."""
    return _engine_health(_e11)


@router.get("/e11/sentiment/{symbol}")
async def e11_sentiment(symbol: str, as_of: str | None = None):
    """Frontend-ready E11State soft sentiment (warm cache)."""
    sent = _e11.get_sentiment_state(symbol, as_of=as_of)
    if sent is None:
        raise HTTPException(status_code=404, detail="E11 sentiment not available")
    return sent.model_dump(mode="json")


@router.get("/e11/state/{symbol}")
async def e11_state(symbol: str, as_of: str | None = None):
    """Alias of /e11/sentiment/{symbol} for EngineState-style clients."""
    sent = _e11.get_sentiment_state(symbol, as_of=as_of)
    if sent is None:
        raise HTTPException(status_code=404, detail="E11 state not available")
    return sent.model_dump(mode="json")


@router.get("/e11/history/{symbol}")
async def e11_history(symbol: str, limit: int = 50):
    """E11 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e11.history(symbol, limit=min(limit, 200))]


@router.get("/e03/health")
async def e03_health():
    """E03 Cross-Sectional Quant Engine health (E03-001–005 P0/M0)."""
    return _engine_health(_e03)


@router.get("/e03/alpha/{symbol}")
async def e03_alpha(symbol: str, as_of: str | None = None):
    """Frontend-ready E03Alpha (warm cache)."""
    alpha = _e03.get_alpha(symbol, as_of=as_of)
    if alpha is None:
        raise HTTPException(status_code=404, detail="E03 alpha not available")
    return alpha.model_dump(mode="json")


@router.get("/e03/history/{symbol}")
async def e03_history(symbol: str, limit: int = 50):
    """E03 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _e03.history(symbol, limit=min(limit, 200))]


@router.get("/e03/parity")
async def e03_parity():
    """Latest SM_AGI_TECH vs legacy score_research parity report."""
    report = _e03.get_parity()
    if report is None:
        raise HTTPException(status_code=404, detail="E03 parity report not available")
    return report.model_dump(mode="json")


@router.get("/l4/health")
async def l4_health():
    """L4 Composite Intelligence health (L4-001–005 P0 Shadow)."""
    return _engine_health(_l4)


@router.get("/l4/opinion/{symbol}")
async def l4_opinion(symbol: str, as_of: str | None = None):
    """Shadow L4Opinion (warm cache). Never replaces E03 production."""
    opinion = _l4.get_opinion(symbol, as_of=as_of)
    if opinion is None:
        raise HTTPException(status_code=404, detail="L4 opinion not available")
    return opinion.model_dump(mode="json")


@router.get("/l4/history/{symbol}")
async def l4_history(symbol: str, limit: int = 50):
    """L4 EngineState history for a symbol (newest first)."""
    return [s.model_dump(mode="json") for s in _l4.history(symbol, limit=min(limit, 200))]


@router.get("/e10/health")
async def e10_health():
    """E10 Portfolio Construction health (E10-001–005 P0)."""
    return _engine_health(_e10)


@router.get("/e10/portfolio")
async def e10_portfolio(as_of: str | None = None):
    """Current model E10Portfolio (warm cache). Research only — not executable."""
    port = _e10.get_portfolio(as_of=as_of)
    if port is None:
        raise HTTPException(status_code=404, detail="E10 portfolio not available")
    return port.model_dump(mode="json")


@router.get("/e10/history")
async def e10_history(limit: int = 50):
    """E10 PortfolioState history (newest first)."""
    return [s.model_dump(mode="json") for s in _e10.history(limit=min(limit, 200))]


@router.get("/validation/health")
async def validation_health():
    """Validation & Backtesting platform health (BT-001–005 P0)."""
    return _validation.health()


@router.get("/validation/datasets")
async def validation_datasets():
    """List frozen golden datasets available for replay."""
    return _validation.list_datasets()


@router.post("/validation/replay")
async def validation_replay(dataset_id: str = Query(default="golden_p0_v1")):
    """Run institutional historical replay (isolated engines; no production influence)."""
    try:
        result = _validation.run_replay(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.get("/validation/runs")
async def validation_runs(limit: int = 50):
    """List recent ReplayRun records."""
    return [r.model_dump(mode="json") for r in _validation.list_runs(limit=min(limit, 200))]


@router.get("/validation/runs/{run_id}")
async def validation_run(run_id: str):
    """Full ReplayResult for a run."""
    result = _validation.get_result(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    return result.model_dump(mode="json")


@router.get("/validation/dashboard/{run_id}")
async def validation_dashboard(run_id: str):
    """Validation dashboard payload (timeline, portfolio, L4 vs E03, distributions)."""
    dash = _validation.get_dashboard(run_id)
    if dash is None:
        raise HTTPException(status_code=404, detail="Replay dashboard not found")
    return dash


@router.get("/cre/health")
async def cre_health():
    """Continuous Research Evaluation platform health (CRE-001–005 P0)."""
    return _cre.health()


@router.post("/cre/evaluate")
async def cre_evaluate(dataset_id: str = Query(default="golden_p0_v1")):
    """Run nightly/on-demand CRE evaluation over Historical Replay (no production influence)."""
    try:
        result = _cre.evaluate(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@router.get("/cre/scorecards")
async def cre_scorecards():
    """Latest EngineScorecards + CompositeScorecard."""
    composite = _cre.get_composite()
    return {
        "engines": [s.model_dump(mode="json") for s in _cre.list_scorecards()],
        "composite": composite.model_dump(mode="json") if composite else None,
    }


@router.get("/cre/scorecards/{engine}")
async def cre_scorecard(engine: str):
    """Latest EngineScorecard for one engine."""
    card = _cre.get_scorecard(engine)
    if card is None:
        raise HTTPException(status_code=404, detail="Engine scorecard not found")
    return card.model_dump(mode="json")


@router.get("/cre/alerts")
async def cre_alerts():
    """Latest DriftAlert + RegressionAlert sets."""
    return _cre.get_alerts()


@router.get("/cre/promotion")
async def cre_promotion():
    """Promotion evidence report (PROMOTION=false ⇒ never ready)."""
    report = _cre.get_promotion()
    if report is None:
        raise HTTPException(status_code=404, detail="Promotion report not found")
    return report.model_dump(mode="json")


@router.get("/cre/dashboard")
async def cre_dashboard():
    """CRE dashboard: trends, rankings, confidence/performance, promotion readiness."""
    dash = _cre.get_dashboard()
    if dash is None:
        raise HTTPException(status_code=404, detail="CRE dashboard not found")
    return dash


@router.get("/kip/health")
async def kip_health():
    """Knowledge Intelligence Platform health (institutional memory layer)."""
    return _kip.health()


@router.get("/kip/integrity")
async def kip_integrity(expected: str | None = None):
    """Knowledge integrity checker — detects orphaned metadata / empty vector plane."""
    expected_ids = [x.strip() for x in (expected or "").split(",") if x.strip()] or None
    return _kip.integrity(expected_document_ids=expected_ids)


@router.get("/kip/verify/{document_id}")
async def kip_verify(document_id: str):
    """Verify a document is retrievable (doc + chunks + embeddings) before marking learned."""
    result = _kip.verify_document(document_id)
    if not result.get("retrievable"):
        raise HTTPException(status_code=404, detail=result)
    return result


@router.post("/kip/snapshot/save")
async def kip_snapshot_save():
    """Force-persist KIP snapshot to disk (+ optional Supabase mirror).

    save_store() serialises the entire store synchronously, so it is run on a
    worker thread. Calling it directly from this async handler blocked the
    uvicorn event loop for the whole write and stalled every other request.
    """
    import asyncio

    return await asyncio.to_thread(_kip.save_snapshot)


@router.post("/kip/snapshot/reload")
async def kip_snapshot_reload():
    """Reload KIP snapshot from disk / Supabase into process memory."""
    return _kip.reload_snapshot()


@router.post("/kip/ingest")
async def kip_ingest(body: IngestRequest):
    """Ingest a document into AGI institutional knowledge."""
    try:
        doc = _kip.ingest(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _kf_soft_learn(doc)
    return doc.model_dump(mode="json")


def _kf_soft_learn(doc) -> None:
    """Soft KF + Knowledge Corpus + IKL learning hook — never fails the KIP ingest path."""
    try:
        _kf.on_document(doc)
    except Exception:
        pass
    try:
        _kc.on_document(doc)
    except Exception:
        pass
    # IKL — extract → company/industry/macro memory → graph (before any Ask)
    try:
        from institutional_knowledge_layer.production import on_document as ikl_on_document

        ikl_on_document(doc)
    except Exception:
        return


def _channel_ingest(body: ChannelIngestRequest, channel: str):
    try:
        if body.items or body.zip_base64:
            bulk = BulkIngestRequest(
                items=body.items,
                zip_base64=body.zip_base64,
                default_broker=body.default_broker or body.broker,
                source_channel=channel,  # type: ignore[arg-type]
            )
            if channel == "broker":
                result = _kip.ingest_broker(bulk)
            elif channel == "newsletter":
                result = _kip.ingest_newsletter(bulk)
            else:
                result = _kip.ingest_bulk(bulk.model_copy(update={"source_channel": channel}))
            # Soft-learn each ingested document into Knowledge Foundation.
            for item in getattr(result, "ingested", None) or []:
                _kf_soft_learn(item)
            return result.model_dump(mode="json")
        single = IngestRequest(**body.model_dump(exclude={"items", "zip_base64", "default_broker"}))
        if channel == "agi":
            doc = _kip.ingest_agi(single)
        elif channel == "broker":
            doc = _kip.ingest_broker(single)
        elif channel == "newsletter":
            doc = _kip.ingest_newsletter(single)
        else:
            doc = _kip.ingest_internal(single)
        _kf_soft_learn(doc)
        return doc.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kip/ingest/agi")
async def kip_ingest_agi(body: ChannelIngestRequest):
    """Auto-ingest published AGI research into institutional memory."""
    return _channel_ingest(body, "agi")


@router.post("/kip/ingest/broker")
async def kip_ingest_broker(body: ChannelIngestRequest):
    """Ingest broker research (single or bulk PDF/DOCX/MD/Email/ZIP)."""
    return _channel_ingest(body, "broker")


@router.post("/kip/ingest/newsletter")
async def kip_ingest_newsletter(body: ChannelIngestRequest):
    """Ingest newsletter content (single or bulk)."""
    return _channel_ingest(body, "newsletter")


@router.post("/kip/ingest/internal")
async def kip_ingest_internal(body: ChannelIngestRequest):
    """Ingest internal AGI research notes."""
    return _channel_ingest(body, "internal")


@router.get("/kip/document/{document_id}")
async def kip_document(document_id: str):
    doc = _kip.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump(mode="json")


@router.get("/kip/company/{ticker}")
async def kip_company(ticker: str):
    try:
        return _kip.get_company(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/theme/{theme_id}")
async def kip_theme(theme_id: str):
    try:
        return _kip.get_theme(theme_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/house-view/{ticker}")
async def kip_house_view(ticker: str):
    """Current AGI House View + thesis evolution for a company."""
    try:
        return _kip.house_view(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/research-history/{ticker}")
async def kip_research_history(ticker: str):
    try:
        return _kip.research_history(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/predictions/{ticker}")
async def kip_predictions(ticker: str):
    try:
        preds = _kip.predictions(ticker)
        stats = _kip.prediction_stats(ticker)
        return {
            "ticker": ticker.upper(),
            "predictions": [p.model_dump(mode="json") for p in preds],
            "stats": stats.model_dump(mode="json"),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kip/predictions/evaluate")
async def kip_predictions_evaluate(body: PredictionEvalRequest):
    try:
        return _kip.evaluate_prediction(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/company-dossier/{ticker}")
async def kip_company_dossier(ticker: str):
    """Full institutional dossier: house view, history, predictions, timeline, graph."""
    try:
        return _kip.company_dossier(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/search")
async def kip_search(
    q: str = Query(..., description="Search query"),
    mode: str = Query(default="hybrid"),
    limit: int = Query(default=10, ge=1, le=50),
    ticker: str | None = None,
    sector: str | None = None,
    theme: str | None = None,
    broker: str | None = None,
):
    try:
        return _kip.search(
            q, mode=mode, limit=limit, ticker=ticker, sector=sector, theme=theme, broker=broker
        ).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kip/client-search")
async def kip_client_search(body: ClientSearchRequest):
    """Homepage search — NEVER answers directly; returns evidence for LLM synthesis."""
    try:
        return _kip.client_search(body).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/timeline/{ticker}")
async def kip_timeline(ticker: str):
    try:
        return _kip.timeline(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/similar/{document_id}")
async def kip_similar(document_id: str, limit: int = Query(default=10, ge=1, le=50)):
    try:
        return _kip.similar(document_id, limit=limit).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/graph/{entity}")
async def kip_graph(entity: str):
    try:
        return _kip.graph(entity).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/rag")
async def kip_rag(
    q: str = Query(..., description="RAG query"),
    ticker: str | None = None,
    limit: int = Query(default=8, ge=1, le=30),
):
    """Priority RAG evidence pack (AGI house view first; never model memory alone)."""
    try:
        return _kip.rag(q, ticker=ticker, limit=limit).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kip/research-context")
async def kip_research_context(q: str = Query(...), ticker: str | None = None):
    """Research continuity context for AGI Research Writer (validation fields included)."""
    try:
        return _kip.research_context(q, ticker=ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rsp/health")
async def rsp_health():
    """Reasoning & Research Synthesis Platform health."""
    return _rsp.health()


@router.post("/rsp/reason")
async def rsp_reason(body: ReasonRequest):
    """Run institutional reasoning pipeline → ReasoningPackage (no raw docs to LLM)."""
    try:
        return _rsp.reason(body).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rsp/synthesize")
async def rsp_synthesize(body: SynthesizeRequest):
    """Generate / refresh research synthesis from reasoning inputs."""
    try:
        return _rsp.synthesize(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rsp/committee")
async def rsp_committee(body: CommitteeRequest):
    """Full Research Committee pass (reason + synthesize)."""
    try:
        return _rsp.committee(body).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rsp/reasoning/{reasoning_id}")
async def rsp_get_reasoning(reasoning_id: str):
    pkg = _rsp.get_reasoning(reasoning_id)
    if pkg is None:
        raise HTTPException(status_code=404, detail="Reasoning package not found")
    return pkg.model_dump(mode="json")


@router.get("/rsp/evidence/{evidence_id}")
async def rsp_get_evidence(evidence_id: str):
    ev = _rsp.get_evidence(evidence_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ev.model_dump(mode="json")


@router.get("/rms/health")
async def rms_health():
    """Research Management System health."""
    return _rms.health()


@router.post("/rms/request")
async def rms_request(body: ResearchRequestCreate):
    """Create research idea/request and optionally collect KIP + run RSP."""
    try:
        return _rms.create_request(body).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rms/draft")
async def rms_draft(body: DraftRequest):
    """Create or update a research draft."""
    try:
        return _rms.create_or_update_draft(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rms/review")
async def rms_review(body: ReviewRequest):
    """Add review comment / internal or compliance decision."""
    try:
        return _rms.review(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rms/approve")
async def rms_approve(body: ApproveRequest):
    """Compliance / final approval gate."""
    try:
        return _rms.approve(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rms/publish")
async def rms_publish(body: PublishRequest):
    """Publish approved research → website/newsletter/LinkedIn/archive + KIP + predictions."""
    try:
        return _rms.publish(body).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rms/dashboard")
async def rms_dashboard():
    """Research pipeline, queues, calendar, coverage, prediction tracker."""
    try:
        return _rms.dashboard().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rms/research/{research_id}")
async def rms_research(research_id: str):
    obj = _rms.get_research(research_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Research not found")
    return obj.model_dump(mode="json")


@router.get("/aws/health")
async def aws_health():
    """AGI Analyst Workspace health (internal terminal — no public website)."""
    return _aws.health()


@router.get("/aws/company/{ticker}")
async def aws_company(ticker: str, as_of: str | None = None):
    """Company workspace — house view, engines, L4, portfolio, KIP, timeline, graph."""
    try:
        return _aws.company(ticker, as_of=as_of).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/theme/{theme_id}")
async def aws_theme(theme_id: str):
    try:
        return _aws.theme(theme_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/sector/{sector_id}")
async def aws_sector(sector_id: str):
    try:
        return _aws.sector(sector_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/replay/{as_of}")
async def aws_replay(as_of: str):
    """Replay explorer for a historical date."""
    try:
        return _aws.replay(as_of).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/dashboard")
async def aws_dashboard():
    try:
        return _aws.dashboard().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/search")
async def aws_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    """Global search across companies, themes, reports, research, predictions, people."""
    try:
        return _aws.search(q, limit=limit).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/copilot")
async def aws_copilot(
    workspace: str = Query(default="company"),
    q: str = Query(default=""),
    ticker: str | None = None,
    theme_id: str | None = None,
    sector_id: str | None = None,
    research_id: str | None = None,
    as_of: str | None = None,
):
    """Context-aware AI copilot pack — never starts from an empty prompt."""
    try:
        return _aws.copilot(
            workspace=workspace,
            question=q,
            ticker=ticker,
            theme_id=theme_id,
            sector_id=sector_id,
            research_id=research_id,
            as_of=as_of,
        ).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/macro")
async def aws_macro(as_of: str | None = None):
    try:
        return _aws.macro(as_of=as_of).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/portfolio")
async def aws_portfolio(as_of: str | None = None):
    try:
        return _aws.portfolio(as_of=as_of).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/research")
async def aws_research(research_id: str | None = None):
    try:
        return _aws.research(research_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/cre")
async def aws_cre():
    try:
        return _aws.cre_workspace().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aws/knowledge/{entity}")
async def aws_knowledge(entity: str):
    """Knowledge explorer — graph, themes, industries, research relationships."""
    try:
        return _aws.knowledge_explorer(entity).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ioc/health")
async def ioc_health():
    """Investment Operations Centre health (monitor-only mission control)."""
    return _ioc.health()


@router.get("/ioc/dashboard")
async def ioc_dashboard():
    """Ops dashboard: overall/engine/platform health, queues, failures, alerts."""
    try:
        return _ioc.dashboard().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ioc/alerts")
async def ioc_alerts():
    try:
        rows = _ioc.alerts()
        return {
            "alerts": [a.model_dump(mode="json") for a in rows],
            "count": len(rows),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ioc/providers")
async def ioc_providers():
    try:
        return _ioc.providers()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ioc/readiness")
async def ioc_readiness():
    """Morning / market-open readiness checklist."""
    try:
        return _ioc.readiness().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ioc/report")
async def ioc_report(
    type: str = Query(
        default="daily_operations",
        description="daily_operations|morning_readiness|market_open|end_of_day|weekly_operations",
    ),
):
    try:
        return _ioc.report(type).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/health")
async def aip_health():
    """Alpha Improvement Programme health (research programme, not a platform)."""
    return _aip.health()


@router.get("/aip/roadmap")
async def aip_roadmap():
    """Long-term AIP research roadmap (AIP-01 … AIP-10)."""
    return _aip.roadmap()


@router.get("/aip/weights")
async def aip_weights():
    """Dynamic Weight Registry — shadow weight sets only."""
    try:
        rows = _aip.list_weights()
        return {
            "weight_sets": [w.model_dump(mode="json") for w in rows],
            "count": len(rows),
            "production_influence": False,
            "l4_remains_shadow": True,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aip/weights")
async def aip_register_weight(
    weight_set_id: str = Query(...),
    name: str = Query(...),
    e03: float = Query(default=0.7),
    e01: float = Query(default=0.2),
    e14: float = Query(default=0.1),
    e11: float = Query(default=0.05),
    e02: float = Query(default=0.0),
    regime: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    description: str = Query(default=""),
):
    """Register a shadow candidate weight set (never applied to production L4)."""
    try:
        ws = _aip.register_weight(
            weight_set_id=weight_set_id,
            name=name,
            weights={"E03": e03, "E01": e01, "E14": e14, "E11": e11, "E02": e02},
            description=description,
            regime=regime,
            sector=sector,
        )
        return ws.model_dump(mode="json")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aip/experiment")
async def aip_experiment(
    candidate_weight_set_id: str | None = Query(default="aip_e03_heavier_v1"),
    dataset_id: str = Query(default="golden_p0_v1"),
    workstream: str = Query(default="AIP-02"),
    hypothesis: str | None = Query(default=None),
    regime: str | None = Query(default=None),
    sector: str | None = Query(default=None),
):
    """Run an AIP shadow experiment vs L4 / E03 / replay / golden / paper portfolio."""
    try:
        req = ExperimentRequest(
            hypothesis=ExperimentHypothesis(
                statement=hypothesis
                or (
                    "Candidate L4 shadow weights improve measurable alpha metrics "
                    "versus current L4 without worsening risk or calibration."
                ),
                workstream=workstream,
                expected_effect="Positive research / portfolio deltas with evidence",
            ),
            candidate_weight_set_id=candidate_weight_set_id,
            dataset_id=dataset_id,
            regime=regime,
            sector=sector,
            name=f"{workstream}:{candidate_weight_set_id}",
        )
        result = _aip.run_experiment(req)
        return result.model_dump(mode="json")
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/experiments")
async def aip_experiments(limit: int = Query(default=50, ge=1, le=200)):
    try:
        rows = _aip.list_experiments(limit=limit)
        return {
            "experiments": [r.model_dump(mode="json") for r in rows],
            "count": len(rows),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/experiments/{experiment_id}")
async def aip_experiment_get(experiment_id: str):
    try:
        row = _aip.get_experiment(experiment_id)
        if row is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        return row.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/contribution")
async def aip_contribution(
    dataset_id: str = Query(default="golden_p0_v1"),
    weight_set_id: str | None = Query(default=None),
):
    """Engine contribution + marginal information gain (AIP-03)."""
    try:
        return _aip.contribution(dataset_id, weight_set_id=weight_set_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/calibration")
async def aip_calibration():
    """Latest confidence calibration plan (suggestion only)."""
    try:
        plan = _aip.calibration()
        if plan is None:
            return {"plan": None, "note": "Run an experiment first"}
        return plan
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/attribution")
async def aip_attribution():
    try:
        report = _aip.attribution()
        if report is None:
            return {"report": None, "note": "Run an experiment first"}
        return report
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/house-view-evolution/{ticker}")
async def aip_house_view_evolution(
    ticker: str,
    dataset_id: str = Query(default="golden_p0_v1"),
):
    try:
        return _aip.house_view_evolution(ticker, dataset_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aip/quality")
async def aip_quality(
    domain: str = Query(default="research"),
    evidence_count: int = Query(default=0),
    has_reasoning_package: bool = Query(default=False),
    has_house_view: bool = Query(default=False),
    contradiction_resolved: bool = Query(default=False),
    grounded: bool = Query(default=False),
    cites_evidence: bool = Query(default=False),
    confidence_stated: bool = Query(default=False),
    unknowns_stated: bool = Query(default=False),
    answer_chars: int = Query(default=0),
):
    """Research / client answer quality scoring (AIP-09 / AIP-10)."""
    try:
        score = _aip.score_quality(
            {
                "domain": domain,
                "evidence_count": evidence_count,
                "has_reasoning_package": has_reasoning_package,
                "has_house_view": has_house_view,
                "contradiction_resolved": contradiction_resolved,
                "grounded": grounded,
                "cites_evidence": cites_evidence,
                "confidence_stated": confidence_stated,
                "unknowns_stated": unknowns_stated,
                "answer_chars": answer_chars,
            }
        )
        return score.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/promotion")
async def aip_promotion():
    """Promotion evidence checklist — never ready when AIP_PROMOTION=false."""
    try:
        return _aip.promotion()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aip/dashboard")
async def aip_dashboard():
    try:
        return _aip.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- KF1 Knowledge Foundation (structured knowledge over KIP; no redesign) ---


@router.get("/kf/health")
async def kf_health():
    return _kf.health()


@router.get("/kf/coverage")
async def kf_coverage():
    try:
        return _kf.coverage()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kf/seed")
async def kf_seed():
    try:
        return _kf.seed()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kf/rebuild")
async def kf_rebuild():
    try:
        return _kf.rebuild()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/search")
async def kf_search(q: str = Query(...), limit: int = Query(default=12, ge=1, le=50)):
    try:
        return _kf.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/companies")
async def kf_companies():
    try:
        return {"companies": _kf.list_companies()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/company/{ticker}")
async def kf_company(ticker: str):
    try:
        return _kf.get_company(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/sectors")
async def kf_sectors():
    try:
        return {"sectors": _kf.list_sectors()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/sector/{sector_id}")
async def kf_sector(sector_id: str):
    try:
        return _kf.get_sector(sector_id)
    except (RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc)) from exc


@router.get("/kf/themes")
async def kf_themes():
    try:
        return {"themes": _kf.list_themes()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/theme/{theme_id}")
async def kf_theme(theme_id: str):
    try:
        return _kf.get_theme(theme_id)
    except (RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc)) from exc


@router.get("/kf/macros")
async def kf_macros():
    try:
        return {"macros": _kf.list_macros()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/macro/{macro_id}")
async def kf_macro(macro_id: str):
    try:
        return _kf.get_macro(macro_id)
    except (RuntimeError, KeyError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc)) from exc


@router.get("/kf/predictions")
async def kf_predictions():
    try:
        return {"predictions": _kf.list_predictions()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kf/extracts")
async def kf_extracts():
    try:
        return {"extracts": _kf.list_extracts()}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- KCV1 Knowledge Corpus (populate/improve KF; no KF/KIP/IRP/RSP redesign) ---


@router.get("/kc/health")
async def kc_health():
    return _kc.health()


@router.get("/kc/metrics")
async def kc_metrics():
    try:
        return _kc.metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kc/dashboard")
async def kc_dashboard():
    try:
        return _kc.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kc/populate")
async def kc_populate(rebuild_kip: bool = Query(default=True)):
    try:
        return _kc.populate(rebuild_kip=rebuild_kip)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kc/universe")
async def kc_universe():
    try:
        return _kc.ensure_universe()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kc/gaps")
async def kc_gaps():
    try:
        return _kc.gaps()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kc/learning")
async def kc_learning():
    try:
        return _kc.learning()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kc/quality")
async def kc_quality(kind: str | None = Query(default=None), key: str | None = Query(default=None)):
    try:
        return _kc.quality(kind=kind, key=key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kc/consult")
async def kc_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _kc.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- AOI v1 Open Intelligence (public acquisition → KC/KF; no core redesign) ---


@router.get("/aoi/health")
async def aoi_health():
    return _aoi.health()


@router.get("/aoi/dashboard")
async def aoi_dashboard():
    try:
        return _aoi.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aoi/registry/seed")
async def aoi_registry_seed():
    try:
        return _aoi.seed_registry()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aoi/run")
async def aoi_run(
    connector_id: str | None = Query(default=None),
    limit_per_connector: int | None = Query(default=30, ge=1, le=500),
    publish: bool = Query(default=True),
):
    try:
        ids = [connector_id] if connector_id else None
        return _aoi.run_cycle(connector_ids=ids, limit_per_connector=limit_per_connector, publish=publish)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/companies")
async def aoi_companies(universe: str | None = Query(default="nifty_50")):
    try:
        return _aoi.list_companies(universe=universe)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/company/{key}")
async def aoi_company(key: str):
    try:
        return _aoi.get_company(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/search")
async def aoi_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _aoi.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/consult")
async def aoi_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _aoi.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/connectors")
async def aoi_connectors():
    try:
        return _aoi.connector_health()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/scheduler")
async def aoi_scheduler():
    try:
        return _aoi.pipeline.scheduler.status()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/gaps")
async def aoi_gaps():
    try:
        dash = _aoi.dashboard()
        return {"count": len(dash.get("gaps") or []), "tasks": dash.get("gaps") or []}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/aoi/learning")
async def aoi_learning():
    try:
        dash = _aoi.dashboard()
        return dash.get("learning") or {}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- EVE v1 Evidence & Verification (between AOI and KCV/KF; no core redesign) ---


@router.get("/eve/health")
async def eve_health():
    return _eve.health()


@router.get("/eve/dashboard")
async def eve_dashboard():
    try:
        return _eve.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/evidence")
async def eve_evidence(
    company_id: str | None = Query(default=None),
    fact_key: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return _eve.list_evidence(company_id=company_id, fact_key=fact_key, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/evidence/{evidence_id}")
async def eve_evidence_one(evidence_id: str):
    try:
        return _eve.get_evidence(evidence_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/company/{key}")
async def eve_company(key: str):
    try:
        return _eve.company_pack(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/conflicts")
async def eve_conflicts(status: str = Query(default="open")):
    try:
        return _eve.conflicts(status=status)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/timeline")
async def eve_timeline(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _eve.timeline(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/trust")
async def eve_trust():
    try:
        return _eve.trust()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/source")
async def eve_source():
    try:
        return _eve.list_sources()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/verification")
async def eve_verification():
    try:
        return _eve.verification_queue()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/eve/verification/run")
async def eve_verification_run():
    try:
        return _eve.run_verification_jobs()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/search")
async def eve_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _eve.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/consult")
async def eve_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _eve.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/eve/audit")
async def eve_audit(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return _eve.audit_logs(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- IIE v1 Investment Intelligence (after EVE/KCV/KF, before reasoning; no core redesign) ---


@router.get("/iie/health")
async def iie_health():
    return _iie.health()


@router.get("/iie/dashboard")
async def iie_dashboard():
    try:
        return _iie.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/iie/analyse")
async def iie_analyse(key: str = Query(...)):
    try:
        return _iie.analyse(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/iie/batch")
async def iie_batch(limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _iie.run_batch(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/company/{key}")
async def iie_company(key: str):
    try:
        return _iie.company(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/sector")
async def iie_sectors():
    try:
        return _iie.list_sectors()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/sector/{sector_id}")
async def iie_sector(sector_id: str):
    try:
        return _iie.sector(sector_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/theme")
async def iie_themes():
    try:
        return _iie.list_themes()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/theme/{theme_id}")
async def iie_theme(theme_id: str):
    try:
        return _iie.theme(theme_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/thesis/{key}")
async def iie_thesis(key: str):
    try:
        return _iie.thesis(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/scenario/{key}")
async def iie_scenario(key: str):
    try:
        return _iie.scenario(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/catalysts")
async def iie_catalysts(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _iie.catalysts(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/risks")
async def iie_risks(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _iie.risks(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/opportunities")
async def iie_opportunities(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _iie.opportunities(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/compare")
async def iie_compare(
    companies: str = Query(..., description="Comma-separated company ids/symbols"),
    dimensions: str | None = Query(default=None),
):
    try:
        ids = [c.strip() for c in companies.split(",") if c.strip()]
        dims = [d.strip() for d in dimensions.split(",") if d.strip()] if dimensions else None
        return _iie.compare(ids, dimensions=dims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/monitor/{key}")
async def iie_monitor(key: str):
    try:
        return _iie.monitor(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/dna/{key}")
async def iie_dna(key: str):
    try:
        return _iie.dna(key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/macro")
async def iie_macro(event: str = Query(...)):
    try:
        return _iie.macro(event)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/evolution")
async def iie_evolution(
    entity_id: str | None = Query(default=None),
    object_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _iie.evolution(entity_id=entity_id, object_type=object_type, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/search")
async def iie_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _iie.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/iie/consult")
async def iie_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _iie.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- FLE v1 Forecasting & Learning (after IIE, before reasoning; no core redesign) ---


@router.get("/fle/health")
async def fle_health():
    return _fle.health()


@router.get("/fle/dashboard")
async def fle_dashboard():
    try:
        return _fle.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/forecast")
async def fle_list_forecasts(
    company_id: str | None = Query(default=None),
    sector_id: str | None = Query(default=None),
    metric: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _fle.list_forecasts(
            company_id=company_id, sector_id=sector_id, metric=metric, status=status, limit=limit
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/forecast")
async def fle_create_forecast(payload: dict[str, Any] = Body(default_factory=dict)):
    try:
        return _fle.create_forecast(payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/forecast/{forecast_id}")
async def fle_get_forecast(forecast_id: str):
    try:
        return _fle.get_forecast(forecast_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/forecast/{forecast_id}/resolve")
async def fle_resolve_forecast(forecast_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
    try:
        return _fle.resolve(forecast_id, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/forecast/{forecast_id}/version")
async def fle_version_forecast(forecast_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
    try:
        return _fle.version(forecast_id, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/compare/{forecast_id}")
async def fle_compare(forecast_id: str):
    try:
        return _fle.compare(forecast_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/company/{key}")
async def fle_company(key: str):
    try:
        return _fle.company(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/outcomes")
async def fle_outcomes(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _fle.outcomes(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/learning")
async def fle_learning(
    q: str | None = Query(default=None),
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _fle.learning(q=q, company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/calibration")
async def fle_calibration():
    try:
        return _fle.calibration()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/scenarios/{forecast_id}")
async def fle_scenarios(forecast_id: str):
    try:
        return _fle.scenarios(forecast_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/accuracy")
async def fle_accuracy(
    scope: str | None = Query(default=None),
    scope_id: str | None = Query(default=None),
):
    try:
        return _fle.accuracy(scope=scope, scope_id=scope_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/history")
async def fle_history(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _fle.history(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/generate")
async def fle_generate(key: str = Query(...)):
    try:
        return _fle.generate(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/batch")
async def fle_batch(limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _fle.batch(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fle/jobs")
async def fle_jobs():
    try:
        return _fle.run_jobs()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/search")
async def fle_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _fle.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fle/consult")
async def fle_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _fle.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- FAA v1 Finance Acquisition Agent (upstream live acquisition; feeds FRE) ---


@router.get("/faa/health")
async def faa_health():
    return _faa.health()


@router.get("/faa/dashboard")
async def faa_dashboard():
    try:
        return _faa.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/faa/discover")
async def faa_discover(q: str = Query(...), limit: int = Query(default=40, ge=1, le=100)):
    try:
        return _faa.discover(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/faa/acquire")
async def faa_acquire(
    q: str = Query(...),
    limit: int = Query(default=24, ge=1, le=100),
):
    try:
        return _faa.acquire(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/faa/connectors")
async def faa_connectors():
    return _faa.connectors_health()


@router.get("/faa/scheduler")
async def faa_scheduler():
    return _faa.scheduler.status()


@router.get("/financials-valuation/bank-kpis/coverage")
async def bank_kpi_coverage():
    from financials_valuation.bank_kpi_backfill import coverage

    try:
        return await run_in_threadpool(coverage)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/financials-valuation/bank-kpis/backfill",
    dependencies=[Depends(require_token)],
)
async def bank_kpi_backfill(
    symbols: list[str] = Body(default=[]),
    limit_per_bank: int = Query(default=5, ge=1, le=8),
):
    if os.environ.get("BANK_KPI_BACKFILL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=423, detail="Bank KPI backfill is paused")
    from financials_valuation.bank_kpi_backfill import run_bank_backfill

    return await run_in_threadpool(
        run_bank_backfill,
        _faa,
        symbols=symbols or None,
        limit_per_bank=limit_per_bank,
    )


@router.post(
    "/financials-valuation/bank-kpis/reprocess-indexed",
    dependencies=[Depends(require_token)],
)
async def bank_kpi_reprocess_indexed(
    symbols: list[str] = Body(default=[]),
    limit_per_bank: int = Query(default=20, ge=1, le=50),
):
    if os.environ.get("BANK_KPI_BACKFILL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=423, detail="Bank KPI backfill is paused")
    from financials_valuation.bank_kpi_backfill import reprocess_indexed_bank_documents

    return await run_in_threadpool(
        reprocess_indexed_bank_documents,
        _faa,
        symbols=symbols or None,
        limit_per_bank=limit_per_bank,
    )


@router.post("/faa/jobs")
async def faa_jobs():
    try:
        return _faa.run_jobs()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/faa/consult")
async def faa_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _faa.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- FRE v1 Finance Retrieval Engine (evidence retrieval & rank; never answers) ---


@router.get("/fre/health")
async def fre_health():
    return _fre.health()


@router.get("/fre/dashboard")
async def fre_dashboard():
    try:
        return _fre.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/query")
async def fre_query(
    q: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    company: str | None = Query(default=None),
):
    try:
        return _fre.query(q, limit=limit, company=company)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/search")
async def fre_search(
    q: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    company: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    min_authority: int | None = Query(default=None),
):
    try:
        return _fre.search(
            q,
            limit=limit,
            company=company,
            document_type=document_type,
            min_authority=min_authority,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/company/{key}")
async def fre_company(key: str, limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _fre.company(key, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/document/{document_id}")
async def fre_document(document_id: str):
    try:
        return _fre.document(document_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/fre/evidence")
async def fre_evidence(company: str | None = Query(default=None), limit: int = Query(default=40, ge=1, le=200)):
    try:
        return _fre.evidence(company=company, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/timeline")
async def fre_timeline(company: str | None = Query(default=None), limit: int = Query(default=40, ge=1, le=200)):
    try:
        return _fre.timeline(company=company, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/news")
async def fre_news(limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _fre.news(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/graph")
async def fre_graph(entity: str | None = Query(default=None)):
    try:
        return _fre.graph(entity=entity)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fre/ingest")
async def fre_ingest(payload: dict[str, Any] | None = Body(default=None)):
    try:
        return _fre.ingest(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fre/jobs")
async def fre_jobs():
    try:
        return _fre.run_jobs()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/consult")
async def fre_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _fre.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fre/scheduler")
async def fre_scheduler():
    return _fre.scheduler.status()


# --- MEE v1 Market Event Engine (after FLE; event backbone; no core redesign) ---


@router.get("/mee/health")
async def mee_health():
    return _mee.health()


@router.get("/mee/dashboard")
async def mee_dashboard():
    try:
        return _mee.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/events")
async def mee_list_events(
    company_id: str | None = Query(default=None),
    sector_id: str | None = Query(default=None),
    theme_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _mee.list_events(
            company_id=company_id,
            sector_id=sector_id,
            theme_id=theme_id,
            category=category,
            event_type=event_type,
            status=status,
            severity=severity,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mee/events")
async def mee_create_event(payload: dict[str, Any] = Body(default_factory=dict)):
    try:
        return _mee.create_event(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/events/{event_id}")
async def mee_get_event(event_id: str):
    try:
        return _mee.get_event(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mee/events/{event_id}/verify")
async def mee_verify_event(event_id: str):
    try:
        return _mee.verify(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mee/events/{event_id}/version")
async def mee_version_event(event_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
    try:
        return _mee.version(event_id, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/company/{key}")
async def mee_company(key: str):
    try:
        return _mee.company(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/sector/{sector_id}")
async def mee_sector(sector_id: str):
    try:
        return _mee.sector(sector_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/theme/{theme_id}")
async def mee_theme(theme_id: str):
    try:
        return _mee.theme(theme_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/timeline")
async def mee_timeline(
    scope: str = Query(default="company"),
    scope_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _mee.timeline(scope=scope, scope_id=scope_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/impact/{event_id}")
async def mee_impact(event_id: str):
    try:
        return _mee.impact(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/relationships")
async def mee_relationships(
    event_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return _mee.relationships(event_id=event_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/history")
async def mee_history(
    company_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _mee.history(company_id=company_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/similar/{event_id}")
async def mee_similar(event_id: str, limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _mee.similar(event_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mee/cycle")
async def mee_cycle(limit: int = Query(default=40, ge=1, le=200)):
    try:
        return _mee.run_cycle(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/search")
async def mee_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _mee.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/mee/consult")
async def mee_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _mee.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- CAE v1 Context Assembly (Ask AGI orchestration gateway; no core redesign) ---


@router.get("/cae/health")
async def cae_health():
    return _cae.health()


@router.get("/cae/dashboard")
async def cae_dashboard():
    try:
        return _cae.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/context")
async def cae_context(
    q: str = Query(...),
    ticker: str | None = Query(default=None),
    use_cache: bool | None = Query(default=None),
):
    try:
        return _cae.context(q, ticker=ticker, use_cache=use_cache)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/query-plan")
async def cae_query_plan(q: str = Query(...), ticker: str | None = Query(default=None)):
    try:
        return _cae.query_plan(q, ticker=ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/retrieval")
async def cae_retrieval(q: str = Query(...), ticker: str | None = Query(default=None)):
    try:
        return _cae.retrieve(q, ticker=ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/cache")
async def cae_cache_stats():
    try:
        return _cae.cache(action="stats")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cae/cache/clear")
async def cae_cache_clear():
    try:
        return _cae.cache(action="clear")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/metrics")
async def cae_metrics():
    try:
        return _cae.metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/explain/{package_id}")
async def cae_explain(package_id: str):
    try:
        return _cae.explain(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/package/{package_id}")
async def cae_package(package_id: str):
    try:
        return _cae.get_package(package_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cae/search")
async def cae_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _cae.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- IB v1 Intelligence Bus (event-driven backbone; no platform redesign) ---


@router.get("/ib/health")
async def ib_health():
    return _ib.health()


@router.get("/ib/dashboard")
async def ib_dashboard():
    try:
        return _ib.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/events")
async def ib_events(
    event_type: str | None = Query(default=None),
    producer: str | None = Query(default=None),
    aggregate_id: str | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    try:
        return _ib.list_events(
            event_type=event_type,
            producer=producer,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ib/publish")
async def ib_publish(payload: dict[str, Any] = Body(default={})):
    try:
        return _ib.publish(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/subscriptions")
async def ib_subscriptions_list():
    try:
        return _ib.list_subscriptions()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ib/subscriptions")
async def ib_subscriptions_create(payload: dict[str, Any] = Body(default={})):
    try:
        return _ib.subscribe(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ib/replay")
async def ib_replay(payload: dict[str, Any] = Body(default={})):
    try:
        return _ib.replay(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/history")
async def ib_history(
    aggregate_id: str | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
):
    try:
        return _ib.history(aggregate_id=aggregate_id, correlation_id=correlation_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/metrics")
async def ib_metrics():
    try:
        return _ib.metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/traces")
async def ib_traces(
    correlation_id: str | None = Query(default=None),
    event_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        return _ib.traces(correlation_id=correlation_id, event_id=event_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/dead-letter")
async def ib_dead_letter(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return _ib.dead_letter(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ib/dead-letter/{dlq_id}/resolve")
async def ib_dead_letter_resolve(dlq_id: str):
    try:
        return _ib.dead_letter(resolve_id=dlq_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ib/schema")
async def ib_schema(event_type: str | None = Query(default=None)):
    try:
        return _ib.schemas(event_type=event_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ib/demo-chain")
async def ib_demo_chain(company_symbol: str = Query(default="INFY")):
    try:
        return _ib.publish_chain_demo(company_symbol=company_symbol)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- VE v1 Valuation Engine (after FLE/MEE; no platform redesign) ---


@router.get("/ve/health")
async def ve_health():
    return _ve.health()


@router.get("/ve/dashboard")
async def ve_dashboard():
    try:
        return _ve.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/company/{key}")
async def ve_company(key: str, value_if_empty: bool = Query(default=True)):
    try:
        return _ve.company(key, value_if_empty=value_if_empty)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/model")
async def ve_model(
    model: str = Query(...),
    key: str = Query(...),
    market_price: float | None = Query(default=None),
):
    try:
        return _ve.model(model, key, market_price=market_price)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/history")
async def ve_history(key: str = Query(...), limit: int = Query(default=50, ge=1, le=200)):
    try:
        return _ve.history(key, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/scenarios")
async def ve_scenarios(key: str = Query(...)):
    try:
        return _ve.scenarios(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/compare")
async def ve_compare(key: str = Query(...), peers: str | None = Query(default=None)):
    try:
        peer_list = [p.strip() for p in (peers or "").split(",") if p.strip()] or None
        return _ve.compare(key, peers=peer_list)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/sensitivity")
async def ve_sensitivity(key: str = Query(...)):
    try:
        return _ve.sensitivity(key)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/search")
async def ve_search(q: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    try:
        return _ve.search(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/consult")
async def ve_consult(q: str = Query(...), limit: int = Query(default=8, ge=1, le=40)):
    try:
        return _ve.consult(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ve/value")
async def ve_value(payload: dict[str, Any] = Body(default={})):
    try:
        key = str((payload or {}).get("key") or (payload or {}).get("symbol") or "").strip()
        if not key:
            raise RuntimeError("key is required")
        models = (payload or {}).get("models")
        market_price = (payload or {}).get("market_price")
        fiscal_year = (payload or {}).get("fiscal_year")
        return _ve.value(
            key,
            models=models,
            market_price=float(market_price) if market_price is not None else None,
            trigger=str((payload or {}).get("trigger") or "api"),
            fiscal_year=fiscal_year,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ve/valuation/{valuation_id}")
async def ve_valuation(valuation_id: str):
    try:
        return _ve.get_valuation(valuation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- FIML v1 Financial Intelligence Model Library (not an engine; no platform redesign) ---


@router.get("/fiml/health")
async def fiml_health():
    return _fiml.health()


@router.get("/fiml/dashboard")
async def fiml_dashboard():
    try:
        return _fiml.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fiml/models")
async def fiml_models():
    try:
        return _fiml.list_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fiml/industries")
async def fiml_industries():
    try:
        return _fiml.industries()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/analyse/{domain}")
async def fiml_analyse(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.analyse(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/score/{domain}")
async def fiml_score(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.score(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/explain/{domain}")
async def fiml_explain(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.explain(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/compare/{domain}")
async def fiml_compare(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.compare(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/monitor/{domain}")
async def fiml_monitor(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.monitor(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/relationships/{domain}")
async def fiml_relationships(domain: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.relationships(domain, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/bundle")
async def fiml_bundle(payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.bundle(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/fiml/consumer/{engine}")
async def fiml_consumer(engine: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _fiml.consumer(engine, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fiml/search")
async def fiml_search(
    q: str = Query(...),
    domain: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        return _fiml.search(q, domain=domain, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fiml/metrics")
async def fiml_metrics():
    try:
        return _fiml.metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fiml/graph")
async def fiml_graph():
    try:
        return _fiml.graph()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- AGI Finance Academy v1.1 (curriculum library; multi-course; no locked-engine redesign) ---


@router.get("/academy/health")
async def academy_health():
    return _academy.health()


@router.get("/academy/dashboard")
async def academy_dashboard():
    try:
        return _academy.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/courses")
async def academy_courses():
    try:
        return _academy.courses()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/course")
async def academy_course(course_id: str | None = Query(default=None)):
    try:
        return _academy.course(course_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/concepts")
async def academy_concepts(
    tag: str | None = Query(default=None),
    course_id: str | None = Query(default=None),
):
    try:
        return _academy.list_concepts(tag=tag, course_id=course_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/concepts/{concept_id}")
async def academy_concept(concept_id: str):
    try:
        return _academy.get_concept(concept_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/teach/{concept_id}")
async def academy_teach(concept_id: str):
    try:
        return _academy.teach(concept_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/graph")
async def academy_graph(course_id: str | None = Query(default=None)):
    try:
        return _academy.graph(course_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/neighborhood/{concept_id}")
async def academy_neighborhood(concept_id: str):
    try:
        return _academy.neighborhood(concept_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/causal-models")
async def academy_causal_models():
    try:
        return _academy.causal_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/mental-models")
async def academy_mental_models():
    try:
        return _academy.mental_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/quality")
async def academy_quality(course_id: str | None = Query(default=None)):
    try:
        return _academy.quality(course_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/provenance")
async def academy_provenance():
    try:
        return _academy.provenance()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/enrich/{concept_id}")
async def academy_enrich(concept_id: str):
    try:
        return _academy.enrich(concept_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/exams")
async def academy_exams(course_id: str | None = Query(default=None)):
    try:
        return _academy.exams(course_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/exams/{question_id}")
async def academy_exam_answer(question_id: str):
    try:
        return _academy.answer(question_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/academy/consumer/{engine}")
async def academy_consumer(engine: str, payload: dict[str, Any] = Body(default={})):
    try:
        return _academy.consumer(engine, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/search")
async def academy_search(
    q: str = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    course_id: str | None = Query(default=None),
):
    try:
        return _academy.search(q, limit=limit, course_id=course_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/red-flags")
async def academy_red_flags():
    try:
        return _academy.red_flags()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/academy/red-flags/score")
async def academy_red_flags_score(payload: dict[str, Any] = Body(default={})):
    try:
        return _academy.red_flags(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/academy/earnings-quality")
async def academy_earnings_quality(payload: dict[str, Any] = Body(default={})):
    try:
        return _academy.earnings_quality(payload or {})
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/accounting")
async def academy_accounting():
    try:
        return _academy.accounting()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/corporate-finance")
async def academy_corporate_finance():
    try:
        return _academy.corporate_finance()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/completion")
async def academy_completion(course_id: str | None = Query(default=None)):
    try:
        return _academy.completion(course_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/metrics")
async def academy_metrics():
    try:
        return _academy.metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/production")
async def academy_production_dashboard():
    """FAPI v1.0 — production usage dashboard (not a new engine)."""
    try:
        return _academy.production_dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/production/ab")
async def academy_production_ab(question: str | None = Query(default=None)):
    try:
        return _academy.production_ab(question)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/academy/production/quality-gates")
async def academy_production_quality_gates():
    try:
        return _academy.production_quality_gates()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/academy/production/package")
async def academy_production_package(
    query: str = Query(...),
    engine: str = Query(default="cae"),
    ticker: str | None = Query(default=None),
):
    try:
        return _academy.production_package(query, engine=engine, ticker=ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- AGI Academy Books V1 (structured learning from curated books; not searchable PDFs) ---


@router.get("/academy/books/health")
async def academy_books_health():
    from academy.books.flags import flags_dict, is_books_enabled
    from academy.books.schema import BOOKS_VERSION

    return {
        "status": "ok" if is_books_enabled() else "disabled",
        "programme": "AGI_ACADEMY_BOOKS",
        "version": BOOKS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "flags": flags_dict(),
        "copyright_policy": "concepts_frameworks_formulas_only",
    }


@router.get("/academy/books/dashboard")
async def academy_books_dashboard():
    from academy.books.production import dashboard

    return dashboard()


@router.get("/academy/books/quality-gates")
async def academy_books_quality_gates():
    from academy.books.production import quality_gates

    return quality_gates()


@router.get("/academy/books/graph")
async def academy_books_graph():
    from academy.books.production import dashboard

    return dashboard().get("knowledge_graph") or {"nodes": [], "edges": []}


@router.post("/academy/books/ingest")
async def academy_books_ingest(payload: dict[str, Any] = Body(default={})):
    """Ingest a book/manual as structured knowledge. Never retains long verbatim text."""
    from academy.books.ingest import ingest_book

    title = str(payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title required")
    content = str(payload.get("content") or payload.get("text") or "")
    content_b64 = str(payload.get("content_base64") or "")
    raw = None
    if content_b64:
        import base64

        try:
            raw = base64.b64decode(content_b64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"invalid content_base64: {exc}") from exc
    result = ingest_book(
        title=title,
        authors=list(payload.get("authors") or []),
        content=content,
        content_bytes=raw,
        filename=str(payload.get("filename") or ""),
        subject=payload.get("subject"),
        difficulty=str(payload.get("difficulty") or "intermediate"),
        publication_year=payload.get("publication_year"),
        publisher=payload.get("publisher"),
        edition=payload.get("edition"),
        language=str(payload.get("language") or "en"),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason") or "ingest_failed")
    return result


@router.post("/academy/books/package")
async def academy_books_package(
    query: str = Query(...),
    ticker: str | None = Query(default=None),
):
    from academy.books.production import package_for_query

    return package_for_query(query, ticker=ticker)


@router.post("/academy/books/attach-kf")
async def academy_books_attach_kf():
    from academy.books.production import soft_attach_kf

    return soft_attach_kf()


@router.get("/academy/books/library")
async def academy_books_library():
    from academy.books.library import library_reachability, scan_library

    scan = scan_library()
    scan["library_reachability"] = library_reachability()
    return scan


@router.post("/academy/books/ingest-library")
async def academy_books_ingest_library(payload: dict[str, Any] = Body(default={})):
    """Batch-ingest personal library into structured Academy knowledge."""
    from academy.books.production import ingest_library

    root = payload.get("root")
    limit = payload.get("limit")
    return ingest_library(root=root, limit=int(limit) if limit is not None else None)


@router.get("/academy/books/ingestion-report")
async def academy_books_ingestion_report():
    from academy.books.production import ingestion_report

    return ingestion_report()


# --- AGI Academy Books V3 (institutional knowledge; never PDF/chapter retrieval) ---


@router.get("/academy/books/v3/health")
async def academy_books_v3_health():
    from academy.books.flags import flag_books_v3, flags_dict
    from academy.books.v3.schema import BOOKS_V3_VERSION

    return {
        "status": "ok" if flag_books_v3() else "disabled",
        "programme": "AGI_ACADEMY_BOOKS_V3",
        "version": BOOKS_V3_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "mode": "institutional_knowledge",
        "never_retrieve": ["chapters", "paragraphs", "pdfs"],
        "flags": flags_dict(),
    }


@router.get("/academy/books/v3/dashboard")
async def academy_books_v3_dashboard():
    from academy.books.v3.production import dashboard

    return dashboard()


@router.get("/academy/books/v3/quality-gates")
async def academy_books_v3_quality_gates():
    from academy.books.v3.production import quality_gates

    return quality_gates()


@router.post("/academy/books/v3/ask")
async def academy_books_v3_ask(payload: dict[str, Any] = Body(default={})):
    """Institutional ask — frameworks, cases, rules, chains, lessons. Never PDFs/chapters."""
    from academy.books.v3.retrieval import institutional_ask

    question = str(payload.get("question") or payload.get("query") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question required")
    return institutional_ask(
        question,
        analyst=payload.get("analyst"),
        ticker=payload.get("ticker"),
        limit=int(payload.get("limit") or 8),
    )


@router.get("/academy/books/v3/analyst/{analyst}")
async def academy_books_v3_analyst(analyst: str, question: str = Query(default="")):
    from academy.books.v3.production import analyst_base

    return analyst_base(analyst, question=question)


# --- Academy Validation Suite V1 (demonstrate knowledge, not ingest status) ---


@router.get("/academy/validation/health")
async def academy_validation_health():
    from academy.validation_suite.production import is_enabled
    from academy.validation_suite.schema import AVS_VERSION, LEVELS

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGI_ACADEMY_VALIDATION_SUITE",
        "version": AVS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "question": "Can it demonstrate institutional knowledge?",
        "not": "Did it ingest the book?",
        "levels": LEVELS,
    }


@router.get("/academy/validation/dashboard")
async def academy_validation_dashboard():
    from academy.validation_suite.production import dashboard

    return dashboard()


@router.get("/academy/validation/exams")
async def academy_validation_exams(level: int | None = Query(default=None)):
    from academy.validation_suite.production import list_exams

    return list_exams(level=level)


@router.post("/academy/validation/run")
async def academy_validation_run(payload: dict[str, Any] = Body(default={})):
    from academy.validation_suite.production import run_level, run_suite

    levels = payload.get("levels")
    if levels is not None and len(list(levels)) == 1:
        return run_level(int(list(levels)[0]))
    return run_suite(levels=[int(x) for x in levels] if levels else None)


@router.post("/academy/validation/exam/{exam_id}")
async def academy_validation_exam(exam_id: str):
    from academy.validation_suite.production import run_exam

    result = run_exam(exam_id)
    if result.get("reason") == "unknown_exam":
        raise HTTPException(status_code=404, detail="unknown_exam")
    return result


@router.get("/academy/validation/quality-gates")
async def academy_validation_quality_gates():
    from academy.validation_suite.production import quality_gates

    return quality_gates()


# --- Academy Certification Suite V1 (institutional intelligence / merge gate) ---


@router.get("/academy/certification/health")
async def academy_certification_health():
    from academy.certification.production import is_enabled
    from academy.certification.schema import ACS_VERSION, LEVELS

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGI_ACADEMY_CERTIFICATION_SUITE",
        "version": ACS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "metric": "reasoning_quality",
        "levels": LEVELS,
    }


@router.get("/academy/certification/dashboard")
async def academy_certification_dashboard():
    from academy.certification.production import dashboard

    return dashboard()


@router.get("/academy/certification/inventory")
async def academy_certification_inventory():
    from academy.certification.production import list_inventory

    return list_inventory()


@router.post("/academy/certification/run")
async def academy_certification_run(payload: dict[str, Any] = Body(default={})):
    from academy.certification.production import certify

    full = bool(payload.get("full"))
    limit = payload.get("limit_per_analyst")
    return certify(
        full=full,
        limit_per_analyst=None if full else (int(limit) if limit is not None else 8),
    )


@router.post("/academy/certification/gate")
async def academy_certification_gate(payload: dict[str, Any] = Body(default={})):
    from academy.certification.gate import certification_gate

    return certification_gate(
        full=bool(payload.get("full")),
        limit_per_analyst=None if payload.get("full") else int(payload.get("limit_per_analyst") or 8),
    )


@router.get("/academy/certification/quality-gates")
async def academy_certification_quality_gates(full: bool = Query(default=False)):
    from academy.certification.production import quality_gates

    return quality_gates(full=full)


@router.post("/academy/certification/exam/{exam_id}")
async def academy_certification_exam(exam_id: str):
    from academy.certification.production import run_one

    result = run_one(exam_id)
    if result.get("reason") == "unknown_exam":
        raise HTTPException(status_code=404, detail="unknown_exam")
    return result


# --- Institutional Regression Suite V1 (Did this PR make AGIB smarter?) ---


@router.get("/academy/regression/health")
async def academy_regression_health():
    from academy.regression.production import is_enabled
    from academy.regression.schema import GOLDEN_SET_VERSION, IRS_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_INSTITUTIONAL_REGRESSION_SUITE",
        "version": IRS_VERSION,
        "golden_set_version": GOLDEN_SET_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Did this pull request make AGIB smarter?",
    }


@router.get("/academy/regression/dashboard")
async def academy_regression_dashboard():
    from academy.regression.production import dashboard

    return dashboard()


@router.post("/academy/regression/run")
async def academy_regression_run(payload: dict[str, Any] = Body(default={})):
    from academy.regression.production import run_regression

    return run_regression(
        release=payload.get("release"),
        persist=bool(payload.get("persist", True)),
        golden_version=str(payload.get("golden_version") or "v1"),
    )


@router.post("/academy/regression/gate")
async def academy_regression_gate(payload: dict[str, Any] = Body(default={})):
    from academy.regression.production import release_gate

    return release_gate(
        release=payload.get("release"),
        persist=bool(payload.get("persist", True)),
    )


@router.get("/academy/regression/quality-gates")
async def academy_regression_quality_gates():
    from academy.regression.production import quality_gates

    return quality_gates()


@router.get("/academy/regression/history")
async def academy_regression_history():
    from academy.regression.history.store import all_releases

    return {"releases": all_releases()}


@router.get("/admin/regression", response_class=HTMLResponse)
async def admin_regression():
    """Soft admin surface — no UI redesign of existing admin systems."""
    from academy.regression.production import admin_page

    return HTMLResponse(admin_page())


# --- Evidence Intelligence Layer V1 (source attribution / peers / confidence) ---


@router.get("/academy/evidence/health")
async def academy_evidence_health():
    from academy.evidence.production import is_enabled
    from academy.evidence.schema import EIL_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_EVIDENCE_INTELLIGENCE_LAYER",
        "version": EIL_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_weakness_addressed": "Evidence quality / source attribution",
    }


@router.get("/academy/evidence/dashboard")
async def academy_evidence_dashboard():
    from academy.evidence.production import dashboard

    return dashboard()


@router.get("/academy/evidence/case/{case_id}")
async def academy_evidence_case(case_id: str):
    from academy.evidence.production import case_pack

    try:
        return case_pack(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/academy/evidence/support")
async def academy_evidence_support(payload: dict[str, Any] = Body(default={})):
    from academy.evidence.production import support

    statement = str(payload.get("statement") or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail="statement_required")
    return support(statement, analyst=payload.get("analyst"))


@router.post("/academy/evidence/confidence")
async def academy_evidence_confidence(payload: dict[str, Any] = Body(default={})):
    from academy.evidence.production import explain_confidence

    return explain_confidence(
        evidence=float(payload.get("evidence", 70)),
        historical=float(payload.get("historical", 50)),
        peer=float(payload.get("peer", 50)),
        macro=float(payload.get("macro", 70)),
    )


@router.get("/academy/evidence/quality-gates")
async def academy_evidence_quality_gates():
    from academy.evidence.production import quality_gates

    return quality_gates()


# --- Peer Intelligence Layer V1 (relative peer / history / percentile) ---


@router.get("/peer-intelligence/health")
async def peer_intelligence_health():
    from peer_intelligence.flags import is_enabled
    from peer_intelligence.schema import PIL_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_PEER_INTELLIGENCE_LAYER",
        "version": PIL_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "How does this company compare to the best and most relevant peers?",
    }


@router.get("/peer-intelligence/dashboard")
async def peer_intelligence_dashboard():
    from peer_intelligence.production import dashboard

    return dashboard()


@router.get("/peer-intelligence/company/{ticker}")
async def peer_intelligence_company(ticker: str):
    from peer_intelligence.production import company

    out = company(ticker)
    if out.get("scorecard") and not out["scorecard"].get("found"):
        raise HTTPException(status_code=404, detail="no_peer_pack")
    return out


@router.get("/peer-intelligence/compare")
async def peer_intelligence_compare(
    tickers: str = Query(default="HDFCBANK,ICICIBANK,AXISBANK"),
    metric: str | None = Query(default=None),
):
    from peer_intelligence.production import compare

    parts = [t.strip() for t in tickers.split(",") if t.strip()]
    return compare(parts, metric=metric)


@router.post("/peer-intelligence/analyse")
async def peer_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from peer_intelligence.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    focus = payload.get("focus_metrics")
    return analyse(ticker, focus_metrics=list(focus) if focus else None)


@router.get("/peer-intelligence/history/{ticker}")
async def peer_intelligence_history(
    ticker: str,
    metric: str | None = Query(default=None),
):
    from peer_intelligence.production import history

    return history(ticker, metric)


@router.get("/peer-intelligence/rankings")
async def peer_intelligence_rankings(
    ticker: str | None = Query(default=None),
    sector: str | None = Query(default=None),
):
    from peer_intelligence.production import rankings

    return rankings(ticker, sector=sector)


@router.get("/peer-intelligence/quality-gates")
async def peer_intelligence_quality_gates():
    from peer_intelligence.production import quality_gates

    return quality_gates()


@router.get("/admin/peer-intelligence", response_class=HTMLResponse)
async def admin_peer_intelligence():
    """Soft admin surface — no UI redesign."""
    from peer_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Filing Intelligence Layer V1 (official filings → institutional memory) ---


@router.get("/filing-intelligence/health")
async def filing_intelligence_health():
    from filing_intelligence.flags import is_enabled
    from filing_intelligence.schema import FIL_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_FILING_INTELLIGENCE_LAYER",
        "version": FIL_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "What do the company's own filings actually say?",
    }


@router.get("/filing-intelligence/dashboard")
async def filing_intelligence_dashboard():
    from filing_intelligence.production import dashboard

    return dashboard()


@router.get("/filing-intelligence/company/{ticker}")
async def filing_intelligence_company(ticker: str):
    from filing_intelligence.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_filings")
    return out


@router.get("/filing-intelligence/history/{ticker}")
async def filing_intelligence_history(ticker: str):
    from filing_intelligence.production import history

    return history(ticker)


@router.get("/filing-intelligence/timeline/{ticker}")
async def filing_intelligence_timeline(ticker: str):
    from filing_intelligence.production import timeline

    return timeline(ticker)


@router.post("/filing-intelligence/analyse")
async def filing_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from filing_intelligence.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    out = analyse(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_filings")
    return out


@router.get("/filing-intelligence/evidence/{ticker}")
async def filing_intelligence_evidence(ticker: str):
    from filing_intelligence.production import evidence

    return evidence(ticker)


@router.post("/filing-intelligence/ingest")
async def filing_intelligence_ingest(payload: dict[str, Any] = Body(default={})):
    from filing_intelligence.production import ingest

    if not payload.get("doc_id") or not payload.get("ticker"):
        raise HTTPException(status_code=400, detail="doc_id_and_ticker_required")
    return ingest(payload)


@router.get("/filing-intelligence/quality-gates")
async def filing_intelligence_quality_gates():
    from filing_intelligence.production import quality_gates

    return quality_gates()


@router.get("/admin/filing-intelligence", response_class=HTMLResponse)
async def admin_filing_intelligence():
    """Soft admin surface — no UI redesign."""
    from filing_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Filing Diff Engine V1 (what materially changed since previous filing) ---


@router.get("/filing-diff/health")
async def filing_diff_health():
    from filing_diff.flags import is_enabled
    from filing_diff.schema import FDI_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_FILING_DIFF_ENGINE",
        "version": FDI_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "What materially changed since the previous filing?",
    }


@router.get("/filing-diff/dashboard")
async def filing_diff_dashboard():
    from filing_diff.production import dashboard

    return dashboard()


@router.get("/filing-diff/company/{ticker}")
async def filing_diff_company(ticker: str):
    from filing_diff.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_filing_diff")
    return out


@router.post("/filing-diff/analyse")
async def filing_diff_analyse(payload: dict[str, Any] = Body(default={})):
    from filing_diff.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    out = analyse(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_filing_diff")
    return out


@router.get("/filing-diff/timeline/{ticker}")
async def filing_diff_timeline(ticker: str):
    from filing_diff.production import timeline

    return timeline(ticker)


@router.get("/filing-diff/changes/{ticker}")
async def filing_diff_changes(ticker: str):
    from filing_diff.production import changes

    return changes(ticker)


@router.get("/filing-diff/quality-gates")
async def filing_diff_quality_gates():
    from filing_diff.production import quality_gates

    return quality_gates()


@router.get("/admin/filing-diff", response_class=HTMLResponse)
async def admin_filing_diff():
    """Soft admin surface — no UI redesign."""
    from filing_diff.production import admin_page

    return HTMLResponse(admin_page())


# --- Management Intelligence Engine V1 (can management be trusted?) ---


@router.get("/management-intelligence/health")
async def management_intelligence_health():
    from management_intelligence.flags import is_enabled
    from management_intelligence.schema import MII_VERSION

    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": "AGIB_MANAGEMENT_INTELLIGENCE_ENGINE",
        "version": MII_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "primary_question": "Can this management team be trusted to compound shareholder value?",
    }


@router.get("/management-intelligence/dashboard")
async def management_intelligence_dashboard():
    from management_intelligence.production import dashboard

    return dashboard()


@router.get("/management-intelligence/company/{ticker}")
async def management_intelligence_company(ticker: str):
    from management_intelligence.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_management_profile")
    return out


@router.get("/management-intelligence/history/{ticker}")
async def management_intelligence_history(ticker: str):
    from management_intelligence.production import history

    return history(ticker)


@router.get("/management-intelligence/guidance/{ticker}")
async def management_intelligence_guidance(ticker: str):
    from management_intelligence.production import guidance

    return guidance(ticker)


@router.post("/management-intelligence/analyse")
async def management_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from management_intelligence.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    out = analyse(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_management_profile")
    return out


@router.get("/management-intelligence/quality-gates")
async def management_intelligence_quality_gates():
    from management_intelligence.production import quality_gates

    return quality_gates()


@router.get("/admin/management-intelligence", response_class=HTMLResponse)
async def admin_management_intelligence():
    """Soft admin surface — no UI redesign."""
    from management_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Intelligence Stack (soft FIL→FDI→MII→EIL→PIL integration) ---


@router.get("/institutional-stack/health")
async def institutional_stack_health():
    from institutional_stack.production import health

    return health()


@router.get("/institutional-stack/dashboard")
async def institutional_stack_dashboard():
    from institutional_stack.production import dashboard

    return dashboard()


@router.get("/institutional-stack/company/{ticker}")
async def institutional_stack_company(ticker: str, analyst: str = "committee"):
    from institutional_stack.production import company

    return company(ticker, analyst=analyst)


@router.post("/institutional-stack/analyse")
async def institutional_stack_analyse(payload: dict[str, Any] = Body(default={})):
    from institutional_stack.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    return analyse(ticker)


@router.post("/institutional-stack/ingest")
async def institutional_stack_ingest(payload: dict[str, Any] = Body(default={})):
    from institutional_stack.production import ingest

    if not payload.get("doc_id") or not payload.get("ticker"):
        raise HTTPException(status_code=400, detail="doc_id_and_ticker_required")
    return ingest(payload)


@router.post("/institutional-stack/bootstrap")
async def institutional_stack_bootstrap(payload: dict[str, Any] = Body(default={})):
    from institutional_stack.production import bootstrap_stack

    tickers = payload.get("tickers")
    return bootstrap_stack(tickers if isinstance(tickers, list) else None)


@router.get("/institutional-stack/quality-gates")
async def institutional_stack_quality_gates():
    from institutional_stack.production import quality_gates

    return quality_gates()


@router.get("/admin/institutional-stack", response_class=HTMLResponse)
async def admin_institutional_stack():
    from institutional_stack.production import admin_page

    return HTMLResponse(admin_page())


# --- FKB-01 Institutional Financial Knowledge Base (definitions only) ---


@router.get("/knowledge/health")
async def financial_knowledge_health():
    from financial_knowledge.production import health

    return health()


@router.get("/knowledge/dashboard")
async def financial_knowledge_dashboard():
    from financial_knowledge.production import dashboard

    return dashboard()


@router.get("/knowledge/metrics")
async def financial_knowledge_metrics():
    from financial_knowledge.production import metrics

    return metrics()


@router.get("/knowledge/ratios")
async def financial_knowledge_ratios():
    from financial_knowledge.production import ratios

    return ratios()


@router.get("/knowledge/relationships")
async def financial_knowledge_relationships():
    from financial_knowledge.production import relationships

    return relationships()


@router.get("/knowledge/glossary")
async def financial_knowledge_glossary():
    from financial_knowledge.production import glossary

    return glossary()


@router.get("/knowledge/thresholds")
async def financial_knowledge_thresholds(sector: str | None = None):
    from financial_knowledge.production import thresholds

    return thresholds(sector=sector)


@router.get("/admin/financial-knowledge", response_class=HTMLResponse)
async def admin_financial_knowledge():
    from financial_knowledge.production import admin_page

    return HTMLResponse(admin_page())


# --- FIRE-01 Financial Narrative & Trend Engine (warehouse consumer) ---


@router.get("/financial-intelligence/health")
async def financial_intelligence_health():
    from financial_intelligence.production import health

    return health()


@router.get("/financial-intelligence/dashboard")
async def financial_intelligence_dashboard():
    from financial_intelligence.production import dashboard

    return dashboard()


@router.get("/financial-intelligence/company/{ticker}")
async def financial_intelligence_company(ticker: str):
    from financial_intelligence.production import company

    return company(ticker.upper())


@router.get("/financial-intelligence/findings/{ticker}")
async def financial_intelligence_findings(ticker: str):
    from financial_intelligence.production import findings

    return findings(ticker.upper())


@router.get("/financial-intelligence/company/{ticker}/drivers")
async def financial_intelligence_drivers(ticker: str):
    """FIRE-02 — Financial Drivers / relationship analysis (read-only)."""
    from financial_intelligence.production import financial_drivers

    return financial_drivers(ticker.upper())


@router.get("/financial-intelligence/company/{ticker}/relationships")
async def financial_intelligence_relationships(ticker: str):
    """FIRE-02 — relationship list only."""
    from financial_intelligence.production import financial_relationships

    return financial_relationships(ticker.upper())


# --- FIRE-03 Business & Management Intelligence (official disclosure evidence) ---


@router.get("/business-intelligence/health")
async def business_intelligence_health():
    from business_intelligence.production import health

    return health()


@router.get("/business-intelligence/dashboard")
async def business_intelligence_dashboard():
    from business_intelligence.production import dashboard

    return dashboard()


@router.get("/business-intelligence/company/{ticker}")
async def business_intelligence_company(ticker: str):
    from business_intelligence.production import company

    return company(ticker.upper())


@router.get("/business-intelligence/company/{ticker}/segments")
async def business_intelligence_segments(ticker: str):
    from business_intelligence.production import segments

    return segments(ticker.upper())


@router.get("/business-intelligence/company/{ticker}/strategy")
async def business_intelligence_strategy(ticker: str):
    from business_intelligence.production import strategy

    return strategy(ticker.upper())


@router.get("/business-intelligence/company/{ticker}/risks")
async def business_intelligence_risks(ticker: str):
    from business_intelligence.production import risks

    return risks(ticker.upper())


@router.get("/business-intelligence/company/{ticker}/guidance")
async def business_intelligence_guidance(ticker: str):
    from business_intelligence.production import guidance

    return guidance(ticker.upper())


@router.get("/admin/business-intelligence", response_class=HTMLResponse)
async def admin_business_intelligence():
    from business_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Phase 3.0 Business Intelligence Foundation (Ask NOT wired) ---


@router.get("/business-intelligence/foundation/health")
async def bi_foundation_health():
    from business_intelligence.foundation.production import health

    return health()


@router.get("/business-intelligence/foundation/dashboard")
async def bi_foundation_dashboard():
    from business_intelligence.foundation.production import dashboard

    return dashboard()


@router.post("/business-intelligence/foundation/analyse")
async def bi_foundation_analyse(payload: dict):
    from business_intelligence.foundation.production import analyse

    question = str((payload or {}).get("question") or "").strip()
    ticker = (payload or {}).get("ticker")
    industry = (payload or {}).get("industry")
    return analyse(question, ticker=ticker, industry=industry)


@router.get("/business-intelligence/foundation/industry/{industry_key}")
async def bi_foundation_industry(industry_key: str):
    from business_intelligence.foundation.production import industry

    return industry(industry_key)


@router.get("/business-intelligence/foundation/company/{ticker}")
async def bi_foundation_company(ticker: str, question: str = ""):
    from business_intelligence.foundation.production import company

    return company(ticker.upper(), question=question)


@router.get("/business-intelligence/foundation/graph/{ticker}")
async def bi_foundation_graph(ticker: str):
    from business_intelligence.foundation.production import graph

    return graph(ticker.upper())


@router.post("/business-intelligence/foundation/compare")
async def bi_foundation_compare(payload: dict):
    from business_intelligence.foundation.production import compare

    return compare(str((payload or {}).get("question") or ""))


# --- Phase 3.1 Industry Intelligence Engine (Ask NOT wired until Acceptance 100%) ---


@router.get("/industry-intelligence/health")
async def industry_intelligence_health():
    from industry_intelligence.production import health

    return health()


@router.get("/industry-intelligence/dashboard")
async def industry_intelligence_dashboard():
    from industry_intelligence.production import dashboard

    return dashboard()


@router.post("/industry-intelligence/analyse")
async def industry_intelligence_analyse(payload: dict):
    from industry_intelligence.production import analyse

    question = str((payload or {}).get("question") or "").strip()
    industry = (payload or {}).get("industry")
    return analyse(question, industry=industry)


@router.get("/industry-intelligence/industry/{industry_key}")
async def industry_intelligence_industry(industry_key: str):
    from industry_intelligence.production import industry

    return industry(industry_key)


@router.get("/industry-intelligence/industry/{industry_key}/kpi/{kpi_key}")
async def industry_intelligence_kpi(industry_key: str, kpi_key: str):
    from industry_intelligence.production import explain_kpi

    return explain_kpi(industry_key, kpi_key)


# --- Phase 3.2 Investment Intelligence Engine (Ask NOT wired until Acceptance 100%) ---


@router.get("/investment-intelligence/health")
async def investment_intelligence_health():
    from investment_intelligence.production import health

    return health()


@router.get("/investment-intelligence/dashboard")
async def investment_intelligence_dashboard():
    from investment_intelligence.production import dashboard

    return dashboard()


@router.post("/investment-intelligence/analyse")
async def investment_intelligence_analyse(payload: dict):
    from investment_intelligence.production import analyse

    question = str((payload or {}).get("question") or "").strip()
    entity = (payload or {}).get("entity")
    return analyse(question, entity=entity)


# --- Phase 3.3 Portfolio Intelligence Foundation (Ask NOT wired until Acceptance 100%) ---


@router.get("/portfolio-intelligence/foundation/health")
async def portfolio_intelligence_foundation_health():
    from portfolio_intelligence.foundation.production import health

    return health()


@router.get("/portfolio-intelligence/foundation/dashboard")
async def portfolio_intelligence_foundation_dashboard():
    from portfolio_intelligence.foundation.production import dashboard

    return dashboard()


@router.get("/portfolio-intelligence/foundation/portfolios")
async def portfolio_intelligence_foundation_portfolios():
    from portfolio_intelligence.foundation.production import portfolios

    return portfolios()


@router.post("/portfolio-intelligence/foundation/analyse")
async def portfolio_intelligence_foundation_analyse(payload: dict):
    from portfolio_intelligence.foundation.production import analyse

    question = str((payload or {}).get("question") or "").strip()
    portfolio_id = (payload or {}).get("portfolio_id")
    compare_with = (payload or {}).get("compare_with")
    return analyse(question, portfolio_id=portfolio_id, compare_with=compare_with)


@router.post("/portfolio-intelligence/foundation/soft_slice")
async def portfolio_intelligence_foundation_soft_slice(payload: dict):
    from portfolio_intelligence.foundation.production import soft_slice_for_ask_agi

    question = str((payload or {}).get("question") or "").strip()
    return soft_slice_for_ask_agi(question)


# --- Phase 3.4 Research Intelligence Engine (Ask NOT wired until Acceptance 100%) ---


@router.get("/research-intelligence/health")
async def research_intelligence_health():
    from research_intelligence.production import health

    return health()


@router.get("/research-intelligence/dashboard")
async def research_intelligence_dashboard():
    from research_intelligence.production import dashboard

    return dashboard()


@router.get("/research-intelligence/entities")
async def research_intelligence_entities():
    from research_intelligence.production import entities

    return entities()


@router.post("/research-intelligence/analyse")
async def research_intelligence_analyse(payload: dict):
    from research_intelligence.production import analyse

    question = str((payload or {}).get("question") or "").strip()
    entity = (payload or {}).get("entity")
    return analyse(question, entity=entity)


@router.post("/research-intelligence/soft_slice")
async def research_intelligence_soft_slice(payload: dict):
    from research_intelligence.production import soft_slice_for_ask_agi

    question = str((payload or {}).get("question") or "").strip()
    return soft_slice_for_ask_agi(question)


# --- FIRE-04 Evidence Fusion Engine (cross-evidence consistency) ---


@router.get("/evidence-fusion/health")
async def evidence_fusion_health():
    from evidence_fusion.production import health

    return health()


@router.get("/evidence-fusion/dashboard")
async def evidence_fusion_dashboard():
    from evidence_fusion.production import dashboard

    return dashboard()


@router.get("/evidence-fusion/company/{ticker}")
async def evidence_fusion_company(ticker: str):
    from evidence_fusion.production import company

    return company(ticker.upper())


@router.get("/evidence-fusion/company/{ticker}/supported")
async def evidence_fusion_supported(ticker: str):
    from evidence_fusion.production import supported

    return supported(ticker.upper())


@router.get("/evidence-fusion/company/{ticker}/conflicts")
async def evidence_fusion_conflicts(ticker: str):
    from evidence_fusion.production import conflicts

    return conflicts(ticker.upper())


@router.get("/evidence-fusion/company/{ticker}/alignment")
async def evidence_fusion_alignment(ticker: str):
    from evidence_fusion.production import alignment

    return alignment(ticker.upper())


@router.get("/admin/evidence-fusion", response_class=HTMLResponse)
async def admin_evidence_fusion():
    from evidence_fusion.production import admin_page

    return HTMLResponse(admin_page())


# --- FIRE-05 Management Execution & Temporal Evidence Engine ---


@router.get("/management-execution/health")
async def management_execution_health():
    from management_execution.production import health

    return health()


@router.get("/management-execution/dashboard")
async def management_execution_dashboard():
    from management_execution.production import dashboard

    return dashboard()


@router.get("/management-execution/company/{ticker}")
async def management_execution_company(ticker: str):
    from management_execution.production import company

    return company(ticker.upper())


@router.get("/management-execution/company/{ticker}/timeline")
async def management_execution_timeline(ticker: str):
    from management_execution.production import timeline

    return timeline(ticker.upper())


@router.get("/management-execution/company/{ticker}/score")
async def management_execution_score(ticker: str):
    from management_execution.production import score

    return score(ticker.upper())


@router.get("/management-execution/company/{ticker}/objectives")
async def management_execution_objectives(ticker: str):
    from management_execution.production import objectives

    return objectives(ticker.upper())


@router.get("/admin/management-execution", response_class=HTMLResponse)
async def admin_management_execution():
    from management_execution.production import admin_page

    return HTMLResponse(admin_page())


# --- FIRE-06 Business Quality Engine (pillar-primary synthesis) ---


@router.get("/business-quality/health")
async def business_quality_health():
    from business_quality.production import health

    return health()


@router.get("/business-quality/dashboard")
async def business_quality_dashboard():
    from business_quality.production import dashboard

    return dashboard()


@router.get("/business-quality/company/{ticker}")
async def business_quality_company(ticker: str):
    from business_quality.production import company

    return company(ticker.upper())


@router.get("/business-quality/company/{ticker}/quality")
async def business_quality_quality(ticker: str):
    from business_quality.production import quality

    return quality(ticker.upper())


@router.get("/business-quality/company/{ticker}/pillars")
async def business_quality_pillars(ticker: str):
    from business_quality.production import pillars

    return pillars(ticker.upper())


@router.get("/admin/business-quality", response_class=HTMLResponse)
async def admin_business_quality():
    from business_quality.production import admin_page

    return HTMLResponse(admin_page())


# --- Accounting Intelligence Engine V1 (can the statements be trusted?) ---


@router.get("/accounting-intelligence/health")
async def accounting_intelligence_health():
    from accounting_intelligence.production import health

    return health()


@router.get("/accounting-intelligence/dashboard")
async def accounting_intelligence_dashboard():
    from accounting_intelligence.production import dashboard

    return dashboard()


@router.get("/accounting-intelligence/company/{ticker}")
async def accounting_intelligence_company(ticker: str):
    from accounting_intelligence.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_accounting_profile")
    return out


@router.get("/accounting-intelligence/history/{ticker}")
async def accounting_intelligence_history(ticker: str):
    from accounting_intelligence.production import history

    return history(ticker)


@router.post("/accounting-intelligence/analyse")
async def accounting_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from accounting_intelligence.production import analyse

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    out = analyse(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="no_accounting_profile")
    return out


@router.get("/accounting-intelligence/quality-gates")
async def accounting_intelligence_quality_gates():
    from accounting_intelligence.production import quality_gates

    return quality_gates()


@router.get("/admin/accounting-intelligence", response_class=HTMLResponse)
async def admin_accounting_intelligence():
    from accounting_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Portfolio Intelligence Office V1 (does this improve the portfolio?) ---


@router.get("/portfolio-intelligence/health")
async def portfolio_intelligence_health_root():
    from portfolio_intelligence.production import health

    return health()


@router.get("/portfolio-intelligence/dashboard")
async def portfolio_intelligence_dashboard():
    from portfolio_intelligence.production import dashboard

    return dashboard()


@router.get("/portfolio-intelligence/portfolio/{portfolio_id}")
async def portfolio_intelligence_portfolio(portfolio_id: str):
    from portfolio_intelligence.production import portfolio

    out = portfolio(portfolio_id)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="portfolio_not_found")
    return out


@router.get("/portfolio-intelligence/health/{portfolio_id}")
async def portfolio_intelligence_health(portfolio_id: str):
    from portfolio_intelligence.production import portfolio_health

    return portfolio_health(portfolio_id)


@router.get("/portfolio-intelligence/scenarios/{portfolio_id}")
async def portfolio_intelligence_scenarios(portfolio_id: str):
    from portfolio_intelligence.production import scenarios

    return scenarios(portfolio_id)


@router.post("/portfolio-intelligence/analyse")
async def portfolio_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from portfolio_intelligence.production import analyse

    out = analyse(
        payload.get("portfolio_id"),
        candidate=payload.get("candidate") or payload.get("ticker"),
        candidate_weight=payload.get("candidate_weight"),
        strategy_id=payload.get("strategy_id"),
    )
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="portfolio_not_found")
    return out


@router.get("/portfolio-intelligence/quality-gates")
async def portfolio_intelligence_quality_gates():
    from portfolio_intelligence.production import quality_gates

    return quality_gates()


@router.get("/portfolio-intelligence/strategy-gate/{strategy_id}")
async def portfolio_intelligence_strategy_gate(strategy_id: str):
    from portfolio_intelligence.production import strategy_execution_gate
    return await run_in_threadpool(strategy_execution_gate, strategy_id)


@router.get("/reliability/roadmap")
async def institutional_reliability_roadmap():
    from institutional_reliability import roadmap_status
    return await run_in_threadpool(roadmap_status)


@router.get("/admin/portfolio-intelligence", response_class=HTMLResponse)
async def admin_portfolio_intelligence():
    from portfolio_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Causal Intelligence Graph V1 (why did this happen?) ---


@router.get("/causal-intelligence/health")
async def causal_intelligence_health():
    from causal_graph.production import health

    return health()


@router.get("/causal-intelligence/dashboard")
async def causal_intelligence_dashboard():
    from causal_graph.production import dashboard

    return dashboard()


@router.get("/causal-intelligence/graph")
async def causal_intelligence_graph():
    from causal_graph.production import graph

    return graph()


@router.get("/causal-intelligence/company/{ticker}")
async def causal_intelligence_company(ticker: str):
    from causal_graph.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="company_not_in_causal_graph")
    return out


@router.get("/causal-intelligence/event/{event}")
async def causal_intelligence_event(event: str):
    from causal_graph.production import event as event_fn

    out = event_fn(event)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="event_not_found")
    return out


@router.post("/causal-intelligence/analyse")
async def causal_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from causal_graph.production import analyse

    out = analyse(
        ticker=payload.get("ticker") or payload.get("company"),
        event=payload.get("event"),
        question=payload.get("question") or payload.get("query"),
    )
    return out


@router.get("/causal-intelligence/quality-gates")
async def causal_intelligence_quality_gates():
    from causal_graph.production import quality_gates

    return quality_gates()


@router.get("/admin/causal-intelligence", response_class=HTMLResponse)
async def admin_causal_intelligence():
    from causal_graph.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Forecast Intelligence (IFI) Sprint 9.1 — Forecast Bundles ---
# Preparation only: no Bull/Base/Bear, no probabilities, no price prediction.


@router.get("/forecast/health")
async def forecast_intelligence_health():
    """Combined health: IFI preparation layer + legacy FIE scenario engine."""
    from forecast_intelligence.production import health as fie_health
    from institutional_forecast_intelligence.production import health as ifi_health

    return {
        "ifi": ifi_health(),
        "fie": fie_health(),
        "note": "Sprint 9.1 IFI prepares Forecast Bundles; FIE scenarios remain on /forecast/scenarios/{ticker}",
    }


@router.get("/forecast/dashboard")
async def forecast_intelligence_dashboard():
    from institutional_forecast_intelligence.production import dashboard as ifi_dashboard

    return ifi_dashboard()


@router.get("/ifi/health")
async def ifi_health():
    from institutional_forecast_intelligence.production import health

    return health()


@router.get("/ifi/dashboard")
async def ifi_dashboard():
    from institutional_forecast_intelligence.production import dashboard

    return dashboard()


@router.get("/forecast/company/{ticker}")
async def forecast_intelligence_company(
    ticker: str,
    mode: str = Query(default="bundle", description="bundle (IFI 9.1) | fie (legacy scenarios)"),
    question: str | None = None,
):
    """Sprint 9.1 default: Institutional Forecast Bundle (preparation only)."""
    if mode.lower() in {"fie", "scenarios", "legacy"}:
        from forecast_intelligence.production import company

        out = company(ticker)
        if out.get("enabled") and not out.get("found"):
            raise HTTPException(status_code=404, detail="company_forecast_not_found")
        return out

    from institutional_forecast_intelligence.production import company as ifi_company

    return ifi_company(ticker, question=question)


@router.get("/ifi/company/{ticker}")
async def ifi_company(ticker: str, question: str | None = None):
    from institutional_forecast_intelligence.production import company

    return company(ticker, question=question)


@router.get("/forecast/sector/{sector}")
async def forecast_sector(sector: str, question: str | None = None):
    from institutional_forecast_intelligence.production import sector as ifi_sector

    return ifi_sector(sector, question=question)


@router.get("/ifi/sector/{sector}")
async def ifi_sector_route(sector: str, question: str | None = None):
    from institutional_forecast_intelligence.production import sector as ifi_sector

    return ifi_sector(sector, question=question)


@router.get("/forecast/market")
async def forecast_market(question: str | None = None):
    from institutional_forecast_intelligence.production import market

    return market(question=question)


@router.get("/ifi/market")
async def ifi_market(question: str | None = None):
    from institutional_forecast_intelligence.production import market

    return market(question=question)


@router.get("/forecast/macro")
async def forecast_macro(question: str | None = None):
    from institutional_forecast_intelligence.production import macro

    return macro(question=question)


@router.get("/ifi/macro")
async def ifi_macro(question: str | None = None):
    from institutional_forecast_intelligence.production import macro

    return macro(question=question)


@router.get("/forecast/theme")
async def forecast_theme(
    theme: str = Query(default="artificial_intelligence"),
    question: str | None = None,
):
    from institutional_forecast_intelligence.production import theme as ifi_theme

    return ifi_theme(theme, question=question)


@router.get("/ifi/theme")
async def ifi_theme_route(
    theme: str = Query(default="artificial_intelligence"),
    question: str | None = None,
):
    from institutional_forecast_intelligence.production import theme as ifi_theme

    return ifi_theme(theme, question=question)


@router.post("/forecast/bundle")
async def forecast_bundle(payload: dict[str, Any] = Body(default={})):
    """Assemble a Forecast Bundle for Scenario Engine consumption (no judgment)."""
    from institutional_forecast_intelligence.production import bundle

    return bundle(
        scope=str(payload.get("scope") or "company"),
        entity=payload.get("entity") or payload.get("ticker") or payload.get("sector") or payload.get("theme"),
        question=payload.get("question"),
    )


@router.post("/ifi/bundle")
async def ifi_bundle(payload: dict[str, Any] = Body(default={})):
    from institutional_forecast_intelligence.production import bundle

    return bundle(
        scope=str(payload.get("scope") or "company"),
        entity=payload.get("entity") or payload.get("ticker") or payload.get("sector") or payload.get("theme"),
        question=payload.get("question"),
    )


# --- Institutional Scenario Intelligence (ISI) Sprint 9.2 — Bull / Base / Bear ---
# Consumes IFI Forecast Bundles. No probabilities (9.4), no BUY/SELL/target prices.


@router.get("/scenarios/health")
async def isi_health():
    from institutional_scenario_intelligence.production import health

    return health()


@router.get("/scenarios/dashboard")
async def isi_dashboard():
    from institutional_scenario_intelligence.production import dashboard

    return dashboard()


@router.get("/scenarios/company/{ticker}")
async def isi_company(ticker: str, question: str | None = None):
    from institutional_scenario_intelligence.production import company

    return company(ticker, question=question)


@router.get("/scenarios/sector/{sector}")
async def isi_sector(sector: str, question: str | None = None):
    from institutional_scenario_intelligence.production import sector as isi_sector_fn

    return isi_sector_fn(sector, question=question)


@router.get("/scenarios/market")
async def isi_market(question: str | None = None):
    from institutional_scenario_intelligence.production import market

    return market(question=question)


@router.get("/scenarios/macro")
async def isi_macro(question: str | None = None):
    from institutional_scenario_intelligence.production import macro

    return macro(question=question)


@router.post("/scenarios/report")
async def isi_report(payload: dict[str, Any] = Body(default={})):
    """Produce a Scenario Report from scope/entity or an explicit Forecast Bundle."""
    from institutional_scenario_intelligence.production import report

    return report(
        scope=str(payload.get("scope") or "company"),
        entity=payload.get("entity") or payload.get("ticker") or payload.get("sector"),
        question=payload.get("question"),
        forecast_bundle=payload.get("forecast_bundle"),
    )


@router.get("/admin/institutional-scenario-intelligence", response_class=HTMLResponse)
async def admin_isi():
    from institutional_scenario_intelligence.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{r.get('scope')}</td><td>{r.get('entity')}</td>"
        f"<td>{', '.join(r.get('scenario_types') or [])}</td>"
        f"<td>{r.get('contradictions')}</td></tr>"
        for r in (board.get("recent") or [])
    )
    html = f"""<!doctype html><html><head><title>ISI Mission Control</title></head>
    <body style="font-family:system-ui;max-width:960px;margin:2rem auto">
    <h1>Institutional Scenario Intelligence</h1>
    <p>Plausible outcomes — Bull / Base / Bear. No BUY/SELL. No probabilities yet.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Recent scenario reports</h2>
    <table border="1" cellpadding="6">
    <tr><th>Scope</th><th>Entity</th><th>Coverage</th><th>Contradictions</th></tr>
    {rows or '<tr><td colspan=4>No reports yet</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Institutional Probability & Confidence Intelligence (IPCI) Sprint 9.4 ---
# Probability ≠ Confidence. Probabilities sum to 100%. No trading recommendations.


@router.get("/probability/health")
async def ipci_health():
    from institutional_probability_confidence.production import health

    return health()


@router.get("/probability/dashboard")
async def ipci_dashboard():
    from institutional_probability_confidence.production import dashboard

    return dashboard()


@router.get("/probability/company/{ticker}")
async def ipci_probability_company(ticker: str, question: str | None = None):
    from institutional_probability_confidence.production import probability_company

    return probability_company(ticker, question=question)


@router.get("/probability/sector/{sector}")
async def ipci_probability_sector(sector: str, question: str | None = None):
    from institutional_probability_confidence.production import probability_sector

    return probability_sector(sector, question=question)


@router.get("/confidence/company/{ticker}")
async def ipci_confidence_company(ticker: str, question: str | None = None):
    from institutional_probability_confidence.production import confidence_company

    return confidence_company(ticker, question=question)


@router.get("/forecast/assessment/{ticker}")
async def ipci_forecast_assessment(ticker: str, question: str | None = None):
    from institutional_probability_confidence.production import assessment

    return assessment(ticker, scope="company", question=question)


@router.post("/forecast/assessment")
async def ipci_forecast_assessment_post(payload: dict[str, Any] = Body(default={})):
    from institutional_probability_confidence.production import assessment

    return assessment(
        ticker=payload.get("ticker"),
        scope=str(payload.get("scope") or "company"),
        entity=payload.get("entity") or payload.get("ticker") or payload.get("sector"),
        question=payload.get("question"),
        scenario_report=payload.get("scenario_report"),
    )


@router.get("/admin/institutional-probability-confidence", response_class=HTMLResponse)
async def admin_ipci():
    from institutional_probability_confidence.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{r.get('entity')}</td><td>{r.get('distribution')}</td>"
        f"<td>{r.get('overall_confidence')}</td><td>{r.get('forecast_quality')}</td></tr>"
        for r in (board.get("recent") or [])
    )
    html = f"""<!doctype html><html><head><title>IPCI Mission Control</title></head>
    <body style="font-family:system-ui;max-width:960px;margin:2rem auto">
    <h1>Institutional Probability &amp; Confidence Intelligence</h1>
    <p>Probability ≠ Confidence. Always sums to 100%. No BUY/SELL.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Recent assessments</h2>
    <table border="1" cellpadding="6">
    <tr><th>Entity</th><th>Distribution</th><th>Confidence</th><th>Quality</th></tr>
    {rows or '<tr><td colspan=4>No assessments yet</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Continuous Macroeconomic Knowledge Platform (CMKP) Sprint 10.1 ---
# Background ingestion only. Ask / Research / Forecast never trigger collectors.


@router.get("/cmkp/health")
async def cmkp_health():
    from continuous_macro_knowledge.production import health

    return health()


@router.get("/macro/dashboard")
async def cmkp_dashboard():
    from continuous_macro_knowledge.production import dashboard

    return dashboard()


@router.get("/macro/india")
async def cmkp_india(limit: int = Query(100, ge=1, le=500)):
    from continuous_macro_knowledge.production import india

    return india(limit=limit)


@router.get("/macro/global")
async def cmkp_global(limit: int = Query(100, ge=1, le=500)):
    from continuous_macro_knowledge.production import global_macro

    return global_macro(limit=limit)


@router.get("/macro/indicator/{indicator}")
async def cmkp_indicator(indicator: str, country: str | None = None):
    from continuous_macro_knowledge.production import indicator as get_indicator

    return get_indicator(indicator, country=country)


@router.get("/macro/releases")
async def cmkp_releases(limit: int = Query(50, ge=1, le=200)):
    from continuous_macro_knowledge.production import releases

    return releases(limit=limit)


@router.get("/macro/calendar")
async def cmkp_calendar(limit: int = Query(50, ge=1, le=200)):
    from continuous_macro_knowledge.production import release_calendar

    return release_calendar(limit=limit)


@router.post("/macro/run")
async def cmkp_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from continuous_macro_knowledge.production import run

    sources = payload.get("sources")
    if sources is not None and not isinstance(sources, list):
        raise HTTPException(status_code=400, detail="sources must be a list")
    return run(sources=sources)


@router.get("/admin/macro-operations", response_class=HTMLResponse)
async def admin_cmkp():
    from continuous_macro_knowledge.production import dashboard

    board = dashboard()
    health_rows = "".join(
        f"<tr><td>{s}</td><td>{h.get('ok')}</td><td>{h.get('success_count')}</td>"
        f"<td>{h.get('failure_count')}</td></tr>"
        for s, h in (board.get("collector_health") or {}).items()
    )
    release_rows = "".join(
        f"<tr><td>{r.get('country')}</td><td>{r.get('indicator')}</td>"
        f"<td>{r.get('current_value')}</td><td>{r.get('materiality_tier')}</td>"
        f"<td>{r.get('source')}</td></tr>"
        for r in (board.get("latest_releases") or [])
    )
    learn_rows = "".join(
        f"<tr><td>{l.get('topic')}</td><td>{l.get('materiality_tier')}</td>"
        f"<td>{l.get('future_guidance')}</td></tr>"
        for l in (board.get("learning_events") or [])
    )
    html = f"""<!doctype html><html><head><title>Macro Operations</title></head>
    <body style="font-family:system-ui;max-width:1000px;margin:2rem auto">
    <h1>Macro Operations — CMKP</h1>
    <p>Continuous background ingestion. Ask never fetches macro data.</p>
    <pre>{board.get('principles')}</pre>
    <p>Coverage: {board.get('knowledge_coverage')}</p>
    <h2>Collector health</h2>
    <table border="1" cellpadding="6">
    <tr><th>Source</th><th>OK</th><th>Success</th><th>Failure</th></tr>
    {health_rows or '<tr><td colspan=4>No collector ticks — run POST /v1/macro/run</td></tr>'}
    </table>
    <h2>Latest releases</h2>
    <table border="1" cellpadding="6">
    <tr><th>Country</th><th>Indicator</th><th>Value</th><th>Materiality</th><th>Source</th></tr>
    {release_rows or '<tr><td colspan=5>None published</td></tr>'}
    </table>
    <h2>Learning events</h2>
    <table border="1" cellpadding="6">
    <tr><th>Topic</th><th>Tier</th><th>Guidance</th></tr>
    {learn_rows or '<tr><td colspan=3>No material learning yet</td></tr>'}
    </table>
    <h2>Upcoming</h2>
    <pre>{board.get('upcoming_releases')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Historical Macroeconomic Intelligence Platform (HMIP) Sprint 10.2 ---
# Immutable decades-scale macro memory. Analysis never calls external providers.


@router.get("/hmip/health")
async def hmip_health():
    from historical_macro_intelligence.production import health

    return health()


@router.get("/macro/history")
async def hmip_history(limit: int = Query(200, ge=1, le=1000), country: str | None = None):
    from historical_macro_intelligence.production import history

    return history(limit=limit, country=country)


@router.get("/macro/history/dashboard")
async def hmip_dashboard():
    from historical_macro_intelligence.production import dashboard

    return dashboard()


@router.get("/macro/history/timeline")
async def hmip_timeline(indicator: str | None = None, country: str = Query("India")):
    from historical_macro_intelligence.production import timeline

    return timeline(indicator=indicator, country=country)


@router.get("/macro/history/search")
async def hmip_search(
    q: str | None = None,
    category: str | None = None,
    country: str | None = None,
    namespace: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    from historical_macro_intelligence.production import search

    return search(q=q, category=category, country=country, namespace=namespace, limit=limit)


@router.post("/macro/history/run")
async def hmip_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from historical_macro_intelligence.production import run

    sources = payload.get("sources")
    if sources is not None and not isinstance(sources, list):
        raise HTTPException(status_code=400, detail="sources must be a list")
    return run(sources=sources)


@router.get("/macro/history/country/{country}")
async def hmip_country(country: str, limit: int = Query(300, ge=1, le=1000)):
    from historical_macro_intelligence.production import country as get_country

    return get_country(country, limit=limit)


@router.get("/macro/history/{indicator}")
async def hmip_indicator(indicator: str, country: str = Query("India")):
    from historical_macro_intelligence.production import indicator as get_indicator

    return get_indicator(indicator, country=country)


@router.get("/admin/historical-macro", response_class=HTMLResponse)
async def admin_hmip():
    from historical_macro_intelligence.production import dashboard

    board = dashboard()
    cov = board.get("historical_coverage") or {}
    tl_rows = "".join(
        f"<tr><td>{s.get('country')}</td><td>{s.get('indicator')}</td>"
        f"<td>{s.get('completeness_pct')}</td><td>{s.get('nodes')}</td>"
        f"<td>{s.get('years_span')}</td></tr>"
        for s in ((board.get("timeline_completeness") or {}).get("sample") or [])
    )
    miss = board.get("missing_periods") or []
    html = f"""<!doctype html><html><head><title>Historical Macro</title></head>
    <body style="font-family:system-ui;max-width:1000px;margin:2rem auto">
    <h1>Historical Macro — HMIP</h1>
    <p>Immutable decades-scale memory. Never overwritten. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <p>Observations: {cov.get('total_observations')} · Indicators: {cov.get('unique_indicators')} ·
    Years: {cov.get('year_span')}</p>
    <h2>Timeline completeness</h2>
    <table border="1" cellpadding="6">
    <tr><th>Country</th><th>Indicator</th><th>Completeness %</th><th>Nodes</th><th>Span</th></tr>
    {tl_rows or '<tr><td colspan=5>Run POST /v1/macro/history/run</td></tr>'}
    </table>
    <h2>Missing periods</h2>
    <pre>{miss[:15]}</pre>
    <h2>Storage by namespace</h2>
    <pre>{cov.get('by_namespace')}</pre>
    <h2>Revision history</h2>
    <pre>{board.get('revision_history')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Macroeconomic Relationship Intelligence (MRI) Sprint 10.3 ---
# Evidence-backed macro relationships. Never inferred without historical support.


@router.get("/mri/health")
async def mri_health():
    from macroeconomic_relationship_intelligence.production import health

    return health()


@router.get("/macro/relationships")
async def mri_relationships(limit: int = Query(200, ge=1, le=1000)):
    from macroeconomic_relationship_intelligence.production import relationships

    return relationships(limit=limit)


@router.get("/macro/relationships/graph")
async def mri_graph():
    from macroeconomic_relationship_intelligence.production import graph

    return graph()


@router.get("/macro/relationships/dashboard")
async def mri_dashboard():
    from macroeconomic_relationship_intelligence.production import dashboard

    return dashboard()


@router.post("/macro/relationships/run")
async def mri_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from macroeconomic_relationship_intelligence.production import run

    return run(enrich_hmip=bool(payload.get("enrich_hmip", True)))


@router.get("/macro/relationships/company/{ticker}")
async def mri_company(ticker: str, limit: int = Query(100, ge=1, le=500)):
    from macroeconomic_relationship_intelligence.production import for_company

    return for_company(ticker, limit=limit)


@router.get("/macro/relationships/sector/{sector}")
async def mri_sector(sector: str, limit: int = Query(100, ge=1, le=500)):
    from macroeconomic_relationship_intelligence.production import for_sector

    return for_sector(sector, limit=limit)


@router.get("/macro/relationships/{indicator}")
async def mri_indicator(indicator: str, limit: int = Query(100, ge=1, le=500)):
    from macroeconomic_relationship_intelligence.production import for_indicator

    return for_indicator(indicator, limit=limit)


@router.get("/admin/macro-relationships", response_class=HTMLResponse)
async def admin_mri():
    from macroeconomic_relationship_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("relationship_confidence_distribution") or {}
    rows = "".join(
        f"<tr><td>{r.get('source')}</td><td>{r.get('target')}</td>"
        f"<td>{r.get('relationship')}</td><td>{r.get('confidence_pct')}</td>"
        f"<td>{r.get('average_lag')}</td></tr>"
        for r in (board.get("recently_validated_relationships") or [])
    )
    html = f"""<!doctype html><html><head><title>Macro Relationship Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1000px;margin:2rem auto">
    <h1>Macro Relationship Intelligence — MRI</h1>
    <p>Evidence-backed only. Versioned graph. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <p>Total: {board.get('total_relationships')} · High confidence: {board.get('high_confidence')} ·
    Distribution: {dist}</p>
    <h2>Coverage</h2>
    <pre>{board.get('coverage_by_indicator_sector_company')}</pre>
    <h2>Recently validated</h2>
    <table border="1" cellpadding="6">
    <tr><th>Source</th><th>Target</th><th>Relationship</th><th>Confidence</th><th>Lag</th></tr>
    {rows or '<tr><td colspan=5>Run POST /v1/macro/relationships/run</td></tr>'}
    </table>
    <h2>Stale</h2>
    <pre>{len(board.get('stale_relationships') or [])} stale relationships</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Historical Macro Analogue Intelligence (HMAI) Sprint 10.4 ---
# Deterministic, explainable historical macro regime analogues. Never collects on Ask.


@router.get("/hmai/health")
async def hmai_health():
    from historical_macro_analogue_intelligence.production import health

    return health()


@router.get("/macro/analogues")
async def hmai_analogues(
    limit: int = Query(20, ge=1, le=100),
    country: str | None = None,
):
    from historical_macro_analogue_intelligence.production import analogues

    return analogues(country=country, limit=limit)


@router.get("/macro/analogues/search")
async def hmai_search(
    q: str | None = None,
    question: str | None = None,
    country: str = Query("India"),
    target_period: str | None = None,
    top_k: int = Query(5, ge=1, le=20),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
):
    from historical_macro_analogue_intelligence.production import search

    return search(
        country=country,
        question=question or q,
        target_period=target_period,
        top_k=top_k,
        min_score=min_score,
    )


@router.get("/macro/analogues/dashboard")
async def hmai_dashboard():
    from historical_macro_analogue_intelligence.production import dashboard

    return dashboard()


@router.post("/macro/analogues/run")
async def hmai_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from historical_macro_analogue_intelligence.production import run

    return run(
        country=str(payload.get("country") or "India"),
        enrich_hmip=bool(payload.get("enrich_hmip", True)),
        top_k=int(payload.get("top_k") or 10),
    )


@router.get("/macro/analogues/{country}")
async def hmai_country(country: str, limit: int = Query(20, ge=1, le=100)):
    from historical_macro_analogue_intelligence.production import analogues_for_country

    return analogues_for_country(country, limit=limit)


@router.get("/macro/regime/current")
async def hmai_regime_current(country: str = Query("India")):
    from historical_macro_analogue_intelligence.production import current_regime

    return current_regime(country=country)


@router.get("/macro/regime/history")
async def hmai_regime_history(
    country: str = Query("India"),
    limit: int = Query(50, ge=1, le=200),
):
    from historical_macro_analogue_intelligence.production import regime_history

    return regime_history(country=country, limit=limit)


@router.get("/admin/macro-analogues", response_class=HTMLResponse)
async def admin_hmai():
    from historical_macro_analogue_intelligence.production import dashboard

    board = dashboard()
    cur = board.get("current_macro_regime") or {}
    dist = board.get("similarity_distribution") or {}
    rows = "".join(
        f"<tr><td>{a.get('rank')}</td><td>{a.get('matched_period')}</td>"
        f"<td>{a.get('matched_label')}</td><td>{a.get('similarity_score')}</td>"
        f"<td>{a.get('confidence')}</td>"
        f"<td>{', '.join(a.get('matching_dimensions') or [])}</td></tr>"
        for a in (board.get("top_analogue_matches") or [])
    )
    html = f"""<!doctype html><html><head><title>Historical Macro Analogue</title></head>
    <body style="font-family:system-ui;max-width:1000px;margin:2rem auto">
    <h1>Historical Macro Analogue Intelligence — HMAI</h1>
    <p>Deterministic multi-dimension similarity. Ask never fetches. No forecasting in 10.4.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current macro regime</h2>
    <pre>Period: {cur.get('period')} · {cur.get('label')}</pre>
    <pre>{cur.get('features')}</pre>
    <h2>Similarity distribution</h2>
    <pre>{dist}</pre>
    <h2>Confidence</h2>
    <pre>{board.get('confidence_distribution')}</pre>
    <h2>Historical coverage</h2>
    <pre>{board.get('historical_coverage')}</pre>
    <h2>Analogue freshness</h2>
    <pre>{board.get('analogue_freshness')}</pre>
    <h2>Top analogue matches</h2>
    <table border="1" cellpadding="6">
    <tr><th>Rank</th><th>Period</th><th>Label</th><th>Similarity</th><th>Confidence</th><th>Matching</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/macro/analogues/run</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Macroeconomic Forecast Intelligence (MFI) Sprint 10.5 ---
# Evidence-based Bull/Base/Bear from AGI macro knowledge. Never external providers.


@router.get("/mfi/health")
async def mfi_health():
    from macroeconomic_forecast_intelligence.production import health

    return health()


@router.get("/macro/forecast/india")
async def mfi_india():
    from macroeconomic_forecast_intelligence.production import india

    return india()


@router.get("/macro/forecast/global")
async def mfi_global():
    from macroeconomic_forecast_intelligence.production import global_forecast

    return global_forecast()


@router.get("/macro/forecast/report")
async def mfi_report(persist: bool = Query(False)):
    from macroeconomic_forecast_intelligence.production import report

    return report(persist=persist)


@router.get("/macro/forecast/dashboard")
async def mfi_dashboard():
    from macroeconomic_forecast_intelligence.production import dashboard

    return dashboard()


@router.get("/macro/forecast/history")
async def mfi_history(limit: int = Query(20, ge=1, le=100), country: str = Query("India")):
    from macroeconomic_forecast_intelligence.production import history

    return history(country=country, limit=limit)


@router.post("/macro/forecast/run")
async def mfi_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from macroeconomic_forecast_intelligence.production import run

    return run(
        country=str(payload.get("country") or "India"),
        region=str(payload.get("region") or "India"),
    )


@router.get("/macro/forecast")
async def mfi_forecast(country: str = Query("India")):
    from macroeconomic_forecast_intelligence.production import forecast

    return forecast(country=country)


@router.get("/macro/scenarios")
async def mfi_scenarios(country: str = Query("India")):
    from macroeconomic_forecast_intelligence.production import scenarios

    return scenarios(country=country)


@router.get("/macro/probability")
async def mfi_probability(country: str = Query("India")):
    from macroeconomic_forecast_intelligence.production import probability

    return probability(country=country)


@router.get("/admin/macro-forecast", response_class=HTMLResponse)
async def admin_mfi():
    from macroeconomic_forecast_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("probability_distribution") or {}
    conf = board.get("confidence") or {}
    rows = "".join(
        f"<tr><td>{s.get('scenario')}</td><td>{s.get('probability_pct')}</td>"
        f"<td>{s.get('confidence_pct')}</td><td>{s.get('gdp')}</td>"
        f"<td>{s.get('inflation')}</td><td>{s.get('repo_rate')}</td></tr>"
        for s in (board.get("bull_base_bear_scenarios") or [])
    )
    html = f"""<!doctype html><html><head><title>Macro Forecast Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Macro Forecast Intelligence — MFI</h1>
    <p>Evidence-based Bull/Base/Bear. AGI-owned knowledge only. No single-path prediction.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current macro regime</h2>
    <pre>{board.get('current_macro_regime')}</pre>
    <h2>Probability distribution</h2>
    <pre>{dist}</pre>
    <h2>Confidence</h2>
    <pre>{conf}</pre>
    <h2>Bull / Base / Bear</h2>
    <table border="1" cellpadding="6">
    <tr><th>Scenario</th><th>Prob %</th><th>Conf %</th><th>GDP</th><th>CPI</th><th>Repo</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/macro/forecast/run</td></tr>'}
    </table>
    <h2>Sector impact matrix</h2>
    <pre>{board.get('sector_impact_matrix')}</pre>
    <h2>Company impact matrix</h2>
    <pre>{board.get('company_impact_matrix')}</pre>
    <h2>Key catalysts</h2>
    <pre>{board.get('key_macro_catalysts')}</pre>
    <h2>Upcoming events</h2>
    <pre>{board.get('upcoming_macro_events')}</pre>
    <h2>Forecast history</h2>
    <pre>{board.get('forecast_history')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Continuous Sector Knowledge Platform (CSKP) Sprint 11.1 ---
# Event-driven derived sector knowledge. Ask never constructs or collects.


@router.get("/cskp/health")
async def cskp_health():
    from continuous_sector_knowledge.production import health

    return health()


@router.get("/sector/dashboard")
async def cskp_dashboard():
    from continuous_sector_knowledge.production import dashboard

    return dashboard()


@router.get("/sector/leaders")
async def cskp_leaders(limit: int = Query(50, ge=1, le=200)):
    from continuous_sector_knowledge.production import leaders

    return leaders(limit=limit)


@router.get("/sector/comparison")
async def cskp_comparison(sectors: str | None = None):
    from continuous_sector_knowledge.production import comparison

    keys = [s.strip() for s in sectors.split(",")] if sectors else None
    return comparison(sectors=keys)


@router.get("/sector/calendar")
async def cskp_calendar(limit: int = Query(50, ge=1, le=200)):
    from continuous_sector_knowledge.production import calendar

    return calendar(limit=limit)


# --- Historical Sector Intelligence Platform (HSIP) Sprint 11.2 ---
# Immutable historical sector memory. Ask never collects.


@router.get("/hsip/health")
async def hsip_health():
    from historical_sector_intelligence.production import health

    return health()


@router.get("/sector/history")
async def hsip_history(
    limit: int = Query(200, ge=1, le=1000),
    sector: str | None = None,
):
    from historical_sector_intelligence.production import history

    return history(limit=limit, sector=sector)


@router.get("/sector/history/timeline")
async def hsip_timeline(
    sector: str | None = None,
    indicator: str | None = None,
):
    from historical_sector_intelligence.production import timeline

    return timeline(sector=sector, indicator=indicator)


@router.get("/sector/history/search")
async def hsip_search(
    q: str | None = None,
    category: str | None = None,
    sector: str | None = None,
    namespace: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    from historical_sector_intelligence.production import search

    return search(q=q, category=category, sector=sector, namespace=namespace, limit=limit)


@router.get("/sector/history/events")
async def hsip_events(
    sector: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    from historical_sector_intelligence.production import events

    return events(sector=sector, limit=limit)


@router.get("/sector/history/dashboard")
async def hsip_dashboard():
    from historical_sector_intelligence.production import dashboard

    return dashboard()


@router.post("/sector/history/run")
async def hsip_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from historical_sector_intelligence.production import run

    sources = payload.get("sources")
    if isinstance(sources, str):
        sources = [s.strip() for s in sources.split(",") if s.strip()]
    return run(sources=sources if isinstance(sources, list) else None)


@router.get("/sector/history/{sector}")
async def hsip_sector(sector: str, limit: int = Query(300, ge=1, le=1000)):
    from historical_sector_intelligence.production import sector as get_sector

    return get_sector(sector, limit=limit)


@router.get("/admin/historical-sector", response_class=HTMLResponse)
async def admin_hsip():
    from historical_sector_intelligence.production import dashboard

    board = dashboard()
    cov = board.get("historical_coverage") or {}
    tl = board.get("timeline_completeness") or {}
    rows = "".join(
        f"<tr><td>{e.get('sector')}</td><td>{e.get('period')}</td>"
        f"<td>{e.get('events')}</td></tr>"
        for e in (board.get("historical_events") or [])[:20]
    )
    html = f"""<!doctype html><html><head><title>Historical Sector</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Historical Sector Intelligence — HSIP</h1>
    <p>Immutable institutional sector memory. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Historical coverage</h2>
    <pre>{cov}</pre>
    <h2>Years available</h2>
    <pre>{board.get('years_available')}</pre>
    <h2>Timeline completeness</h2>
    <pre>{tl}</pre>
    <h2>Historical events</h2>
    <table border="1" cellpadding="6">
    <tr><th>Sector</th><th>Period</th><th>Events</th></tr>
    {rows or '<tr><td colspan=3>Run POST /v1/sector/history/run</td></tr>'}
    </table>
    <h2>Policy history</h2>
    <pre>{board.get('policy_history')}</pre>
    <h2>Valuation history</h2>
    <pre>{board.get('valuation_history')}</pre>
    <h2>Missing periods</h2>
    <pre>{board.get('missing_periods')}</pre>
    <h2>Data quality</h2>
    <pre>{board.get('data_quality')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Sector Relationship Intelligence (SRI) Sprint 11.3 ---
# Evidence-backed sector relationship graph. Ask never collects or rebuilds.


@router.get("/sri/health")
async def sri_health():
    from sector_relationship_intelligence.production import health

    return health()


@router.get("/sector/relationships")
async def sri_relationships(limit: int = Query(200, ge=1, le=1000)):
    from sector_relationship_intelligence.production import relationships

    return relationships(limit=limit)


@router.get("/sector/relationships/graph")
async def sri_graph(
    start: str | None = None,
    end: str | None = None,
):
    from sector_relationship_intelligence.production import graph

    return graph(start=start, end=end)


@router.get("/sector/relationships/search")
async def sri_search(
    q: str | None = None,
    kind: str | None = None,
    source: str | None = None,
    target: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    from sector_relationship_intelligence.production import search

    return search(q=q, kind=kind, source=source, target=target, limit=limit)


@router.get("/sector/relationships/dashboard")
async def sri_dashboard():
    from sector_relationship_intelligence.production import dashboard

    return dashboard()


@router.post("/sector/relationships/run")
async def sri_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from sector_relationship_intelligence.production import run

    return run(
        enrich_hsip=bool(payload.get("enrich_hsip", True)),
        enrich_hmip=bool(payload.get("enrich_hmip", True)),
        enrich_mri=bool(payload.get("enrich_mri", True)),
    )


@router.get("/sector/relationships/company/{ticker}")
async def sri_company(ticker: str, limit: int = Query(100, ge=1, le=500)):
    from sector_relationship_intelligence.production import for_company

    return for_company(ticker, limit=limit)


@router.get("/sector/relationships/{sector}")
async def sri_sector(sector: str, limit: int = Query(100, ge=1, le=500)):
    from sector_relationship_intelligence.production import for_sector

    return for_sector(sector, limit=limit)


@router.get("/admin/sector-relationships", response_class=HTMLResponse)
async def admin_sri():
    from sector_relationship_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("confidence_distribution") or {}
    rows = "".join(
        f"<tr><td>{r.get('source')}</td><td>{r.get('target')}</td>"
        f"<td>{r.get('relationship')}</td><td>{r.get('confidence_pct')}</td>"
        f"<td>{r.get('average_lag')}</td><td>{r.get('kind')}</td></tr>"
        for r in (board.get("recently_validated_relationships") or [])
    )
    html = f"""<!doctype html><html><head><title>Sector Relationship Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Sector Relationship Intelligence — SRI</h1>
    <p>Evidence-backed only. Versioned graph. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <p>Total: {board.get('total_relationships')} · Active: {board.get('active_relationships')} ·
    High confidence: {board.get('high_confidence')} · Distribution: {dist}</p>
    <h2>Coverage by sector</h2>
    <pre>{board.get('relationship_coverage_by_sector')}</pre>
    <h2>Freshness</h2>
    <pre>{board.get('relationship_freshness')}</pre>
    <h2>Recently validated</h2>
    <table border="1" cellpadding="6">
    <tr><th>Source</th><th>Target</th><th>Relationship</th><th>Confidence</th><th>Lag</th><th>Kind</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/sector/relationships/run</td></tr>'}
    </table>
    <h2>Validation failures</h2>
    <pre>{board.get('validation_failures')}</pre>
    <h2>By kind</h2>
    <pre>{board.get('by_kind')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Historical Sector Analogue Intelligence (HSAI) Sprint 11.4 ---
# Deterministic, explainable historical sector regime analogues. Ask never collects.


@router.get("/hsai/health")
async def hsai_health():
    from historical_sector_analogue_intelligence.production import health

    return health()


@router.get("/sector/analogues")
async def hsai_analogues(
    sector: str | None = None,
    limit: int = Query(20, ge=1, le=200),
):
    from historical_sector_analogue_intelligence.production import analogues

    return analogues(sector=sector, limit=limit)


@router.get("/sector/analogues/search")
async def hsai_search(
    q: str | None = None,
    question: str | None = None,
    sector: str | None = None,
    target_period: str | None = None,
    top_k: int = Query(5, ge=1, le=20),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
):
    from historical_sector_analogue_intelligence.production import search

    return search(
        sector=sector,
        question=question or q,
        target_period=target_period,
        top_k=top_k,
        min_score=min_score,
    )


@router.get("/sector/analogues/dashboard")
async def hsai_dashboard():
    from historical_sector_analogue_intelligence.production import dashboard

    return dashboard()


@router.post("/sector/analogues/run")
async def hsai_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from historical_sector_analogue_intelligence.production import run

    return run(
        sector=payload.get("sector"),
        enrich_hsip=bool(payload.get("enrich_hsip", True)),
        enrich_cskp=bool(payload.get("enrich_cskp", True)),
        top_k=int(payload.get("top_k", 10)),
    )


@router.get("/sector/analogues/{sector}")
async def hsai_sector(sector: str, limit: int = Query(20, ge=1, le=200)):
    from historical_sector_analogue_intelligence.production import analogues_for_sector

    return analogues_for_sector(sector, limit=limit)


@router.get("/sector/regime/current")
async def hsai_regime_current(sector: str = Query("Banking")):
    from historical_sector_analogue_intelligence.production import current_regime

    return current_regime(sector=sector)


@router.get("/sector/regime/history")
async def hsai_regime_history(
    sector: str = Query("Banking"),
    limit: int = Query(50, ge=1, le=200),
):
    from historical_sector_analogue_intelligence.production import regime_history

    return regime_history(sector=sector, limit=limit)


@router.get("/admin/sector-analogues", response_class=HTMLResponse)
async def admin_hsai():
    from historical_sector_analogue_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("similarity_distribution") or {}
    rows = "".join(
        f"<tr><td>{r.get('sector')}</td><td>{r.get('matched_period')}</td>"
        f"<td>{r.get('matched_label')}</td><td>{r.get('similarity_score')}</td>"
        f"<td>{r.get('confidence')}</td></tr>"
        for r in (board.get("top_analogue_matches") or [])
    )
    html = f"""<!doctype html><html><head><title>Historical Sector Analogue</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Historical Sector Analogue Intelligence — HSAI</h1>
    <p>Deterministic similarity. Evidence-linked. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current sector regime</h2>
    <pre>{board.get('current_sector_regime')}</pre>
    <p>Similarity distribution: {dist} · Confidence: {board.get('confidence_distribution')}</p>
    <h2>Coverage by sector</h2>
    <pre>{board.get('coverage_by_sector')}</pre>
    <h2>Top analogue matches</h2>
    <table border="1" cellpadding="6">
    <tr><th>Sector</th><th>Period</th><th>Label</th><th>Similarity</th><th>Confidence</th></tr>
    {rows or '<tr><td colspan=5>Run POST /v1/sector/analogues/run</td></tr>'}
    </table>
    <h2>Historical coverage</h2>
    <pre>{board.get('historical_coverage')}</pre>
    <h2>Freshness</h2>
    <pre>{board.get('analogue_freshness')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Sector Forecast Intelligence (SFI) Sprint 11.5 ---
# Evidence-based Bull/Base/Bear sector scenarios. Ask never collects. Inherits MFI.


@router.get("/sfi/health")
async def sfi_health():
    from sector_forecast_intelligence.production import health

    return health()


@router.get("/sector/forecast")
async def sfi_forecast_all(limit: int = Query(20, ge=1, le=50)):
    from sector_forecast_intelligence.production import forecast_all

    return forecast_all(limit=limit)


@router.get("/sector/forecast/report")
async def sfi_report(
    sector: str = Query("Banking"),
    persist: bool = Query(False),
):
    from sector_forecast_intelligence.production import report

    return report(sector=sector, persist=persist)


@router.get("/sector/forecast/dashboard")
async def sfi_dashboard():
    from sector_forecast_intelligence.production import dashboard

    return dashboard()


@router.get("/sector/forecast/history")
async def sfi_history(
    sector: str | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    from sector_forecast_intelligence.production import history

    return history(sector=sector, limit=limit)


@router.post("/sector/forecast/run")
async def sfi_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from sector_forecast_intelligence.production import run

    return run(sector=payload.get("sector"), country=payload.get("country") or "India")


@router.get("/sector/forecast/{sector}")
async def sfi_forecast_sector(sector: str):
    from sector_forecast_intelligence.production import forecast

    return forecast(sector=sector)


@router.get("/sector/scenarios")
async def sfi_scenarios(sector: str = Query("Banking")):
    from sector_forecast_intelligence.production import scenarios

    return scenarios(sector=sector)


@router.get("/sector/probability")
async def sfi_probability(sector: str = Query("Banking")):
    from sector_forecast_intelligence.production import probability

    return probability(sector=sector)


@router.get("/admin/sector-forecast", response_class=HTMLResponse)
async def admin_sfi():
    from sector_forecast_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("probability_distribution") or {}
    rows = "".join(
        f"<tr><td>{s.get('scenario')}</td><td>{s.get('probability_pct')}</td>"
        f"<td>{s.get('confidence_pct')}</td><td>{s.get('revenue_growth')}</td>"
        f"<td>{s.get('expected_relative_performance')}</td></tr>"
        for s in (board.get("bull_base_bear_scenarios") or [])
    )
    html = f"""<!doctype html><html><head><title>Sector Forecast Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Sector Forecast Intelligence — SFI</h1>
    <p>Bull/Base/Bear pathways. AGI-owned knowledge only. Ask never fetches. Inherits MFI.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current sector outlook</h2>
    <pre>{board.get('current_sector_outlook')}</pre>
    <p>Probability: {dist} · Confidence: {board.get('confidence')}</p>
    <h2>Bull / Base / Bear</h2>
    <table border="1" cellpadding="6">
    <tr><th>Scenario</th><th>Probability</th><th>Confidence</th><th>Rev Growth</th><th>Rel Perf</th></tr>
    {rows or '<tr><td colspan=5>Run POST /v1/sector/forecast/run</td></tr>'}
    </table>
    <h2>Key catalysts</h2>
    <pre>{board.get('key_catalysts')}</pre>
    <h2>Major risks</h2>
    <pre>{board.get('major_risks')}</pre>
    <h2>Company impacts</h2>
    <pre>{board.get('company_impact_summaries')}</pre>
    <h2>Macro inheritance</h2>
    <pre>{board.get('macro_inheritance')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Continuous Market Knowledge Platform (CMKTP) Sprint 12.1 ---
# Institutional Market Knowledge Objects. Not a market data service. Ask never collects.


@router.get("/cmktp/health")
async def cmktp_health():
    from continuous_market_knowledge.production import health

    return health()


@router.get("/market/dashboard")
async def cmktp_dashboard():
    from continuous_market_knowledge.production import dashboard

    return dashboard()


@router.get("/market/regime")
async def cmktp_regime():
    from continuous_market_knowledge.production import regime

    return regime()


@router.get("/market/breadth")
async def cmktp_breadth():
    from continuous_market_knowledge.production import breadth

    return breadth()


@router.get("/market/liquidity")
async def cmktp_liquidity():
    from continuous_market_knowledge.production import liquidity

    return liquidity()


@router.get("/market/leadership")
async def cmktp_leadership():
    from continuous_market_knowledge.production import leadership

    return leadership()


@router.get("/market/flows")
async def cmktp_flows():
    from continuous_market_knowledge.production import flows

    return flows()


@router.get("/market/volatility")
async def cmktp_volatility():
    from continuous_market_knowledge.production import volatility

    return volatility()


@router.get("/market/health")
async def cmktp_market_health():
    from continuous_market_knowledge.production import market_health

    return market_health()


@router.post("/market/run")
async def cmktp_run(payload: dict[str, Any] = Body(default={})):
    """Ops / event-driven only — never called by Ask."""
    from continuous_market_knowledge.production import run

    domains = payload.get("domains")
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    return run(
        domains=domains if isinstance(domains, list) else None,
        trigger=payload.get("trigger"),
    )


@router.get("/market")
async def cmktp_market():
    from continuous_market_knowledge.production import market

    return market()


@router.get("/admin/market-operations", response_class=HTMLResponse)
async def admin_cmktp():
    from continuous_market_knowledge.production import dashboard

    board = dashboard()
    html = f"""<!doctype html><html><head><title>Market Intelligence Operations</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Market Intelligence Operations — CMKTP</h1>
    <p>Not a market data service. Higher-order knowledge only. Ask never fetches.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current market regime</h2>
    <pre>{board.get('current_market_regime')}</pre>
    <h2>Market health score</h2>
    <pre>{board.get('market_health_score')}</pre>
    <h2>Breadth</h2>
    <pre>{board.get('breadth_dashboard')}</pre>
    <h2>Liquidity</h2>
    <pre>{board.get('liquidity_dashboard')}</pre>
    <h2>Institutional flows</h2>
    <pre>{board.get('institutional_flows')}</pre>
    <h2>Sector leadership</h2>
    <pre>{board.get('sector_leadership')}</pre>
    <h2>Cross-asset</h2>
    <pre>{board.get('cross_asset_dashboard')}</pre>
    <h2>Risk sentiment</h2>
    <pre>{board.get('risk_sentiment')}</pre>
    <h2>Latest material events</h2>
    <pre>{board.get('latest_material_events')}</pre>
    <h2>Knowledge freshness</h2>
    <pre>{board.get('knowledge_freshness')}</pre>
    <h2>Collection / publication</h2>
    <pre>{board.get('collection_status')}</pre>
    <pre>{board.get('publication_status')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Historical Market Intelligence Platform (HMKIP) Sprint 12.2 ---
# Immutable Historical Market Knowledge Objects. Ask never collects.
# Programme short HMKIP avoids collision with Historical Macro Intelligence (HMIP).


@router.get("/hmkip/health")
async def hmkip_health():
    from historical_market_intelligence.production import health

    return health()


@router.get("/market/history")
async def hmkip_history(
    limit: int = Query(200, ge=1, le=2000),
    market: str | None = Query(None),
):
    from historical_market_intelligence.production import history

    return history(limit=limit, market=market)


@router.get("/market/history/timeline")
async def hmkip_timeline(
    market: str | None = Query(None),
    indicator: str | None = Query(None),
):
    from historical_market_intelligence.production import timeline

    return timeline(market=market, indicator=indicator)


@router.get("/market/history/regimes")
async def hmkip_regimes(
    market: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import regimes

    return regimes(market=market, limit=limit)


@router.get("/market/history/breadth")
async def hmkip_breadth(
    market: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import breadth

    return breadth(market=market, limit=limit)


@router.get("/market/history/liquidity")
async def hmkip_liquidity(
    market: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import liquidity

    return liquidity(market=market, limit=limit)


@router.get("/market/history/volatility")
async def hmkip_volatility(
    market: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import volatility

    return volatility(market=market, limit=limit)


@router.get("/market/history/flows")
async def hmkip_flows(
    market: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import flows

    return flows(market=market, limit=limit)


@router.get("/market/history/search")
async def hmkip_search(
    q: str | None = Query(None),
    category: str | None = Query(None),
    market: str | None = Query(None),
    namespace: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    from historical_market_intelligence.production import search

    return search(q=q, category=category, market=market, namespace=namespace, limit=limit)


@router.post("/market/history/run")
async def hmkip_run(payload: dict[str, Any] = Body(default={})):
    """Ops / backfill only — never called by Ask."""
    from historical_market_intelligence.production import run

    sources = payload.get("sources")
    if isinstance(sources, str):
        sources = [s.strip() for s in sources.split(",") if s.strip()]
    markets = payload.get("markets")
    if isinstance(markets, str):
        markets = [m.strip() for m in markets.split(",") if m.strip()]
    return run(
        sources=sources if isinstance(sources, list) else None,
        markets=markets if isinstance(markets, list) else None,
    )


@router.get("/market/history/{market}")
async def hmkip_market(market: str, limit: int = Query(300, ge=1, le=1000)):
    from historical_market_intelligence.production import market as get_market

    return get_market(market, limit=limit)


@router.get("/admin/historical-market", response_class=HTMLResponse)
async def admin_hmkip():
    from historical_market_intelligence.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{r.get('market')}</td><td>{r.get('indicator')}</td>"
        f"<td>{r.get('completeness_pct')}</td></tr>"
        for r in ((board.get("timeline_completeness") or {}).get("sample") or [])
    )
    html = f"""<!doctype html><html><head><title>Historical Market Operations</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Historical Market Intelligence — HMKIP</h1>
    <p>Immutable institutional market memory. Ask never fetches. No external providers on read.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Historical coverage</h2>
    <pre>{board.get('historical_coverage')}</pre>
    <h2>Timeline completeness</h2>
    <table border=1 cellpadding=6><tr><th>Market</th><th>Indicator</th><th>Completeness %</th></tr>
    {rows or '<tr><td colspan=3>Run POST /v1/market/history/run</td></tr>'}
    </table>
    <h2>Regime history</h2>
    <pre>{board.get('regime_history')}</pre>
    <h2>Breadth / Liquidity / Volatility / Flows</h2>
    <pre>{board.get('breadth_history')}</pre>
    <pre>{board.get('liquidity_history')}</pre>
    <pre>{board.get('volatility_history')}</pre>
    <pre>{board.get('flow_history')}</pre>
    <h2>Cross-asset</h2>
    <pre>{board.get('cross_asset_history')}</pre>
    <h2>Missing periods</h2>
    <pre>{board.get('missing_periods')}</pre>
    <h2>Data quality / freshness</h2>
    <pre>{board.get('data_quality')}</pre>
    <pre>{board.get('knowledge_freshness')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Market Relationship Intelligence (MKRI) Sprint 12.3 ---
# Evidence-backed market relationship graph. Ask never collects or rebuilds.
# Programme short MKRI avoids collision with Macroeconomic Relationship Intelligence (MRI).


@router.get("/mkri/health")
async def mkri_health():
    from market_relationship_intelligence.production import health

    return health()


@router.get("/market/relationships")
async def mkri_relationships(limit: int = Query(200, ge=1, le=1000)):
    from market_relationship_intelligence.production import relationships

    return relationships(limit=limit)


@router.get("/market/relationships/graph")
async def mkri_graph(
    start: str | None = None,
    end: str | None = None,
):
    from market_relationship_intelligence.production import graph

    return graph(start=start, end=end)


@router.get("/market/relationships/search")
async def mkri_search(
    q: str | None = None,
    kind: str | None = None,
    source: str | None = None,
    target: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    from market_relationship_intelligence.production import search

    return search(q=q, kind=kind, source=source, target=target, limit=limit)


@router.get("/market/relationships/dashboard")
async def mkri_dashboard():
    from market_relationship_intelligence.production import dashboard

    return dashboard()


@router.post("/market/relationships/run")
async def mkri_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from market_relationship_intelligence.production import run

    return run(
        enrich_hmkip=bool(payload.get("enrich_hmkip", True)),
        enrich_hmip=bool(payload.get("enrich_hmip", True)),
        enrich_hsip=bool(payload.get("enrich_hsip", True)),
        enrich_macro_mri=bool(payload.get("enrich_macro_mri", True)),
    )


@router.get("/market/relationships/sector/{sector}")
async def mkri_sector(sector: str, limit: int = Query(100, ge=1, le=500)):
    from market_relationship_intelligence.production import for_sector

    return for_sector(sector, limit=limit)


@router.get("/market/relationships/company/{ticker}")
async def mkri_company(ticker: str, limit: int = Query(100, ge=1, le=500)):
    from market_relationship_intelligence.production import for_company

    return for_company(ticker, limit=limit)


@router.get("/market/relationships/{indicator}")
async def mkri_indicator(indicator: str, limit: int = Query(100, ge=1, le=500)):
    from market_relationship_intelligence.production import for_indicator

    return for_indicator(indicator, limit=limit)


@router.get("/admin/market-relationships", response_class=HTMLResponse)
async def admin_mkri():
    from market_relationship_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("confidence_distribution") or {}
    rows = "".join(
        f"<tr><td>{r.get('source')}</td><td>{r.get('target')}</td>"
        f"<td>{r.get('relationship')}</td><td>{r.get('confidence_pct')}</td>"
        f"<td>{r.get('average_lag')}</td><td>{r.get('kind')}</td></tr>"
        for r in (board.get("recently_validated_relationships") or [])
    )
    html = f"""<!doctype html><html><head><title>Market Relationship Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Market Relationship Intelligence — MKRI</h1>
    <p>Evidence-backed only. Versioned graph. Ask never fetches. (Short MKRI avoids Macro MRI.)</p>
    <pre>{board.get('principles')}</pre>
    <p>Total: {board.get('total_relationships')} · Active: {board.get('active_relationships')} ·
    High confidence: {board.get('high_confidence')} · Distribution: {dist}</p>
    <h2>Coverage</h2>
    <pre>{board.get('relationship_coverage')}</pre>
    <h2>Graph health</h2>
    <pre>{board.get('graph_health')}</pre>
    <h2>Freshness</h2>
    <pre>{board.get('relationship_freshness')}</pre>
    <h2>Recently validated</h2>
    <table border="1" cellpadding="6">
    <tr><th>Source</th><th>Target</th><th>Relationship</th><th>Confidence</th><th>Lag</th><th>Kind</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/market/relationships/run</td></tr>'}
    </table>
    <h2>Validation failures</h2>
    <pre>{board.get('validation_failures')}</pre>
    <h2>By kind</h2>
    <pre>{board.get('by_kind')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Historical Market Analogue Intelligence (HMKAI) Sprint 12.4 ---
# Deterministic market analogues. Ask never rebuilds catalogues.
# Programme short HMKAI avoids collision with Historical Macro Analogue Intelligence (HMAI).


@router.get("/hmkai/health")
async def hmkai_health():
    from historical_market_analogue_intelligence.production import health

    return health()


@router.get("/market/analogues")
async def hmkai_analogues(
    market: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    from historical_market_analogue_intelligence.production import analogues

    return analogues(market=market, limit=limit)


@router.get("/market/analogues/search")
async def hmkai_search(
    market: str | None = Query(None),
    question: str | None = Query(None),
    target_period: str | None = Query(None),
    top_k: int = Query(5, ge=1, le=50),
):
    from historical_market_analogue_intelligence.production import search

    return search(market=market, question=question, target_period=target_period, top_k=top_k)


@router.get("/market/analogues/report")
async def hmkai_report(
    market: str = Query("India"),
    top_k: int = Query(5, ge=1, le=50),
):
    from historical_market_analogue_intelligence.production import report

    return report(market=market, top_k=top_k)


@router.get("/market/analogues/dashboard")
async def hmkai_dashboard():
    from historical_market_analogue_intelligence.production import dashboard

    return dashboard()


@router.post("/market/analogues/run")
async def hmkai_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from historical_market_analogue_intelligence.production import run

    return run(
        market=payload.get("market"),
        enrich_hmkip=bool(payload.get("enrich_hmkip", True)),
        enrich_cmktp=bool(payload.get("enrich_cmktp", True)),
        top_k=int(payload.get("top_k") or 10),
    )


@router.get("/market/regime/current")
async def hmkai_regime_current(market: str = Query("India")):
    from historical_market_analogue_intelligence.production import current_regime

    return current_regime(market=market)


@router.get("/market/regime/history")
async def hmkai_regime_history(
    market: str = Query("India"),
    limit: int = Query(50, ge=1, le=200),
):
    from historical_market_analogue_intelligence.production import regime_history

    return regime_history(market=market, limit=limit)


@router.get("/market/analogues/{market}")
async def hmkai_market(market: str, limit: int = Query(20, ge=1, le=200)):
    from historical_market_analogue_intelligence.production import analogues_for_market

    return analogues_for_market(market, limit=limit)


@router.get("/admin/historical-market-analogues", response_class=HTMLResponse)
async def admin_hmkai():
    from historical_market_analogue_intelligence.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{r.get('matched_period')}</td><td>{r.get('matched_label')}</td>"
        f"<td>{r.get('similarity_score')}</td><td>{r.get('confidence')}</td>"
        f"<td>{', '.join(r.get('matching_dimensions') or [])}</td></tr>"
        for r in (board.get("top_analogue_matches") or [])
    )
    html = f"""<!doctype html><html><head><title>Historical Market Analogues</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Historical Market Analogue Intelligence — HMKAI</h1>
    <p>Deterministic similarity. Explainable scores. Ask never fetches. (Short HMKAI avoids Macro HMAI.)</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current market regime</h2>
    <pre>{board.get('current_market_regime')}</pre>
    <h2>Top analogue matches</h2>
    <table border="1" cellpadding="6">
    <tr><th>Period</th><th>Label</th><th>Similarity</th><th>Confidence</th><th>Matching dims</th></tr>
    {rows or '<tr><td colspan=5>Run POST /v1/market/analogues/run</td></tr>'}
    </table>
    <h2>Similarity / confidence</h2>
    <pre>{board.get('similarity_distribution')}</pre>
    <pre>{board.get('confidence_distribution')}</pre>
    <h2>Historical outcomes</h2>
    <pre>{board.get('historical_outcomes_sample')}</pre>
    <h2>Key differences</h2>
    <pre>{board.get('key_differences_sample')}</pre>
    <h2>Freshness / coverage</h2>
    <pre>{board.get('analogue_freshness')}</pre>
    <pre>{board.get('historical_coverage')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Market Forecast Intelligence (MKFI) Sprint 12.5 ---
# Evidence-based Bull/Base/Bear market scenarios. Ask never collects.
# Programme short MKFI avoids collision with Macroeconomic Forecast Intelligence (MFI).


@router.get("/mkfi/health")
async def mkfi_health():
    from market_forecast_intelligence.production import health

    return health()


@router.get("/market/forecast")
async def mkfi_forecast_all(
    market: str | None = Query(None),
    horizon: str = Query("6 Months"),
    limit: int = Query(20, ge=1, le=50),
):
    from market_forecast_intelligence.production import forecast, forecast_all

    if market:
        return forecast(market=market, horizon=horizon)
    return forecast_all(limit=limit)


@router.get("/market/forecast/india")
async def mkfi_forecast_india(horizon: str = Query("6 Months")):
    from market_forecast_intelligence.production import forecast

    return forecast(market="India", horizon=horizon)


@router.get("/market/forecast/report")
async def mkfi_report(
    market: str = Query("India"),
    horizon: str = Query("6 Months"),
    persist: bool = Query(False),
):
    from market_forecast_intelligence.production import report

    return report(market=market, horizon=horizon, persist=persist)


@router.get("/market/forecast/history")
async def mkfi_history(
    market: str | None = Query(None),
    horizon: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from market_forecast_intelligence.production import history

    return history(market=market, horizon=horizon, limit=limit)


@router.get("/market/forecast/dashboard")
async def mkfi_dashboard():
    from market_forecast_intelligence.production import dashboard

    return dashboard()


@router.post("/market/forecast/run")
async def mkfi_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from market_forecast_intelligence.production import run

    markets = payload.get("markets")
    if isinstance(markets, str):
        markets = [m.strip() for m in markets.split(",") if m.strip()]
    horizons = payload.get("horizons")
    if isinstance(horizons, str):
        horizons = [h.strip() for h in horizons.split(",") if h.strip()]
    return run(
        market=payload.get("market"),
        horizon=payload.get("horizon"),
        country=payload.get("country"),
        markets=markets if isinstance(markets, list) else None,
        horizons=horizons if isinstance(horizons, list) else None,
    )


@router.get("/market/scenarios")
async def mkfi_scenarios(
    market: str = Query("India"),
    horizon: str = Query("6 Months"),
):
    from market_forecast_intelligence.production import scenarios

    return scenarios(market=market, horizon=horizon)


@router.get("/market/probability")
async def mkfi_probability(
    market: str = Query("India"),
    horizon: str = Query("6 Months"),
):
    from market_forecast_intelligence.production import probability

    return probability(market=market, horizon=horizon)


@router.get("/market/catalysts")
async def mkfi_catalysts(
    market: str = Query("India"),
    horizon: str = Query("6 Months"),
):
    from market_forecast_intelligence.production import catalysts

    return catalysts(market=market, horizon=horizon)


@router.get("/market/risks")
async def mkfi_risks(
    market: str = Query("India"),
    horizon: str = Query("6 Months"),
):
    from market_forecast_intelligence.production import risks

    return risks(market=market, horizon=horizon)


@router.get("/market/forecast/{market}")
async def mkfi_forecast_market(
    market: str,
    horizon: str = Query("6 Months"),
):
    from market_forecast_intelligence.production import forecast

    return forecast(market=market, horizon=horizon)


@router.get("/admin/market-forecast", response_class=HTMLResponse)
async def admin_mkfi():
    from market_forecast_intelligence.production import dashboard

    board = dashboard()
    dist = board.get("probability_distribution") or {}
    rows = "".join(
        f"<tr><td>{s.get('scenario')}</td><td>{s.get('probability_pct')}</td>"
        f"<td>{s.get('confidence_pct')}</td><td>{s.get('market_direction')}</td>"
        f"<td>{s.get('breadth')}</td><td>{s.get('liquidity')}</td></tr>"
        for s in (board.get("bull_base_bear_scenarios") or [])
    )
    html = f"""<!doctype html><html><head><title>Market Forecast Intelligence</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Market Forecast Intelligence — MKFI</h1>
    <p>Bull/Base/Bear market pathways. AGI-owned knowledge only. Ask never fetches. (Short MKFI avoids Macro MFI.)</p>
    <pre>{board.get('principles')}</pre>
    <h2>Current market outlook</h2>
    <pre>{board.get('current_market_outlook')}</pre>
    <p>Probability: {dist} · Confidence: {board.get('confidence')}</p>
    <h2>Bull / Base / Bear</h2>
    <table border="1" cellpadding="6">
    <tr><th>Scenario</th><th>Probability</th><th>Confidence</th><th>Direction</th><th>Breadth</th><th>Liquidity</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/market/forecast/run</td></tr>'}
    </table>
    <h2>Forecast horizons</h2>
    <pre>{board.get('forecast_horizons')}</pre>
    <h2>Key catalysts</h2>
    <pre>{board.get('key_catalysts')}</pre>
    <h2>Major risks / invalidators</h2>
    <pre>{board.get('major_risks')}</pre>
    <pre>{board.get('invalidation_alerts')}</pre>
    <h2>Sector leadership forecast</h2>
    <pre>{board.get('sector_leadership_forecast')}</pre>
    <h2>Macro / sector inheritance</h2>
    <pre>{board.get('macro_inheritance')}</pre>
    <pre>{board.get('sector_inheritance')}</pre>
    <h2>Accuracy tracking</h2>
    <pre>{board.get('accuracy_tracking')}</pre>
    </body></html>"""
    return HTMLResponse(html)


@router.post("/sector/run")
async def cskp_run(payload: dict[str, Any] = Body(default={})):
    """Ops / event-driven only — never called by Ask."""
    from continuous_sector_knowledge.production import run

    sectors = payload.get("sectors")
    if isinstance(sectors, str):
        sectors = [s.strip() for s in sectors.split(",") if s.strip()]
    return run(
        sectors=sectors if isinstance(sectors, list) else None,
        trigger=payload.get("trigger"),
    )


@router.get("/sector")
async def cskp_sectors(limit: int = Query(100, ge=1, le=500)):
    from continuous_sector_knowledge.production import sectors as list_sectors

    return list_sectors(limit=limit)


@router.get("/sector/{sector}")
async def cskp_sector(sector: str):
    from continuous_sector_knowledge.production import sector as get_sector

    return get_sector(sector)


@router.get("/admin/sector-operations", response_class=HTMLResponse)
async def admin_cskp():
    from continuous_sector_knowledge.production import dashboard

    board = dashboard()
    health = board.get("sector_health") or {}
    rows = "".join(
        f"<tr><td>{s.get('sector')}</td><td>{s.get('outlook')}</td>"
        f"<td>{s.get('trigger')}</td><td>{s.get('version')}</td></tr>"
        for s in (board.get("latest_sector_events") or [])
    )
    html = f"""<!doctype html><html><head><title>Sector Operations</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Sector Operations — CSKP</h1>
    <p>Event-driven derived sector knowledge. Ask never constructs.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Sector health</h2>
    <pre>{health}</pre>
    <h2>Coverage</h2>
    <pre>{board.get('knowledge_coverage')}</pre>
    <h2>Knowledge freshness</h2>
    <pre>{board.get('knowledge_freshness')}</pre>
    <h2>Latest sector events</h2>
    <table border="1" cellpadding="6">
    <tr><th>Sector</th><th>Outlook</th><th>Trigger</th><th>Version</th></tr>
    {rows or '<tr><td colspan=4>Run POST /v1/sector/run</td></tr>'}
    </table>
    <h2>Learning events</h2>
    <pre>{board.get('learning_events')}</pre>
    <h2>Company coverage by sector</h2>
    <pre>{board.get('company_coverage_by_sector')}</pre>
    <h2>Material updates</h2>
    <pre>{board.get('material_updates')}</pre>
    <h2>Research coverage</h2>
    <pre>{board.get('research_coverage')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# --- Forecast Provider Integration (FPI) — India-first Knowledge Platform path ---
# Forecast never calls Groww/Yahoo/NSE/BSE directly; stale market snapshot refresh only.


@router.get("/forecast/providers/health")
async def fpi_provider_health():
    from forecast_provider_integration.production import provider_health

    return provider_health()


@router.get("/forecast/providers/dashboard")
async def fpi_dashboard():
    from forecast_provider_integration.production import dashboard

    return dashboard()


@router.get("/fpi/health")
async def fpi_health():
    from forecast_provider_integration.production import health

    return health()


@router.post("/forecast/providers/publish/{entity}")
async def fpi_publish_company(entity: str, payload: dict[str, Any] = Body(default={})):
    from forecast_provider_integration.production import publish_company

    return publish_company(entity, catalog_tip=payload.get("catalog_tip"))


@router.post("/forecast/providers/snapshot/{entity}")
async def fpi_refresh_snapshot(
    entity: str,
    force: bool = Query(False),
    scope: str = Query("company"),
):
    from forecast_provider_integration.production import refresh_snapshot

    return refresh_snapshot(entity, scope=scope, force=force)


@router.get("/forecast/providers/company/{entity}")
async def fpi_company_knowledge(entity: str):
    from forecast_provider_integration.production import company_knowledge

    return company_knowledge(entity)


@router.get("/admin/forecast-providers", response_class=HTMLResponse)
async def admin_fpi():
    from forecast_provider_integration.production import dashboard

    board = dashboard()
    providers = board.get("providers") or []
    rows = "".join(
        f"<tr><td>{p.get('provider')}</td><td>{p.get('status')}</td>"
        f"<td>{p.get('role')}</td><td>{p.get('connection')}</td>"
        f"<td>{p.get('detail')}</td></tr>"
        for p in providers
    )
    snaps = board.get("snapshot_freshness") or {}
    fails = board.get("provider_failover_events") or []
    fail_rows = "".join(
        f"<tr><td>{f.get('from_provider')}→{f.get('to_provider')}</td>"
        f"<td>{f.get('reason')}</td><td>{f.get('entity')}</td></tr>"
        for f in fails[:15]
    )
    html = f"""<!doctype html><html><head><title>Forecast Provider Health</title></head>
    <body style="font-family:system-ui;max-width:980px;margin:2rem auto">
    <h1>Forecast Provider Health</h1>
    <p>India-first: Groww live · Yahoo research · NSE/BSE disclosures · Company IR.</p>
    <p>Forecast Intelligence never reasons over raw APIs.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Providers</h2>
    <table border="1" cellpadding="6">
    <tr><th>Provider</th><th>Status</th><th>Role</th><th>Connection</th><th>Detail</th></tr>
    {rows or '<tr><td colspan=5>No providers</td></tr>'}
    </table>
    <h2>Snapshot freshness</h2>
    <pre>{snaps}</pre>
    <h2>Failover events</h2>
    <table border="1" cellpadding="6">
    <tr><th>Path</th><th>Reason</th><th>Entity</th></tr>
    {fail_rows or '<tr><td colspan=3>None</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Forecast Validation & Learning (FVL) Sprint 9.5 ---
# Closes Phase 9: register → validate vs actuals → score → learn (never rewrite history).


@router.get("/fvl/health")
async def fvl_health():
    from forecast_validation_learning.production import health

    return health()


@router.get("/forecast/validation/dashboard")
async def fvl_dashboard():
    from forecast_validation_learning.production import dashboard

    return dashboard()


@router.get("/forecast/validation/{forecast_id}")
async def fvl_get_validation(forecast_id: str):
    from forecast_validation_learning.production import get_validation

    try:
        return get_validation(forecast_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/forecast/validation/{forecast_id}")
async def fvl_post_validation(forecast_id: str, payload: dict[str, Any] = Body(default={})):
    from forecast_validation_learning.production import validate

    try:
        return validate(
            forecast_id,
            actual_outcome=payload.get("actual_outcome"),
            generate_learning=bool(payload.get("generate_learning", True)),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/forecast/register")
async def fvl_register(payload: dict[str, Any] = Body(default={})):
    from forecast_validation_learning.production import register

    try:
        return register(
            entity=payload.get("entity") or payload.get("ticker"),
            scope=str(payload.get("scope") or "company"),
            question=payload.get("question"),
            assessment=payload.get("assessment"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/forecast/validate")
async def fvl_validate_entity(payload: dict[str, Any] = Body(default={})):
    from forecast_validation_learning.production import validate_entity

    entity = payload.get("entity") or payload.get("ticker")
    if not entity:
        raise HTTPException(status_code=400, detail="entity required")
    try:
        return validate_entity(
            str(entity),
            scope=str(payload.get("scope") or "company"),
            question=payload.get("question"),
            actual_outcome=payload.get("actual_outcome"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/forecast/learning")
async def fvl_learning(limit: int = Query(50, ge=1, le=200), category: str | None = None):
    from forecast_validation_learning.production import learning

    return learning(limit=limit, category=category)


@router.get("/forecast/performance")
async def fvl_performance(scope: str | None = None):
    from forecast_validation_learning.production import performance

    return performance(scope=scope)


@router.get("/forecast/calibration")
async def fvl_calibration():
    from forecast_validation_learning.production import calibration

    return calibration()


@router.get("/forecast/history")
async def fvl_history(
    entity: str | None = None,
    scope: str = Query("company"),
    limit: int = Query(50, ge=1, le=200),
):
    from forecast_validation_learning.production import history

    return history(entity=entity, scope=scope, limit=limit)


@router.get("/admin/forecast-validation", response_class=HTMLResponse)
async def admin_fvl():
    from forecast_validation_learning.production import dashboard

    board = dashboard()
    score = board.get("forecast_score") or {}
    biases = board.get("bias_indicators") or []
    learnings = board.get("recent_learnings") or []
    rows = "".join(
        f"<tr><td>{v.get('entity')}</td><td>{v.get('validation_status')}</td>"
        f"<td>{(v.get('score') or {}).get('overall')}</td>"
        f"<td>{(v.get('difference') or {}).get('summary')}</td></tr>"
        for v in (board.get("recent_validations") or [])
    )
    learn_rows = "".join(
        f"<tr><td>{l.get('topic')}</td><td>{l.get('category')}</td>"
        f"<td>{l.get('future_guidance')}</td></tr>"
        for l in learnings
    )
    bias_rows = "".join(
        f"<tr><td>{b.get('label')}</td><td>{b.get('severity')}</td>"
        f"<td>{b.get('evidence_count')}</td></tr>"
        for b in biases
    )
    html = f"""<!doctype html><html><head><title>FVL Mission Control</title></head>
    <body style="font-family:system-ui;max-width:980px;margin:2rem auto">
    <h1>Forecast Validation &amp; Learning</h1>
    <p>Were we right? History is never rewritten. Phase 9 closed-loop forecasting.</p>
    <pre>{board.get('principles')}</pre>
    <p>Active: {board.get('active_forecasts')} · Validated: {board.get('validated_forecasts')} ·
    Accuracy: {board.get('validation_accuracy')}% · Learnings: {board.get('learning_generated')}</p>
    <h2>Forecast score</h2>
    <pre>{score}</pre>
    <h2>Recent validations</h2>
    <table border="1" cellpadding="6">
    <tr><th>Entity</th><th>Status</th><th>Score</th><th>Difference</th></tr>
    {rows or '<tr><td colspan=4>No validations yet</td></tr>'}
    </table>
    <h2>Bias indicators</h2>
    <table border="1" cellpadding="6">
    <tr><th>Bias</th><th>Severity</th><th>Evidence</th></tr>
    {bias_rows or '<tr><td colspan=3>No recurring biases yet</td></tr>'}
    </table>
    <h2>Learning generated</h2>
    <table border="1" cellpadding="6">
    <tr><th>Topic</th><th>Category</th><th>Future guidance</th></tr>
    {learn_rows or '<tr><td colspan=3>No learnings yet</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Legacy FIE scenario surface (pre-ISI) — prefer /scenarios/* for Investment Office ---


@router.get("/forecast/scenarios/{ticker}")
async def forecast_intelligence_scenarios(ticker: str):
    from forecast_intelligence.production import scenarios

    out = scenarios(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="company_forecast_not_found")
    return out


@router.get("/forecast/catalysts/{ticker}")
async def forecast_intelligence_catalysts(ticker: str):
    from forecast_intelligence.production import catalysts

    out = await run_in_threadpool(catalysts, ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="company_forecast_not_found")
    return out


@router.post("/forecast/analyse")
async def forecast_intelligence_analyse(payload: dict[str, Any] = Body(default={})):
    from forecast_intelligence.production import analyse

    return analyse(
        ticker=payload.get("ticker") or payload.get("company"),
        question=payload.get("question") or payload.get("query"),
    )


@router.get("/forecast/quality-gates")
async def forecast_intelligence_quality_gates():
    from forecast_intelligence.production import quality_gates

    return quality_gates()


@router.get("/admin/forecast-intelligence", response_class=HTMLResponse)
async def admin_forecast_intelligence():
    from forecast_intelligence.production import admin_page

    return HTMLResponse(admin_page())


@router.get("/admin/institutional-forecast-intelligence", response_class=HTMLResponse)
async def admin_ifi():
    from institutional_forecast_intelligence.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{r.get('scope')}</td><td>{r.get('entity')}</td>"
        f"<td>{r.get('completeness_score')}</td><td>{r.get('latency_ms')}</td></tr>"
        for r in (board.get("recent") or [])
    )
    html = f"""<!doctype html><html><head><title>IFI Mission Control</title></head>
    <body style="font-family:system-ui;max-width:960px;margin:2rem auto">
    <h1>Institutional Forecast Intelligence</h1>
    <p>Preparation only — no Bull/Base/Bear, no price prediction.</p>
    <pre>{board.get('principles')}</pre>
    <h2>Recent bundle generations</h2>
    <table border="1" cellpadding="6"><tr><th>Scope</th><th>Entity</th><th>Completeness</th><th>Latency ms</th></tr>
    {rows or '<tr><td colspan=4>No generations yet</td></tr>'}
    </table>
    </body></html>"""
    return HTMLResponse(html)


# --- Institutional Knowledge Graph V1 (what is connected?) ---


@router.get("/knowledge-graph/health")
async def knowledge_graph_health():
    from knowledge_graph.production import health

    return health()


@router.get("/knowledge-graph/dashboard")
async def knowledge_graph_dashboard():
    from knowledge_graph.production import dashboard

    return dashboard()


@router.get("/knowledge-graph/entity/{entity_id}")
async def knowledge_graph_entity(entity_id: str):
    from knowledge_graph.production import entity

    out = entity(entity_id)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="entity_not_found")
    return out


@router.get("/knowledge-graph/company/{ticker}")
async def knowledge_graph_company(ticker: str):
    from knowledge_graph.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="company_not_in_knowledge_graph")
    return out


@router.get("/knowledge-graph/relationships/{entity_id}")
async def knowledge_graph_relationships(entity_id: str):
    from knowledge_graph.production import relationships

    out = relationships(entity_id)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="entity_not_found")
    return out


@router.post("/knowledge-graph/query")
async def knowledge_graph_query(payload: dict[str, Any] = Body(default={})):
    from knowledge_graph.production import query

    return query(payload)


@router.get("/knowledge-graph/path")
async def knowledge_graph_path(source: str, target: str):
    from knowledge_graph.production import path

    return path(source, target)


@router.get("/knowledge-graph/quality-gates")
async def knowledge_graph_quality_gates():
    from knowledge_graph.production import quality_gates

    return quality_gates()


@router.get("/admin/knowledge-graph", response_class=HTMLResponse)
async def admin_knowledge_graph():
    from knowledge_graph.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Learning & Memory Engine V1 (what have we learned?) ---


@router.get("/ilm/health")
async def ilm_health():
    from institutional_memory.production import health

    return health()


@router.get("/ilm/dashboard")
async def ilm_dashboard():
    from institutional_memory.production import dashboard

    return dashboard()


@router.get("/ilm/company/{ticker}")
async def ilm_company(ticker: str):
    from institutional_memory.production import company

    out = company(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="company_memory_not_found")
    return out


@router.get("/ilm/thesis/{ticker}")
async def ilm_thesis(ticker: str):
    from institutional_memory.production import thesis

    out = thesis(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="thesis_memory_not_found")
    return out


@router.get("/ilm/committee/{ticker}")
async def ilm_committee(ticker: str):
    from institutional_memory.production import committee

    out = committee(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="committee_memory_not_found")
    return out


@router.get("/ilm/forecast/{ticker}")
async def ilm_forecast(ticker: str):
    from institutional_memory.production import forecast

    out = forecast(ticker)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="forecast_memory_not_found")
    return out


@router.get("/ilm/portfolio/{portfolio_id}")
async def ilm_portfolio(portfolio_id: str):
    from institutional_memory.production import portfolio

    out = portfolio(portfolio_id)
    if out.get("enabled") and not out.get("found"):
        raise HTTPException(status_code=404, detail="portfolio_memory_not_found")
    return out


@router.post("/ilm/learning/update")
async def ilm_learning_update(payload: dict[str, Any] = Body(default={})):
    from institutional_memory.production import learning_update

    return learning_update(payload)


@router.get("/ilm/quality-gates")
async def ilm_quality_gates():
    from institutional_memory.production import quality_gates

    return quality_gates()


@router.get("/admin/institutional-memory", response_class=HTMLResponse)
async def admin_institutional_memory():
    from institutional_memory.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Simulation & Strategy Lab V1 (what happens if we decide?) ---


@router.get("/simulation/health")
async def ssl_health():
    from simulation_lab.production import health

    return health()


@router.get("/simulation/dashboard")
async def ssl_dashboard():
    from simulation_lab.production import dashboard

    return dashboard()


@router.get("/simulation/scenarios")
async def ssl_scenarios():
    from simulation_lab.production import scenarios

    return scenarios()


@router.post("/simulation/run")
async def ssl_run(payload: dict[str, Any] = Body(default={})):
    from simulation_lab.production import run

    return run(payload or {})


@router.post("/simulation/portfolio")
async def ssl_portfolio(payload: dict[str, Any] = Body(default={})):
    from simulation_lab.production import portfolio

    return portfolio(payload or {})


@router.get("/simulation/history")
async def ssl_history(limit: int = 50):
    from simulation_lab.production import history

    return history(limit=limit)


@router.get("/simulation/quality-gates")
async def ssl_quality_gates():
    from simulation_lab.production import quality_gates

    return quality_gates()


@router.get("/admin/simulation-lab", response_class=HTMLResponse)
async def admin_simulation_lab():
    from simulation_lab.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Decision Engine V2 (final architectural component) ---


@router.get("/decision-engine-v2/health")
async def idev2_health():
    from decision_engine_v2.production import health

    return health()


@router.get("/decision-engine-v2/dashboard")
async def idev2_dashboard():
    from decision_engine_v2.production import dashboard

    return dashboard()


@router.get("/decision-engine-v2/company/{ticker}")
async def idev2_company(ticker: str):
    from decision_engine_v2.production import company

    out = company(ticker)
    if out.get("enabled") and out.get("found") is False:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="company_not_found")
    return out


@router.post("/decision-engine-v2/analyse")
async def idev2_analyse(payload: dict[str, Any] = Body(default={})):
    from decision_engine_v2.production import analyse

    return analyse(payload or {})


@router.get("/decision-engine-v2/audit/{audit_id}")
async def idev2_audit(audit_id: str):
    from decision_engine_v2.production import audit

    return audit(audit_id)


@router.get("/decision-engine-v2/monitoring/{ticker}")
async def idev2_monitoring(ticker: str):
    from decision_engine_v2.production import monitoring

    return monitoring(ticker)


@router.get("/decision-engine-v2/quality-gates")
async def idev2_quality_gates():
    from decision_engine_v2.production import quality_gates

    return quality_gates()


@router.get("/decision-engine-v2/freeze-review")
async def idev2_freeze_review():
    from decision_engine_v2.production import freeze_review

    return freeze_review()


@router.get("/admin/decision-engine-v2", response_class=HTMLResponse)
async def admin_decision_engine_v2():
    from decision_engine_v2.production import admin_page

    return HTMLResponse(admin_page())


# --- Institutional Decision Quality (Sprint 7 — observability only; never reasons) ---


@router.get("/decision-quality/health")
async def decision_quality_health():
    from decision_quality.production import health

    return health()


@router.get("/decision-quality/dashboard")
async def decision_quality_dashboard():
    from decision_quality.production import dashboard

    return dashboard()


@router.post("/decision-quality/run")
async def decision_quality_run():
    from decision_quality.production import run_pipeline

    return run_pipeline()


@router.get("/decision-quality/quality-gates")
async def decision_quality_gates():
    from decision_quality.production import quality_gates

    return quality_gates()


@router.get("/decision-quality/decisions")
async def decision_quality_list():
    from decision_quality.production import list_decisions

    return list_decisions()


@router.get("/decision-quality/decisions/{decision_id}")
async def decision_quality_decision(decision_id: str):
    from decision_quality.production import get_decision

    return get_decision(decision_id)


@router.get("/decision-quality/replay/{decision_id}")
async def decision_quality_replay(decision_id: str, as_of: str | None = None):
    from decision_quality.production import replay

    return replay(decision_id, as_of=as_of)


@router.get("/decision-quality/scorecards/framework")
async def decision_quality_framework_scorecards():
    from decision_quality.production import framework_scorecards

    return framework_scorecards()


@router.get("/decision-quality/scorecards/sector")
async def decision_quality_sector_scorecards():
    from decision_quality.production import sector_scorecards

    return sector_scorecards()


@router.get("/decision-quality/scorecards/macro")
async def decision_quality_macro_scorecards():
    from decision_quality.production import macro_scorecards

    return macro_scorecards()


@router.get("/decision-quality/scorecards/portfolio")
async def decision_quality_portfolio_scorecard():
    from decision_quality.production import portfolio_scorecard

    return portfolio_scorecard()


@router.get("/decision-quality/calibration")
async def decision_quality_calibration():
    from decision_quality.production import calibration

    return calibration()


@router.get("/decision-quality/hall")
async def decision_quality_hall(category: str | None = None, which: str | None = None):
    from decision_quality.production import hall

    return hall(category=category, which=which)


@router.get("/decision-quality/missing-outcome")
async def decision_quality_missing_outcome(decision_id: str = "dec_tcs_open_no_outcome"):
    from decision_quality.production import outcome_missing

    return outcome_missing(decision_id)


# --- RQ1 Research Ontology (Sprint 1 — classify-only constitution; not a top-level layer) ---


@router.get("/research-ontology/health")
async def research_ontology_health():
    from research_ontology.production import health

    return health()


@router.get("/research-ontology/dashboard")
async def research_ontology_dashboard():
    from research_ontology.production import dashboard

    return dashboard()


@router.get("/research-ontology/constitution")
async def research_ontology_constitution():
    from research_ontology.production import constitution

    return constitution()


@router.get("/research-ontology/quality-gates")
async def research_ontology_quality_gates():
    from research_ontology.production import quality_gates

    return quality_gates()


@router.post("/research-ontology/classify")
async def research_ontology_classify(payload: dict[str, Any] = Body(default={})):
    from research_ontology.production import classify

    return classify(payload or {})


# --- RQ1 Entity Resolution Engine (Sprint 2 — identity soft-wire; not a top-level layer) ---


@router.get("/entity-resolution/health")
async def entity_resolution_health():
    from entity_resolution.production import health

    return health()


@router.get("/entity-resolution/dashboard")
async def entity_resolution_dashboard():
    from entity_resolution.production import dashboard

    return dashboard()


@router.get("/entity-resolution/constitution")
async def entity_resolution_constitution():
    from entity_resolution.production import constitution

    return constitution()


@router.get("/entity-resolution/quality-gates")
async def entity_resolution_quality_gates():
    from entity_resolution.production import quality_gates

    return quality_gates()


@router.post("/entity-resolution/resolve")
async def entity_resolution_resolve(payload: dict[str, Any] = Body(default={})):
    from entity_resolution.production import resolve

    return resolve(payload or {})


@router.post("/entity-resolution/diagnostics")
async def entity_resolution_diagnostics(payload: dict[str, Any] = Body(default={})):
    from entity_resolution.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Research Objective Engine (Sprint 3 — objective planning soft-wire; not a top-level layer) ---


@router.get("/research-objective/health")
async def research_objective_health():
    from research_objective.production import health

    return health()


@router.get("/research-objective/dashboard")
async def research_objective_dashboard():
    from research_objective.production import dashboard

    return dashboard()


@router.get("/research-objective/constitution")
async def research_objective_constitution():
    from research_objective.production import constitution

    return constitution()


@router.get("/research-objective/quality-gates")
async def research_objective_quality_gates():
    from research_objective.production import quality_gates

    return quality_gates()


@router.post("/research-objective/plan")
async def research_objective_plan(payload: dict[str, Any] = Body(default={})):
    from research_objective.production import plan

    return plan(payload or {})


@router.post("/research-objective/diagnostics")
async def research_objective_diagnostics(payload: dict[str, Any] = Body(default={})):
    from research_objective.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Context Intelligence Engine (Sprint 4 — context enrichment soft-wire; not a top-level layer) ---


@router.get("/context-intelligence/health")
async def context_intelligence_health():
    from context_intelligence.production import health

    return health()


@router.get("/context-intelligence/dashboard")
async def context_intelligence_dashboard():
    from context_intelligence.production import dashboard

    return dashboard()


@router.get("/context-intelligence/constitution")
async def context_intelligence_constitution():
    from context_intelligence.production import constitution

    return constitution()


@router.get("/context-intelligence/quality-gates")
async def context_intelligence_quality_gates():
    from context_intelligence.production import quality_gates

    return quality_gates()


@router.post("/context-intelligence/enrich")
async def context_intelligence_enrich(payload: dict[str, Any] = Body(default={})):
    from context_intelligence.production import enrich

    return enrich(payload or {})


@router.post("/context-intelligence/diagnostics")
async def context_intelligence_diagnostics(payload: dict[str, Any] = Body(default={})):
    from context_intelligence.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Institutional Analyst Router (Sprint 5 — participation soft-wire; not a top-level layer) ---


@router.get("/analyst-router/health")
async def analyst_router_health():
    from analyst_router.production import health

    return health()


@router.get("/analyst-router/dashboard")
async def analyst_router_dashboard():
    from analyst_router.production import dashboard

    return dashboard()


@router.get("/analyst-router/constitution")
async def analyst_router_constitution():
    from analyst_router.production import constitution

    return constitution()


@router.get("/analyst-router/quality-gates")
async def analyst_router_quality_gates():
    from analyst_router.production import quality_gates

    return quality_gates()


@router.post("/analyst-router/route")
async def analyst_router_route(payload: dict[str, Any] = Body(default={})):
    from analyst_router.production import route

    return route(payload or {})


@router.post("/analyst-router/diagnostics")
async def analyst_router_diagnostics(payload: dict[str, Any] = Body(default={})):
    from analyst_router.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Intelligence Layer Router (Sprint 6 — execution planner soft-wire; not a top-level layer) ---


@router.get("/layer-router/health")
async def layer_router_health():
    from layer_router.production import health

    return health()


@router.get("/layer-router/dashboard")
async def layer_router_dashboard():
    from layer_router.production import dashboard

    return dashboard()


@router.get("/layer-router/constitution")
async def layer_router_constitution():
    from layer_router.production import constitution

    return constitution()


@router.get("/layer-router/quality-gates")
async def layer_router_quality_gates():
    from layer_router.production import quality_gates

    return quality_gates()


@router.post("/layer-router/plan")
async def layer_router_plan(payload: dict[str, Any] = Body(default={})):
    from layer_router.production import plan

    return plan(payload or {})


@router.post("/layer-router/diagnostics")
async def layer_router_diagnostics(payload: dict[str, Any] = Body(default={})):
    from layer_router.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Institutional Acquisition & API Planning Engine (Sprint 7 — acquisition planner soft-wire; not a top-level layer) ---


@router.get("/acquisition-planner/health")
async def acquisition_planner_health():
    from acquisition_planner.production import health

    return health()


@router.get("/acquisition-planner/dashboard")
async def acquisition_planner_dashboard():
    from acquisition_planner.production import dashboard

    return dashboard()


@router.get("/acquisition-planner/constitution")
async def acquisition_planner_constitution():
    from acquisition_planner.production import constitution

    return constitution()


@router.get("/acquisition-planner/quality-gates")
async def acquisition_planner_quality_gates():
    from acquisition_planner.production import quality_gates

    return quality_gates()


@router.post("/acquisition-planner/plan")
async def acquisition_planner_plan(payload: dict[str, Any] = Body(default={})):
    from acquisition_planner.production import plan

    return plan(payload or {})


@router.post("/acquisition-planner/enrich")
async def acquisition_planner_enrich(payload: dict[str, Any] = Body(default={})):
    from acquisition_planner.production import enrich

    return enrich(payload or {})


@router.post("/acquisition-planner/diagnostics")
async def acquisition_planner_diagnostics(payload: dict[str, Any] = Body(default={})):
    from acquisition_planner.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Dynamic Research Blueprint Engine (Sprint 8 — publication plan soft-wire; not a top-level layer) ---


@router.get("/research-blueprint/health")
async def research_blueprint_health():
    from research_blueprint.production import health

    return health()


@router.get("/research-blueprint/dashboard")
async def research_blueprint_dashboard():
    from research_blueprint.production import dashboard

    return dashboard()


@router.get("/research-blueprint/constitution")
async def research_blueprint_constitution():
    from research_blueprint.production import constitution

    return constitution()


@router.get("/research-blueprint/quality-gates")
async def research_blueprint_quality_gates():
    from research_blueprint.production import quality_gates

    return quality_gates()


@router.post("/research-blueprint/plan")
async def research_blueprint_plan(payload: dict[str, Any] = Body(default={})):
    from research_blueprint.production import plan

    return plan(payload or {})


@router.post("/research-blueprint/enrich")
async def research_blueprint_enrich(payload: dict[str, Any] = Body(default={})):
    from research_blueprint.production import enrich

    return enrich(payload or {})


@router.post("/research-blueprint/diagnostics")
async def research_blueprint_diagnostics(payload: dict[str, Any] = Body(default={})):
    from research_blueprint.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Institutional Validation & Clarification Engine (Sprint 9 — readiness gate soft-wire; not a top-level layer) ---


@router.get("/validation-engine/health")
async def validation_engine_health():
    from validation_engine.production import health

    return health()


@router.get("/validation-engine/dashboard")
async def validation_engine_dashboard():
    from validation_engine.production import dashboard

    return dashboard()


@router.get("/validation-engine/constitution")
async def validation_engine_constitution():
    from validation_engine.production import constitution

    return constitution()


@router.get("/validation-engine/quality-gates")
async def validation_engine_quality_gates():
    from validation_engine.production import quality_gates

    return quality_gates()


@router.post("/validation-engine/validate")
async def validation_engine_validate(payload: dict[str, Any] = Body(default={})):
    from validation_engine.production import validate

    return validate(payload or {})


@router.post("/validation-engine/plan")
async def validation_engine_plan(payload: dict[str, Any] = Body(default={})):
    from validation_engine.production import plan

    return plan(payload or {})


@router.post("/validation-engine/enrich")
async def validation_engine_enrich(payload: dict[str, Any] = Body(default={})):
    from validation_engine.production import enrich

    return enrich(payload or {})


@router.post("/validation-engine/diagnostics")
async def validation_engine_diagnostics(payload: dict[str, Any] = Body(default={})):
    from validation_engine.production import diagnostics

    return diagnostics(payload or {})


# --- RQ1 Institutional Research Execution Package (Sprint 10 — final RQ1 planning package; not a top-level layer) ---


@router.get("/research-execution/health")
async def research_execution_health():
    from research_execution.production import health

    return health()


@router.get("/research-execution/dashboard")
async def research_execution_dashboard():
    from research_execution.production import dashboard

    return dashboard()


@router.get("/research-execution/constitution")
async def research_execution_constitution():
    from research_execution.production import constitution

    return constitution()


@router.get("/research-execution/quality-gates")
async def research_execution_quality_gates():
    from research_execution.production import quality_gates

    return quality_gates()


@router.post("/research-execution/build")
async def research_execution_build(payload: dict[str, Any] = Body(default={})):
    from research_execution.production import build

    return build(payload or {})


@router.post("/research-execution/plan")
async def research_execution_plan(payload: dict[str, Any] = Body(default={})):
    from research_execution.production import plan

    return plan(payload or {})


@router.post("/research-execution/enrich")
async def research_execution_enrich(payload: dict[str, Any] = Body(default={})):
    from research_execution.production import enrich

    return enrich(payload or {})


@router.post("/research-execution/export")
async def research_execution_export(payload: dict[str, Any] = Body(default={})):
    from research_execution.production import export

    return export(payload or {})


@router.post("/research-execution/diagnostics")
async def research_execution_diagnostics(payload: dict[str, Any] = Body(default={})):
    from research_execution.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Hypothesis Generation Engine (Sprint 1 — soft-wire AFTER IREP; not a top-level layer) ---


@router.get("/hypothesis-engine/health")
async def hypothesis_engine_health():
    from hypothesis_engine.production import health

    return health()


@router.get("/hypothesis-engine/dashboard")
async def hypothesis_engine_dashboard():
    from hypothesis_engine.production import dashboard

    return dashboard()


@router.get("/hypothesis-engine/constitution")
async def hypothesis_engine_constitution():
    from hypothesis_engine.production import constitution

    return constitution()


@router.get("/hypothesis-engine/quality-gates")
async def hypothesis_engine_quality_gates():
    from hypothesis_engine.production import quality_gates

    return quality_gates()


@router.post("/hypothesis-engine/plan")
async def hypothesis_engine_plan(payload: dict[str, Any] = Body(default={})):
    from hypothesis_engine.production import plan

    return plan(payload or {})


@router.post("/hypothesis-engine/diagnostics")
async def hypothesis_engine_diagnostics(payload: dict[str, Any] = Body(default={})):
    from hypothesis_engine.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Research Question Engine (Sprint 2 — soft-wire AFTER IHG; not a top-level layer) ---


@router.get("/research-questions/health")
async def research_questions_health():
    from research_questions.production import health

    return health()


@router.get("/research-questions/dashboard")
async def research_questions_dashboard():
    from research_questions.production import dashboard

    return dashboard()


@router.get("/research-questions/constitution")
async def research_questions_constitution():
    from research_questions.production import constitution

    return constitution()


@router.get("/research-questions/quality-gates")
async def research_questions_quality_gates():
    from research_questions.production import quality_gates

    return quality_gates()


@router.post("/research-questions/plan")
async def research_questions_plan(payload: dict[str, Any] = Body(default={})):
    from research_questions.production import plan

    return plan(payload or {})


@router.post("/research-questions/diagnostics")
async def research_questions_diagnostics(payload: dict[str, Any] = Body(default={})):
    from research_questions.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Hypothesis Testing Engine (Sprint 4 — soft-wire AFTER evidence planning; not a top-level layer) ---


@router.get("/hypothesis-testing/health")
async def hypothesis_testing_health():
    from hypothesis_testing.production import health

    return health()


@router.get("/hypothesis-testing/dashboard")
async def hypothesis_testing_dashboard():
    from hypothesis_testing.production import dashboard

    return dashboard()


@router.get("/hypothesis-testing/constitution")
async def hypothesis_testing_constitution():
    from hypothesis_testing.production import constitution

    return constitution()


@router.get("/hypothesis-testing/quality-gates")
async def hypothesis_testing_quality_gates():
    from hypothesis_testing.production import quality_gates

    return quality_gates()


@router.post("/hypothesis-testing/plan")
async def hypothesis_testing_plan(payload: dict[str, Any] = Body(default={})):
    from hypothesis_testing.production import plan

    return plan(payload or {})


@router.post("/hypothesis-testing/diagnostics")
async def hypothesis_testing_diagnostics(payload: dict[str, Any] = Body(default={})):
    from hypothesis_testing.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Bayesian Belief & Confidence Engine (Sprint 6 — soft-wire AFTER falsification; not a top-level layer) ---


@router.get("/belief-engine/health")
async def belief_engine_health():
    from belief_engine.production import health

    return health()


@router.get("/belief-engine/dashboard")
async def belief_engine_dashboard():
    from belief_engine.production import dashboard

    return dashboard()


@router.get("/belief-engine/constitution")
async def belief_engine_constitution():
    from belief_engine.production import constitution

    return constitution()


@router.get("/belief-engine/quality-gates")
async def belief_engine_quality_gates():
    from belief_engine.production import quality_gates

    return quality_gates()


@router.post("/belief-engine/plan")
async def belief_engine_plan(payload: dict[str, Any] = Body(default={})):
    from belief_engine.production import plan

    return plan(payload or {})


@router.post("/belief-engine/diagnostics")
async def belief_engine_diagnostics(payload: dict[str, Any] = Body(default={})):
    from belief_engine.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Thesis Construction Engine (Sprint 7 — soft-wire BEFORE Committee; not a top-level layer) ---


@router.get("/thesis-engine/health")
async def thesis_engine_health():
    from thesis_engine.production import health

    return health()


@router.get("/thesis-engine/dashboard")
async def thesis_engine_dashboard():
    from thesis_engine.production import dashboard

    return dashboard()


@router.get("/thesis-engine/constitution")
async def thesis_engine_constitution():
    from thesis_engine.production import constitution

    return constitution()


@router.get("/thesis-engine/quality-gates")
async def thesis_engine_quality_gates():
    from thesis_engine.production import quality_gates

    return quality_gates()


@router.post("/thesis-engine/plan")
async def thesis_engine_plan(payload: dict[str, Any] = Body(default={})):
    from thesis_engine.production import plan

    return plan(payload or {})


@router.post("/thesis-engine/diagnostics")
async def thesis_engine_diagnostics(payload: dict[str, Any] = Body(default={})):
    from thesis_engine.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Debate Engine (Sprint 8 — structured pre-Committee debate; not a layer/committee) ---


@router.get("/debate-engine/health")
async def debate_engine_health():
    from debate_engine.production import health

    return health()


@router.get("/debate-engine/dashboard")
async def debate_engine_dashboard():
    from debate_engine.production import dashboard

    return dashboard()


@router.get("/debate-engine/constitution")
async def debate_engine_constitution():
    from debate_engine.production import constitution

    return constitution()


@router.get("/debate-engine/quality-gates")
async def debate_engine_quality_gates():
    from debate_engine.production import quality_gates

    return quality_gates()


@router.post("/debate-engine/plan")
async def debate_engine_plan(payload: dict[str, Any] = Body(default={})):
    from debate_engine.production import plan

    return plan(payload or {})


@router.post("/debate-engine/diagnostics")
async def debate_engine_diagnostics(payload: dict[str, Any] = Body(default={})):
    from debate_engine.production import diagnostics

    return diagnostics(payload or {})


# --- RQ2 Institutional Decision Readiness Engine (Sprint 9 — final pre-Committee quality gate) ---


@router.get("/decision-readiness/health")
async def decision_readiness_health():
    from decision_readiness.production import health

    return health()


@router.get("/decision-readiness/dashboard")
async def decision_readiness_dashboard():
    from decision_readiness.production import dashboard

    return dashboard()


@router.get("/decision-readiness/constitution")
async def decision_readiness_constitution():
    from decision_readiness.production import constitution

    return constitution()


@router.get("/decision-readiness/quality-gates")
async def decision_readiness_quality_gates():
    from decision_readiness.production import quality_gates

    return quality_gates()


@router.post("/decision-readiness/plan")
async def decision_readiness_plan(payload: dict[str, Any] = Body(default={})):
    from decision_readiness.production import plan

    return plan(payload or {})


@router.post("/decision-readiness/diagnostics")
async def decision_readiness_diagnostics(payload: dict[str, Any] = Body(default={})):
    from decision_readiness.production import diagnostics

    return diagnostics(payload or {})


# --- IROS Governance Layer (evidence lineage / audit / re-evaluation) ---


@router.get("/iros/health")
async def iros_governance_health():
    from decision_engine.governance.production import health

    return health()


@router.post("/iros/package")
async def iros_governance_package(payload: dict[str, Any] = Body(default={})):
    """Build governance package (lineage, engine confidence, drift, delta, audit, re-eval)."""
    from decision_engine.governance.production import package_governance

    body = payload or {}
    return package_governance(
        query=str(body.get("query") or ""),
        ticker=body.get("ticker"),
        company_name=body.get("company_name"),
        readiness_gate=body.get("readiness_gate") or body.get("institutional_readiness_gate"),
        decision=body.get("decision"),
        layers=body.get("layers"),
        company_analysis=body.get("company_analysis"),
        cid=body.get("cid"),
        live_evidence=body.get("live_evidence"),
        valuation_pack=body.get("valuation_pack"),
        persist=bool(body.get("persist", True)),
    )


@router.get("/iros/audit/{recommendation_id}")
async def iros_governance_audit(recommendation_id: str):
    from decision_engine.governance.production import get_recommendation_audit

    row = get_recommendation_audit(recommendation_id)
    if not row:
        return {"found": False, "recommendation_id": recommendation_id}
    return {"found": True, "audit": row}


@router.get("/iros/reeval-queue")
async def iros_reeval_queue(limit: int = 50):
    from decision_engine.governance.production import reevaluation_queue

    return reevaluation_queue(limit=limit)


# --- RQ2 Institutional Reasoning Audit Engine (Sprint 10 — final reasoning certification) ---


@router.get("/reasoning-audit/health")
async def reasoning_audit_health():
    from reasoning_audit.production import health

    return health()


@router.get("/reasoning-audit/dashboard")
async def reasoning_audit_dashboard():
    from reasoning_audit.production import dashboard

    return dashboard()


@router.get("/reasoning-audit/constitution")
async def reasoning_audit_constitution():
    from reasoning_audit.production import constitution

    return constitution()


@router.get("/reasoning-audit/quality-gates")
async def reasoning_audit_quality_gates():
    from reasoning_audit.production import quality_gates

    return quality_gates()


@router.post("/reasoning-audit/plan")
async def reasoning_audit_plan(payload: dict[str, Any] = Body(default={})):
    from reasoning_audit.production import plan

    return plan(payload or {})


@router.post("/reasoning-audit/diagnostics")
async def reasoning_audit_diagnostics(payload: dict[str, Any] = Body(default={})):
    from reasoning_audit.production import diagnostics

    return diagnostics(payload or {})


# --- SIF v1.0 (Sector Intelligence Framework — additive; not an engine) ---


@router.get("/sif/health")
async def sif_health():
    from sif.production import SIF_VERSION, is_sif_enabled
    from sif.frameworks import FRAMEWORKS

    return {
        "status": "ok" if is_sif_enabled() else "disabled",
        "layer": "Sector Intelligence Framework",
        "programme": "SIF",
        "version": SIF_VERSION,
        "not_an_engine": True,
        "sector_count": len(FRAMEWORKS),
        "architecture_status": "v1.0.1 LOCKED",
    }


@router.get("/sif/dashboard")
async def sif_dashboard():
    from sif.production import production_dashboard

    return production_dashboard()


@router.get("/sif/frameworks")
async def sif_frameworks():
    from sif.frameworks import list_frameworks

    return {"count": len(list_frameworks()), "frameworks": list_frameworks()}


@router.get("/sif/frameworks/{sector_id}")
async def sif_framework(sector_id: str):
    from sif.frameworks import get_framework

    fw = get_framework(sector_id)
    if not fw:
        raise HTTPException(status_code=404, detail=f"Unknown sector framework: {sector_id}")
    return fw.to_dict()


@router.post("/sif/analyse")
async def sif_analyse(
    query: str = Query(...),
    ticker: str | None = Query(default=None),
    engine: str = Query(default="ask_agi"),
):
    from sif.production import analyse_query

    return analyse_query(query, ticker=ticker, engine=engine, kip=_kip, eve=_eve, aws=_aws)


@router.get("/sif/quality-gates")
async def sif_quality_gates():
    from sif.production import quality_gates

    return quality_gates(warm=True)


# --- LEO v1.0 (Live Evidence Orchestrator — additive; not an engine) ---


@router.get("/leo/health")
async def leo_health():
    from leo.production import is_leo_enabled
    from leo.schema import LEO_VERSION

    return {
        "status": "ok" if is_leo_enabled() else "disabled",
        "layer": "Live Evidence Orchestrator",
        "programme": "LEO",
        "version": LEO_VERSION,
        "not_an_engine": True,
        "architecture_status": "v1.0.1 LOCKED",
        "position": "before_cae_academy_sif_irp",
    }


@router.get("/leo/dashboard")
async def leo_dashboard():
    from leo.production import production_dashboard

    return production_dashboard()


@router.post("/leo/package")
async def leo_package(
    query: str = Query(...),
    ticker: str | None = Query(default=None),
    engine: str = Query(default="ask_agi"),
):
    from leo.production import package_for_query

    return package_for_query(
        query,
        ticker=ticker,
        engine=engine,
        eve=_eve,
        kip=_kip,
        aoi=_aoi,
        mee=_mee,
    )


@router.get("/leo/quality-gates")
async def leo_quality_gates():
    from leo.production import run_quality_gates

    return run_quality_gates(eve=_eve)


@router.get("/leo/dossier/{ticker}")
async def leo_dossier(ticker: str):
    from leo.dossier import get_dossier

    d = get_dossier(ticker)
    if not d:
        raise HTTPException(status_code=404, detail=f"No LEO dossier for {ticker}")
    return d


# --- CID v1.0 (Company Intelligence Dossier — permanent memory; not an engine) ---


@router.get("/company-dossier")
async def company_dossier_dashboard():
    from cid.production import production_dashboard

    return production_dashboard()


@router.get("/company-dossier/quality-gates")
async def company_dossier_quality_gates():
    from cid.production import quality_gates

    return quality_gates()


@router.get("/company-dossier/health")
async def company_dossier_health():
    from cid.production import is_cid_enabled
    from cid.schema import CID_VERSION

    from cid.openai_dossier import status as openai_dossier_status
    from cid.worker import read_status as dossier_worker_status

    return {
        "status": "ok" if is_cid_enabled() else "disabled",
        "layer": "Company Intelligence Dossier",
        "programme": "CID",
        "version": CID_VERSION,
        "not_an_engine": True,
        "architecture_status": "v1.0.1 LOCKED",
        "position": "permanent_company_memory_after_leo",
        "openai_generation": openai_dossier_status(),
        "background_worker": dossier_worker_status(),
    }


@router.post("/company-dossier/{ticker}/generate")
async def company_dossier_generate(ticker: str, refresh_evidence: bool = True):
    from cid.production import generate_openai_dossier

    result = generate_openai_dossier(ticker, refresh_evidence=refresh_evidence)
    if not result.get("ok"):
        error = result.get("error")
        status_code = 503 if error == "missing_openai_api_key" else 422
        raise HTTPException(status_code=status_code, detail=result)
    return result


@router.get("/company-dossier/{ticker}")
async def company_dossier_get(ticker: str):
    from cid.production import get_dossier

    d = get_dossier(ticker)
    if not d.get("ticker") and d.get("bypassed"):
        raise HTTPException(status_code=404, detail=f"CID disabled or missing for {ticker}")
    return d


@router.get("/company-dossier/{ticker}/timeline")
async def company_dossier_timeline(ticker: str, limit: int = Query(default=100, ge=1, le=500)):
    from cid.production import timeline

    return timeline(ticker, limit=limit)


@router.get("/company-dossier/{ticker}/coverage")
async def company_dossier_coverage(ticker: str):
    from cid.production import coverage

    return coverage(ticker)


@router.get("/company-dossier/{ticker}/valuation")
async def company_dossier_valuation(ticker: str):
    from cid.production import valuation_view

    return valuation_view(ticker)


@router.get("/company-dossier/{ticker}/risk")
async def company_dossier_risk(ticker: str):
    from cid.production import risk_view

    return risk_view(ticker)


@router.get("/company-dossier/{ticker}/forecast")
async def company_dossier_forecast(ticker: str):
    from cid.production import forecast_view

    return forecast_view(ticker)


@router.get("/company-dossier/{ticker}/documents")
async def company_dossier_documents(ticker: str):
    from cid.production import documents_view

    return documents_view(ticker)


# --- IRP V1 (above KIP/RSP, below Ask AGI; no platform redesign) ---


@router.get("/irp/health")
async def irp_health():
    return _irp.health()


@router.post("/irp/run")
async def irp_run(
    question: str = Query(...),
    ticker: str | None = Query(default=None),
):
    try:
        return _irp.run(question, ticker=ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/irp/learning")
async def irp_learning(limit: int = Query(default=20, ge=1, le=100)):
    try:
        return {"records": _irp.recent_learning(limit=limit)}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- UI Aggregation Layer (client facade; no engine name exposure) ---


@router.get("/ui/health")
async def ui_health():
    return _ui.health()


async def _cached_ui_home():
    """Return a bounded, process-local home snapshot without blocking the event loop."""
    import asyncio
    import logging
    import time

    cache = getattr(_cached_ui_home, "_cache", None)
    if cache is None:
        cache = {
            "payload": None,
            "expires_at": 0.0,
            "lock": asyncio.Lock(),
        }
        setattr(_cached_ui_home, "_cache", cache)

    now = time.monotonic()
    if cache["payload"] is not None and now < cache["expires_at"]:
        return cache["payload"]

    async with cache["lock"]:
        now = time.monotonic()
        if cache["payload"] is not None and now < cache["expires_at"]:
            return cache["payload"]

        started = time.monotonic()
        try:
            payload = await asyncio.wait_for(
                asyncio.to_thread(lambda: _ui.home().model_dump(mode="json")),
                timeout=15.0,
            )
        except TimeoutError:
            if cache["payload"] is not None:
                logging.getLogger(__name__).warning(
                    "ui_home_refresh_timeout serving_stale=true timeout_seconds=15"
                )
                return cache["payload"]
            raise HTTPException(
                status_code=503,
                detail="Home intelligence is still loading. Please retry shortly.",
            )

        cache["payload"] = payload
        cache["expires_at"] = time.monotonic() + 30.0
        logging.getLogger(__name__).info(
            "ui_home_refresh duration_ms=%d cache_ttl_seconds=30",
            int((time.monotonic() - started) * 1000),
        )
        return payload


@router.get("/ui/home")
async def ui_home():
    try:
        return await _cached_ui_home()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/calendar")
async def ui_calendar():
    try:
        return _ui.calendar()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/company/{ticker}")
async def ui_company(ticker: str):
    try:
        return _ui.company(ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ui/search")
async def ui_search(
    question: str = Query(...),
    ticker: str | None = Query(default=None),
    body: dict[str, Any] | None = Body(default=None),
    x_ask_trace_id: str | None = Header(default=None, alias="X-Ask-Trace-Id"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
):
    """Run sync UiService.search off the event loop so health checks stay responsive.

    Prefer a degraded SearchView over research_desk_unavailable whenever possible.
    Propagates gateway request_id / ask_trace_id (body / X-Ask-Trace-Id / X-Request-Id).
    """
    from functools import partial

    from starlette.concurrency import run_in_threadpool

    from app.ui.ask_pipeline_trace import normalize_request_id

    ask_trace_id = None
    conversation_id = None
    reset_conversation = False
    if isinstance(body, dict):
        ask_trace_id = (
            body.get("request_id")
            or body.get("ask_trace_id")
            or body.get("askTraceId")
        )
        if not ticker and body.get("ticker"):
            ticker = str(body.get("ticker"))
        conversation_id = body.get("conversation_id") or body.get("conversationId")
        reset_conversation = bool(body.get("reset_conversation") or body.get("resetConversation"))
    ask_trace_id = (str(ask_trace_id).strip() if ask_trace_id else None) or (
        str(x_request_id).strip() if x_request_id else None
    ) or (str(x_ask_trace_id).strip() if x_ask_trace_id else None)
    ask_trace_id = normalize_request_id(ask_trace_id)

    try:
        view = await run_in_threadpool(
            partial(
                _ui.search,
                question,
                ticker=ticker,
                ask_trace_id=ask_trace_id,
                conversation_id=str(conversation_id) if conversation_id else None,
                reset_conversation=reset_conversation,
            )
        )
        payload = view.model_dump(mode="json")
        # Echo request_id / ask_trace_id for gateway / clients.
        orch = payload.get("ask_orchestration") if isinstance(payload, dict) else None
        if isinstance(orch, dict):
            orch.setdefault("ask_trace_id", ask_trace_id)
            orch.setdefault("request_id", ask_trace_id)
        return payload
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Last-resort structured error — UiService.search should already degrade.
        import logging

        logging.getLogger("agi.ui.search").exception(
            "ui_search_unhandled q=%r request_id=%s", str(question)[:120], ask_trace_id
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "research_desk_unavailable",
                "retryable": True,
                "message": str(exc)[:240],
                "ask_trace_id": ask_trace_id,
                "request_id": ask_trace_id,
            },
        ) from exc


@router.get("/ui/ask-trace/{ask_trace_id}")
async def ui_ask_trace(ask_trace_id: str):
    """Return in-flight partial or completed Ask orchestration for a trace id.

    Used by the Node gateway on engine timeout so last_completed_stage is real.
    """
    from app.ui.ask_observability_store import (
        get_partial_trace,
        get_request_debug,
        recent_traces,
    )
    from app.ui.ask_pipeline_trace import normalize_request_id

    tid = normalize_request_id((ask_trace_id or "").strip() or None)
    if not tid:
        raise HTTPException(status_code=400, detail="ask_trace_id required")
    partial = get_partial_trace(tid) or get_partial_trace(ask_trace_id)
    if partial:
        return {"ok": True, "partial": True, "trace": partial, "request_id": tid}
    debug = get_request_debug(tid) or get_request_debug(ask_trace_id)
    if debug:
        return {
            "ok": True,
            "partial": bool(debug.get("partial")),
            "trace": debug,
            "request_id": tid,
            "pipeline": True,
        }
    for row in recent_traces(limit=50):
        row_tid = str(row.get("ask_trace_id") or "")
        if row_tid == tid or row_tid == str(ask_trace_id or ""):
            return {"ok": True, "partial": False, "trace": row, "request_id": tid}
    return {
        "ok": False,
        "partial": False,
        "trace": None,
        "ask_trace_id": tid,
        "request_id": tid,
    }


@router.get("/debug/request/{request_id}")
async def debug_request(request_id: str):
    """Phase-1 Ask pipeline debug — intent, entities, sources, evidence, LLM, fallback.

    Debugging only. Does not change Ask behavior.
    """
    from app.ui.ask_observability_store import get_request_debug
    from app.ui.ask_pipeline_trace import normalize_request_id

    rid = (request_id or "").strip()
    if not rid:
        raise HTTPException(status_code=400, detail="request_id required")
    # Accept both ask_* and legacy ASK-* without forcing a new id when empty-normalized.
    looked = get_request_debug(rid) or get_request_debug(normalize_request_id(rid))
    if not looked:
        raise HTTPException(
            status_code=404,
            detail={"error": "request_trace_not_found", "request_id": rid},
        )
    return looked


@router.get("/resilience/providers")
async def resilience_providers():
    """Circuit-breaker / provider health snapshot for Mission Control."""
    from app.resilience import get_provider_circuits

    return {
        "programme": "provider_resilience",
        "circuits": get_provider_circuits().status(),
        "policy": {
            "never_retry": [401, 402, 403, 404],
            "retry_transient": [429, 500, 502, 503, 504],
            "circuit_cooldown_sec": 900,
        },
    }


@router.get("/ui/autocomplete")
async def ui_autocomplete(q: str = Query(default="")):
    try:
        return _ui.autocomplete(q).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/article/{article_id}")
async def ui_article(
    article_id: str,
    ticker: str | None = Query(default=None),
):
    try:
        return _ui.article(article_id, ticker=ticker).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/timeline/{entity}")
async def ui_timeline(entity: str):
    try:
        return _ui.timeline(entity).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/research/{research_id}")
async def ui_research(research_id: str):
    try:
        return _ui.research(research_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/theme/{theme_id}")
async def ui_theme(theme_id: str):
    try:
        return _ui.theme(theme_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/sector/{sector_id}")
async def ui_sector(sector_id: str):
    try:
        return _ui.sector(sector_id).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/dashboard")
async def ui_dashboard():
    try:
        return _ui.dashboard().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/macro")
async def ui_macro():
    try:
        return _ui.macro().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/predictions")
async def ui_predictions():
    try:
        return _ui.predictions().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/portfolio")
async def ui_portfolio():
    try:
        return _ui.portfolio().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/copilot")
async def ui_copilot(
    page: str = Query(default="home"),
    question: str = Query(default=""),
    ticker: str | None = Query(default=None),
    theme_id: str | None = Query(default=None),
    sector_id: str | None = Query(default=None),
    research_id: str | None = Query(default=None),
):
    try:
        return _ui.copilot(
            page=page,
            question=question,
            ticker=ticker,
            theme_id=theme_id,
            sector_id=sector_id,
            research_id=research_id,
        ).model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ui/workflow")
async def ui_workflow():
    try:
        return _ui.workflow().model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orch/l2/trigger", dependencies=[Depends(require_token)])
async def orch_l2_trigger(body: BuildBatchRequest):
    """Enqueue + drain an L2 feature build. Engines must not call this for research."""
    if body.feature_ids:
        _l2.enqueue_manual(
            as_of=body.as_of,
            symbol=body.symbol,
            feature_ids=body.feature_ids,
            ctx=body.ctx,
        )
    else:
        event = MarketDataUpdateEvent(
            update_type=body.update_type,
            symbol=body.symbol,
            as_of=body.as_of,
            input_keys=body.input_keys,
        )
        _l2.dirty.mark(event)
        _l2.queue.enqueue(
            as_of=body.as_of,
            symbol=body.symbol,
            feature_ids=_l2.dirty.snapshot(symbol=body.symbol, as_of=body.as_of),
            ctx=body.ctx,
            update_type=body.update_type,
        )
    result = _l2.drain(parallel=body.parallel, max_workers=body.max_workers)
    if result is None:
        return {"ok": True, "status": "empty", "impacted": []}
    return {
        "ok": True,
        "status": result.status,
        "batch_id": result.batch_id,
        "orch_run_id": result.orch_run_id,
        "impacted": result.impacted,
        "snapshot_id": result.snapshot.snapshot_id if result.snapshot else None,
        "ready": result.ready.model_dump(mode="json") if result.ready else None,
        "builds": [b.model_dump(mode="json") for b in result.builds],
    }


@router.get("/orch/l2/builds", dependencies=[Depends(require_token)])
async def orch_l2_builds(limit: int = 50):
    return [b.model_dump(mode="json") for b in _l2.build_ledger.recent(limit=min(limit, 200))]


@router.get("/orch/l2/builds/{build_id}", dependencies=[Depends(require_token)])
async def orch_l2_build(build_id: str):
    row = _l2.build_ledger.get(build_id)
    if row is None:
        raise HTTPException(status_code=404, detail="build not found")
    return row.model_dump(mode="json")


@router.post("/orch/l2/drain", dependencies=[Depends(require_token)])
async def orch_l2_drain(parallel: bool = True, max_workers: int = 4):
    result = _l2.drain(parallel=parallel, max_workers=max_workers)
    if result is None:
        return {"ok": True, "status": "empty"}
    return {
        "ok": True,
        "status": result.status,
        "batch_id": result.batch_id,
        "impacted": result.impacted,
        "ready": result.ready.model_dump(mode="json") if result.ready else None,
    }


@router.get("/market-data/health")
async def market_data_health():
    """WS02 provider health + cache/latency metrics (no provider-native payloads)."""
    return _market_data.health.snapshot()


# --- YFP V1 (Yahoo Finance Institutional Provider — secondary MarketData adapter) ---


@router.get("/us-stock-intelligence/analyse")
async def us_stock_intelligence_analyse(symbol: str = "AAPL"):
    """Canonical US equity research package backed by Yahoo Finance."""
    from fastapi import HTTPException
    from us_stock_intelligence.production import analyse_us_stock

    try:
        return await analyse_us_stock(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/us-stock-intelligence/market-overview")
async def us_stock_intelligence_market_overview():
    """Live/daily US benchmarks, sectors, breadth and screeners."""
    from us_stock_intelligence.production import market_overview

    return await market_overview()


@router.get("/yfp/health")
async def yfp_health():
    from yfp.production import is_yfp_enabled, production_dashboard
    from yfp.schema import YFP_VERSION

    dash = production_dashboard(client=_market_data)
    return {
        "status": "ok" if is_yfp_enabled() else "disabled",
        "layer": "Yahoo Finance Institutional Provider",
        "programme": "YFP",
        "version": YFP_VERSION,
        "not_an_engine": True,
        "architecture_status": "v1.0.1 LOCKED",
        "position": "secondary_market_data_provider",
        "yahoo_status": dash.get("yahoo_status"),
        "flags": dash.get("coverage_flags"),
    }


@router.get("/yfp/dashboard")
async def yfp_dashboard():
    from yfp.production import production_dashboard

    return production_dashboard(client=_market_data)


@router.get("/yfp/quality-gates")
async def yfp_quality_gates():
    from yfp.production import quality_gates

    return quality_gates()


@router.get("/yfp/search")
async def yfp_search(q: str = Query(...), limit: int = Query(default=8, ge=1, le=25)):
    from yfp.production import search

    return search(q, limit=limit, client=_market_data)


@router.post("/yfp/enrich/{ticker}")
async def yfp_enrich(ticker: str):
    from yfp.production import enrich_cid

    return enrich_cid(ticker, client=_market_data)


# --- DVC V1 (Data Validation & Consensus — Market Data platform layer) ---


@router.get("/dvc/health")
async def dvc_health():
    from dvc.production import is_dvc_enabled, production_dashboard
    from dvc.schema import DVC_VERSION

    dash = production_dashboard()
    return {
        "status": "ok" if is_dvc_enabled() else "disabled",
        "layer": "Data Validation & Consensus",
        "programme": "DVC",
        "version": DVC_VERSION,
        "not_an_engine": True,
        "not_a_provider": True,
        "architecture_status": "v1.0.1 LOCKED",
        "position": "after_canonical_mapper_before_market_data_client_consumers",
        "metrics": dash.get("metrics"),
        "enabled": is_dvc_enabled(),
    }


@router.get("/dvc/dashboard")
async def dvc_dashboard():
    from dvc.production import production_dashboard

    return production_dashboard()


@router.get("/dvc/quality-gates")
async def dvc_quality_gates():
    from dvc.production import quality_gates

    return quality_gates()


@router.get("/dvc/metrics")
async def dvc_metrics():
    from dvc.production import success_metrics

    return success_metrics()


@router.get("/dvc/company/{ticker}")
async def dvc_company(ticker: str):
    from dvc.production import get_company_quality

    return get_company_quality(ticker)


@router.get("/dvc/conflicts")
async def dvc_conflicts(
    limit: int = Query(default=40, ge=1, le=200),
    severity: str | None = Query(default=None),
):
    from dvc import store as dvc_store

    return {"conflicts": dvc_store.list_conflicts(limit=limit, severity=severity)}


@router.post("/dvc/validate/{ticker}")
async def dvc_validate(ticker: str):
    from dvc.validate import validate_symbol

    return await validate_symbol(_market_data, ticker)


@router.post("/dvc/enrich/{ticker}")
async def dvc_enrich(ticker: str):
    from dvc.production import enrich_cid

    return enrich_cid(ticker, client=_market_data)


# --- ECP V1 (Evidence Completion Pipeline — orchestration layer) ---


@router.get("/ecp/health")
async def ecp_health():
    from ecp.production import is_ecp_enabled, production_dashboard
    from ecp.schema import ECP_VERSION

    dash = production_dashboard()
    return {
        "status": "ok" if is_ecp_enabled() else "disabled",
        "layer": "Evidence Completion Pipeline",
        "programme": "ECP",
        "version": ECP_VERSION,
        "not_an_engine": True,
        "not_a_recommendation_model": True,
        "architecture_status": "v1.0.1 LOCKED",
        "metrics": dash.get("metrics"),
        "enabled": is_ecp_enabled(),
    }


@router.get("/ecp/dashboard")
async def ecp_dashboard():
    from ecp.production import production_dashboard

    return production_dashboard()


@router.get("/ecp/quality-gates")
async def ecp_quality_gates():
    from ecp.production import quality_gates

    return quality_gates()


@router.get("/ecp/reports")
async def ecp_reports(limit: int = Query(default=30, ge=1, le=100)):
    from ecp import store as ecp_store

    return {"reports": ecp_store.list_reports(limit=limit)}


@router.get("/ecp/report/{ticker}")
async def ecp_report(ticker: str):
    from ecp import store as ecp_store

    row = ecp_store.get_report(ticker)
    return row or {"ticker": ticker.upper(), "found": False}


@router.post("/ecp/complete")
async def ecp_complete(
    ticker: str = Query(...),
    q: str = Query(default="Should I buy?"),
):
    """Run evidence completion for a ticker (admin / probe)."""
    from ecp.production import soft_complete

    leo_pkg: dict = {}
    cid: dict = {}
    sif_pkg: dict = {}
    try:
        from leo.production import package_for_query as leo_package

        leo_pkg = leo_package(q, ticker=ticker, engine="ecp_admin") or {}
    except Exception:
        leo_pkg = {"ticker": ticker.upper(), "evidence_objects": [], "quality_gate": {"blocked": True}}
    try:
        from cid.production import get_dossier

        cid = get_dossier(ticker) or {}
    except Exception:
        cid = {"ticker": ticker.upper()}
    try:
        from sif.production import analyse_query as sif_analyse

        sif_pkg = sif_analyse(q, ticker=ticker, engine="ecp_admin") or {}
    except Exception:
        sif_pkg = {}

    return soft_complete(
        query=q,
        ticker=ticker,
        leo_pkg=leo_pkg,
        cid=cid,
        sif_pkg=sif_pkg,
        kip=_kip,
        kf=_kf,
        client=_market_data,
        force=True,
    )


# --- Mission Control V1 (administrator operations centre; read-only) ---


@router.get("/mission-control/health")
async def mission_control_health():
    from mission_control.production import health

    return health()


@router.get("/mission-control/agent-map")
async def mission_control_agent_map():
    """Snapshot reader only — never runs build_agent_map() / probe fan-out."""
    from mission_control.production import agent_map

    return agent_map()


@router.get("/mission-control/intelligence-map")
async def mission_control_intelligence_map():
    """Snapshot reader only — never probes catalog health routes on the HTTP path."""
    from mission_control.production import intelligence_map

    return intelligence_map()


@router.get("/mission-control/institutional-intelligence")
async def mission_control_institutional_intelligence():
    """Snapshot reader only — never fans out institutional dashboard aggregation."""
    from mission_control.production import institutional_intelligence

    return institutional_intelligence()


@router.get("/mission-control/dashboard")
async def mission_control_dashboard():
    """Snapshot reader only — never runs build_mission_control() on the HTTP path."""
    from mission_control.production import dashboard

    return dashboard()


@router.get("/mission-control/ask-observability")
async def mission_control_ask_observability(limit: int = 25):
    """Ask evidence funnel + latency KPIs (internal diagnostics; not client-facing)."""
    from mission_control.production import ask_observability

    return ask_observability(limit=max(1, min(int(limit or 25), 100)))


@router.post("/mission-control/rebuild")
async def mission_control_rebuild(payload: dict[str, Any] = Body(default={})):
    """Admin: queue worker snapshot rebuild. Returns immediately. Never builds inline."""
    from mission_control.production import rebuild

    body = payload or {}
    trigger = str(body.get("trigger") or "admin_rebuild").strip() or "admin_rebuild"
    return rebuild(trigger=trigger, wait=False)


# --- Continuous Gather → Learn (autonomous; never on Ask path) ---


@router.get("/continuous-gather-learn/health")
async def continuous_gather_learn_health():
    from starlette.concurrency import run_in_threadpool

    from continuous_gather_learn.production import health

    return await run_in_threadpool(health)


@router.post(
    "/continuous-gather-learn/heartbeat",
    dependencies=[Depends(require_token)],
)
async def continuous_gather_learn_heartbeat(payload: dict[str, Any] = Body(default={})):
    """Accept a signed heartbeat from the isolated gather worker."""
    from starlette.concurrency import run_in_threadpool

    from continuous_gather_learn.persist import write_remote_gather_heartbeat

    heartbeat = await run_in_threadpool(write_remote_gather_heartbeat, payload or {})
    return {"ok": True, "accepted_at": heartbeat.get("beat_at")}


@router.get("/continuous-gather-learn/dashboard")
async def continuous_gather_learn_dashboard():
    from starlette.concurrency import run_in_threadpool

    from continuous_gather_learn.production import dashboard

    return await run_in_threadpool(dashboard)


@router.post("/continuous-gather-learn/run")
async def continuous_gather_learn_run(payload: dict[str, Any] = Body(default={})):
    """Ops-only: run one gather→learn cycle. Failures never affect Ask."""
    from functools import partial

    from starlette.concurrency import run_in_threadpool

    from continuous_gather_learn.production import run as cgl_run

    return await run_in_threadpool(
        partial(
            cgl_run,
            slot=payload.get("slot"),
            force_morning_dag=bool(payload.get("force_morning_dag")),
            include_faa=payload.get("include_faa"),
        )
    )


@router.get("/universe-learning/health")
async def universe_learning_health():
    """Universe learning bootstrap — gather/learn across Nifty + NSE book."""
    from universe_learning.production import health

    return health()


@router.get("/universe-learning/status")
async def universe_learning_status():
    from universe_learning.production import learning_status

    return learning_status()


@router.post("/universe-learning/bootstrap")
async def universe_learning_bootstrap(payload: dict[str, Any] = Body(default={})):
    """Seed HD queue from index/trading universe and start CGL gather→learn.

    scope: nifty500 (default) | indices | all
    """
    from universe_learning.production import bootstrap_universe_learning

    body = payload or {}
    return bootstrap_universe_learning(
        scope=str(body.get("scope") or "nifty500"),
        run_cgl=bool(body.get("run_cgl", True)),
        slot=str(body.get("slot") or "overnight"),
        force_refresh_queue=bool(body.get("force_refresh_queue", True)),
        icf_tick=bool(body.get("icf_tick", False)),
    )


# --- AGIB V1.5 — Institutional Universe Data Factory (IUDF) ---


@router.get("/universe-master-registry/health")
async def universe_master_registry_health():
    from universe_master_registry.production import health

    return health()


@router.get("/universe-master-registry/dashboard")
async def universe_master_registry_dashboard():
    from universe_master_registry.production import dashboard

    return dashboard()


@router.get("/universe-master-registry")
async def universe_master_registry_list(
    index: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    include_coverage: bool = False,
):
    from universe_master_registry.production import list_registry

    return list_registry(index=index, limit=limit, offset=offset, include_coverage=include_coverage)


@router.get("/universe-master-registry/company/{ticker}")
async def universe_master_registry_company(ticker: str):
    from universe_master_registry.production import get_company

    return get_company(ticker)


@router.get("/coverage-matrix/health")
async def coverage_matrix_health():
    from coverage_matrix.production import health

    return health()


@router.get("/coverage-matrix/company/{ticker}")
async def coverage_matrix_company(ticker: str):
    from coverage_matrix.production import matrix_for_company

    return matrix_for_company(ticker)


@router.get("/coverage-matrix/universe")
async def coverage_matrix_universe(scope: str = "nifty500", limit: int = 20):
    from coverage_matrix.production import matrix_for_universe

    return matrix_for_universe(scope=scope, limit=limit)


@router.get("/institutional-knowledge-tables/health")
async def ikt_health():
    from institutional_knowledge_tables.production import health

    return health()


@router.get("/institutional-knowledge-tables/tables")
async def ikt_tables_catalog():
    from institutional_knowledge_tables.production import tables_catalog

    return tables_catalog()


@router.get("/institutional-knowledge-tables/company/{ticker}")
async def ikt_company(ticker: str):
    from institutional_knowledge_tables.production import get_company_tables

    return get_company_tables(ticker)


@router.get("/institutional-knowledge-tables/company/{ticker}/{table}")
async def ikt_company_table(ticker: str, table: str, period: str | None = None):
    from institutional_knowledge_tables.production import get_company_table

    return get_company_table(ticker, table, period=period)


@router.get("/institutional-knowledge-tables/company/{ticker}/{table}/{field}/history")
async def ikt_field_history(ticker: str, table: str, field: str, period: str | None = None):
    from institutional_knowledge_tables.production import get_field_timeline

    return get_field_timeline(ticker, table, field, period=period)


@router.post("/institutional-knowledge-tables/fact")
async def ikt_record_fact(payload: dict[str, Any] = Body(default={})):
    """Admin/collector write path. Every fact must carry an evidence `source` —
    never fabricated. Gate this route at the ops/admin layer upstream.
    """
    from institutional_knowledge_tables.production import record_fact

    body = payload or {}
    try:
        return record_fact(
            ticker=str(body.get("ticker") or ""),
            table=str(body.get("table") or ""),
            field=str(body.get("field") or ""),
            value=body.get("value"),
            source=str(body.get("source") or ""),
            effective_date=body.get("effective_date"),
            period=body.get("period"),
            trigger=str(body.get("trigger") or "manual"),
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/institutional-knowledge-tables/onboard-universe")
async def ikt_onboard_universe(payload: dict[str, Any] = Body(default={})):
    """Onboard every company in the uploaded universe file — no code changes."""
    from institutional_knowledge_tables.production import onboard_universe

    body = payload or {}
    return onboard_universe(scope=str(body.get("scope") or "nifty500"), limit=body.get("limit"))


@router.post("/institutional-knowledge-tables/company/{ticker}/rebuild")
async def ikt_rebuild_company(ticker: str):
    from institutional_knowledge_tables.production import rebuild_company_tables

    return rebuild_company_tables(ticker)


@router.post("/institutional-knowledge-tables/seed-capital-iq")
async def ikt_seed_capital_iq(payload: dict[str, Any] = Body(default={})):
    """(Re-)ingest the committed Capital IQ screener exports
    (capital_iq_exports/) into IKT. Runs automatically (non-blocking) at
    boot — this endpoint is for manually re-triggering it (e.g. after a
    persistent-disk migration) or checking the current resolved/unresolved
    counts. Body: {force?: bool}."""
    from institutional_knowledge_tables.production import seed_capital_iq_status

    body = payload or {}
    return seed_capital_iq_status(force=bool(body.get("force", False)))


@router.post("/institutional-knowledge-tables/upload-sheet")
async def ikt_upload_sheet(payload: dict[str, Any] = Body(default={})):
    """Drop an Excel/CSV of companies + info. Each recognized column becomes a
    versioned fact per resolved ticker. Rows that can't be matched to the
    uploaded universe registry are reported, never guessed.

    Body: { filename, content_base64, sheet_name?, dry_run?, actor?, column_names? }
    `column_names`: reuse the header list from a sibling upload when this
    file is a headerless continuation batch of the same export.
    """
    from institutional_knowledge_tables.production import upload_company_sheet

    body = payload or {}
    try:
        return upload_company_sheet(
            filename=str(body.get("filename") or "upload.xlsx"),
            content_base64=body.get("content_base64"),
            sheet_name=body.get("sheet_name", 0),
            dry_run=bool(body.get("dry_run", False)),
            actor=body.get("actor"),
            column_names=body.get("column_names"),
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# Valuation Intelligence — Institutional Consensus Dashboard (Capital IQ)
# Excel is import-source only; UI/Ask read the normalized valuation_consensus store.
# ---------------------------------------------------------------------------


@router.get("/valuation-consensus/health")
async def valuation_consensus_health():
    from valuation_consensus.production import health

    return health()


@router.get("/valuation-consensus/analytics")
async def valuation_consensus_analytics():
    from valuation_consensus.production import analytics

    return analytics()


@router.get("/valuation-consensus/rows")
async def valuation_consensus_rows(
    q: str = "",
    page: int = 1,
    page_size: int = 50,
    sort: str = "coverage",
    sort_dir: str | None = None,
    sector: str | None = None,
    industry: str | None = None,
    recommendation: str | None = None,
    country: str | None = None,
    exchange: str | None = None,
    market_cap_min: float | None = None,
    market_cap_max: float | None = None,
    coverage_min: float | None = None,
    coverage_max: float | None = None,
    upside_min: float | None = None,
    upside_max: float | None = None,
    buy_min: float | None = None,
    hold_min: float | None = None,
    sell_min: float | None = None,
    return_min: float | None = None,
    return_max: float | None = None,
):
    from valuation_consensus.production import query_rows

    filters = {
        k: v
        for k, v in {
            "sector": sector,
            "industry": industry,
            "recommendation": recommendation,
            "country": country,
            "exchange": exchange,
            "market_cap_min": market_cap_min,
            "market_cap_max": market_cap_max,
            "coverage_min": coverage_min,
            "coverage_max": coverage_max,
            "upside_min": upside_min,
            "upside_max": upside_max,
            "buy_min": buy_min,
            "hold_min": hold_min,
            "sell_min": sell_min,
            "return_min": return_min,
            "return_max": return_max,
        }.items()
        if v is not None and v != ""
    }
    return query_rows(
        q=q,
        page=page,
        page_size=page_size,
        sort=sort,
        sort_dir=sort_dir,
        filters=filters,
    )


@router.get("/valuation-consensus/company/{ticker}")
async def valuation_consensus_company(ticker: str):
    from valuation_consensus.production import company_detail

    return company_detail(ticker)


@router.post("/valuation-consensus/import/preview")
def valuation_consensus_import_preview(payload: dict[str, Any] = Body(default={})):
    """Admin: upload CapIQ Excel → parse → stage preview (does not publish)."""
    from valuation_consensus.production import import_preview

    body = payload or {}
    try:
        return import_preview(
            filename=str(body.get("filename") or "capiq.xlsx"),
            content_base64=body.get("content_base64"),
            sheet_name=body.get("sheet_name", 0),
            column_names=body.get("column_names"),
            actor=body.get("actor"),
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


@router.post("/valuation-consensus/import/validate")
def valuation_consensus_import_validate(payload: dict[str, Any] = Body(default={})):
    from valuation_consensus.production import import_validate

    body = payload or {}
    return import_validate(str(body.get("import_id") or ""))


@router.post("/valuation-consensus/import/publish")
def valuation_consensus_import_publish(payload: dict[str, Any] = Body(default={})):
    from valuation_consensus.production import import_publish

    body = payload or {}
    return import_publish(str(body.get("import_id") or ""), actor=body.get("actor"))


@router.post("/valuation-consensus/import/rollback")
def valuation_consensus_import_rollback(payload: dict[str, Any] = Body(default={})):
    from valuation_consensus.production import import_rollback

    body = payload or {}
    return import_rollback(str(body.get("version_id") or ""), actor=body.get("actor"))


@router.get("/valuation-consensus/imports")
def valuation_consensus_imports():
    from valuation_consensus.production import list_imports

    return list_imports()


@router.get("/valuation-consensus/versions")
async def valuation_consensus_versions():
    from valuation_consensus.production import list_versions

    return list_versions()


@router.get("/valuation-consensus/export")
async def valuation_consensus_export():
    from valuation_consensus.production import export_snapshot

    return export_snapshot()


@router.post("/valuation-consensus/seed")
async def valuation_consensus_seed(payload: dict[str, Any] = Body(default={})):
    """Ops: seed from committed broker_estimates.xlsx (or an explicit path)."""
    body = payload or {}
    path = body.get("path")
    if path:
        from valuation_consensus.production import seed_from_path

        return seed_from_path(path, actor=str(body.get("actor") or "seed"))
    from valuation_consensus.seed_broker_estimates import seed_if_needed

    return seed_if_needed(force=bool(body.get("force", True)))


# ---------------------------------------------------------------------------
# Hedge Fund Strategy Lab — strategy library plus server-side calculators.
# ---------------------------------------------------------------------------


def _month_end_closes(db) -> list[dict[str, Any]]:
    """Last trading close of each month, aggregated in SQL.

    The monthly strategies previously selected every daily bar - 6.86 million
    rows - into the request process, which is what took the engine down during
    market hours on 2026-08-20. Only the month-end close is ever used, so the
    reduction happens in the database: roughly 300k rows instead of 6.86M.

    Weekends are excluded here too. NSE does not trade then and those rows
    carry a differently scaled series, so one could otherwise decide a month's
    closing price.
    """
    table = db.physical_table("daily_market_history")
    return db.query(
        f"""SELECT symbol, date, close FROM (
                SELECT symbol, date, close,
                       ROW_NUMBER() OVER (
                           PARTITION BY symbol, substr(date, 1, 7)
                           ORDER BY date DESC
                       ) AS rn
                FROM {table}
                WHERE COALESCE(sys_published, 1) = 1
                  AND close IS NOT NULL
                  AND CAST(strftime('%w', date) AS INTEGER) BETWEEN 1 AND 5
            ) WHERE rn = 1"""
    ) or []


@router.post("/hedge-fund-lab/backtest/neglected-quality")
def hedge_fund_neglected_quality_backtest(payload: dict[str, Any] = Body(default={})):
    """Quality ranking over companies with no analyst coverage.

    Long only by design: estimate revision showed real information that could
    not be reached, because the only shortable names in India are the 214 with
    single-stock futures. Here shortability never binds, and the universe is
    the roughly 1,800 companies nobody models.
    """
    from hedge_fund_lab.neglected_quality import backtest
    from institutional_warehouse import db, store

    body = payload or {}
    try:
        ratios = store.all_rows("sector_ratio_history", limit=200000) or []
        covered = {str(r.get("symbol") or "").upper()
                   for r in (store.all_rows("consensus", limit=20000) or [])
                   if r.get("symbol")}
        prices = _month_end_closes(db)
    except Exception as exc:
        return {"ok": False, "error": "warehouse_unavailable", "detail": str(exc)[:200]}

    result = backtest(
        ratio_rows=ratios,
        price_rows=prices,
        covered=covered if body.get("exclude_covered", True) else None,
        holdings=int(body.get("holdings") or 30),
        cost_bps=float(body.get("cost_bps") or 25.0),
        lag_months=int(body.get("lag_months") or 6),
    )
    return result


@router.post("/hedge-fund-lab/backtest/estimate-revision")
def hedge_fund_estimate_revision_backtest(payload: dict[str, Any] = Body(default={})):
    """Monthly walk-forward on point-in-time consensus revisions.

    The one strategy here whose edge is data assembly rather than speed: it
    reads 258,465 vintages that say what was believed on each month end, so
    ranking on them involves no look-ahead. Sync def on purpose - it scans the
    warehouse, so FastAPI runs it in the threadpool.
    """
    from hedge_fund_lab.estimate_revision import backtest
    from institutional_warehouse import db, store

    body = payload or {}
    try:
        vintages = store.all_rows("consensus_metric_vintages", limit=400000) or []
        prices = _month_end_closes(db)
    except Exception as exc:
        return {"ok": False, "error": "warehouse_unavailable", "detail": str(exc)[:200]}

    result = backtest(
        vintage_rows=vintages,
        price_rows=prices,
        lookback_months=int(body.get("lookback_months") or 3),
        holdings=int(body.get("holdings") or 25),
        cost_bps=float(body.get("cost_bps") or 25.0),
    )
    # The month-by-month series is long and only useful for plotting.
    if not body.get("include_periods"):
        result.pop("periods", None)
    return result


@router.get("/hedge-fund-lab/corporate-action-audit")
def hedge_fund_corporate_action_audit(limit: int = 30000, symbols: int = 150):
    """What the price adjustment can and cannot stand behind.

    The receipt the validation registry asks for under CORPORATE_ACTION_UNVERIFIED,
    which blocks the pairs strategy. Three findings drive it, all verified against
    production on 2026-08-19:

    * `daily_market_history.adjusted_close` equals `close` wherever populated and
      reflects no structural action, so it is ignored rather than trusted.
    * The stated split ratios disagree with the price series about half the time,
      so each one is corroborated against the gap across its own ex-date.
    * Roughly 18% of price rows fall on a weekend and carry a differently scaled
      series, so they are dropped as non-trading days.

    Bounded to the busiest symbols on purpose: an unbounded price scan on the
    request path is what took the engine down on 2026-08-19.
    """
    from hedge_fund_lab.price_adjustment import _as_date, audit, is_trading_day
    from institutional_warehouse import db, store

    actions = store.all_rows("corporate_actions", limit=max(1, min(int(limit or 30000), 60000))) or []
    structural = {"split", "bonus", "rights", "merger", "demerger"}
    wanted: list[str] = []
    for action in actions:
        if str(action.get("action_type") or "").lower() not in structural:
            continue
        symbol = str(action.get("symbol") or "").strip().upper()
        if symbol and symbol not in wanted:
            wanted.append(symbol)
    wanted = wanted[: max(1, min(int(symbols or 150), 400))]

    prices: dict[str, list] = {}
    if wanted:
        try:
            table = db.physical_table("daily_market_history")
            marks = ",".join("?" for _ in wanted)
            rows = db.query(
                f"""SELECT symbol, date, close FROM {table}
                    WHERE COALESCE(sys_published, 1) = 1 AND symbol IN ({marks})
                    ORDER BY symbol, date""",
                tuple(wanted),
            ) or []
            for row in rows:
                parsed = _as_date(str(row.get("date") or "")[:10])
                try:
                    close = float(row.get("close"))
                except (TypeError, ValueError):
                    continue
                if parsed and close > 0 and is_trading_day(parsed):
                    prices.setdefault(str(row.get("symbol") or "").upper(), []).append((parsed, close))
        except Exception as exc:  # corroboration is best-effort; the audit still reports
            return {**audit(actions), "price_lookup_error": str(exc)[:200]}

    report = audit(actions, prices)
    report["symbols_corroborated_against_prices"] = len(prices)
    return report


@router.get("/hedge-fund-lab/live-strategies")
def hedge_fund_live_strategies(limit: int = 12):
    """Intraday-native strategies: live engine signal + historical risk/liquidity.

    Sync def on purpose - it reads the warehouse, so FastAPI runs it in the
    threadpool rather than on the event loop.
    """
    from hedge_fund_lab.live_strategies import board

    return board(limit=max(1, min(int(limit or 12), 50)))


@router.get("/hedge-fund-lab/live-strategies/{strategy_id}")
def hedge_fund_live_strategy(strategy_id: str, limit: int = 20):
    from hedge_fund_lab.live_strategies import LIVE_STRATEGIES

    entry = LIVE_STRATEGIES.get(str(strategy_id or "").strip().lower())
    if not entry:
        return {"ok": False, "error": "unknown_strategy", "strategy_id": strategy_id,
                "available": sorted(LIVE_STRATEGIES)}
    return entry[1](max(1, min(int(limit or 20), 50)))


@router.get("/hedge-fund-lab/health")
async def hedge_fund_lab_health():
    from hedge_fund_lab.production import health

    return await run_in_threadpool(health)


@router.get("/hedge-fund-lab/strategies")
async def hedge_fund_lab_strategies():
    from hedge_fund_lab.production import library

    return library()


@router.get("/hedge-fund-lab/reliability")
async def hedge_fund_lab_reliability():
    from hedge_fund_lab.terminal import reliability_status

    return await run_in_threadpool(reliability_status)


@router.get("/research-factors/health")
async def research_factors_health():
    from research_factor_layer.production import health

    return health()


@router.get("/research-factors/audit")
async def research_factors_audit(limit: int = 20, as_of: str | None = None):
    from research_factor_layer.production import audit

    return audit(as_of=as_of, limit=max(1, min(int(limit or 20), 100)))


@router.get("/research-factors/company/{symbol}")
async def research_factors_company(symbol: str, as_of: str | None = None):
    from research_factor_layer.production import company

    return company(symbol, as_of=as_of)


@router.get("/hedge-fund-lab/compare")
async def hedge_fund_lab_compare():
    from hedge_fund_lab.production import compare

    return compare()


@router.get("/hedge-fund-lab/strategy/{strategy_id}")
async def hedge_fund_lab_strategy(strategy_id: str):
    from hedge_fund_lab.production import strategy

    return strategy(strategy_id)


@router.get("/hedge-fund-lab/long-short/readiness")
async def hedge_fund_lab_long_short_readiness():
    from hedge_fund_lab.long_short_equity import readiness

    return await run_in_threadpool(readiness)


@router.get("/hedge-fund-lab/long-short/research-book")
async def hedge_fund_lab_long_short_research_book(limit: int = 10):
    from hedge_fund_lab.long_short_equity import research_book

    return await run_in_threadpool(research_book, limit=max(1, min(int(limit or 10), 25)))


@router.get("/hedge-fund-lab/regime")
async def hedge_fund_lab_regime():
    from hedge_fund_lab.scanner import market_regime

    return await run_in_threadpool(market_regime)


@router.get("/hedge-fund-lab/scan/{strategy}")
async def hedge_fund_lab_scan(strategy: str, limit: int = 20, sector: str | None = None):
    """Run a strategy across the live NSE universe."""
    from hedge_fund_lab.terminal import scan

    return await run_in_threadpool(scan, strategy, limit=limit, sector=sector)


@router.get("/hedge-fund-lab/terminal")
async def hedge_fund_lab_terminal(limit: int = 12, refresh: bool = False):
    """Serve the stored terminal snapshot. Live warehouse scans stay on POST /snapshot."""
    from hedge_fund_lab.snapshot_store import serve_terminal_overview

    return await run_in_threadpool(
        serve_terminal_overview,
        limit=max(1, min(int(limit or 12), 50)),
        refresh=refresh,
    )


@router.post("/hedge-fund-lab/terminal/snapshot")
async def hedge_fund_lab_terminal_snapshot(limit: int = 12):
    """Compute the full terminal once and persist it to Supabase for Node reads."""
    from hedge_fund_lab.snapshot_store import compute_and_persist

    return await run_in_threadpool(compute_and_persist, limit=max(1, min(int(limit or 12), 50)))


@router.get("/hedge-fund-lab/terminal/snapshot/latest")
async def hedge_fund_lab_terminal_snapshot_latest():
    """Return the latest stored terminal snapshot metadata (engine-side debug)."""
    from hedge_fund_lab.snapshot_store import latest_snapshot_row

    row = await run_in_threadpool(latest_snapshot_row)
    if not row:
        return {"ok": False, "error": "no_snapshot"}
    return {"ok": True, **{k: row.get(k) for k in (
        "id", "generated_at", "source_as_of", "status", "freshness",
        "schema_version", "calculation_version", "data_quality",
        "limit_used", "universe_scanned", "live_opportunities",
    )}, "payload": row.get("payload")}


@router.get("/hedge-fund-lab/desk-timings")
async def hedge_fund_lab_desk_timings():
    """Where a cold desk request actually spends its time.

    Added because I guessed twice and was wrong twice - first that the universe
    build was the cost, then that the ratio history was. Each stage is timed
    from a cold cache so the next decision is made from a measurement.
    """
    from hedge_fund_lab import desk_timings

    # include_builds re-runs the expensive builders and makes the engine
    # unresponsive for minutes. It took the engine down once already, so it has
    # to be asked for explicitly.
    return await run_in_threadpool(desk_timings.measure, include_builds=False)


@router.get("/hedge-fund-lab/desk-snapshot")
def hedge_fund_lab_desk_snapshot():
    """How old the desk's universe is and whether the builder is well.

    /health answers in 0.14s while the desk is completely unresponsive, so it is
    no evidence the application is usable. This reports the thing that actually
    determines what a client sees.
    """
    from hedge_fund_lab.scanner import desk_artifacts_status

    return {"ok": True, "artifacts": desk_artifacts_status()}


@router.post("/hedge-fund-lab/desk-snapshot/rebuild")
async def hedge_fund_lab_desk_snapshot_rebuild(
    payload: dict[str, Any] = Body(default_factory=dict),
):
    """Build a new universe now. Returns the build, not a queued acknowledgement."""
    from hedge_fund_lab import desk_snapshot

    # Named maintenance action, not a diagnostic. Observability endpoints read
    # recorded state; anything that clears a cache or forces a heavy rebuild has
    # to be asked for explicitly - the alternative took the engine down once.
    body = payload or {}
    if body.get("force"):
        names = body.get("names") or ["universe", "ratio_history"]
        return await run_in_threadpool(
            lambda: {"ok": True, "forced": {n: desk_snapshot.rebuild(n) for n in names}})
    return await run_in_threadpool(desk_snapshot.refresh_stale)


@router.get("/hedge-fund-lab/opportunity/{ticker}")
async def hedge_fund_lab_opportunity(ticker: str):
    """Why a company was surfaced: evidence, calculation chain, risks and timeline."""
    from hedge_fund_lab.terminal import opportunity

    return await run_in_threadpool(opportunity, ticker)


@router.get("/hedge-fund-lab/daily-monitor")
async def hedge_fund_lab_daily_monitor(limit: int = 6):
    from hedge_fund_lab.scanner import daily_monitor

    return await run_in_threadpool(daily_monitor, limit=limit)


@router.get("/options-lab/collector", dependencies=[Depends(require_token)])
async def options_lab_collector_status():
    """Whether the embedded collector is actually running, and what it has done.

    Without this the only way to tell a live collector from a dead one is to
    watch the tables stay empty and guess why.
    """
    from options_lab.embedded import status

    return status()


@router.post("/options-lab/collect", dependencies=[Depends(require_token)])
async def options_lab_collect(payload: dict[str, Any] = Body(default_factory=dict)):
    """Capture one option-chain snapshot.

    The lab had storage configured in render.yaml and no process writing to it:
    options_lab.automation.run_worker polls through the session, and nothing
    starts it, so every table behind the validation dashboard was empty.

    This is the same collection driven from the outside instead. A schedule
    calling it several times a session is not the same as a worker polling
    every ten seconds, but it produces real snapshots on a service that is
    already deployed, which the worker does not.
    """
    from options_lab.automation import collect_command
    from options_lab.upstox_live import LiveConfig

    body = payload or {}
    config = LiveConfig.from_environment()
    # force skips the market-session gate. Off by default so a scheduled call
    # outside session hours records a skip rather than a snapshot of a closed
    # book, and available because an operator checking the wiring should not
    # have to wait for Monday.
    code = await run_in_threadpool(collect_command, config, force=bool(body.get("force")))
    return {
        "ok": code == 0,
        "exit_code": code,
        "forced": bool(body.get("force")),
        "note": ("0 collected or skipped outside session, 2 means the provider "
                 "call failed"),
    }


@router.post("/warehouse/company-names/repair", dependencies=[Depends(require_token)])
async def warehouse_company_names_repair(payload: dict[str, Any] = Body(default_factory=dict)):
    """Put real company names back where a row is named after its own ticker.

    Defaults to a dry run: pass {"apply": true} to write. A repair that runs
    on a bare call is how a couple of thousand rows get rewritten by accident.
    """
    from financial_warehouse_completion import company_names

    apply = bool((payload or {}).get("apply"))
    return await run_in_threadpool(company_names.repair, dry_run=not apply)


@router.post("/options-lab/signals/build", dependencies=[Depends(require_token)])
async def options_lab_signals_build(payload: dict[str, Any] = Body(default_factory=dict)):
    """Signals over a range of stored days, and what followed each.

    Two tables, written together. A signal is a claim made from what was
    knowable that day; an outcome is what the market did next. Kept apart so an
    outcome cannot be reached from the condition that selected it -- a signal
    row simply has no forward column to filter on by accident.

    Dry by default.
    """
    from options_lab import signals

    body = payload or {}
    start, end = str(body.get("start") or "").strip(), str(body.get("end") or "").strip()
    if not start or not end:
        raise HTTPException(status_code=400,
                            detail="start and end are required, as YYYY-MM-DD")
    return await run_in_threadpool(
        signals.build_range, start, end,
        underlying=str(body.get("underlying") or "NIFTY").strip().upper(),
        dry_run=not bool(body.get("apply")))


@router.get("/options-lab/studies")
async def options_lab_studies(
    start: str = Query(...),
    end: str = Query(...),
    underlying: str = Query(default="NIFTY"),
):
    """What followed each condition, split by how unusual the condition was.

    Read-only, so unauthenticated like the other probes. It reports n, the
    spread and a difference in standard errors, and calls nothing significant:
    with fifty-nine days and several implicit comparisons, a p-value would be
    decoration.

    Every return it aggregates is an end-of-day mark, and the result says so.
    """
    from options_lab import canonical_store, studies

    try:
        rows = canonical_store.signals_with_outcomes(
            start, end, underlying.strip().upper())
    except canonical_store.CanonicalStoreError as exc:
        return {"ok": False, "stage": "read", "error": str(exc)[:250]}
    if not rows:
        return {"ok": False, "stage": "read",
                "error": "no signals stored in that range"}
    resolved = sum(1 for r in rows if r.get("outcome_version"))
    return {
        "ok": True,
        "range": {"start": start, "end": end, "underlying": underlying},
        "signals": len(rows),
        "with_outcome": resolved,
        "awaiting_horizon": len(rows) - resolved,
        **studies.run_all(rows),
    }


@router.post("/options-lab/market-state/build", dependencies=[Depends(require_token)])
async def options_lab_market_state_build(payload: dict[str, Any] = Body(default_factory=dict)):
    """Describe one stored trading day: volatility, positioning, regime.

    Built only from what was knowable at that close. The variance premium
    against the volatility that followed is deliberately not here -- it is an
    outcome, and a state row carrying it would let a study condition on the
    future and report an edge nobody could have traded.
    """
    from options_lab import market_state

    body = payload or {}
    day = str(body.get("day") or "").strip()
    if not day:
        raise HTTPException(status_code=400, detail="day is required, as YYYY-MM-DD")
    return await run_in_threadpool(
        market_state.build_day, day,
        underlying=str(body.get("underlying") or "NIFTY").strip().upper(),
        dry_run=not bool(body.get("apply")))


@router.post("/options-lab/surfaces/build", dependencies=[Depends(require_token)])
async def options_lab_surfaces_build(payload: dict[str, Any] = Body(default_factory=dict)):
    """Fit and store the volatility surfaces for one stored trading day.

    Reads the canonical observations back rather than re-deriving from NSE, so
    a surface always describes the same numbers a study will join to.

    Dry by default, like every other write here.
    """
    from options_lab import surfaces

    body = payload or {}
    day = str(body.get("day") or "").strip()
    if not day:
        raise HTTPException(status_code=400, detail="day is required, as YYYY-MM-DD")
    underlying = str(body.get("underlying") or "NIFTY").strip().upper() or None
    return await run_in_threadpool(
        surfaces.build_day, day,
        underlying=underlying, dry_run=not bool(body.get("apply")))


@router.post("/options-lab/nse-history/backfill", dependencies=[Depends(require_token)])
async def options_lab_nse_history_backfill(payload: dict[str, Any] = Body(default_factory=dict)):
    """Walk a range of trading days into the warehouse, a chunk at a time.

    Bounded on purpose. Six months of fetching outlives the request, so a call
    does max_days and returns resume_from; calling again with the same range
    continues, because days already holding rows are skipped. The table is the
    only state, so a half-finished run is just a shorter next run.

    Dry by default, like the single-day ingest.
    """
    from options_lab import nse_history

    body = payload or {}
    start, end = str(body.get("start") or "").strip(), str(body.get("end") or "").strip()
    if not start or not end:
        raise HTTPException(status_code=400,
                            detail="start and end are required, as YYYY-MM-DD")
    raw = body.get("underlyings")
    underlyings = {str(u).strip().upper() for u in raw if str(u).strip()} if raw else None
    try:
        max_days = max(1, min(60, int(body.get("max_days") or nse_history.DEFAULT_MAX_DAYS)))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="max_days must be a number")
    return await run_in_threadpool(
        nse_history.backfill, start, end,
        underlyings=underlyings, dry_run=not bool(body.get("apply")),
        max_days=max_days)


@router.post("/options-lab/nse-history/ingest", dependencies=[Depends(require_token)])
async def options_lab_nse_history_ingest(payload: dict[str, Any] = Body(default_factory=dict)):
    """Pull one NSE trading day into the canonical warehouse.

    Defaults to a dry run: pass {"apply": true} to write. A methodology change
    plus an ingest that runs on a bare call is how history gets restated
    without anyone deciding to restate it.

    Token-guarded because unlike the probes this writes.
    """
    from options_lab import nse_history

    body = payload or {}
    day = str(body.get("day") or "").strip()
    if not day:
        raise HTTPException(status_code=400, detail="day is required, as YYYY-MM-DD")
    raw = body.get("underlyings")
    underlyings = {str(u).strip().upper() for u in raw if str(u).strip()} if raw else None
    return await run_in_threadpool(
        nse_history.ingest_day, day,
        underlyings=underlyings, dry_run=not bool(body.get("apply")))


@router.get("/options-lab/live-coverage")
async def options_lab_live_coverage():
    """How much intraday evidence the engine disk holds, and how far back.

    Read-only. Exists because the live snapshots carry bid and ask, and a quote
    that was never stored cannot be fetched again later -- unlike candles.
    How far this reaches back therefore decides whether an execution study is
    possible at all, and nothing was reporting it.
    """
    from options_lab.store import OptionEvidenceStore
    from options_lab.upstox_live import LiveConfig

    def _read():
        store = OptionEvidenceStore(LiveConfig.from_environment().database_path)
        return store.coverage()

    try:
        return {"ok": True, **(await run_in_threadpool(_read))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:250]}


@router.get("/options-lab/nse-history/probe")
async def options_lab_nse_history_probe(
    day: str | None = Query(default=None),
    underlying: str = Query(default="NIFTY"),
):
    """Read one real bhavcopy end to end and report what came out.

    Separate from the intraday collector on purpose. Bhavcopy is end-of-day: it
    carries no path within the day, so anything built on it is close-to-close
    and must not be folded into the 5-30 minute repricing test.

    Read-only, and unauthenticated for the same reason the other probes are --
    it fetches a public NSE file and derives from it, writing nothing.
    """
    from options_lab import nse_history

    return await run_in_threadpool(
        nse_history.probe, (day or "2026-08-21"), underlying.strip().upper())


@router.get("/options-lab/expired-history/probe")
async def options_lab_expired_history_probe(instrument_key: str | None = Query(default=None)):
    """Whether this account can read expired instruments, and how far back.

    Unauthenticated because it is read-only, returns no market data beyond one
    sample candle, and exists to answer a capability question before anyone
    plans a backfill on it. The endpoints behind it are an Upstox paid tier, so
    "can we" is a real question with a real answer rather than an assumption.
    """
    from options_lab import expired_history

    key = (instrument_key or expired_history.NIFTY_KEY).strip()
    return await run_in_threadpool(expired_history.probe, key)


@router.get("/warehouse/company-names/audit")
async def warehouse_company_names_audit():
    """How many master rows carry their ticker instead of a name."""
    from financial_warehouse_completion import company_names

    return await run_in_threadpool(company_names.audit)


@router.post("/options-lab/price", dependencies=[Depends(require_token)])
def options_lab_price(payload: dict[str, Any] = Body(default={})):
    """Run the provider-neutral local options model without placing an order."""
    try:
        return price_option_snapshot(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/options-lab/validation/dashboard",
    dependencies=[Depends(require_token)],
)
async def options_lab_validation_dashboard():
    """Admin-only, read-only evidence for the frozen V1 validation protocol."""
    from options_lab.dashboard import validation_dashboard

    return await run_in_threadpool(validation_dashboard)


@router.post("/hedge-fund-lab/calculate/{kind}")
async def hedge_fund_lab_calculate(kind: str, payload: dict[str, Any] = Body(default={})):
    """Every strategy calculation runs here, never in the browser."""
    from hedge_fund_lab.production import calculate

    return await run_in_threadpool(calculate, kind, payload or {})


@router.post("/hedge-fund-lab/backtest/{strategy_id}")
async def hedge_fund_lab_backtest(strategy_id: str, payload: dict[str, Any] = Body(default={})):
    """Run a bounded, point-in-time research backtest from warehouse data."""
    from hedge_fund_lab.production import backtest

    return await run_in_threadpool(backtest, strategy_id, payload or {})


# ---------------------------------------------------------------------------
# Admin Strategy Lab — governed medium-horizon systematic research.
# The intelligence service itself is token-protected; the Node proxy also
# enforces the signed-in AGI administrator before exposing these endpoints.
# ---------------------------------------------------------------------------


@router.get("/strategy-lab/health")
async def strategy_lab_health():
    from strategy_lab.production import health
    return health()


@router.get("/strategy-lab/dashboard")
async def strategy_lab_dashboard(limit: int = 5):
    from strategy_lab.production import dashboard
    bounded_limit = max(1, min(int(limit or 5), 20))
    return await run_in_threadpool(dashboard, limit=bounded_limit)


@router.get("/strategy-lab/paper-validation")
async def strategy_lab_paper_validation():
    from strategy_lab.paper import board
    return await run_in_threadpool(board)


@router.get("/strategy-lab/strategy/{strategy_id}")
async def strategy_lab_strategy(strategy_id: str):
    from strategy_lab.production import strategy
    return strategy(strategy_id)


@router.get("/strategy-lab/scan/{strategy_id}")
async def strategy_lab_scan(strategy_id: str, limit: int = 20):
    from strategy_lab.production import scan
    bounded_limit = max(1, min(int(limit or 20), 100))
    return await run_in_threadpool(scan, strategy_id, limit=bounded_limit)


@router.post("/strategy-lab/backtest/{strategy_id}")
async def strategy_lab_backtest(strategy_id: str, payload: dict[str, Any] = Body(default={})):
    from strategy_lab.production import backtest
    return await run_in_threadpool(backtest, strategy_id, payload or {})


@router.get("/strategy-lab/operating-system")
async def strategy_lab_operating_system(run_limit: int = 10):
    """Admin evidence board for immutable strategies, runs and capital gates."""
    from strategy_lab.operating_system import catalog
    bounded = max(1, min(int(run_limit or 10), 100))
    return await run_in_threadpool(catalog, run_limit=bounded)


@router.get("/strategy-lab/definitions")
async def strategy_lab_definitions():
    from strategy_lab.definitions import all_definitions
    return {"ok": True, "definitions": [item.to_dict() for item in all_definitions()]}


@router.get("/strategy-lab/definition/{strategy_id}")
async def strategy_lab_definition(strategy_id: str):
    from strategy_lab.operating_system import definition
    try:
        return await run_in_threadpool(definition, strategy_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/strategy-lab/registry/sync", dependencies=[Depends(require_token)])
async def strategy_lab_registry_sync(payload: dict[str, Any] = Body(default={})):
    """Seal code-defined versions into the immutable warehouse registry."""
    from strategy_lab.operating_system import sync_registry
    return await run_in_threadpool(sync_registry, actor=str((payload or {}).get("actor") or "admin"))


@router.post("/strategy-lab/research/{strategy_id}", dependencies=[Depends(require_token)])
async def strategy_lab_run_research(strategy_id: str, payload: dict[str, Any] = Body(default={})):
    """Run bounded factor research or a standardized point-in-time backtest."""
    from strategy_lab.operating_system import run_research
    try:
        return await run_in_threadpool(run_research, strategy_id, payload or {})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/strategy-lab/capital-decision/{strategy_id}")
async def strategy_lab_capital_decision(strategy_id: str):
    """Fail-closed capital decision; this endpoint never places an order."""
    from strategy_lab.operating_system import capital_decision
    try:
        return await run_in_threadpool(capital_decision, strategy_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/strategy-lab/data-readiness")
async def strategy_lab_data_readiness(as_of: str | None = None):
    """Read-only point-in-time, universe, action and price readiness evidence."""
    from strategy_lab.prospective import readiness
    return await run_in_threadpool(readiness, as_of)


@router.post("/strategy-lab/prospective/capture", dependencies=[Depends(require_token)])
async def strategy_lab_prospective_capture(payload: dict[str, Any] = Body(default={})):
    """Capture facts from now forward; legacy facts are never backdated."""
    from strategy_lab.prospective import capture
    try:
        return await run_in_threadpool(
            capture,
            as_of=(payload or {}).get("as_of"),
            actor=str((payload or {}).get("actor") or "daily_validation_cron"),
            confirm=(payload or {}).get("confirm"),
            dry_run=bool((payload or {}).get("dry_run", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Valuation Intelligence Terminal — market multiples plus AGI interpretation.
# ---------------------------------------------------------------------------


@router.get("/valuation-terminal/health")
async def valuation_terminal_health():
    """Migrated: Warehouse → Unified Valuation Engine → Terminal."""
    from valuation_engine.terminal import health as terminal_health

    return terminal_health()


@router.get("/valuation-terminal/overview")
async def valuation_terminal_overview():
    """Market dashboard deferred (PR #492). Terminal is company-first now."""
    return {
        "ok": True,
        "migrated": True,
        "engine": "unified_valuation_engine",
        "version": "3.0",
        "note": "Market dashboard deferred. Use /v1/valuation-engine/terminal/company/{symbol}.",
        "companies_covered": None,
    }


@router.get("/valuation-terminal/sectors")
async def valuation_terminal_sectors():
    from valuation_terminal.production import sectors

    return sectors()


@router.get("/valuation-terminal/sector/{sector}")
async def valuation_terminal_sector(sector: str):
    from valuation_terminal.production import sector_intelligence

    return sector_intelligence(sector)


@router.get("/valuation-terminal/sector-intelligence")
async def valuation_terminal_all_sectors():
    from valuation_terminal.production import all_sector_intelligence

    return all_sector_intelligence()


@router.get("/valuation-terminal/companies")
async def valuation_terminal_companies(
    q: str = "",
    sector: str | None = None,
    industry: str | None = None,
    sort: str = "market_cap",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 50,
    pe_max: float | None = None,
    pb_max: float | None = None,
    ev_ebitda_max: float | None = None,
    roe_min: float | None = None,
    dividend_yield_min: float | None = None,
    market_cap_min: float | None = None,
    upside_min: float | None = None,
    coverage_min: float | None = None,
):
    from valuation_terminal.production import companies

    filters = {
        k: v
        for k, v in {
            "pe_max": pe_max,
            "pb_max": pb_max,
            "ev_ebitda_max": ev_ebitda_max,
            "roe_min": roe_min,
            "dividend_yield_min": dividend_yield_min,
            "market_cap_min": market_cap_min,
            "upside_min": upside_min,
            "coverage_min": coverage_min,
        }.items()
        if v is not None
    }
    return companies(
        q=q,
        sector=sector,
        industry=industry,
        sort=sort,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
        filters=filters,
    )


@router.get("/valuation-terminal/company/{ticker}")
async def valuation_terminal_company(
    ticker: str,
    window: str = "5Y",
    peer_limit: int = 12,
    refresh: bool = False,
):
    """Serve the stored company pack. Live warehouse compute stays on POST /snapshot."""
    from valuation_engine.snapshot_store import serve_company_pack

    return await run_in_threadpool(
        serve_company_pack,
        ticker,
        window=window,
        peer_limit=peer_limit,
        refresh=refresh,
    )


@router.get("/valuation-terminal/peers/{ticker}")
async def valuation_terminal_peers(ticker: str):
    from valuation_terminal.production import peers

    return peers(ticker)


@router.get("/valuation-terminal/insights")
async def valuation_terminal_insights():
    from valuation_terminal.production import insights

    return insights()


@router.get("/valuation-terminal/explain/{metric}")
async def valuation_terminal_explain(metric: str):
    from valuation_terminal.production import metric_explainer

    return metric_explainer(metric)


@router.get("/valuation-terminal/statistics")
async def valuation_terminal_statistics():
    from valuation_terminal.production import sector_statistics

    return sector_statistics()


@router.get("/valuation-terminal/overrides/audit")
async def valuation_terminal_override_audit(limit: int = 100, ticker: str | None = None):
    from valuation_terminal.overrides import audit_log, summary

    return {**audit_log(limit=limit, ticker=ticker), "summary": summary()}


@router.post("/valuation-terminal/overrides")
async def valuation_terminal_set_override(payload: dict[str, Any] = Body(default={})):
    """Admin: override an imported value. The import is never overwritten."""
    from valuation_terminal.overrides import set_override
    from valuation_terminal.store import get as get_row

    body = payload or {}
    ticker = str(body.get("ticker") or "")
    field = str(body.get("field") or "")
    imported = (get_row(ticker) or {}).get(field)
    return set_override(
        ticker,
        field,
        body.get("value"),
        actor=str(body.get("actor") or "admin"),
        reason=str(body.get("reason") or ""),
        imported_value=imported,
    )


@router.post("/valuation-terminal/overrides/clear")
async def valuation_terminal_clear_override(payload: dict[str, Any] = Body(default={})):
    from valuation_terminal.overrides import clear_override

    body = payload or {}
    return clear_override(
        str(body.get("ticker") or ""),
        str(body.get("field") or ""),
        actor=str(body.get("actor") or "admin"),
        reason=str(body.get("reason") or "manual revert"),
    )


@router.post("/valuation-terminal/ingest")
async def valuation_terminal_ingest(payload: dict[str, Any] = Body(default={})):
    """Retired — terminal reads the warehouse via the Unified Valuation Engine."""
    return {
        "ok": False,
        "retired": True,
        "error": "json_loader_retired",
        "note": (
            "Committed Yahoo JSON ingest is retired. Valuation Terminal reads "
            "Warehouse → Unified Valuation Engine. Refresh warehouse data instead."
        ),
        "engine": "unified_valuation_engine",
        "version": "3.0",
    }


# ---------------------------------------------------------------------------
# Company Identity Service — canonical Capital IQ classification.
# Every engine consumes this immutable object instead of inferring identity.
# ---------------------------------------------------------------------------


@router.get("/company-identity/health")
async def company_identity_health():
    from company_identity.service import health

    return health()


@router.post("/company-identity/metadata")
async def company_identity_metadata(payload: dict[str, Any] = Body(default={})):
    """Company Metadata Router — direct Capital IQ field lookup, no reasoning."""
    from company_identity.metadata_router import route

    body = payload or {}
    hit = route(str(body.get("question") or body.get("q") or ""))
    if not hit:
        return {"ok": False, "routed": False, "reason": "not_a_company_metadata_question"}
    return {"routed": True, **hit}


@router.get("/company-identity/{ticker}")
async def company_identity_lookup(ticker: str):
    from company_identity.service import resolve

    identity = resolve(ticker)
    if not identity.resolved:
        return {"ok": False, "error": "unresolved_company", "ticker": ticker.upper()}
    return {"ok": True, **identity.to_dict()}


@router.post("/company-identity/validate")
async def company_identity_validate(payload: dict[str, Any] = Body(default={})):
    """Check text or a classification claim against the canonical identity."""
    from company_identity.guard import validate_classification, validate_text
    from company_identity.service import resolve

    body = payload or {}
    identity = resolve(str(body.get("ticker") or body.get("company") or ""))
    if not identity.resolved:
        return {"ok": False, "error": "unresolved_company"}
    reports = {}
    if body.get("text"):
        reports["text"] = validate_text(identity, str(body["text"])).to_dict()
    if any(body.get(k) for k in ("sector", "industry", "business_type", "industry_dna")):
        reports["classification"] = validate_classification(
            identity,
            sector=body.get("sector"),
            industry=body.get("industry"),
            business_type=body.get("business_type"),
            industry_dna=body.get("industry_dna"),
        ).to_dict()
    return {
        "ok": all(r.get("ok") for r in reports.values()) if reports else True,
        "identity": identity.context(),
        "reports": reports,
    }


@router.get("/system/intelligence-stack")
async def system_intelligence_stack():
    """Inventory of integrated Macro / Sector / Market / Research programmes."""
    from system_integration.production import health, inventory

    return {**health(), "detail": inventory()}


@router.post("/system/intelligence-stack/bootstrap")
async def system_intelligence_stack_bootstrap(payload: dict[str, Any] = Body(default={})):
    """Ops only — soft-publish catalog RIH hubs (and optional MKFI). Never Ask."""
    from system_integration.production import bootstrap

    return bootstrap(
        publish_rih=bool(payload.get("publish_rih", True)),
        publish_mkfi=bool(payload.get("publish_mkfi", False)),
    )


@router.get("/mission-control/quality-gates")
async def mission_control_quality_gates():
    from mission_control.production import quality_gates

    return quality_gates()


@router.get("/mission-control/report")
async def mission_control_report():
    from mission_control.production import system_report

    return system_report(ioc_service=getattr(_ui, "ioc", None) or _ioc)


@router.post("/mission-control/acknowledge")
async def mission_control_acknowledge(payload: dict[str, Any] = Body(default={})):
    from mission_control.production import acknowledge_alert

    alert_id = str(payload.get("alert_id") or payload.get("id") or "").strip()
    if not alert_id:
        raise HTTPException(status_code=400, detail="alert_id required")
    return acknowledge_alert(alert_id)


# --- Investment Office V1 (executive operating cockpit; additive aggregate) ---


@router.get("/investment-office/health")
async def investment_office_health():
    from investment_office.production import health

    return health()


@router.get("/investment-office/dashboard")
async def investment_office_dashboard():
    from investment_office.production import dashboard

    # Soft aggregate only — do not call UiService.home() (would recurse into IO package)
    return dashboard(ui_home=None, ioc_service=getattr(_ui, "ioc", None))


@router.get("/investment-office/quality-gates")
async def investment_office_quality_gates():
    from investment_office.production import quality_gates

    return quality_gates()


@router.post("/investment-office/package")
async def investment_office_package(payload: dict[str, Any] = Body(default={})):
    from investment_office.production import package_for_ask_agi

    return package_for_ask_agi(
        str(payload.get("query") or ""),
        ticker=payload.get("ticker"),
    )


@router.get("/investment-office/company/{ticker}")
async def investment_office_company(ticker: str, question: str | None = None, package_type: str | None = None):
    """IO-01: Institutional Research Package for a company (orchestration only)."""
    from investment_office.production import company

    return company(ticker, question=question, package_type=package_type)


@router.post("/investment-office/query")
async def investment_office_query(payload: dict[str, Any] = Body(default={})):
    """IO-01: route a question and assemble IRP from FIRE modules."""
    from investment_office.production import query

    ticker = str(payload.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    return query(
        ticker=ticker,
        question=str(payload.get("question") or ""),
        package_type=payload.get("package_type") or payload.get("package"),
    )


# --- AGI V1.3 Institutional Morning Office (admin desk; monitoring only) ---


@router.get("/investment-office/overview")
async def investment_office_overview_v13():
    from investment_office.production import morning_overview

    return morning_overview()


@router.get("/investment-office/morning-office")
async def investment_office_morning_office_v13():
    from investment_office.production import morning_office

    return morning_office()


@router.get("/investment-office/daily-brief")
async def investment_office_daily_brief_v13():
    from investment_office.production import daily_brief

    return daily_brief()


@router.get("/investment-office/research-queue")
async def investment_office_research_queue_v13():
    from investment_office.production import research_queue_v13

    return research_queue_v13()


@router.get("/investment-office/opportunities")
async def investment_office_opportunities_v13():
    from investment_office.production import opportunities_v13

    return opportunities_v13()


@router.get("/investment-office/market-summary")
async def investment_office_market_summary_v13():
    from investment_office.production import market_summary_v13

    return market_summary_v13()


@router.get("/investment-office/macro")
async def investment_office_macro_v13():
    from investment_office.production import macro_v13

    return macro_v13()


@router.get("/investment-office/calendar")
async def investment_office_calendar_v13():
    from investment_office.production import calendar_v13

    return calendar_v13()


@router.get("/investment-office/portfolio-monitor")
async def investment_office_portfolio_monitor_v13():
    from investment_office.production import portfolio_monitor_v13

    return portfolio_monitor_v13()


@router.get("/investment-office/sector-monitor")
async def investment_office_sector_monitor_v13():
    from investment_office.production import sector_monitor_v13

    return sector_monitor_v13()


@router.get("/investment-office/metrics")
async def investment_office_metrics_v13():
    from investment_office.production import metrics_v13

    return metrics_v13()


@router.get("/investment-office/snapshot")
async def investment_office_snapshot_v13():
    """Snapshot metadata — no heavy recompute."""
    from investment_office.production import snapshot_status

    return snapshot_status()


@router.get("/investment-office/system-health")
async def investment_office_system_health_v13():
    """Live operational status (seconds) — ICF/IEP/CGL off path."""
    from investment_office.production import system_health_v13

    return system_health_v13()


@router.post("/investment-office/refresh")
async def investment_office_refresh_v13(payload: dict[str, Any] = Body(default={})):
    """Queue morning snapshot rebuild (async). Pass wait=true for ops sync."""
    from investment_office.production import refresh_morning_office

    body = payload or {}
    wait = bool(body.get("wait") or body.get("sync"))
    return refresh_morning_office(wait=wait)


@router.post("/investment-office/generate-morning-brief")
async def investment_office_generate_morning_brief_v13(
    payload: dict[str, Any] = Body(default={}),
):
    from investment_office.production import generate_morning_brief

    _ = payload
    return generate_morning_brief()


# --- CIO-01 Comparative Intelligence Office (cross-company orchestration; additive) ---


@router.get("/comparative-intelligence/health")
async def comparative_intelligence_health():
    from comparative_intelligence.production import health

    return health()


@router.get("/comparative-intelligence/dashboard")
async def comparative_intelligence_dashboard():
    from comparative_intelligence.production import dashboard

    return dashboard()


@router.post("/comparative-intelligence/compare")
async def comparative_intelligence_compare(payload: dict[str, Any] = Body(default={})):
    """CIO-01: side-by-side Institutional Comparison Report from FIRE outputs."""
    from comparative_intelligence.production import compare_companies

    tickers = payload.get("tickers") or payload.get("companies") or []
    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.replace(",", " ").split() if t.strip()]
    if not isinstance(tickers, list) or len(tickers) < 2:
        raise HTTPException(status_code=400, detail="tickers requires at least two symbols")
    return compare_companies(
        [str(t) for t in tickers],
        question=payload.get("question"),
        comparison_type=payload.get("comparison_type") or payload.get("type"),
        modules=payload.get("modules"),
    )


@router.post("/comparative-intelligence/query")
async def comparative_intelligence_query(payload: dict[str, Any] = Body(default={})):
    """CIO-01: route a comparative question and assemble ICR."""
    from comparative_intelligence.production import query

    tickers = payload.get("tickers") or payload.get("companies")
    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.replace(",", " ").split() if t.strip()]
    try:
        return query(
            tickers=list(tickers) if isinstance(tickers, list) else None,
            question=str(payload.get("question") or ""),
            comparison_type=payload.get("comparison_type") or payload.get("type"),
            modules=payload.get("modules"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/comparative-intelligence", response_class=HTMLResponse)
async def admin_comparative_intelligence():
    from comparative_intelligence.production import admin_page

    return HTMLResponse(admin_page())


# --- Office SDK — shared application office contract (additive) ---


@router.get("/office-sdk/health")
async def office_sdk_health():
    from office_sdk.production import health

    return health()


@router.get("/office-sdk/dashboard")
async def office_sdk_dashboard():
    from office_sdk.production import dashboard

    return dashboard()


@router.get("/office-sdk/catalog")
async def office_sdk_catalog():
    from office_sdk.production import office_catalog

    return office_catalog()


@router.get("/office-sdk/domains")
async def office_sdk_domains():
    from office_sdk.production import domains

    return domains()


@router.post("/office-sdk/invoke")
async def office_sdk_invoke(payload: dict[str, Any] = Body(default={})):
    """Dispatch a shared OfficeRequest to a live office (io-01 / cio-01)."""
    from office_sdk.production import invoke

    result = invoke(payload or {})
    if result.get("ok") is False and result.get("error"):
        # Keep 200 for planned/unknown offices with structured error; 400 for missing office_id shape
        if "not dispatchable" in str(result.get("error")):
            raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/admin/office-sdk", response_class=HTMLResponse)
async def admin_office_sdk():
    from office_sdk.production import admin_page

    return HTMLResponse(admin_page())


# --- PO-01 Portfolio Office (canonical portfolio state; additive) ---
# NOTE: /v1/portfolio/* is reserved by the existing Portfolio Ideas OS.
# PO-01 is exposed under /v1/portfolio-office/* to remain additive.


@router.get("/portfolio-office/health")
async def portfolio_office_health():
    from portfolio_office.production import health

    return health()


@router.get("/portfolio-office/dashboard")
async def portfolio_office_dashboard():
    from portfolio_office.production import dashboard

    return dashboard()


@router.get("/portfolio-office/{portfolio_id}")
async def portfolio_office_get(portfolio_id: str):
    from portfolio_office.production import get_portfolio

    result = get_portfolio(portfolio_id)
    if result.get("ok") is False and "not found" in str(result.get("error") or ""):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/portfolio-office/{portfolio_id}/holdings")
async def portfolio_office_holdings(portfolio_id: str):
    from portfolio_office.production import get_holdings

    result = get_holdings(portfolio_id)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/portfolio-office/{portfolio_id}/exposures")
async def portfolio_office_exposures(portfolio_id: str):
    from portfolio_office.production import get_exposures

    result = get_exposures(portfolio_id)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/portfolio-office/{portfolio_id}/quality")
async def portfolio_office_quality(portfolio_id: str):
    from portfolio_office.production import get_quality

    result = get_quality(portfolio_id)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/portfolio-office/{portfolio_id}/concentration")
async def portfolio_office_concentration(portfolio_id: str):
    from portfolio_office.production import get_concentration

    result = get_concentration(portfolio_id)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/portfolio-office")
async def portfolio_office_create(payload: dict[str, Any] = Body(default={})):
    from portfolio_office.production import create

    result = create(payload or {})
    if result.get("ok") is False:
        raise HTTPException(status_code=400, detail=result.get("error") or "create failed")
    return result


@router.post("/portfolio-office/{portfolio_id}/snapshot")
async def portfolio_office_snapshot_route(portfolio_id: str, payload: dict[str, Any] = Body(default={})):
    from portfolio_office.production import snapshot

    result = snapshot(portfolio_id, payload or {})
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/admin/portfolio-office", response_class=HTMLResponse)
async def admin_portfolio_office():
    from portfolio_office.production import admin_page

    return HTMLResponse(admin_page())


# --- PEB-01 Platform Event Bus (infrastructure; additive) ---


@router.get("/platform/events/health")
async def platform_events_health():
    from platform_event_bus.production import health

    return health()


@router.get("/platform/events")
async def platform_events_list(limit: int = 50):
    from platform_event_bus.production import list_events

    return list_events(limit=limit)


@router.get("/platform/events/types")
async def platform_events_types():
    from platform_event_bus.production import list_types

    return list_types()


@router.get("/platform/events/statistics")
async def platform_events_statistics():
    from platform_event_bus.production import statistics

    return statistics()


@router.get("/admin/platform-event-bus", response_class=HTMLResponse)
async def admin_platform_event_bus():
    from platform_event_bus.production import admin_page

    return HTMLResponse(admin_page())


# --- WO-01 Watchlist Office (research queue; event-driven; additive) ---


@router.get("/watchlist-office/health")
async def watchlist_office_health():
    from watchlist_office.production import health

    return health()


@router.get("/watchlist-office/dashboard")
async def watchlist_office_dashboard():
    from watchlist_office.production import dashboard

    return dashboard()


@router.get("/watchlist-office/{watchlist_id}")
async def watchlist_office_get(watchlist_id: str):
    from watchlist_office.production import get_watchlist

    result = get_watchlist(watchlist_id)
    if result.get("ok") is False and "not found" in str(result.get("error") or ""):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/watchlist-office/{watchlist_id}/queue")
async def watchlist_office_queue(watchlist_id: str):
    from watchlist_office.production import get_queue

    result = get_queue(watchlist_id)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/watchlist-office")
async def watchlist_office_create(payload: dict[str, Any] = Body(default={})):
    from watchlist_office.production import create

    result = create(payload or {})
    if result.get("ok") is False:
        raise HTTPException(status_code=400, detail=result.get("error") or "create failed")
    return result


@router.post("/watchlist-office/{watchlist_id}/companies")
async def watchlist_office_add(watchlist_id: str, payload: dict[str, Any] = Body(default={})):
    from watchlist_office.production import add

    result = add(watchlist_id, payload or {})
    if result.get("ok") is False:
        raise HTTPException(status_code=400, detail=result.get("error") or "add failed")
    return result


@router.delete("/watchlist-office/{watchlist_id}/companies/{ticker}")
async def watchlist_office_remove(watchlist_id: str, ticker: str):
    from watchlist_office.production import remove

    result = remove(watchlist_id, ticker)
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.patch("/watchlist-office/{watchlist_id}/companies/{ticker}")
async def watchlist_office_patch(watchlist_id: str, ticker: str, payload: dict[str, Any] = Body(default={})):
    from watchlist_office.production import patch_entry

    result = patch_entry(watchlist_id, ticker, payload or {})
    if result.get("ok") is False:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/admin/watchlist-office", response_class=HTMLResponse)
async def admin_watchlist_office():
    from watchlist_office.production import admin_page

    return HTMLResponse(admin_page())


# --- CW-01 Company Workspace (primary company UX; presentation only; additive) ---


@router.get("/company-workspace/health")
async def company_workspace_health():
    from company_workspace.production import health

    return health()


@router.get("/company-workspace/dashboard")
async def company_workspace_dashboard():
    from company_workspace.production import dashboard

    return dashboard()


@router.get("/company-workspace/{ticker}")
async def company_workspace_get(ticker: str, q: str | None = None):
    from company_workspace.production import workspace

    result = workspace(ticker, question=q)
    if result.get("ok") is False and result.get("enabled") is False:
        raise HTTPException(status_code=503, detail="company workspace disabled")
    return result


@router.get("/company-workspace/{ticker}/timeline")
async def company_workspace_timeline(
    ticker: str,
    event_type: str | None = None,
    source: str | None = None,
    q: str | None = None,
):
    from company_workspace.production import timeline

    return timeline(ticker, event_type=event_type, source=source, query=q)


@router.get("/company-workspace/{ticker}/research")
async def company_workspace_research(ticker: str):
    from company_workspace.production import research

    return research(ticker)


@router.get("/company-workspace/{ticker}/evidence")
async def company_workspace_evidence(ticker: str, q: str | None = None):
    from company_workspace.production import evidence

    return evidence(ticker, query=q)


@router.get("/company-workspace/{ticker}/search")
async def company_workspace_search(ticker: str, q: str, scope: str = "all"):
    from company_workspace.production import search

    return search(ticker, q, scope=scope)


@router.get("/admin/company-workspace", response_class=HTMLResponse)
async def admin_company_workspace():
    from company_workspace.production import admin_page

    return HTMLResponse(admin_page())


# --- IST-01 Institutional Stress Tests (orchestration exams; additive) ---


@router.get("/institutional-stress-tests/health")
async def institutional_stress_tests_health():
    from institutional_stress_tests.production import health

    return health()


@router.get("/institutional-stress-tests/dashboard")
async def institutional_stress_tests_dashboard():
    from institutional_stress_tests.production import dashboard

    return dashboard()


@router.post("/institutional-stress-tests/run")
async def institutional_stress_tests_run(payload: dict[str, Any] = Body(default={})):
    from institutional_stress_tests.production import run

    body = payload or {}
    return run(
        str(body.get("case_id") or body.get("case") or "IST-01"),
        prebuilt=body.get("prebuilt"),
        answers=body.get("answers"),
        final_view=body.get("final_view"),
        modules_filter=body.get("modules_filter"),
        write_report=bool(body.get("write_report")),
        corpus=body.get("corpus"),
        fixture_answers=body.get("fixture_answers"),
    )


@router.post("/institutional-stress-tests/run-raw")
async def institutional_stress_tests_run_raw(payload: dict[str, Any] = Body(default={})):
    """IST-02 — raw evidence institutional research validation."""
    from institutional_stress_tests.production import run_raw_evidence

    body = payload or {}
    return run_raw_evidence(
        str(body.get("case_id") or body.get("case") or "IST-02"),
        corpus=body.get("corpus"),
        fixture_answers=body.get("fixture_answers"),
    )


@router.get("/institutional-stress-tests/report")
async def institutional_stress_tests_report(case_id: str = "IST-01"):
    from institutional_stress_tests.production import report

    return report(case_id)


@router.get("/admin/institutional-stress-tests", response_class=HTMLResponse)
async def admin_institutional_stress_tests():
    from institutional_stress_tests.production import admin_page

    return HTMLResponse(admin_page())


# --- IBS-01 AGI Institutional Benchmark Suite (permanent; additive) ---


@router.get("/institutional-benchmarks/health")
async def institutional_benchmarks_health():
    from institutional_benchmarks.production import health

    return health()


@router.get("/institutional-benchmarks/dashboard")
async def institutional_benchmarks_dashboard():
    from institutional_benchmarks.production import dashboard

    return dashboard()


@router.get("/institutional-benchmarks")
async def institutional_benchmarks_list(sector: str | None = None):
    from institutional_benchmarks.production import list_benchmarks

    return list_benchmarks(sector=sector)


@router.get("/institutional-benchmarks/{case_id}")
async def institutional_benchmarks_get(case_id: str, cutoff: str | None = None):
    from institutional_benchmarks.production import get_benchmark

    try:
        return get_benchmark(case_id, cutoff=cutoff)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/institutional-benchmarks/run")
async def institutional_benchmarks_run(payload: dict[str, Any] = Body(default={})):
    from institutional_benchmarks.production import run

    body = payload or {}
    case_id = str(body.get("case_id") or body.get("case") or "").strip()
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id required")
    try:
        return run(
            case_id,
            cutoff=body.get("cutoff") or body.get("historical_cutoff"),
            fixture_answers=body.get("fixture_answers"),
            consistency=bool(body.get("consistency", True)),
            include_consensus=bool(body.get("include_consensus")),
            house_notes=body.get("house_notes"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/institutional-benchmarks/run-all")
async def institutional_benchmarks_run_all(payload: dict[str, Any] = Body(default={})):
    from institutional_benchmarks.production import run_all_benchmarks, run_sector_benchmarks

    body = payload or {}
    cutoff = body.get("cutoff") or body.get("historical_cutoff")
    sector = body.get("sector")
    if sector:
        return run_sector_benchmarks(str(sector), cutoff=cutoff)
    return run_all_benchmarks(cutoff=cutoff)


@router.get("/admin/institutional-benchmarks", response_class=HTMLResponse)
async def admin_institutional_benchmarks():
    from institutional_benchmarks.production import admin_page

    return HTMLResponse(admin_page())


# --- E2E-01 Institutional Product Experience Validation (not an engine; additive) ---


@router.get("/product-experience/health")
async def product_experience_health():
    from product_experience_validation.production import health

    return health()


@router.get("/product-experience/dashboard")
async def product_experience_dashboard():
    from product_experience_validation.production import dashboard

    return dashboard()


@router.get("/product-experience/report")
async def product_experience_report():
    from product_experience_validation.production import report

    return report()


@router.post("/product-experience/run")
async def product_experience_run(payload: dict[str, Any] = Body(default={})):
    from product_experience_validation.production import run

    return run(payload or {})


@router.get("/admin/product-experience", response_class=HTMLResponse)
async def admin_product_experience():
    from product_experience_validation.production import admin_page

    return HTMLResponse(admin_page())


# --- RH-01 AGI Release Health (single release gate dashboard; additive) ---


@router.get("/release-health/health")
async def release_health_health():
    from release_health.production import health

    return health()


@router.get("/release-health/dashboard")
async def release_health_dashboard(refresh: bool = False):
    from release_health.production import dashboard

    return dashboard(refresh=refresh)


@router.post("/release-health/run")
async def release_health_run(payload: dict[str, Any] = Body(default={})):
    from release_health.production import run

    return run(payload or {})


@router.get("/admin/release-health-engine", response_class=HTMLResponse)
async def admin_release_health_engine():
    from release_health.production import admin_page

    return HTMLResponse(admin_page())


# --- IRE-02 Institutional Reporting Engine + Reason Composer (deterministic; no LLM) ---


@router.get("/report/health")
async def institutional_report_health():
    from institutional_reporting.production import health

    return health()


@router.post("/report/company")
async def institutional_report_company(payload: dict[str, Any] = Body(default={})):
    from institutional_reporting.production import compose_company_report

    body = dict(payload or {})
    include_reasons = body.pop("include_reasons", True)
    return compose_company_report(body, include_reasons=bool(include_reasons))


@router.get("/report/company/{ticker}")
async def institutional_report_company_ticker(
    ticker: str,
    include_reasons: bool = True,
):
    from institutional_reporting.production import report_for_ticker

    return report_for_ticker(ticker, include_reasons=include_reasons)


# --- IDS-01 Institutional Decision System (deterministic decisions; no LLM) ---


@router.get("/decision/health")
async def institutional_decision_health():
    from institutional_decision.production import health

    return health()


@router.post("/decision/company")
async def institutional_decision_company(payload: dict[str, Any] = Body(default={})):
    from institutional_decision.production import decide_company

    return decide_company(payload or {})


@router.get("/decision/company/{ticker}")
async def institutional_decision_company_ticker(
    ticker: str,
    include_history: bool = False,
    include_calibration: bool = True,
    include_drift: bool = True,
):
    from institutional_decision.production import get_company_decision

    return get_company_decision(
        ticker,
        include_history=include_history,
        include_calibration=include_calibration,
        include_drift=include_drift,
    )


# --- IDS-02 Decision Calibration & Explainability ---


@router.get("/calibration/health")
async def institutional_calibration_health():
    from institutional_calibration.production import health

    return health()


@router.post("/calibration/company")
async def institutional_calibration_company(payload: dict[str, Any] = Body(default={})):
    from institutional_calibration.production import calibrate_company

    return calibrate_company(payload or {})


@router.get("/calibration/company/{ticker}")
async def institutional_calibration_company_ticker(
    ticker: str,
    include_calibration: bool = True,
    include_drift: bool = True,
):
    from institutional_calibration.production import get_calibrated_decision

    return get_calibrated_decision(
        ticker,
        include_calibration=include_calibration,
        include_drift=include_drift,
    )


# --- KG-01 Institutional Knowledge Graph (single-company; deterministic) ---


@router.get("/graph/health")
async def institutional_graph_health():
    from institutional_graph.production import health

    return health()


@router.post("/graph/company")
async def institutional_graph_company(payload: dict[str, Any] = Body(default={})):
    from institutional_graph.production import graph_company

    return graph_company(payload or {})


@router.get("/graph/company/{ticker}")
async def institutional_graph_company_ticker(
    ticker: str,
    include_paths: bool = False,
    include_inference: bool = True,
):
    from institutional_graph.production import get_company_graph

    return get_company_graph(
        ticker,
        include_paths=include_paths,
        include_inference=include_inference,
        rebuild=True,
    )


# --- FG-01 Forecast & Scenario Graph (deterministic propagation; no ML) ---


@router.get("/scenario/health")
async def institutional_forecast_health():
    from institutional_forecasting.production import health

    return health()


@router.post("/scenario/company")
async def institutional_forecast_company(payload: dict[str, Any] = Body(default={})):
    from institutional_forecasting.production import scenario_company

    return scenario_company(payload or {})


@router.get("/scenario/company/{ticker}")
async def institutional_forecast_company_ticker(
    ticker: str,
    include_graph: bool = False,
    include_propagation: bool = True,
):
    from institutional_forecasting.production import get_company_scenarios

    return get_company_scenarios(
        ticker,
        include_graph=include_graph,
        include_propagation=include_propagation,
        rebuild=True,
    )


# --- IO-01 Institutional Observation Engine (proactive; hysteresis; no LLM) ---


@router.get("/observation/health")
async def institutional_observation_health():
    from institutional_observation.production import health

    return health()


@router.post("/observation/company")
async def institutional_observation_company(payload: dict[str, Any] = Body(default={})):
    from institutional_observation.production import observation_company

    return observation_company(payload or {})


@router.get("/observation/company/{ticker}")
async def institutional_observation_company_ticker(
    ticker: str,
    critical_only: bool = False,
    include_decision_changes: bool = True,
    refresh: bool = False,
    inject: str | None = None,
):
    from institutional_observation.production import get_company_observations, observe_company

    events = None
    if inject:
        key = str(inject).strip().lower()
        events = [{"key": key, "detail": f"Injected institutional event: {key}", "magnitude": 1.0}]
    if refresh or inject:
        return observe_company(
            ticker,
            critical_only=critical_only,
            include_decision_changes=include_decision_changes,
            force_events=events,
        )
    return get_company_observations(
        ticker,
        critical_only=critical_only,
        include_decision_changes=include_decision_changes,
        observe=True,
    )

# --- PKG-01 / Phase 4.1 PO-01 Portfolio Knowledge Graph ---


@router.get("/portfolio-graph/health")
async def institutional_portfolio_graph_health():
    from institutional_portfolio.production import health

    return health()


@router.post("/portfolio-graph")
async def institutional_portfolio_graph_post(payload: dict[str, Any] = Body(default={})):
    from institutional_portfolio.production import portfolio_graph_api

    return portfolio_graph_api(payload or {})


@router.get("/portfolio-graph/{portfolio_id}")
async def institutional_portfolio_graph_get(
    portfolio_id: str,
    include_company_graphs: bool = True,
):
    from institutional_portfolio.production import get_portfolio_graph

    return get_portfolio_graph(
        portfolio_id,
        rebuild=True,
        include_company_graphs=include_company_graphs,
    )


@router.get("/portfolio-graph/{portfolio_id}/portfolio")
async def institutional_portfolio_object_get(portfolio_id: str):
    from institutional_portfolio.production import get_institutional_portfolio

    return get_institutional_portfolio(portfolio_id)


# --- CIO-01 Institutional Portfolio Decision System (referential; no company mutation) ---


@router.get("/portfolio-decision/health")
async def institutional_portfolio_decision_health():
    from institutional_portfolio_decision.production import health

    return health()


@router.post("/portfolio-decision")
async def institutional_portfolio_decision_post(payload: dict[str, Any] = Body(default={})):
    from institutional_portfolio_decision.production import decide_portfolio

    return decide_portfolio(payload or {})


@router.get("/portfolio-decision/{portfolio_id}")
async def institutional_portfolio_decision_get(
    portfolio_id: str,
    refresh: bool = True,
    include_history: bool = False,
):
    from institutional_portfolio_decision.production import get_portfolio_decision

    return get_portfolio_decision(
        portfolio_id,
        refresh=refresh,
        include_history=include_history,
    )


# --- PRE-01 Institutional Portfolio Risk Engine (authoritative risk for CIO-01) ---


@router.get("/portfolio-risk/health")
async def institutional_portfolio_risk_health():
    from institutional_portfolio_risk.production import health

    return health()


@router.post("/portfolio-risk")
async def institutional_portfolio_risk_post(payload: dict[str, Any] = Body(default={})):
    from institutional_portfolio_risk.production import evaluate_portfolio_risk

    return evaluate_portfolio_risk(payload or {})


@router.get("/portfolio-risk/{portfolio_id}")
async def institutional_portfolio_risk_get(
    portfolio_id: str,
    refresh: bool = True,
    include_history: bool = False,
):
    from institutional_portfolio_risk.production import get_portfolio_risk

    return get_portfolio_risk(
        portfolio_id,
        refresh=refresh,
        include_history=include_history,
    )


# --- PCE-01 Institutional Policy & Constraint Engine (mandate governance for CIO-01) ---


@router.get("/policy/health")
async def institutional_policy_health():
    from institutional_policy.production import health

    return health()


@router.post("/policy/check")
async def institutional_policy_check(payload: dict[str, Any] = Body(default={})):
    from institutional_policy.production import check_policy

    return check_policy(payload or {})


@router.get("/policy/{portfolio_id}")
async def institutional_policy_get(
    portfolio_id: str,
    policy: str = "family_office",
    profile_id: str | None = None,
    refresh: bool = True,
    include_history: bool = False,
):
    from institutional_policy.production import get_policy_assessment

    return get_policy_assessment(
        portfolio_id,
        profile_id=str(profile_id or policy or "family_office"),
        refresh=refresh,
        include_history=include_history,
    )


# --- ICE-01 Investment Committee Engine (governs CIO-01; does not mutate upstream) ---


@router.get("/committee-engine/health")
async def institutional_committee_engine_health():
    from institutional_committee.production import health

    return health()


@router.post("/committee/review")
async def institutional_committee_review(payload: dict[str, Any] = Body(default={})):
    from institutional_committee.production import review_committee

    return review_committee(payload or {})


@router.get("/committee/pending")
async def institutional_committee_pending():
    from institutional_committee.production import get_pending

    return get_pending()


@router.get("/committee/resolution/{resolution_id}")
async def institutional_committee_resolution_get(resolution_id: str):
    from institutional_committee.production import get_resolution

    return get_resolution(resolution_id)


@router.get("/committee/portfolio/{portfolio_id}")
async def institutional_committee_portfolio_get(
    portfolio_id: str,
    refresh: bool = True,
):
    from institutional_committee.production import get_portfolio_resolutions

    return get_portfolio_resolutions(portfolio_id, refresh=refresh)


# --- UAG-01 Universal Ask AGI Orchestrator (stateless; orchestration only) ---


@router.get("/orchestrator/health")
async def institutional_orchestrator_health():
    from institutional_orchestrator.production import health

    return health()


@router.post("/ask", dependencies=[Depends(require_token)])
async def universal_ask_post(payload: dict[str, Any] = Body(default={})):
    """UAG-01: orchestrate registered institutional objects. Does not generate recommendations."""
    from institutional_orchestrator.production import ask

    return ask(payload or {})


@router.post("/ask/stream", dependencies=[Depends(require_token)])
async def universal_ask_stream(payload: dict[str, Any] = Body(default={})):
    from institutional_orchestrator.production import ask_stream

    # Structured event list (not LLM token stream)
    return {"ok": True, "events": list(ask_stream(payload or {})), "stream": True}


@router.get("/query/{query_id}", dependencies=[Depends(require_token)])
async def universal_ask_query_get(query_id: str):
    from institutional_orchestrator.production import get_query

    return get_query(query_id)


# --- RW-01 Institutional Research Workspace (analyst workstation; presentation only) ---


@router.get("/workspace/health")
async def institutional_workspace_health():
    from institutional_workspace.production import health

    return health()


@router.get("/workspace/company/{ticker}")
async def institutional_workspace_company(ticker: str, focus: str = "overview"):
    from institutional_workspace.production import get_company_workspace

    return get_company_workspace(ticker, focus=focus)


@router.get("/workspace/portfolio/{portfolio_id}")
async def institutional_workspace_portfolio(portfolio_id: str, focus: str = "overview"):
    from institutional_workspace.production import get_portfolio_workspace

    return get_portfolio_workspace(portfolio_id, focus=focus)


@router.get("/workspace/committee")
async def institutional_workspace_committee():
    from institutional_workspace.production import get_committee_workspace

    return get_committee_workspace()


@router.get("/workspace/object/{object_id}")
async def institutional_workspace_object(object_id: str, object_type: str = ""):
    from institutional_workspace.production import get_object

    return get_object(object_id, object_type=object_type)


@router.get("/workspace/timeline/{context_id}")
async def institutional_workspace_timeline(context_id: str, context_type: str = "company"):
    from institutional_workspace.production import get_timeline

    return get_timeline(context_id, context=context_type)


@router.get("/workspace/search")
async def institutional_workspace_search(
    q: str,
    context_type: str = "company",
    context_id: str = "AXISBANK",
):
    from institutional_workspace.production import search

    return search(context_id, q, context=context_type)


@router.post("/workspace/notes")
async def institutional_workspace_notes(payload: dict[str, Any] = Body(default={})):
    from institutional_workspace.production import add_analyst_note

    return add_analyst_note(payload or {})


# --- CCI-01 Cross-Company Intelligence (relationship reasoning over KG-01) ---


@router.get("/relationships/health")
async def cross_company_relationships_health():
    from institutional_cross_company.production import health

    return health()


@router.get("/relationships/company/{ticker}")
async def cross_company_relationships_company(ticker: str, portfolio_id: str = "agi-core-equity"):
    from institutional_cross_company.production import get_company_relationships

    return get_company_relationships(ticker, portfolio_id=portfolio_id)


@router.get("/relationships/sector/{sector}")
async def cross_company_relationships_sector(sector: str):
    from institutional_cross_company.production import get_sector_relationships

    return get_sector_relationships(sector)


@router.get("/relationships/macro/{driver}")
async def cross_company_relationships_macro(driver: str):
    from institutional_cross_company.production import get_macro_relationships

    return get_macro_relationships(driver)


@router.post("/relationships/query")
async def cross_company_relationships_query(payload: dict[str, Any] = Body(default={})):
    from institutional_cross_company.production import query_relationships

    return query_relationships(payload or {})


@router.get("/relationships/similar/{ticker}")
async def cross_company_relationships_similar(ticker: str):
    from institutional_cross_company.production import get_similarity

    return get_similarity(ticker)


@router.get("/relationships/clusters")
async def cross_company_relationships_clusters():
    from institutional_cross_company.production import get_clusters

    return get_clusters()


@router.get("/relationships/propagate/{driver}")
async def cross_company_relationships_propagate(driver: str):
    from institutional_cross_company.production import get_propagation

    return get_propagation(driver)


# --- PUB-01 Publishing & Distribution (compose only; never analyzes) ---


@router.get("/publications/health")
async def institutional_publications_health():
    from institutional_publishing.production import health

    return health()


@router.get("/publications/types")
async def institutional_publications_types():
    from institutional_publishing.production import list_types

    return list_types()


@router.get("/publications")
async def institutional_publications_list(limit: int = 20):
    from institutional_publishing.production import list_publications

    return list_publications(limit=limit)


@router.post("/publications/generate")
async def institutional_publications_generate(payload: dict[str, Any] = Body(default={})):
    from institutional_publishing.production import generate

    return generate(payload or {})


@router.get("/publications/{publication_id}")
async def institutional_publications_get(publication_id: str):
    from institutional_publishing.production import get_publication

    return get_publication(publication_id)


@router.post("/publications/export")
async def institutional_publications_export(payload: dict[str, Any] = Body(default={})):
    from institutional_publishing.production import export_publication

    return export_publication(payload or {})


# --- MPC-01 Multi-Portfolio & Client Platform (tenancy/workflow; intelligence global) ---


@router.get("/platform/health")
async def multi_portfolio_platform_health():
    from institutional_multi_portfolio.production import health

    return health()


@router.get("/portfolios")
async def multi_portfolio_list():
    from institutional_multi_portfolio.production import list_portfolios_api

    return list_portfolios_api()


@router.post("/portfolios")
async def multi_portfolio_create(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import create_portfolio

    return create_portfolio(payload or {})


@router.get("/clients")
async def multi_portfolio_clients():
    from institutional_multi_portfolio.production import list_clients_api

    return list_clients_api()


@router.post("/clients")
async def multi_portfolio_client_create(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import create_client

    return create_client(payload or {})


@router.get("/workspaces/{workspace_id}")
async def multi_portfolio_workspace_get(
    workspace_id: str,
    portfolio_id: str = "",
    client_id: str = "",
    role_id: str = "analyst",
    user_id: str = "",
    mandate_id: str = "",
):
    from institutional_multi_portfolio.production import get_workspace

    return get_workspace(
        workspace_id,
        portfolio_id=portfolio_id,
        client_id=client_id,
        role_id=role_id,
        user_id=user_id,
        mandate_id=mandate_id,
    )


@router.post("/workspaces/resolve")
async def multi_portfolio_workspace_resolve(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import get_workspace

    body = payload or {}
    return get_workspace(
        str(body.get("workspace_id") or ""),
        portfolio_id=str(body.get("portfolio_id") or body.get("portfolio") or ""),
        client_id=str(body.get("client_id") or ""),
        role_id=str(body.get("role_id") or "analyst"),
        user_id=str(body.get("user_id") or ""),
        mandate_id=str(body.get("mandate_id") or ""),
    )


@router.post("/permissions")
async def multi_portfolio_permissions(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import set_permissions

    return set_permissions(payload or {})


@router.post("/platform/context")
async def multi_portfolio_context(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import resolve_context

    return resolve_context(payload or {})


@router.post("/platform/ask")
async def multi_portfolio_ask(payload: dict[str, Any] = Body(default={})):
    from institutional_multi_portfolio.production import ask_scoped

    return ask_scoped(payload or {})


# --- PRP-01 Performance & Scale (cache / queue / metrics / Performance Center) ---


@router.get("/performance/health")
async def performance_health():
    from institutional_performance.production import health

    return health()


@router.get("/performance/metrics")
async def performance_metrics():
    from institutional_performance.production import metrics_api

    return metrics_api()


@router.get("/performance/cache")
async def performance_cache_stats():
    from institutional_performance.production import cache_stats

    return cache_stats()


@router.post("/performance/cache/get")
async def performance_cache_get(payload: dict[str, Any] = Body(default={})):
    from institutional_performance.production import cache_get_api

    return cache_get_api(payload or {})


@router.post("/performance/cache/set")
async def performance_cache_set(payload: dict[str, Any] = Body(default={})):
    from institutional_performance.production import cache_set_api

    return cache_set_api(payload or {})


@router.get("/performance/queue")
async def performance_queue():
    from institutional_performance.production import queue_stats_api

    return queue_stats_api()


@router.post("/performance/jobs")
async def performance_enqueue(payload: dict[str, Any] = Body(default={})):
    from institutional_performance.production import enqueue_job

    return enqueue_job(payload or {})


@router.get("/performance/jobs")
async def performance_list_jobs(limit: int = 40):
    from institutional_performance.production import list_jobs_api

    return list_jobs_api(limit=limit)


@router.get("/performance/jobs/{job_id}")
async def performance_job(job_id: str):
    from institutional_performance.production import get_job

    return get_job(job_id)


@router.post("/performance/graph/incremental")
async def performance_graph_incremental(payload: dict[str, Any] = Body(default={})):
    from institutional_performance.production import graph_incremental_api

    return graph_incremental_api(payload or {})


@router.post("/performance/parallel")
async def performance_parallel(payload: dict[str, Any] = Body(default={})):
    from institutional_performance.production import parallel_demo

    return parallel_demo(payload or {})


# --- PRP-02 Security & Governance (auth / authz / audit / tenant isolation) ---


@router.get("/security/health")
async def security_health():
    from institutional_security.production import health

    return health()


@router.post("/auth/login")
async def auth_login(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import login

    return login(payload or {})


@router.post("/auth/logout")
async def auth_logout(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import logout

    return logout(payload or {})


@router.post("/auth/refresh")
async def auth_refresh(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import refresh

    return refresh(payload or {})


@router.get("/security/context")
async def security_context_get(
    session_id: str = "",
    user_id: str = "",
    tenant_id: str = "",
    correlation_id: str = "",
):
    from institutional_security.production import get_context

    return get_context(
        {
            "session_id": session_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
        }
    )


@router.post("/security/context")
async def security_context_post(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import get_context

    return get_context(payload or {})


@router.get("/security/audit")
async def security_audit_get(
    limit: int = 50,
    tenant_id: str = "",
    user_id: str = "",
    action: str = "",
    correlation_id: str = "",
    session_id: str = "",
):
    from institutional_security.production import list_audit

    return list_audit(
        {
            "limit": limit,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "correlation_id": correlation_id,
            "session_id": session_id,
        }
    )


@router.post("/security/audit")
async def security_audit_post(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import list_audit

    return list_audit(payload or {})


@router.post("/security/api-keys")
async def security_api_keys_create(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import create_api_key

    return create_api_key(payload or {})


@router.delete("/security/api-keys/{api_key_id}")
async def security_api_keys_revoke(api_key_id: str, payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import revoke_api_key

    return revoke_api_key(api_key_id, payload or {})


@router.get("/security/roles")
async def security_roles():
    from institutional_security.production import roles_api

    return roles_api()


@router.get("/security/permissions")
async def security_permissions():
    from institutional_security.production import permissions_api

    return permissions_api()


@router.post("/security/permissions/grant")
async def security_permissions_grant(payload: dict[str, Any] = Body(default={})):
    from institutional_security.production import grant_permissions

    return grant_permissions(payload or {})


@router.get("/security/tenants")
async def security_tenants():
    from institutional_security.production import tenants_api

    return tenants_api()


# --- PRP-03 Observability & Operations (tracing / metrics / health / alerts) ---


@router.get("/ops/health")
async def ops_health():
    from institutional_observability.production import ops_health as _ops_health

    return _ops_health()


@router.get("/observability/health")
async def observability_health():
    from institutional_observability.production import health

    return health()


@router.get("/ops/metrics")
async def ops_metrics():
    from institutional_observability.production import ops_metrics as _ops_metrics

    return _ops_metrics()


@router.get("/ops/traces/{trace_id}")
async def ops_trace(trace_id: str):
    from institutional_observability.production import ops_trace as _ops_trace

    return _ops_trace(trace_id)


@router.get("/ops/service-map")
async def ops_service_map():
    from institutional_observability.production import ops_service_map as _ops_map

    return _ops_map()


@router.get("/ops/alerts")
async def ops_alerts():
    from institutional_observability.production import ops_alerts as _ops_alerts

    return _ops_alerts()


@router.get("/ops/dependencies")
async def ops_dependencies():
    from institutional_observability.production import ops_dependencies as _ops_deps

    return _ops_deps()


@router.get("/ops/logs")
async def ops_logs(
    limit: int = 50,
    severity: str = "",
    correlation_id: str = "",
    component: str = "",
):
    from institutional_observability.production import ops_logs as _ops_logs

    return _ops_logs(
        {
            "limit": limit,
            "severity": severity,
            "correlation_id": correlation_id,
            "component": component,
        }
    )


# --- RC-01 Architecture Conformance & Release Candidate ---


@router.get("/architecture/health")
async def architecture_health():
    from institutional_architecture.production import health

    return health()


@router.post("/architecture/conformance")
async def architecture_conformance(payload: dict[str, Any] = Body(default={})):
    from institutional_architecture.production import run

    return run(payload or {})


@router.get("/architecture/conformance")
async def architecture_conformance_get(force: bool = False):
    from institutional_architecture.production import run

    return run({"force": force})


@router.get("/architecture/report")
async def architecture_report():
    from institutional_architecture.production import report_api

    return report_api()


@router.get("/architecture/violations")
async def architecture_violations():
    from institutional_architecture.production import violations_api

    return violations_api()


# --- L-01 Launch Phase (usage analytics / feedback / SLAs / feature flags) ---


@router.get("/launch/health")
async def launch_health():
    from institutional_launch.production import health

    return health()


@router.get("/launch/metrics")
async def launch_metrics():
    from institutional_launch.production import metrics_api

    return metrics_api()


@router.get("/launch/funnel")
async def launch_funnel():
    from institutional_launch.production import funnel_api

    return funnel_api()


@router.post("/launch/events")
async def launch_events(payload: dict[str, Any] = Body(default={})):
    from institutional_launch.production import track_event

    return track_event(payload or {})


@router.post("/launch/journey")
async def launch_journey(payload: dict[str, Any] = Body(default={})):
    from institutional_launch.production import track_journey

    return track_journey(payload or {})


@router.post("/launch/feedback")
async def launch_feedback_submit(payload: dict[str, Any] = Body(default={})):
    from institutional_launch.production import feedback_submit_api

    return feedback_submit_api(payload or {})


@router.get("/launch/feedback")
async def launch_feedback_list(limit: int = 40):
    from institutional_launch.production import feedback_list_api

    return feedback_list_api(limit=limit)


@router.get("/launch/flags")
async def launch_flags():
    from institutional_launch.production import flags_api

    return flags_api()


@router.post("/launch/flags")
async def launch_flags_set(payload: dict[str, Any] = Body(default={})):
    from institutional_launch.production import flag_set_api

    return flag_set_api(payload or {})


@router.get("/launch/sla")
async def launch_sla():
    from institutional_launch.production import sla_api

    return sla_api()


@router.get("/launch/report")
async def launch_report():
    from institutional_launch.production import report_api

    return report_api()


# --- PAT-01 Production Acceptance Test (break AGIB before onboarding users) ---


@router.get("/acceptance/health")
async def acceptance_health():
    from institutional_acceptance.production import health

    return health()


@router.post("/acceptance/run")
async def acceptance_run(payload: dict[str, Any] = Body(default={})):
    from institutional_acceptance.production import run

    return run(payload or {})


@router.get("/acceptance/report")
async def acceptance_report():
    from institutional_acceptance.production import report_api

    return report_api()


@router.get("/acceptance/cases")
async def acceptance_cases(limit: int = 500):
    from institutional_acceptance.production import cases_api

    return cases_api(limit=limit)


@router.get("/acceptance/phase/{phase}")
async def acceptance_phase_get(phase: str):
    from institutional_acceptance.production import phase_api

    return phase_api(phase)


@router.post("/acceptance/phase/{phase}")
async def acceptance_phase_post(phase: str, payload: dict[str, Any] = Body(default={})):
    from institutional_acceptance.production import phase_api

    return phase_api(phase, payload or {})


@router.get("/acceptance/diagnostics")
async def acceptance_diagnostics():
    from institutional_acceptance.production import diagnostics_api

    return diagnostics_api()


# --- IEP-01 Institutional Evidence Platform (AGI v1.1 evidence foundation) ---


@router.get("/iep/health")
async def iep_health():
    from institutional_evidence.production import health

    return health()


@router.get("/iep/status")
async def iep_status():
    from institutional_evidence.production import get_iep_status

    return get_iep_status()


@router.get("/iep/pack/{ticker}")
async def iep_research_pack(ticker: str):
    from institutional_evidence.production import get_research_pack

    return get_research_pack(ticker)


@router.get("/iep/readiness/{ticker}")
async def iep_readiness(ticker: str):
    from institutional_evidence.production import get_research_readiness

    return get_research_readiness(ticker)


@router.get("/iep/validate/{ticker}")
async def iep_validate(ticker: str):
    from institutional_evidence.production import validate_research_pack

    return validate_research_pack(ticker)


@router.post("/iep/orchestrate/{ticker}")
async def iep_orchestrate(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import orchestrate_research

    body = payload or {}
    return orchestrate_research(
        ticker,
        generate_research=bool(body.get("generate_research")),
        force_ingest=bool(body.get("force_ingest")),
    )


@router.get("/iep/registry/{ticker}")
async def iep_registry(ticker: str):
    from institutional_evidence.production import get_evidence_registry

    return get_evidence_registry(ticker)


@router.get("/iep/canonical/{ticker}")
async def iep_canonical(ticker: str):
    from institutional_evidence.production import get_canonical_statements

    return get_canonical_statements(ticker)


@router.get("/iep/memory/{ticker}")
async def iep_memory(ticker: str):
    from institutional_evidence.production import get_company_memory_bridge

    return get_company_memory_bridge(ticker)


@router.get("/iep/phase1")
async def iep_phase1():
    from institutional_evidence.production import get_phase1_coverage

    return get_phase1_coverage()


@router.get("/iep/metrics")
async def iep_metrics():
    from institutional_evidence.production import get_success_metrics

    return get_success_metrics()


@router.get("/iep/center")
async def iep_center():
    from institutional_evidence.dashboards import evidence_center_payload

    return evidence_center_payload()


@router.get("/iep/gates/writer/{ticker}")
async def iep_writer_gate(ticker: str):
    from institutional_evidence.production import check_writer_gate

    return check_writer_gate(ticker)


@router.post("/iep/gates/decision/{ticker}")
async def iep_decision_gate(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import check_decision_gate

    body = payload or {}
    return check_decision_gate(ticker, str(body.get("recommendation") or body.get("action") or ""))


@router.get("/iep/gates/publish/{ticker}")
async def iep_publish_gate(ticker: str):
    from institutional_evidence.production import check_publish_gate

    return check_publish_gate(ticker)


# IEP v1.1.1 — Knowledge OS surfaces


@router.get("/iep/entity/{query}")
async def iep_entity_resolve(query: str):
    from institutional_evidence.production import resolve_company_entity

    return resolve_company_entity(query)


@router.get("/iep/timeline/{ticker}")
async def iep_timeline(ticker: str):
    from institutional_evidence.production import get_company_timeline

    return get_company_timeline(ticker)


@router.get("/iep/graph/{ticker}")
async def iep_evidence_graph(ticker: str):
    from institutional_evidence.production import get_evidence_graph

    return get_evidence_graph(ticker)


@router.get("/iep/eligibility/{ticker}")
async def iep_decision_eligibility(ticker: str):
    from institutional_evidence.production import get_decision_eligibility

    return get_decision_eligibility(ticker)


@router.get("/iep/quality/{ticker}")
async def iep_evidence_quality(ticker: str):
    from institutional_evidence.production import get_evidence_quality

    return get_evidence_quality(ticker)


@router.get("/iep/domains/{ticker}")
async def iep_canonical_domains(ticker: str):
    from institutional_evidence.production import get_canonical_domains

    return get_canonical_domains(ticker)


@router.get("/iep/coverage/{ticker}")
async def iep_phase1_acceptance(ticker: str):
    from institutional_evidence.production import get_phase1_acceptance

    return get_phase1_acceptance(ticker)


@router.post("/iep/learn/{ticker}")
async def iep_continuous_learning(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import run_continuous_learning

    body = payload or {}
    return run_continuous_learning(
        ticker,
        event_type=str(body.get("event_type") or "new_filing"),
        force_ingest=bool(body.get("force_ingest")),
    )


@router.get("/iep/lifecycle/{ticker}")
async def iep_research_lifecycle(ticker: str):
    from institutional_evidence.production import get_research_lifecycle

    return get_research_lifecycle(ticker)


@router.get("/iep/observability")
async def iep_observability():
    from institutional_evidence.production import get_observability_metrics

    return get_observability_metrics()


@router.get("/iep/company/{company_ref}")
async def iep_company(company_ref: str):
    from institutional_evidence.production import institutional_company

    return institutional_company(company_ref)


@router.get("/iep/company/{company_ref}/{resource}")
async def iep_company_resource(company_ref: str, resource: str):
    from institutional_evidence.production import company_subresource

    return company_subresource(company_ref, resource)


# KIL-01 — Knowledge Integration Layer (AGI v1.1.2)


@router.get("/iep/kil/health")
async def iep_kil_health():
    from institutional_evidence.production import get_kil_status

    return get_kil_status()


@router.post("/iep/kil/integrate")
async def iep_kil_integrate(payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import run_kil_integration

    body = payload or {}
    return run_kil_integration(
        body.get("cgl_run"),
        companies=body.get("companies"),
    )


@router.post("/iep/kil/integrate/{ticker}")
async def iep_kil_integrate_company(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import integrate_company_knowledge

    body = payload or {}
    return integrate_company_knowledge(
        ticker,
        trigger_repair=bool(body.get("trigger_repair", True)),
    )


@router.get("/iep/knowledge-health")
async def iep_knowledge_health():
    from institutional_evidence.production import get_knowledge_health

    return get_knowledge_health()


@router.get("/iep/knowledge-confidence/{ticker}")
async def iep_knowledge_confidence(ticker: str):
    from institutional_evidence.production import get_knowledge_confidence

    return get_knowledge_confidence(ticker)


@router.get("/iep/coverage-state/{ticker}")
async def iep_coverage_state(ticker: str):
    from institutional_evidence.production import get_coverage_state

    return get_coverage_state(ticker)


@router.get("/iep/snapshots")
async def iep_knowledge_snapshots():
    from institutional_evidence.production import get_knowledge_snapshots

    return get_knowledge_snapshots()


@router.get("/iep/events")
async def iep_kil_events():
    from institutional_evidence.production import get_kil_events

    return get_kil_events()


@router.post("/iep/ask/{ticker}")
async def iep_orchestrate_ask(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import orchestrate_ask

    body = payload or {}
    return orchestrate_ask(ticker, force_kil_refresh=bool(body.get("force_kil_refresh")))


@router.get("/iep/expansion")
async def iep_expansion_status():
    from institutional_evidence.production import get_expansion_status

    return get_expansion_status()


@router.post("/iep/expansion/nifty500")
async def iep_expansion_enqueue(payload: dict[str, Any] = Body(default={})):
    from institutional_evidence.production import enqueue_nifty_500_expansion

    body = payload or {}
    return enqueue_nifty_500_expansion(force=bool(body.get("force")))


# ICF-01 — Institutional Coverage Factory (companies → ICC, not crawl count)


@router.get("/icf/health")
async def icf_health():
    from institutional_coverage_factory.production import health

    return health()


@router.get("/icf/status")
async def icf_status():
    from institutional_coverage_factory.production import get_icf_status

    return get_icf_status()


@router.get("/icf/dashboard")
async def icf_dashboard(scope: str = "TOP20", sample_limit: int | None = None):
    from institutional_coverage_factory.production import coverage_dashboard

    return coverage_dashboard(scope=scope, sample_limit=sample_limit)


@router.get("/icf/score/{ticker}")
async def icf_score(ticker: str):
    from institutional_coverage_factory.production import coverage_score_for

    return coverage_score_for(ticker)


@router.get("/icf/icc/{ticker}")
async def icf_icc(ticker: str):
    from institutional_coverage_factory.production import icc_status_for

    return icc_status_for(ticker)


@router.get("/icf/plan")
async def icf_plan(scope: str = "TOP20", limit: int | None = None):
    from institutional_coverage_factory.production import plan_coverage

    return plan_coverage(limit=limit, scope=scope)


@router.post("/icf/plan-dispatch")
async def icf_plan_dispatch(payload: dict[str, Any] = Body(default={})):
    from institutional_coverage_factory.production import plan_and_dispatch

    body = payload or {}
    return plan_and_dispatch(
        limit=body.get("limit"),
        scope=str(body.get("scope") or "TOP20"),
        dispatch=body.get("dispatch"),
    )


@router.post("/icf/tick")
async def icf_tick(payload: dict[str, Any] = Body(default={})):
    from institutional_coverage_factory.production import run_coverage_tick

    body = payload or {}
    return run_coverage_tick(
        scope=str(body.get("scope") or "TOP20"),
        limit=body.get("limit"),
        dispatch=body.get("dispatch"),
    )


@router.post("/icf/dispatch/{ticker}")
async def icf_dispatch_company(ticker: str, payload: dict[str, Any] = Body(default={})):
    from institutional_coverage_factory.production import dispatch_company

    body = payload or {}
    return dispatch_company(ticker, missing_classes=body.get("missing_classes"))


@router.get("/icf/scheduler")
async def icf_scheduler():
    from institutional_coverage_factory.production import scheduler_status

    return scheduler_status()


# KOC V1.2 — Institutional Knowledge Mission Control (admin control room)


@router.get("/koc/health")
async def koc_health():
    from knowledge_operations.production import health

    return health()


@router.get("/koc/status")
async def koc_status():
    from knowledge_operations.production import get_status

    return get_status()


@router.get("/koc/overview")
async def koc_overview(scope: str = "TOP20", deep: bool = False):
    from knowledge_operations.production import get_overview

    return get_overview(scope=scope, deep=deep)


@router.get("/koc/desk")
async def koc_desk(scope: str = "TOP20", deep: bool = False):
    from knowledge_operations.production import get_desk

    return get_desk(scope=scope, deep=deep)


@router.get("/koc/system-health")
async def koc_system_health():
    from knowledge_operations.production import get_system_health

    return get_system_health()


@router.get("/koc/coverage")
async def koc_coverage(scope: str = "TOP20"):
    from knowledge_operations.production import get_coverage

    return get_coverage(scope=scope)


@router.get("/koc/missing-inbox")
async def koc_missing_inbox(scope: str = "TOP20", limit: int = 50):
    from knowledge_operations.production import get_missing_inbox

    return get_missing_inbox(scope=scope, limit=limit)


@router.get("/koc/missing-knowledge")
async def koc_missing_knowledge(scope: str = "TOP20", limit: int = 50):
    from knowledge_operations.production import get_missing_knowledge

    return get_missing_knowledge(scope=scope, limit=limit)


@router.get("/koc/company/{ticker}")
async def koc_company(ticker: str):
    from knowledge_operations.production import get_company

    return get_company(ticker)


@router.get("/koc/collectors")
async def koc_collectors():
    from knowledge_operations.production import get_collectors

    return get_collectors()


@router.get("/koc/evidence")
async def koc_evidence(
    q: str = "",
    ticker: str | None = None,
    document_type: str | None = None,
    limit: int = 50,
):
    from knowledge_operations.production import get_evidence

    return get_evidence(q=q, ticker=ticker, document_type=document_type, limit=limit)


@router.get("/koc/evidence/{ticker}/{document_id}")
async def koc_evidence_detail(ticker: str, document_id: str):
    from knowledge_operations.production import get_evidence_detail

    return get_evidence_detail(ticker, document_id)


@router.get("/koc/knowledge-versions")
async def koc_knowledge_versions(limit: int = 20):
    from knowledge_operations.production import get_knowledge_versions

    return get_knowledge_versions(limit=limit)


@router.get("/koc/gap-ai")
async def koc_gap_ai(scope: str = "TOP20", limit: int = 30):
    from knowledge_operations.production import get_gap_ai

    return get_gap_ai(scope=scope, limit=limit)


@router.get("/koc/gap-ai/{ticker}")
async def koc_gap_ai_ticker(ticker: str):
    from knowledge_operations.production import find_missing_knowledge

    return find_missing_knowledge(ticker)


@router.get("/koc/search")
async def koc_search(q: str = "", limit: int = 30):
    from knowledge_operations.production import global_search

    return global_search(q, limit=limit)


@router.post("/koc/upload")
async def koc_upload(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import upload_knowledge

    body = payload or {}
    return upload_knowledge(
        ticker=str(body.get("ticker") or ""),
        document_type=str(body.get("document_type") or "other"),
        filename=str(body.get("filename") or "upload.bin"),
        content_base64=body.get("content_base64"),
        actor=body.get("actor"),
        mime_type=body.get("mime_type"),
    )


@router.get("/koc/queue")
async def koc_queue(limit: int = 100):
    from knowledge_operations.production import get_queue

    return get_queue(limit=limit)


@router.get("/koc/audit")
async def koc_audit(limit: int = 100, ticker: str | None = None):
    from knowledge_operations.production import get_audit

    return get_audit(limit=limit, ticker=ticker)


@router.post("/koc/action")
async def koc_action(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import run_action

    body = payload or {}
    return run_action(
        str(body.get("action") or ""),
        ticker=body.get("ticker"),
        actor=body.get("actor"),
        force=bool(body.get("force")),
    )


@router.post("/koc/run-cgl")
async def koc_run_cgl(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import run_cgl

    body = payload or {}
    return run_cgl(actor=body.get("actor"))


@router.post("/koc/run-kil")
async def koc_run_kil(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import run_kil

    body = payload or {}
    return run_kil(ticker=body.get("ticker"), actor=body.get("actor"))


@router.post("/koc/run-coverage")
async def koc_run_coverage(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import run_coverage

    body = payload or {}
    return run_coverage(actor=body.get("actor"))


@router.post("/koc/repair")
async def koc_repair(payload: dict[str, Any] = Body(default={})):
    from knowledge_operations.production import run_repair

    body = payload or {}
    return run_repair(ticker=body.get("ticker"), actor=body.get("actor"))


# --- Company Monitoring System V1 (continuous living analyst; additive) ---


@router.get("/company-monitor/health")
async def company_monitor_health():
    from company_monitor.production import health

    return health()


@router.get("/company-monitor/dashboard")
async def company_monitor_dashboard():
    from company_monitor.production import dashboard

    return dashboard()


@router.get("/company-monitor/quality-gates")
async def company_monitor_quality_gates():
    from company_monitor.production import quality_gates

    return quality_gates()


@router.get("/company-monitor/changes")
async def company_monitor_changes(
    ticker: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=100),
):
    from company_monitor import store as cms_store

    return {"changes": cms_store.list_changes(ticker, limit=limit)}


@router.get("/company-monitor/alerts")
async def company_monitor_alerts(limit: int = Query(default=40, ge=1, le=100)):
    from company_monitor import store as cms_store

    return {"alerts": cms_store.list_alerts(limit=limit)}


@router.get("/company-monitor/reviews")
async def company_monitor_reviews(limit: int = Query(default=40, ge=1, le=100)):
    from company_monitor import store as cms_store

    return {"reviews": cms_store.list_reviews(limit=limit)}


@router.post("/company-monitor/run")
async def company_monitor_run(payload: dict[str, Any] = Body(default={})):
    from company_monitor.production import analyse

    ticker = str(payload.get("ticker") or "").upper()
    query = str(payload.get("query") or payload.get("q") or f"Monitor {ticker}")
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    return analyse(ticker, query=query)


@router.post("/company-monitor/run-universe")
async def company_monitor_run_universe(payload: dict[str, Any] = Body(default={})):
    from company_monitor.production import run_universe

    limit = payload.get("limit")
    return run_universe(limit=int(limit) if limit is not None else None)


# --- Company Analysis Engine V1 (institutional company reasoning; not Context Assembly) ---


@router.get("/company-analysis/health")
async def company_analysis_health():
    from company_analysis.production import health

    return health()


@router.get("/company-analysis/dashboard")
async def company_analysis_dashboard():
    from company_analysis.production import dashboard

    return dashboard()


@router.get("/company-analysis/quality-gates")
async def company_analysis_quality_gates():
    from company_analysis.production import quality_gates

    return quality_gates()


@router.get("/company-analysis/reports")
async def company_analysis_reports(limit: int = Query(default=30, ge=1, le=100)):
    from company_analysis import store as ca_store

    return {"reports": ca_store.list_reports(limit=limit)}


@router.get("/company-analysis/report/{ticker}")
async def company_analysis_report(ticker: str):
    from company_analysis import store as ca_store

    row = ca_store.get_report(ticker)
    return row or {"ticker": ticker.upper(), "found": False}


@router.post("/company-analysis/analyse")
async def company_analysis_analyse(payload: dict[str, Any] = Body(default={})):
    """Run institutional company analysis for a ticker/query (admin / Ask AGI soft path)."""
    from company_analysis.production import analyse

    query = str(payload.get("query") or payload.get("q") or "Company analysis")
    ticker = payload.get("ticker")
    return analyse(query, ticker=ticker)


@router.get("/features/health")
async def features_health():
    """WS03 Feature Registry health + cache/metrics."""
    return _features.health()


@router.get("/features", dependencies=[Depends(require_token)])
async def list_features():
    return [m.model_dump(mode="json") for m in _features.list_features()]


@router.get("/features/dependency-order", dependencies=[Depends(require_token)])
async def feature_dependency_order(feature_id: str | None = None):
    ids = [feature_id] if feature_id else None
    return {"order": _features.dependency_order(ids)}


@router.post("/features/register", dependencies=[Depends(require_token)])
async def register_feature(body: FeatureMetadata):
    _features.register_metadata(body)
    return {"ok": True, "feature_id": body.feature_id}


@router.get("/features/schedule/frequencies", dependencies=[Depends(require_token)])
async def feature_schedule_frequencies():
    """Calculation Scheduler frequency map (topo-ordered calculator IDs)."""
    return {"frequencies": _features.scheduler.frequencies()}


@router.get("/features/schedule/plan", dependencies=[Depends(require_token)])
async def feature_schedule_plan(
    as_of: str = Query(...),
    refresh_frequency: str | None = None,
    feature_id: list[str] | None = Query(default=None),
):
    plan = _features.scheduler.plan(
        as_of=as_of,
        refresh_frequency=refresh_frequency,
        feature_ids=feature_id,
    )
    return {
        "as_of": plan.as_of,
        "refresh_frequency": plan.refresh_frequency,
        "feature_ids": plan.feature_ids,
        "symbols": plan.symbols,
    }


@router.get("/features/{feature_id}", dependencies=[Depends(require_token)])
async def get_feature_metadata(feature_id: str):
    meta = _features.get_metadata(feature_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="feature not found")
    return meta.model_dump(mode="json")


@router.get("/features/{feature_id}/value", dependencies=[Depends(require_token)])
async def get_feature_value(
    feature_id: str,
    as_of: str = Query(...),
    symbol: str | None = None,
    pit_mode: bool = True,
):
    value = _features.get(feature_id, symbol=symbol, as_of=as_of, pit_mode=pit_mode)
    if value is None:
        raise HTTPException(status_code=404, detail="feature value not found")
    return value.model_dump(mode="json")


@router.post("/research/runs", response_model=ResearchRun, dependencies=[Depends(require_token)])
async def create_run(body: ResearchRunCreate):
    return await _director.execute(body)


@router.get("/research/runs/{run_id}", response_model=ResearchRun, dependencies=[Depends(require_token)])
async def get_run(run_id: str):
    run = await _store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/research/runs", response_model=list[ResearchRun], dependencies=[Depends(require_token)])
async def list_runs(desk: str | None = None, limit: int = 10):
    return await _store.latest_runs(desk=desk, limit=min(limit, 50))


@router.post("/eval/predictions", response_model=PredictionRecord, dependencies=[Depends(require_token)])
async def record_prediction(body: PredictionRecord):
    return _eval.record(body)


@router.get("/eval/predictions/pending", response_model=list[PredictionRecord], dependencies=[Depends(require_token)])
async def pending_predictions(limit: int = 50):
    return _eval.list_pending(limit=limit)


# --- AGIB Intelligence Layer V2 (CDE/EDE/TE/PE/CME/EL; soft-wire; no FAA/FRE/CAE redesign) ---


@router.get("/ail/health")
async def ail_health():
    return _ail.health()


@router.get("/ail/dashboard")
async def ail_dashboard():
    try:
        return _ail.dashboard()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ail/analyse")
async def ail_analyse(q: str = Query(...), ticker: str | None = Query(default=None)):
    try:
        return _ail.analyse(q, ticker=ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ail/monitor/run")
async def ail_monitor_run(watchlist: str = Query(default="default")):
    try:
        return _ail.run_monitor(watchlist=watchlist)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/dossier")
async def company_dossier_ail(ticker: str):
    try:
        return _ail.dossier(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/timeline")
async def company_timeline_ail(ticker: str, limit: int = Query(default=100, ge=1, le=500)):
    try:
        return _ail.timeline(ticker, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/events")
async def company_events_ail(ticker: str, limit: int = Query(default=50, ge=1, le=200)):
    try:
        return _ail.events(ticker, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/thesis")
async def company_thesis_ail(ticker: str):
    try:
        return _ail.thesis(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/forecast")
async def company_forecast_ail(ticker: str):
    try:
        return _ail.forecast(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/ledger")
async def company_ledger_ail(ticker: str):
    try:
        return _ail.ledger(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/company/{ticker}/monitor")
async def company_monitor_ail(ticker: str):
    try:
        return _ail.monitor(ticker)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/event/{event_id}")
async def ail_event(event_id: str):
    try:
        return _ail.event(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="event_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# AGIB v3.2 Track 5 — Institutional Evidence Retrieval Engine (IERE)
# Static paths MUST be registered before /evidence/{evidence_id}.
# Ranked structured evidence packs only. Reasoning / governance frozen.
# ---------------------------------------------------------------------------
@router.get("/evidence/health")
async def evidence_health():
    from evidence_retrieval.production import health

    return health()


@router.get("/evidence/dashboard")
async def evidence_dashboard_route():
    from evidence_retrieval.production import dashboard

    return dashboard()


@router.get("/evidence/search")
async def evidence_search(
    q: str = Query(..., description="User question"),
    ticker: str | None = None,
    as_of: str | None = None,
):
    from evidence_retrieval.production import search

    return search(q, ticker=ticker, as_of=as_of)


@router.get("/evidence/company/{ticker}")
async def evidence_company(ticker: str, as_of: str | None = None):
    from evidence_retrieval.production import company

    return company(ticker, as_of=as_of)


@router.get("/evidence/document/{doc_id}")
async def evidence_document(doc_id: str):
    from evidence_retrieval.production import document

    return document(doc_id)


@router.get("/evidence/graph")
async def evidence_graph(graph_id: str | None = None):
    from evidence_retrieval.production import graph

    return graph(graph_id)


@router.get("/evidence/replay")
async def evidence_replay(
    q: str = Query(..., description="User question"),
    as_of: str = Query(..., description="Point-in-time date YYYY-MM-DD"),
    ticker: str | None = None,
):
    from evidence_retrieval.production import replay

    return replay(question=q, as_of=as_of, ticker=ticker)


@router.get("/evidence/{evidence_id}")
async def ail_evidence(evidence_id: str):
    try:
        return _ail.evidence(evidence_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="evidence_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# AGIB v3.4 Track C — Institutional Framework Selection Engine (IFSE)
# Soft-wire only. Reasoning / governance / KF frozen.
# ---------------------------------------------------------------------------
@router.get("/framework-selection/health")
async def framework_selection_health():
    from framework_selection.production import health

    return health()


@router.get("/framework-selection/dashboard")
async def framework_selection_dashboard():
    from framework_selection.production import dashboard

    return dashboard()


@router.get("/framework-selection/registry")
async def framework_selection_registry():
    from framework_selection.production import registry

    return registry()


@router.get("/framework-selection/framework/{framework_id}")
async def framework_selection_framework(framework_id: str):
    from framework_selection.production import framework

    return framework(framework_id)


@router.get("/framework-selection/select")
async def framework_selection_select(
    q: str = Query(..., description="User question"),
    intent_v2: str | None = None,
    ticker: str | None = None,
    as_of: str | None = None,
    concept_mode: bool = False,
):
    from framework_selection.production import select

    return select(
        question=q,
        intent_v2=intent_v2,
        ticker_hint=ticker,
        as_of=as_of,
        concept_mode=concept_mode,
        entities=[{"type": "company", "id": ticker, "confidence": 0.99}] if ticker else [],
    )


@router.get("/framework-selection/history")
async def framework_selection_history(limit: int = 50):
    from framework_selection.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGIB Phase 1 — Financial Foundations (accounting intelligence, not
# investment/valuation). Soft-wire only; standalone engine.
# ---------------------------------------------------------------------------
@router.get("/financial-foundations/health")
async def financial_foundations_health():
    from financial_foundations.production import health

    return health()


@router.get("/financial-foundations/dashboard")
async def financial_foundations_dashboard():
    from financial_foundations.production import dashboard

    return dashboard()


@router.get("/financial-foundations/curriculum")
async def financial_foundations_curriculum():
    from financial_foundations.production import curriculum

    return curriculum()


@router.get("/financial-foundations/explain/{topic}")
async def financial_foundations_explain(topic: str, amount: float = 100_000.0):
    from financial_foundations.production import explain

    return explain(topic, amount=amount)


@router.get("/financial-foundations/chart-of-accounts")
async def financial_foundations_chart_of_accounts():
    from financial_foundations.production import chart_of_accounts

    return chart_of_accounts()


@router.get("/financial-foundations/chart-of-accounts/{code}")
async def financial_foundations_classify_account(code: str):
    from financial_foundations.production import classify_account

    return classify_account(code)


@router.get("/financial-foundations/transaction/{transaction_type}")
async def financial_foundations_transaction(transaction_type: str, amount: float = 100_000.0):
    from financial_foundations.production import transaction_linkage

    return transaction_linkage(transaction_type, amount=amount)


@router.get("/financial-foundations/lesson/pat-vs-cash-flow")
async def financial_foundations_pat_vs_cash_flow():
    from financial_foundations.production import pat_vs_cash_flow_lesson

    return pat_vs_cash_flow_lesson()


@router.get("/financial-foundations/simulate")
async def financial_foundations_simulate(period: int = 1):
    from financial_foundations.production import simulate

    return simulate(period=period)


@router.get("/financial-foundations/assessment")
async def financial_foundations_assessment_list(category: str | None = None, module: int | None = None):
    from financial_foundations.production import assessment_list

    return assessment_list(category=category, module=module)


@router.get("/financial-foundations/assessment/{scenario_id}")
async def financial_foundations_assessment_get(scenario_id: str):
    from financial_foundations.production import assessment_get

    return assessment_get(scenario_id)


@router.post("/financial-foundations/assessment/{scenario_id}/grade")
async def financial_foundations_assessment_grade(scenario_id: str, payload: dict[str, Any] = Body(default={})):
    from financial_foundations.production import assessment_grade

    answer = str(payload.get("answer") or "")
    return assessment_grade(scenario_id, answer)


# ---------------------------------------------------------------------------
# AGIB Phase 2 — Financial Statement Intelligence (analyst reasoning, not a
# recommendation engine). Soft-wire only; standalone engine.
# ---------------------------------------------------------------------------
@router.get("/financial-statement-intelligence/health")
async def fsi_health():
    from financial_statement_intelligence.production import health

    return health()


@router.get("/financial-statement-intelligence/dashboard")
async def fsi_dashboard():
    from financial_statement_intelligence.production import dashboard

    return dashboard()


@router.get("/financial-statement-intelligence/explain/{metric}")
async def fsi_explain_metric(metric: str):
    from financial_statement_intelligence.production import explain_metric

    return explain_metric(metric)


@router.get("/financial-statement-intelligence/sector/{sector}")
async def fsi_sector_context(sector: str):
    from financial_statement_intelligence.production import sector_context

    return sector_context(sector)


@router.get("/financial-statement-intelligence/case-studies")
async def fsi_case_studies():
    from financial_statement_intelligence.production import case_studies

    return case_studies()


@router.get("/financial-statement-intelligence/case-studies/{key}")
async def fsi_case_study(key: str):
    from financial_statement_intelligence.production import case_study

    return case_study(key)


@router.post("/financial-statement-intelligence/analyze")
async def fsi_analyze(payload: dict[str, Any] = Body(default={})):
    """Analyze a custom multi-period series supplied by the caller.

    Body: {"company": str, "sector": str | None, "periods": [{"label": str, ...StatementPeriod fields}, ...]}
    """
    from financial_statement_intelligence.production import analyze
    from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod

    company = str(payload.get("company") or "Unnamed Company")
    sector = payload.get("sector")
    rows = payload.get("periods") or []
    if not isinstance(rows, list) or len(rows) < 2:
        raise HTTPException(status_code=400, detail="periods must be a list of at least 2 period objects")
    periods = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or "label" not in row:
            raise HTTPException(status_code=400, detail=f"period[{i}] must include a 'label'")
        row = dict(row)
        label = row.pop("label")
        row.pop("sequence", None)
        try:
            periods.append(StatementPeriod(label=str(label), sequence=i + 1, **row))
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=f"period[{i}] invalid field: {exc}") from exc
    series = FinancialSeries(company=company, periods=periods, sector=sector, data_source="api_request")
    return analyze(series)


# ---------------------------------------------------------------------------
# AGIB Phase 2.6 — Institutional Financial Concepts (FC). Deterministic
# concept library (Enterprise Value, WACC, DuPont, banking/credit/market
# vocabulary, economic moats, ...). Ask integration is exclusively via
# Phase X — Knowledge Unification Layer (KUL). Deterministic gateway over
# every existing institutional knowledge source. No LLM, no new datasets.
# ---------------------------------------------------------------------------
@router.get("/knowledge-unification/health")
async def kul_health():
    from knowledge_unification.production import health

    return health()


@router.get("/knowledge-unification/registry")
async def kul_registry():
    from knowledge_unification.registry import get_registry

    return get_registry().dashboard()


@router.post("/knowledge-unification/plan")
async def kul_plan(payload: dict):
    from knowledge_unification.production import plan_and_gather

    question = str((payload or {}).get("question") or "").strip()
    ticker = (payload or {}).get("ticker")
    return plan_and_gather(question, ticker=ticker)


@router.get("/universal-knowledge/health")
async def uko_health():
    """Phase 6.0 — Universal Knowledge Orchestration provider health."""
    from universal_knowledge.production import health

    return health()


@router.get("/universal-knowledge/registry")
async def uko_registry():
    from universal_knowledge.registry import registered_providers

    return {"ok": True, "engine": "universal_knowledge", "providers": registered_providers()}


@router.post("/universal-knowledge/orchestrate")
async def uko_orchestrate(payload: dict[str, Any] = Body(default={})):
    """Plan once, gather once — the route-independent knowledge surface."""
    from universal_knowledge.production import orchestrate

    question = str((payload or {}).get("question") or "").strip()
    ticker = (payload or {}).get("ticker")
    return orchestrate(question, ticker=ticker)


# app/ui/financial_router.py + app/ui/coverage_policy.py — these routes are
# the standalone verification/documentation surface, same pattern as FF/FSI.
# ---------------------------------------------------------------------------
@router.get("/financial-concepts/health")
async def fc_health():
    from financial_concepts.production import health

    return health()


@router.get("/financial-concepts/dashboard")
async def fc_dashboard():
    from financial_concepts.production import dashboard

    return dashboard()


@router.get("/financial-concepts/concepts")
async def fc_list_concepts(module: str | None = None):
    from financial_concepts.production import list_concepts

    return list_concepts(module)


@router.get("/financial-concepts/concepts/{key}")
async def fc_concept_card(key: str):
    from financial_concepts.production import concept_card

    return concept_card(key)


@router.get("/financial-concepts/explain/{topic}")
async def fc_explain(topic: str):
    from financial_concepts.production import explain

    return explain(topic)


@router.get("/financial-concepts/search")
async def fc_search(q: str, limit: int = 5):
    from financial_concepts.production import search

    return search(q, limit=limit)


@router.get("/financial-concepts/related/{key}")
async def fc_related(key: str):
    from financial_concepts.production import related

    return related(key)


@router.get("/financial-concepts/path")
async def fc_path(start: str, end: str):
    from financial_concepts.production import path

    return path(start, end)


@router.get("/financial-concepts/graph")
async def fc_graph():
    from financial_concepts.production import graph

    return graph()


@router.get("/financial-concepts/exam/items")
async def fc_exam_items(section: str | None = None):
    from financial_concepts.production import exam_questions

    return exam_questions(section)


@router.get("/financial-concepts/exam/items/{item_id}")
async def fc_exam_run_item(item_id: str):
    from financial_concepts.production import exam_run_item

    return exam_run_item(item_id)


@router.post("/financial-concepts/exam/items/{item_id}/grade")
async def fc_exam_grade(item_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
    from financial_concepts.production import exam_grade

    return exam_grade(item_id, str(payload.get("answer") or ""))


# ---------------------------------------------------------------------------
# AGI Institutional Accounting & Financial Analysis Exam (Level 1) — the
# Phase 1/2 -> Phase 3 release gate. Debugging/verification surface only;
# not part of the Ask product path.
# ---------------------------------------------------------------------------
@router.get("/institutional-accounting-exam/health")
async def iae_health():
    from institutional_accounting_exam.production import health

    return health()


@router.get("/institutional-accounting-exam/items")
async def iae_list_items(section: str | None = None):
    from institutional_accounting_exam.production import list_items

    return list_items(section)


@router.get("/institutional-accounting-exam/items/{item_id}")
async def iae_run_item(item_id: str):
    from institutional_accounting_exam.production import run_item

    return run_item(item_id)


@router.get("/institutional-accounting-exam/run")
async def iae_run_full_exam():
    """Runs all 30 items live against the real Phase 1/2 engines and grades
    them — this can take a moment; it is a verification tool, not a
    user-facing endpoint."""
    from institutional_accounting_exam.production import run_full_exam

    return run_full_exam()


# ---------------------------------------------------------------------------
# AGIB v3.4 Track D — Institutional Communication Engine (ICE)
# Deterministic renderer of InstitutionalAnswer. Reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/institutional-communication/health")
async def institutional_communication_health():
    from institutional_communication.production import health

    return health()


@router.get("/institutional-communication/dashboard")
async def institutional_communication_dashboard():
    from institutional_communication.production import dashboard

    return dashboard()


@router.get("/institutional-communication/history")
async def institutional_communication_history(limit: int = 50):
    from institutional_communication.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGIB v3.5 — Institutional Analytical Playbooks (IAP)
# Registry + selector between Framework Selection and Reasoning.
# ---------------------------------------------------------------------------
@router.get("/institutional-playbooks/health")
async def institutional_playbooks_health():
    from institutional_playbooks.production import health

    return health()


@router.get("/institutional-playbooks/dashboard")
async def institutional_playbooks_dashboard():
    from institutional_playbooks.production import dashboard

    return dashboard()


@router.get("/institutional-playbooks/registry")
async def institutional_playbooks_registry():
    from institutional_playbooks.production import registry

    return registry()


@router.get("/institutional-playbooks/playbook/{playbook_id}")
async def institutional_playbooks_playbook(playbook_id: str):
    from institutional_playbooks.production import playbook

    return playbook(playbook_id)


@router.get("/institutional-playbooks/select")
async def institutional_playbooks_select(
    question: str,
    intent_v2: str | None = None,
    question_type: str | None = None,
    sector: str | None = None,
    concept_mode: bool = False,
    as_of: str | None = None,
):
    from institutional_playbooks.production import select

    return select(
        question=question,
        intent_v2=intent_v2,
        question_type=question_type,
        sector=sector,
        concept_mode=concept_mode,
        as_of=as_of,
    )


@router.get("/institutional-playbooks/history")
async def institutional_playbooks_history(limit: int = 50):
    from institutional_playbooks.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGIB v3.6 Phase 2 Sprint 2.1 — Institutional Evidence Graph (IEG)
# Entity-centric relationships soft-read from IERE/IERI; reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/institutional-evidence-graph/health")
async def institutional_evidence_graph_health():
    from institutional_evidence_graph.production import health

    return health()


@router.get("/institutional-evidence-graph/dashboard")
async def institutional_evidence_graph_dashboard():
    from institutional_evidence_graph.production import dashboard

    return dashboard()


@router.get("/institutional-evidence-graph/company/{ticker}")
async def institutional_evidence_graph_company(ticker: str, as_of: str | None = None):
    from institutional_evidence_graph.production import company

    return company(ticker, as_of=as_of)


@router.get("/institutional-evidence-graph/build")
async def institutional_evidence_graph_build(
    question: str,
    ticker: str | None = None,
    as_of: str | None = None,
    concept_mode: bool = False,
):
    from institutional_evidence_graph.production import build

    entities = [{"type": "company", "id": ticker, "confidence": 0.99}] if ticker else []
    return build(
        question=question,
        entities=entities,
        ticker_hint=ticker,
        as_of=as_of,
        concept_mode=concept_mode,
    )


@router.get("/institutional-evidence-graph/history")
async def institutional_evidence_graph_history(limit: int = 50):
    from institutional_evidence_graph.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGIB v3.6 Phase 2 Sprint 2.2 — Institutional Memory & Analog Intelligence
# Soft-wire only; distinct from ILM; reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/institutional-analog-intelligence/health")
async def institutional_analog_intelligence_health():
    from institutional_analog_intelligence.production import status

    return status()


@router.get("/institutional-analog-intelligence/dashboard")
async def institutional_analog_intelligence_dashboard():
    from institutional_analog_intelligence.production import board

    return board()


@router.get("/institutional-analog-intelligence/retrieve")
async def institutional_analog_intelligence_retrieve(
    question: str,
    as_of: str | None = None,
    top_k: int = 5,
):
    from institutional_analog_intelligence.production import retrieve

    return retrieve(question=question, as_of=as_of, top_k=top_k)


@router.get("/institutional-analog-intelligence/catalog")
async def institutional_analog_intelligence_catalog(limit: int = 100):
    from institutional_analog_intelligence.production import catalog

    return {"n": limit, "memories": catalog(limit=limit), "fabricated": False}


@router.get("/institutional-analog-intelligence/memory/{memory_id}")
async def institutional_analog_intelligence_memory(memory_id: str):
    from institutional_analog_intelligence.production import memory

    row = memory(memory_id)
    if not row:
        raise HTTPException(status_code=404, detail="memory_not_found")
    return row


@router.get("/institutional-analog-intelligence/audits")
async def institutional_analog_intelligence_audits(limit: int = 50):
    from institutional_analog_intelligence.production import audits

    return {"n": limit, "rows": audits(limit=limit), "fabricated": False}


# ---------------------------------------------------------------------------
# AGIB Phase 3 Sprint 3.1 — Institutional Evaluation Lab (IEL)
# Measurement-only quality engineering; reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/institutional-evaluation-lab/health")
async def institutional_evaluation_lab_health():
    from institutional_evaluation_lab.production import status

    return status()


@router.get("/institutional-evaluation-lab/dashboard")
async def institutional_evaluation_lab_dashboard():
    from institutional_evaluation_lab.production import board

    return board()


@router.get("/institutional-evaluation-lab/catalog")
async def institutional_evaluation_lab_catalog(suite: str = "institutional_1000", limit: int = 50):
    from institutional_evaluation_lab.production import catalog

    return catalog(suite=suite, limit=limit)


@router.get("/institutional-evaluation-lab/phase1-golden-universe")
async def institutional_evaluation_lab_phase1_golden_universe():
    """Phase 1 Golden Test Set — 200-stock institutional benchmark universe."""
    from institutional_evaluation_lab.production import phase1_golden_universe

    return phase1_golden_universe()


@router.get("/institutional-evaluation-lab/golden/health")
async def institutional_evaluation_lab_golden_health():
    from institutional_evaluation_lab.production import golden_evaluation_health

    return golden_evaluation_health()


@router.post("/institutional-evaluation-lab/golden/run")
async def institutional_evaluation_lab_golden_run(payload: dict[str, Any] = Body(default={})):
    """Evaluation Runner — pack → Groww price → freshness → Decision Engine → report."""
    from institutional_evaluation_lab.production import run_golden_evaluation

    body = payload or {}
    summary = run_golden_evaluation(
        limit=body.get("limit"),
        bucket=body.get("bucket"),
        force_price_refresh=bool(body.get("force_price_refresh", False)),
        persist=bool(body.get("persist", True)),
        persist_baseline=bool(body.get("persist_baseline", False)),
        compare_previous=bool(body.get("compare_previous", True)),
        release_id=body.get("release_id"),
    )
    light = {k: v for k, v in summary.items() if k not in {"rows", "drift_table"}}
    light["rows_sample"] = (summary.get("rows") or [])[:20]
    light["drift_sample"] = (summary.get("drift_table") or [])[:20]
    return light


@router.get("/institutional-evaluation-lab/golden/scorecard")
async def institutional_evaluation_lab_golden_scorecard():
    from institutional_evaluation_lab.production import golden_scorecard

    return golden_scorecard()


@router.get("/institutional-evaluation-lab/golden/drift")
async def institutional_evaluation_lab_golden_drift():
    from institutional_evaluation_lab.production import golden_drift_report

    return golden_drift_report()


@router.get("/institutional-evaluation-lab/golden/releases")
async def institutional_evaluation_lab_golden_releases():
    """List Evaluation Lab result trees under results/{release_id}/."""
    from institutional_evaluation_lab.production import golden_list_releases

    return golden_list_releases()


@router.get("/institutional-evaluation-lab/golden/releases/{release_id}")
async def institutional_evaluation_lab_golden_release(release_id: str):
    """Load a release artifact tree (Phase 6+ tests consume this)."""
    from institutional_evaluation_lab.production import golden_load_release

    row = golden_load_release(release_id)
    if not row.get("found"):
        raise HTTPException(status_code=404, detail="release_not_found")
    return row


@router.post("/institutional-evaluation-lab/golden/replay")
async def institutional_evaluation_lab_golden_replay(payload: dict[str, Any] = Body(default={})):
    """Deterministic replay of a stored release result (regression if mismatch)."""
    from institutional_evaluation_lab.production import golden_replay

    body = payload or {}
    release_id = str(body.get("release_id") or body.get("release") or "").strip()
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id_required")
    return golden_replay(
        release_id=release_id,
        ticker=body.get("ticker"),
        limit=body.get("limit"),
    )


@router.get("/governance-spec")
@router.get("/governance-spec/health")
async def governance_spec_health():
    """Governance Spec v1.0 — constitutional rule catalogue."""
    from governance_spec.registry import list_specs
    from governance_spec.v1_0.rules import spec_board

    return {
        "status": "ok",
        "active": "v1.0",
        "specs": list_specs(),
        "board": spec_board(),
    }


@router.get("/governance-spec/v1.0")
async def governance_spec_v1():
    from governance_spec.v1_0.rules import spec_board

    return spec_board()


@router.post("/institutional-evaluation-lab/phase6")
@router.post("/governance-spec/phase6")
async def governance_spec_phase6(payload: dict[str, Any] = Body(default={})):
    """Phase 6 — assert Evaluation Lab JSON against Governance Spec rule IDs."""
    from institutional_evaluation_lab.production import phase6_governance

    body = payload or {}
    release_id = str(body.get("release_id") or body.get("release") or "").strip()
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id_required")
    report = phase6_governance(
        release_id=release_id,
        spec_version=body.get("spec_version") or "v1.0",
        limit=body.get("limit"),
        persist=bool(body.get("persist", True)),
    )
    if report.get("error") == "release_not_found":
        raise HTTPException(status_code=404, detail="release_not_found")
    light = {k: v for k, v in report.items() if k != "ticker_results"}
    light["ticker_results_sample"] = (report.get("ticker_results") or [])[:15]
    return light


@router.get("/institutional-evaluation-lab/drift/health")
async def institutional_evaluation_lab_drift_health():
    from institutional_evaluation_lab.drift.production import health

    return health()


@router.post("/institutional-evaluation-lab/drift/compare")
async def institutional_evaluation_lab_drift_compare(payload: dict[str, Any] = Body(default={})):
    """PR #308 — compare two releases with reason codes, budget, review queue, release notes."""
    from institutional_evaluation_lab.production import recommendation_drift

    body = payload or {}
    previous = str(body.get("previous_release") or body.get("previous") or "").strip()
    current = str(body.get("current_release") or body.get("current") or "").strip()
    if not previous or not current:
        raise HTTPException(status_code=400, detail="previous_release_and_current_release_required")
    report = recommendation_drift(
        previous_release=previous,
        current_release=current,
        governance_failures=body.get("governance_failures"),
        persist=bool(body.get("persist", True)),
        hints=body.get("hints") if isinstance(body.get("hints"), dict) else None,
    )
    if report.get("error"):
        raise HTTPException(status_code=404, detail=report.get("error"))
    light = {k: v for k, v in report.items() if k not in {"rows", "changed_rows"}}
    light["changed_sample"] = (report.get("changed_rows") or [])[:25]
    return light


@router.get("/institutional-evaluation-lab/observability/health")
async def institutional_evaluation_lab_observability_health():
    from institutional_evaluation_lab.observability.production import health

    return health()


@router.get("/institutional-evaluation-lab/observability/{release_id}")
async def institutional_evaluation_lab_observability_release(release_id: str, persist: bool = True):
    """PR #309 — executive / sector / governance / drift / performance / coverage dashboards."""
    from institutional_evaluation_lab.production import release_observability

    pack = release_observability(release_id=release_id, persist=persist)
    if not pack.get("found"):
        raise HTTPException(status_code=404, detail="release_not_found")
    return pack


@router.post("/institutional-evaluation-lab/observability")
async def institutional_evaluation_lab_observability(payload: dict[str, Any] = Body(default={})):
    from institutional_evaluation_lab.production import release_observability

    body = payload or {}
    release_id = str(body.get("release_id") or body.get("release") or "").strip()
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id_required")
    history = body.get("previous_releases") or body.get("history") or []
    if isinstance(history, str):
        history = [x.strip() for x in history.split(",") if x.strip()]
    pack = release_observability(
        release_id=release_id,
        previous_releases=list(history) if history else None,
        persist=bool(body.get("persist", True)),
    )
    if not pack.get("found"):
        raise HTTPException(status_code=404, detail="release_not_found")
    return pack


@router.get("/institutional-evaluation-lab/iat/health")
async def institutional_evaluation_lab_iat_health():
    from institutional_evaluation_lab.iat.production import health

    return health()


@router.post("/institutional-evaluation-lab/iat")
async def institutional_evaluation_lab_iat(payload: dict[str, Any] = Body(default={})):
    """Phase 1 Institutional Acceptance Test — baseline qualification exam."""
    from institutional_evaluation_lab.production import institutional_acceptance_test

    body = payload or {}
    release_id = str(body.get("release_id") or body.get("release") or "").strip()
    if not release_id:
        raise HTTPException(status_code=400, detail="release_id_required")
    pack = institutional_acceptance_test(
        release_id=release_id,
        previous_release=(str(body["previous_release"]).strip() if body.get("previous_release") else None),
        persist=bool(body.get("persist", True)),
        freeze=bool(body.get("freeze", False)),
        require_full_universe=bool(body.get("require_full_universe", True)),
    )
    if not pack.get("found"):
        raise HTTPException(status_code=404, detail="release_not_found")
    # Keep response light
    light = {k: v for k, v in pack.items() if k not in {"thresholds"}}
    return light


@router.get("/phase2/health")
async def phase2_investment_intelligence_health():
    """Phase 2 programme registry — extends Baseline v1.0; does not replace it."""
    from phase2_investment_intelligence.production import health

    return health()


@router.get("/phase2/contracts")
async def phase2_investment_intelligence_contracts():
    """Standard engine contract for every Phase 2 workstream."""
    from phase2_investment_intelligence.production import contracts

    return contracts()


@router.get("/phase2/scorecard")
async def phase2_investment_intelligence_scorecard():
    """Intelligence Scorecard templates — Phase 2 measurement frame."""
    from phase2_investment_intelligence.production import scorecard

    return scorecard()


@router.get("/phase2/milestones")
async def phase2_investment_intelligence_milestones():
    from phase2_investment_intelligence.milestones import milestones_board

    return milestones_board()


@router.get("/phase2/workstreams")
@router.get("/phase2/programme")
async def phase2_investment_intelligence_programme():
    from phase2_investment_intelligence.production import programme

    return programme()


@router.get("/live-market-context/health")
async def live_market_context_health():
    """P2.6 Live Market Context — Phase 2.1 Sprint 1."""
    from live_market_context.production import health

    return health()


@router.get("/live-market-context/{ticker}")
async def live_market_context_ticker(ticker: str, force: bool = False, intrinsic_value: float | None = None):
    from live_market_context.production import analyse

    return analyse(ticker, force=force, intrinsic_value=intrinsic_value)


@router.post("/live-market-context")
async def live_market_context_post(payload: dict[str, Any] = Body(default={})):
    from live_market_context.production import analyse

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    intrinsic = body.get("intrinsic_value")
    try:
        intrinsic_f = float(intrinsic) if intrinsic is not None else None
    except (TypeError, ValueError):
        intrinsic_f = None
    return analyse(ticker, force=bool(body.get("force")), intrinsic_value=intrinsic_f)


@router.get("/financial-statements/health")
async def financial_statements_health():
    """FSE-01 Financial Statements Engine — canonical financial warehouse."""
    from financial_statements_engine.production import health

    return health()


@router.get("/financial-statements/dashboard")
async def financial_statements_dashboard():
    from financial_statements_engine.production import dashboard

    return dashboard()


@router.get("/financial-statements/cfdm/health")
async def financial_statements_cfdm_health():
    """FSE-03 Canonical Financial Data Model + Metric Registry."""
    from financial_statements_engine.cfdm.production import health

    return health()


@router.get("/financial-statements/parsing/health")
async def financial_statements_parsing_health():
    """FSE-04 Parsing & Normalization Engine."""
    from financial_statements_engine.parsing.production import health

    return health()


@router.get("/financial-statements/parsing/dashboard")
async def financial_statements_parsing_dashboard():
    from financial_statements_engine.parsing.production import dashboard

    return dashboard()


@router.get("/financial-statements/parsing/quality/health")
async def financial_statements_parsing_quality_health():
    """FSE-04.1 Parse Manifest, Replay & Certification Framework."""
    from financial_statements_engine.parsing.quality.production import health

    return health()


@router.get("/financial-statements/parsing/quality/dashboard")
async def financial_statements_parsing_quality_dashboard():
    from financial_statements_engine.parsing.quality.production import dashboard

    return dashboard()


@router.get("/financial-statements/parsing/manifests/{ticker}")
async def financial_statements_parsing_manifests(ticker: str):
    from financial_statements_engine.parsing.quality.production import manifests_for

    return manifests_for(ticker)


@router.get("/financial-statements/parsing/unknown-metrics")
async def financial_statements_parsing_unknown_metrics(status: str = "open"):
    from financial_statements_engine.parsing.quality.production import unknown_metrics

    return unknown_metrics(status=status)


@router.post("/financial-statements/parsing/replay")
async def financial_statements_parsing_replay(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.parsing.quality.production import run_replay

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    evidence_id = str(body.get("evidence_id") or "").strip()
    if not ticker or not evidence_id:
        raise HTTPException(status_code=400, detail="ticker_and_evidence_id_required")
    return run_replay(ticker, evidence_id, prior_manifest_id=body.get("prior_manifest_id"))


@router.post("/financial-statements/parsing/certify")
async def financial_statements_parsing_certify():
    from financial_statements_engine.parsing.quality.production import run_certification

    return run_certification()


@router.post("/financial-statements/parsing/benchmark")
async def financial_statements_parsing_benchmark():
    from financial_statements_engine.parsing.quality.production import run_benchmark_suite

    return run_benchmark_suite()


@router.get("/financial-statements/parsing/coverage/health")
async def financial_statements_parsing_coverage_health():
    """FSE-04.2 Evidence Coverage Matrix & Extraction Audit."""
    from financial_statements_engine.parsing.coverage.production import health

    return health()


@router.get("/financial-statements/parsing/coverage/dashboard")
async def financial_statements_parsing_coverage_dashboard():
    from financial_statements_engine.parsing.coverage.production import dashboard

    return dashboard()


@router.get("/financial-statements/parsing/coverage/analytics")
async def financial_statements_parsing_coverage_analytics():
    from financial_statements_engine.parsing.coverage.production import analytics

    return analytics()


@router.get("/financial-statements/parsing/coverage/matrices/{ticker}")
async def financial_statements_parsing_coverage_matrices(ticker: str):
    from financial_statements_engine.parsing.coverage.production import matrices_for

    return matrices_for(ticker)


@router.get("/financial-statements/parsing/coverage/matrices/{ticker}/{matrix_id}")
async def financial_statements_parsing_coverage_matrix_detail(ticker: str, matrix_id: str):
    from financial_statements_engine.parsing.coverage.production import matrix_detail

    return matrix_detail(ticker, matrix_id)


@router.get("/financial-statements/parsing/coverage/history/{ticker}")
async def financial_statements_parsing_coverage_history(ticker: str, document_hash: str | None = None):
    from financial_statements_engine.parsing.coverage.production import history_for

    return history_for(ticker, document_hash=document_hash)


@router.post("/financial-statements/parsing/coverage/diff")
async def financial_statements_parsing_coverage_diff(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.parsing.coverage.production import diff_matrices

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    old_id = str(body.get("old_matrix_id") or "").strip()
    new_id = str(body.get("new_matrix_id") or "").strip()
    if not ticker or not old_id or not new_id:
        raise HTTPException(status_code=400, detail="ticker_old_matrix_id_new_matrix_id_required")
    return diff_matrices(ticker, old_id, new_id)


@router.get("/financial-statements/parsing/pcc/health")
async def financial_statements_parsing_pcc_health():
    """FSE-04.3 Production Certification Corpus & Golden Dataset."""
    from financial_statements_engine.parsing.pcc.production import health

    return health()


@router.get("/financial-statements/parsing/pcc/dashboard")
async def financial_statements_parsing_pcc_dashboard():
    from financial_statements_engine.parsing.pcc.production import dashboard

    return dashboard()


@router.get("/financial-statements/parsing/pcc/analytics")
async def financial_statements_parsing_pcc_analytics():
    from financial_statements_engine.parsing.pcc.production import analytics

    return analytics()


@router.get("/financial-statements/parsing/pcc/cases")
async def financial_statements_parsing_pcc_cases(sector: str | None = None):
    from financial_statements_engine.parsing.pcc.production import cases

    return cases(sector=sector)


@router.get("/financial-statements/parsing/pcc/history")
async def financial_statements_parsing_pcc_history(limit: int = 50):
    from financial_statements_engine.parsing.pcc.production import history

    return history(limit=limit)


@router.get("/financial-statements/parsing/pcc/certifications/{certification_id}")
async def financial_statements_parsing_pcc_certification(certification_id: str):
    from financial_statements_engine.parsing.pcc.production import certification_detail

    return certification_detail(certification_id)


@router.post("/financial-statements/parsing/pcc/certify")
async def financial_statements_parsing_pcc_certify(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.parsing.pcc.production import run_certification

    body = payload or {}
    sector = body.get("sector")
    return run_certification(sector=str(sector) if sector else None)


@router.get("/financial-statements/validation/health")
async def financial_statements_validation_health():
    """FSE-05 Validation & Financial Quality Engine."""
    from financial_statements_engine.validation.production import health

    return health()


@router.get("/financial-statements/validation/dashboard")
async def financial_statements_validation_dashboard():
    from financial_statements_engine.validation.production import dashboard

    return dashboard()


@router.get("/financial-statements/validation/reports")
async def financial_statements_validation_reports(ticker: str | None = None):
    from financial_statements_engine.validation.production import reports_for

    return reports_for(ticker=ticker)


@router.get("/financial-statements/validation/reports/{ticker}/{validation_id}")
async def financial_statements_validation_report_detail(ticker: str, validation_id: str):
    from financial_statements_engine.validation.production import report_detail

    return report_detail(ticker, validation_id)


@router.post("/financial-statements/validation/run")
async def financial_statements_validation_run(payload: dict[str, Any] = Body(default={})):
    """Validate a Canonical Draft (inline JSON or draft_path). Never edits the draft."""
    from financial_statements_engine.validation.production import run_validation, run_validation_file

    body = payload or {}
    publish = bool(body.get("publish", True))
    if body.get("draft_path"):
        return run_validation_file(str(body["draft_path"]), publish=publish)
    draft = body.get("draft")
    if not isinstance(draft, dict):
        raise HTTPException(status_code=400, detail="draft_or_draft_path_required")
    return run_validation(draft, context=body.get("context"), publish=publish)


@router.get("/financial-statements/warehouse/health")
def financial_statements_warehouse_health():
    """FSE-06 Financial Warehouse."""
    from financial_statements_engine.financial_warehouse.production import health

    return health()


@router.get("/financial-statements/warehouse/dashboard")
def financial_statements_warehouse_dashboard():
    from financial_statements_engine.financial_warehouse.production import dashboard

    return dashboard()


@router.get("/financial-statements/warehouse/latest/{ticker}")
def financial_statements_warehouse_latest(ticker: str, statement_type: str | None = None):
    from financial_statements_engine.financial_warehouse.production import get_latest

    return get_latest(ticker, statement_type=statement_type)


@router.get("/financial-statements/warehouse/metrics/{ticker}/{metric}")
def financial_statements_warehouse_metric_history(ticker: str, metric: str):
    from financial_statements_engine.financial_warehouse.production import get_metric_history

    return get_metric_history(ticker, metric)


@router.get("/financial-statements/warehouse/timeline/{ticker}")
def financial_statements_warehouse_timeline(ticker: str):
    from financial_statements_engine.financial_warehouse.production import get_timeline

    return get_timeline(ticker)


@router.get("/financial-statements/warehouse/view/{ticker}/{view}")
def financial_statements_warehouse_view(ticker: str, view: str, as_of: str | None = None):
    from financial_statements_engine.financial_warehouse.production import time_travel

    return time_travel(ticker, view, as_of=as_of)


@router.get("/financial-statements/warehouse/contracts")
def financial_statements_warehouse_contracts():
    from financial_statements_engine.financial_warehouse.production import contracts

    return contracts()


@router.get("/financial-statements/warehouse/contracts/{contract_id}/{ticker}")
def financial_statements_warehouse_contract(contract_id: str, ticker: str, view: str | None = None, metric: str | None = None):
    from financial_statements_engine.financial_warehouse.production import contract

    kwargs: dict[str, Any] = {}
    if view:
        kwargs["view"] = view
    if metric:
        kwargs["metric"] = metric
    return contract(contract_id, ticker, **kwargs)


@router.get("/financial-statements/warehouse/restatements")
def financial_statements_warehouse_restatements(company_id: str | None = None):
    from financial_statements_engine.financial_warehouse.production import restatements

    return restatements(company_id=company_id)


@router.get("/financial-statements/derived-metrics/health")
async def financial_statements_dme_health():
    """FSE-07 Derived Metrics Engine."""
    from financial_statements_engine.derived_metrics.production import health

    return health()


@router.get("/financial-statements/derived-metrics/dashboard")
async def financial_statements_dme_dashboard():
    from financial_statements_engine.derived_metrics.production import dashboard

    return dashboard()


@router.post("/financial-statements/derived-metrics/calculate/{ticker}")
async def financial_statements_dme_calculate(ticker: str, payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.derived_metrics.production import calculate

    body = payload or {}
    metrics = body.get("metrics")
    if metrics is not None and not isinstance(metrics, list):
        raise HTTPException(status_code=400, detail="metrics_must_be_list")
    persist = bool(body.get("persist", True))
    return calculate(ticker, metrics=metrics, persist=persist)


@router.get("/financial-statements/derived-metrics/formulas")
async def financial_statements_dme_formulas(category: str | None = None):
    from financial_statements_engine.derived_metrics.production import formulas

    return formulas(category=category)


@router.get("/financial-statements/derived-metrics/lineage/{metric_name}")
async def financial_statements_dme_lineage(metric_name: str):
    from financial_statements_engine.derived_metrics.production import lineage

    return lineage(metric_name)


@router.get("/financial-statements/derived-metrics/contracts")
async def financial_statements_dme_contracts():
    from financial_statements_engine.derived_metrics.production import contracts

    return contracts()


@router.get("/financial-statements/derived-metrics/contracts/{contract_id}/{ticker}")
async def financial_statements_dme_contract(contract_id: str, ticker: str):
    from financial_statements_engine.derived_metrics.production import contract

    return contract(contract_id, ticker)


@router.get("/financial-statements/derived-metrics/{ticker}")
async def financial_statements_dme_company(ticker: str):
    from financial_statements_engine.derived_metrics.production import company_metrics

    return company_metrics(ticker)


@router.get("/financial-statements/derived-metrics/{ticker}/{metric_name}")
async def financial_statements_dme_metric(ticker: str, metric_name: str, period: str | None = None):
    from financial_statements_engine.derived_metrics.production import get_metric

    return get_metric(ticker, metric_name, period=period)


@router.get("/financial-statements/evidence-coverage/health")
async def financial_statements_ecd_health():
    """FSE-ECD Evidence Coverage Dashboard — how many companies do we have?"""
    from financial_statements_engine.evidence_coverage.production import health

    return health()


@router.get("/financial-statements/evidence-coverage/dashboard")
async def financial_statements_ecd_dashboard(universe: str = "nifty500", rows: bool = False):
    from financial_statements_engine.evidence_coverage.production import dashboard

    return dashboard(universe, include_rows=rows)


@router.get("/financial-statements/evidence-coverage/company/{ticker}")
async def financial_statements_ecd_company(ticker: str):
    from financial_statements_engine.evidence_coverage.production import company

    return company(ticker)


@router.post("/financial-statements/parsing/run")
async def financial_statements_parsing_run(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.parsing.production import parse_bytes
    import base64

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    raw_b64 = body.get("bytes_b64")
    if not raw_b64:
        raise HTTPException(status_code=400, detail="bytes_b64_required")
    try:
        data = base64.b64decode(str(raw_b64))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid_bytes_b64:{exc}") from exc
    return parse_bytes(
        ticker,
        data,
        document_type=str(body.get("document_type") or "xbrl"),
        period_end=body.get("period_end"),
        period_type=body.get("period_type"),
        consolidation_type=str(body.get("consolidation_type") or "consolidated"),
        source=str(body.get("source") or "nse_xbrl"),
        evidence_id=body.get("evidence_id"),
    )


@router.get("/financial-statements/schema-evolution/health")
async def financial_statements_schema_evolution_health():
    from financial_statements_engine.schema_evolution.production import health

    return health()


@router.get("/financial-statements/schema-evolution/resolve")
async def financial_statements_schema_evolution_resolve(
    label: str,
    as_of: str | None = None,
    reporting_standard: str = "IND_AS",
    taxonomy: str | None = None,
):
    from financial_statements_engine.schema_evolution.production import resolve_payload

    return resolve_payload(label, as_of=as_of, reporting_standard=reporting_standard, taxonomy=taxonomy)


@router.get("/financial-statements/metrics")
async def financial_statements_metrics(category: str | None = None, appendix_only: bool = False):
    from financial_statements_engine.metric_registry.production import metrics_payload

    return metrics_payload(category=category, appendix_only=bool(appendix_only))


@router.get("/financial-statements/metrics/resolve")
async def financial_statements_metrics_resolve(name: str):
    from financial_statements_engine.metric_registry.production import resolve_payload

    return resolve_payload(name)


@router.get("/financial-statements/metrics/{metric}")
async def financial_statements_metric_get(metric: str):
    from financial_statements_engine.metric_registry.service import get_metric
    from financial_statements_engine.metric_registry.schema import REGISTRY_VERSION, WORKSTREAM_ID

    rec = get_metric(metric)
    if not rec:
        raise HTTPException(status_code=404, detail="metric_not_found")
    return {
        "ok": True,
        "metric": rec,
        "registry_version": REGISTRY_VERSION,
        "workstream_id": WORKSTREAM_ID,
        "issues_recommendations": False,
    }


@router.get("/financial-statements/orchestrator/health")
async def financial_statements_orchestrator_health():
    """FSE-00 Pipeline Orchestrator — coordinates engines only."""
    from financial_statements_engine.orchestrator.production import health

    return health()


@router.get("/financial-statements/orchestrator/dashboard")
async def financial_statements_orchestrator_dashboard():
    from financial_statements_engine.orchestrator.production import dashboard

    return dashboard()


@router.get("/financial-statements/orchestrator/workflows")
async def financial_statements_orchestrator_workflows(state: str | None = None, limit: int = 100):
    from financial_statements_engine.orchestrator.production import workflows

    return workflows(state=state, limit=limit)


@router.get("/financial-statements/orchestrator/workflows/{workflow_id}")
async def financial_statements_orchestrator_workflow(workflow_id: str):
    from financial_statements_engine.orchestrator.production import workflow_detail

    return workflow_detail(workflow_id)


@router.get("/financial-statements/orchestrator/queue")
async def financial_statements_orchestrator_queue(limit: int = 100):
    from financial_statements_engine.orchestrator.production import queue

    return queue(limit=limit)


@router.get("/financial-statements/orchestrator/history")
async def financial_statements_orchestrator_history(limit: int = 100):
    from financial_statements_engine.orchestrator.production import history

    return history(limit=limit)


@router.get("/financial-statements/orchestrator/dlq")
async def financial_statements_orchestrator_dlq(limit: int = 100):
    """Dead Letter Queue — exhausted retries awaiting manual replay."""
    from financial_statements_engine.orchestrator.production import dlq

    return dlq(limit=limit)


@router.post("/financial-statements/orchestrator/start")
async def financial_statements_orchestrator_start(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.orchestrator.production import start

    return start(payload or {}, run=bool((payload or {}).get("run", True)))


@router.post("/financial-statements/orchestrator/retry/{workflow_id}")
async def financial_statements_orchestrator_retry(workflow_id: str):
    from financial_statements_engine.orchestrator.production import retry

    return retry(workflow_id)


@router.post("/financial-statements/orchestrator/replay/{workflow_id}")
async def financial_statements_orchestrator_replay(workflow_id: str, payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.orchestrator.production import replay

    body = payload or {}
    return replay(workflow_id, from_stage=body.get("from_stage"))


@router.get("/financial-statements/verification/dashboard")
async def financial_statements_verification_dashboard():
    """FSE-02.2 Production Verification Mission Control."""
    from financial_statements_engine.verification.production import dashboard

    return dashboard()


@router.get("/financial-statements/verification/workflows")
async def financial_statements_verification_workflows(state: str | None = None, limit: int = 100):
    from financial_statements_engine.verification.production import workflows

    return workflows(state=state, limit=max(1, min(int(limit), 1000)))


@router.get("/financial-statements/verification/workflows/{workflow_id}")
async def financial_statements_verification_workflow(workflow_id: str):
    from financial_statements_engine.verification.production import workflow_detail

    return workflow_detail(workflow_id)


@router.get("/financial-statements/verification/provenance/{workflow_id}")
async def financial_statements_verification_provenance(workflow_id: str):
    from financial_statements_engine.verification.production import workflow_provenance

    return workflow_provenance(workflow_id)


@router.get("/financial-statements/verification/report/{workflow_id}")
async def financial_statements_verification_report(workflow_id: str):
    from financial_statements_engine.verification.production import workflow_report

    return workflow_report(workflow_id)


@router.get("/financial-statements/verification/sla")
async def financial_statements_verification_sla():
    from financial_statements_engine.verification.production import sla

    return sla()


@router.post("/financial-statements/verification/run/{company}")
async def financial_statements_verification_run(company: str):
    """Run end-to-end production verification for one company."""
    from financial_statements_engine.verification.production import run_company

    ticker = str(company or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="company_required")
    return run_company(ticker)


@router.get("/financial-statements/collection/health")
async def financial_statements_collection_health():
    """FSE-02 Data Sources & Collection Pipeline."""
    from financial_statements_engine.collection.production import health

    return health()


@router.get("/financial-statements/collection/dashboard")
async def financial_statements_collection_dashboard():
    from financial_statements_engine.collection.production import dashboard

    return dashboard()


@router.get("/financial-statements/collection/ingest-dashboard")
async def financial_statements_ingest_dashboard():
    """FSE-02.1 Mission Control — canonical ingestion metrics."""
    from financial_statements_engine.collection.production import ingest_dashboard

    return ingest_dashboard()


@router.get("/financial-statements/collection/source-coverage")
async def financial_statements_source_coverage():
    """FSE-02.3 Mission Control — official source coverage dashboard."""
    from financial_statements_engine.collection.production import source_coverage

    return source_coverage()


@router.get("/financial-statements/collection/source-registry")
async def financial_statements_source_registry():
    """FSE-02.3 Source Registry (priority, health, filing types)."""
    from financial_statements_engine.collection.production import source_registry

    return source_registry()


@router.get("/financial-statements/collection/events")
async def financial_statements_collection_events(limit: int = 50):
    from financial_statements_engine.collection.production import recent_events

    return recent_events(max(1, min(int(limit), 500)))


@router.post("/financial-statements/collection/run")
async def financial_statements_collection_run(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.collection.production import collect_ticker

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    mode = str(body.get("mode") or "live")
    if mode not in ("live", "historical"):
        mode = "live"
    return collect_ticker(ticker, mode=mode)


@router.post("/financial-statements/collection/run-official")
async def financial_statements_collection_run_official(payload: dict[str, Any] = Body(default={})):
    """FSE-02.3 multi-source official collect → FSE-02 ingest()."""
    from financial_statements_engine.collection.production import collect_official

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    return collect_official(
        ticker.upper(),
        filing_type=body.get("filing_type"),
        period_end=body.get("period_end"),
        company_name=body.get("company_name"),
    )


@router.get("/financial-statements/fdo/dashboard")
async def financial_statements_fdo_dashboard(universe: str = "gold"):
    """FSE-FDO Phase 1 — Financial Data Operations Mission Control."""
    from financial_statements_engine.fdo.production import dashboard

    return dashboard(universe)


@router.get("/financial-statements/fdo/schedule")
async def financial_statements_fdo_schedule(universe: str = "gold", limit: int = 50):
    from financial_statements_engine.fdo.production import schedule

    return schedule(universe, limit=max(1, min(int(limit), 500)))


@router.get("/financial-statements/fdo/alerts")
async def financial_statements_fdo_alerts(universe: str = "gold"):
    from financial_statements_engine.fdo.production import alerts

    return alerts(universe)


@router.get("/financial-statements/coverage")
async def financial_statements_fdo_coverage(universe: str = "gold"):
    """FDO company coverage / completeness aggregate."""
    from financial_statements_engine.fdo.production import coverage

    return coverage(universe)


@router.get("/financial-statements/coverage/{company}")
async def financial_statements_fdo_coverage_company(company: str):
    from financial_statements_engine.fdo.production import coverage_company

    return coverage_company(company.upper())


@router.get("/financial-statements/source-health")
async def financial_statements_source_health():
    """FDO per-source availability / success / latency comparison."""
    from financial_statements_engine.fdo.production import source_health

    return source_health()


@router.get("/financial-statements/{ticker}")
async def financial_statements_ticker(ticker: str):
    from financial_statements_engine.production import get_statements

    return get_statements(ticker)


@router.post("/financial-statements/ingest")
async def financial_statements_ingest(payload: dict[str, Any] = Body(default={})):
    from financial_statements_engine.production import ingest_and_publish

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    try:
        max_periods = max(0, min(int(body.get("max_periods", 8)), 40))
    except (TypeError, ValueError):
        max_periods = 8
    return ingest_and_publish(
        ticker,
        publish=bool(body.get("publish", True)),
        allow_flagged=bool(body.get("allow_flagged", True)),
        max_periods=max_periods,
    )


@router.get("/earnings-intelligence/health")
async def earnings_intelligence_health():
    """P2.1 Financial Statements & Earnings Intelligence — NSE XBRL extraction adapter under FSE-01."""
    from earnings_intelligence.production import health

    return health()


@router.get("/earnings-intelligence/{ticker}")
async def earnings_intelligence_ticker(
    ticker: str,
    force: bool = False,
    quarterly_xbrl: int = 4,
    annual_xbrl: int = 2,
    skip_xbrl: bool = False,
):
    from earnings_intelligence.production import analyse

    return analyse(
        ticker,
        force=force,
        quarterly_xbrl=max(0, min(int(quarterly_xbrl), 20)),
        annual_xbrl=max(0, min(int(annual_xbrl), 15)),
        skip_xbrl=bool(skip_xbrl),
        persist=False,
    )


@router.post("/earnings-intelligence")
async def earnings_intelligence_post(payload: dict[str, Any] = Body(default={})):
    from earnings_intelligence.production import analyse

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    try:
        q = max(0, min(int(body.get("quarterly_xbrl", 4)), 20))
    except (TypeError, ValueError):
        q = 4
    try:
        a = max(0, min(int(body.get("annual_xbrl", 2)), 15))
    except (TypeError, ValueError):
        a = 2
    return analyse(
        ticker,
        force=bool(body.get("force")),
        quarterly_xbrl=q,
        annual_xbrl=a,
        skip_xbrl=bool(body.get("skip_xbrl")),
        persist=bool(body.get("persist", False)),
    )


@router.get("/ownership-intelligence/health")
async def ownership_intelligence_health():
    """P2.3 Ownership Intelligence — NSE Master + XBRL evidence layer."""
    from ownership_intelligence.production import health

    return health()


@router.get("/ownership-intelligence/{ticker}")
async def ownership_intelligence_ticker(
    ticker: str,
    force: bool = False,
    xbrl_quarters: int = 2,
    skip_xbrl: bool = False,
):
    from ownership_intelligence.production import analyse

    return analyse(
        ticker,
        force=force,
        xbrl_quarters=max(0, min(int(xbrl_quarters), 8)),
        skip_xbrl=bool(skip_xbrl),
        persist=False,
    )


@router.post("/ownership-intelligence")
async def ownership_intelligence_post(payload: dict[str, Any] = Body(default={})):
    from ownership_intelligence.production import analyse

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    xq = body.get("xbrl_quarters", 2)
    try:
        xq_i = max(0, min(int(xq), 8))
    except (TypeError, ValueError):
        xq_i = 2
    return analyse(
        ticker,
        force=bool(body.get("force")),
        xbrl_quarters=xq_i,
        skip_xbrl=bool(body.get("skip_xbrl")),
        persist=bool(body.get("persist", False)),
    )


@router.get("/valuation-intelligence/health")
async def valuation_intelligence_health():
    """P2.2 Valuation Intelligence — peer-relative + historical synthesis (no BUY/SELL)."""
    from valuation_intelligence.production import health

    return health()


@router.get("/valuation-intelligence/{ticker}")
async def valuation_intelligence_ticker(
    ticker: str,
    force: bool = False,
    max_peers: int = 5,
    include_secondary: bool = False,
):
    from valuation_intelligence.production import analyse

    return analyse(
        ticker,
        force=force,
        max_peers=max(1, min(int(max_peers), 12)),
        include_secondary=bool(include_secondary),
        persist=False,
    )


@router.post("/valuation-intelligence")
async def valuation_intelligence_post(payload: dict[str, Any] = Body(default={})):
    from valuation_intelligence.production import analyse

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    try:
        mp = max(1, min(int(body.get("max_peers", 5)), 12))
    except (TypeError, ValueError):
        mp = 5
    return analyse(
        ticker,
        force=bool(body.get("force")),
        max_peers=mp,
        include_secondary=bool(body.get("include_secondary")),
        persist=bool(body.get("persist", False)),
    )


@router.get("/valuation-intelligence-ic10")
async def valuation_intelligence_ic10(max_peers: int = 3):
    from valuation_intelligence.production import ic10_smoke

    return ic10_smoke(max_peers=max(1, min(int(max_peers), 8)))


@router.get("/valuation-intelligence/live-snapshots/health")
async def live_valuation_snapshot_health():
    from valuation_intelligence.live_snapshots import health
    return health()


@router.get("/valuation-intelligence/live-snapshots/{symbol}")
async def live_valuation_snapshot_latest(symbol: str):
    from valuation_intelligence.live_snapshots import latest_state
    return latest_state(symbol)


@router.get("/valuation-intelligence/live-snapshots/{symbol}/history")
async def live_valuation_snapshot_history(symbol: str, limit: int = 100):
    from valuation_intelligence.live_snapshots import snapshot_history
    return snapshot_history(symbol, limit=limit)


@router.post("/valuation-intelligence/live-snapshots/{symbol}/refresh", dependencies=[Depends(require_token)])
async def live_valuation_snapshot_refresh(symbol: str, reason: str | None = None):
    from valuation_intelligence.live_snapshots import refresh_symbol
    return await refresh_symbol(symbol, reason=reason)


@router.get("/ikl/health")
async def ikl_health():
    """Institutional Knowledge Intelligence Layer — Gather → Memory → Ask."""
    from institutional_knowledge_layer.production import health

    return health()


@router.get("/ikl/memory/{ticker}")
async def ikl_memory_ticker(ticker: str):
    """Read persistent IKL company memory (incremental institutional profile)."""
    from institutional_knowledge_layer.production import memory_snapshot

    return memory_snapshot(ticker)


@router.post("/ikl/learn")
async def ikl_learn(payload: dict[str, Any] = Body(default={})):
    """Soft writeback: extract knowledge from a document payload into IKL memories."""
    from institutional_knowledge_layer.production import on_document

    return on_document(payload or {})


@router.get("/company-memory/health")
async def company_memory_health():
    """Company Memory Knowledge Compiler — persistent institutional intelligence."""
    from company_memory.production import health

    return health()


@router.get("/company-memory/{ticker}")
async def company_memory_ticker(
    ticker: str,
    force: bool = False,
    cache: bool = False,
    persist: bool = True,
):
    from company_memory.production import compile as memory_compile

    return memory_compile(
        ticker,
        force=force,
        use_cache=bool(cache),
        persist=bool(persist),
    )


@router.get("/company-memory-ic10")
async def company_memory_ic10(persist: bool = False):
    from company_memory.production import ic10_compile

    return ic10_compile(persist=bool(persist))


@router.get("/knowledge-delta-engine/health")
async def knowledge_delta_engine_health():
    """P3.1 Knowledge Delta Engine — incremental CompanyMemory compilation."""
    from knowledge_delta_engine.production import health

    return health()


@router.get("/knowledge-delta-engine/{ticker}")
async def knowledge_delta_engine_compile(
    ticker: str,
    force: bool = False,
    persist: bool = True,
):
    from knowledge_delta_engine.production import compile_incremental

    return compile_incremental(ticker, force=bool(force), persist=bool(persist))


@router.post("/knowledge-delta-engine")
async def knowledge_delta_engine_post(payload: dict[str, Any] = Body(default={})):
    from knowledge_delta_engine.production import compile_incremental

    body = payload or {}
    ticker = str(body.get("ticker") or "").strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker_required")
    return compile_incremental(
        ticker,
        force=bool(body.get("force")),
        persist=bool(body.get("persist", True)),
        reason=body.get("reason"),
    )


@router.get("/knowledge-delta-engine/{ticker}/versions")
async def knowledge_delta_engine_versions(ticker: str):
    from knowledge_delta_engine.production import versions

    return versions(ticker)


@router.get("/knowledge-delta-engine/{ticker}/versions/{ver}")
async def knowledge_delta_engine_version(ticker: str, ver: int):
    from knowledge_delta_engine.production import version

    return version(ticker, int(ver))


@router.get("/knowledge-delta-engine/{ticker}/ledger")
async def knowledge_delta_engine_ledger(ticker: str):
    from knowledge_delta_engine.production import ledger

    return ledger(ticker)


@router.get("/knowledge-delta-engine/{ticker}/explain")
async def knowledge_delta_engine_explain(
    ticker: str,
    topic: str = "management_confidence",
):
    from knowledge_delta_engine.production import explain

    return explain(ticker, topic=topic)


@router.get("/investment-knowledge-graph/health")
async def investment_knowledge_graph_health():
    """P3.2 Investment Knowledge Graph — relationship intelligence façade."""
    from investment_knowledge_graph.production import health

    return health()


@router.get("/investment-knowledge-graph/theme/{name}")
async def investment_knowledge_graph_theme(name: str):
    from investment_knowledge_graph.production import theme

    return theme(name)


@router.get("/investment-knowledge-graph/macro")
async def investment_knowledge_graph_macro(chain_id: str | None = None):
    from investment_knowledge_graph.production import macro

    return macro(chain_id)


@router.get("/investment-knowledge-graph/{ticker}/retrieve")
async def investment_knowledge_graph_retrieve(
    ticker: str,
    include_cid: bool = False,
    persist_delta: bool = False,
):
    from investment_knowledge_graph.production import retrieve

    return retrieve(
        ticker,
        include_cid=bool(include_cid),
        compile_delta=True,
        persist_delta=bool(persist_delta),
    )


@router.get("/investment-knowledge-graph/{ticker}")
async def investment_knowledge_graph_analyse(ticker: str):
    from investment_knowledge_graph.production import analyse

    return analyse(ticker)


@router.get("/opportunity-intelligence/health")
async def opportunity_intelligence_health():
    """P4.5 Opportunity Intelligence — institutional research prioritisation (no BUY/SELL)."""
    from opportunity_intelligence.production import health

    return health()


@router.get("/opportunity-intelligence/top")
async def opportunity_intelligence_top(limit: int = 10):
    from opportunity_intelligence.production import top

    return top(limit=max(1, min(int(limit), 50)))


@router.get("/opportunity-intelligence/watchlist")
async def opportunity_intelligence_watchlist():
    from opportunity_intelligence.production import watchlist

    return watchlist()


@router.get("/opportunity-intelligence/catalysts")
async def opportunity_intelligence_catalysts():
    from opportunity_intelligence.production import catalysts

    return catalysts()


@router.get("/opportunity-intelligence/research-priority")
async def opportunity_intelligence_research_priority():
    from opportunity_intelligence.production import research_priority_board

    return research_priority_board()


@router.get("/opportunity-intelligence-ic10")
async def opportunity_intelligence_ic10():
    from opportunity_intelligence.production import ic10_smoke

    return ic10_smoke()


@router.get("/opportunity-intelligence/{ticker}")
async def opportunity_intelligence_ticker(ticker: str):
    from opportunity_intelligence.production import analyse

    return analyse(ticker, persist_memory=False)


@router.get("/investment-operations/health")
async def investment_operations_health():
    """P5 Investment Operations Layer — orchestration façade (not an intelligence engine)."""
    from investment_operations.production import health

    return health()


@router.get("/investment-operations/morning-office")
async def investment_operations_morning_office(holdings: str | None = None):
    from investment_operations.production import morning_office

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return morning_office(holdings=h, include_soft_reasoning=False)


@router.get("/investment-operations/research-queue")
async def investment_operations_research_queue(holdings: str | None = None, limit: int = 25):
    from investment_operations.production import research_queue

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return research_queue(holdings=h, include_soft_reasoning=False)


@router.get("/investment-operations/portfolio")
async def investment_operations_portfolio(holdings: str | None = None):
    from investment_operations.production import portfolio

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return portfolio(holdings=h, include_soft_reasoning=False)


@router.get("/investment-operations/alerts")
async def investment_operations_alerts(holdings: str | None = None):
    from investment_operations.production import alerts

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return alerts(holdings=h, include_soft_reasoning=False)


@router.get("/investment-operations/catalysts")
async def investment_operations_catalysts():
    from investment_operations.production import catalysts

    return catalysts(include_soft_reasoning=False)


@router.get("/investment-operations/daily-brief")
async def investment_operations_daily_brief(brief_type: str = "morning", holdings: str | None = None):
    from investment_operations.production import daily_brief

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return daily_brief(brief_type=brief_type, holdings=h, include_soft_reasoning=False)


@router.get("/investment-operations/metrics")
async def investment_operations_metrics():
    from investment_operations.production import metrics

    return metrics(include_soft_reasoning=False)


@router.get("/investment-operations/workspace/{ticker}")
async def investment_operations_workspace(ticker: str):
    from investment_operations.production import workspace

    return workspace(ticker, include_soft_reasoning=True)


@router.get("/investment-operations/decision-replay/{ticker}")
async def investment_operations_decision_replay(ticker: str, version: int | None = None):
    from investment_operations.production import decision_replay

    return decision_replay(ticker, version=version)


@router.get("/investment-operations/monitoring")
async def investment_operations_monitoring():
    from investment_operations.production import monitoring

    return monitoring(include_soft_reasoning=False)


@router.get("/investment-operations-ic10")
async def investment_operations_ic10():
    from investment_operations.production import ic10_smoke

    return ic10_smoke()


@router.get("/autonomous-research/health")
async def autonomous_research_health():
    """P6 Autonomous Research Office — continuous research workflows (no BUY/SELL)."""
    from autonomous_research.production import health

    return health()


@router.get("/autonomous-research/status")
async def autonomous_research_status(holdings: str | None = None):
    from autonomous_research.production import status

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return status(holdings=h)


@router.get("/autonomous-research/planner")
async def autonomous_research_planner(holdings: str | None = None):
    from autonomous_research.production import planner

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return planner(holdings=h)


@router.get("/autonomous-research/tasks")
async def autonomous_research_tasks(holdings: str | None = None):
    from autonomous_research.production import tasks

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return tasks(holdings=h)


@router.get("/autonomous-research/watchlists")
async def autonomous_research_watchlists(holdings: str | None = None):
    from autonomous_research.production import watchlists

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return watchlists(holdings=h)


@router.get("/autonomous-research/themes")
async def autonomous_research_themes():
    from autonomous_research.production import themes

    return themes()


@router.get("/autonomous-research/coverage")
async def autonomous_research_coverage():
    from autonomous_research.production import coverage

    return coverage()


@router.get("/autonomous-research/research/{ticker}")
async def autonomous_research_ticker(ticker: str):
    from autonomous_research.production import research

    return research(ticker)


@router.get("/autonomous-research/publications")
async def autonomous_research_publications(holdings: str | None = None):
    from autonomous_research.production import publications

    h = [x.strip().upper() for x in (holdings or "").split(",") if x.strip()] or None
    return publications(holdings=h)


@router.get("/autonomous-research/qa")
async def autonomous_research_qa():
    from autonomous_research.production import qa

    return qa()


@router.get("/autonomous-research/learning")
async def autonomous_research_learning():
    from autonomous_research.production import learning

    return learning()


@router.get("/autonomous-research-ic10")
async def autonomous_research_ic10():
    from autonomous_research.production import ic10_smoke

    return ic10_smoke()


@router.get("/production-hardening/health")
async def production_hardening_health():
    """Production Hardening — scale, observability, gold regression, DQ, performance."""
    from production_hardening.production import health

    return health()


@router.get("/production-hardening/dashboard")
async def production_hardening_dashboard():
    from production_hardening.production import dashboard

    return dashboard()


@router.get("/production-hardening/regression")
async def production_hardening_regression():
    from production_hardening.production import regression

    return regression(update_baseline=False)


@router.post("/production-hardening/regression/baseline")
async def production_hardening_regression_baseline():
    from production_hardening.production import regression

    return regression(update_baseline=True)


@router.get("/production-hardening/scale")
async def production_hardening_scale(
    preset: str = "smoke",
    limit: int | None = None,
    mode: str = "opportunity",
):
    from production_hardening.production import scale

    return scale(preset=preset, limit=limit, mode=mode)


@router.get("/production-hardening/data-quality")
async def production_hardening_data_quality():
    from production_hardening.production import data_quality

    return data_quality()


@router.get("/production-hardening/performance")
async def production_hardening_performance():
    from production_hardening.production import performance

    return performance()


@router.get("/production-hardening/suite")
async def production_hardening_suite(
    scale_preset: str = "smoke",
    update_baseline: bool = False,
):
    from production_hardening.production import run_hardening_suite

    return run_hardening_suite(scale_preset=scale_preset, update_baseline=bool(update_baseline))


@router.get("/production-hardening/universe")
async def production_hardening_universe(preset: str = "smoke", limit: int | None = None):
    from production_hardening.production import universe_info

    return universe_info(preset=preset, limit=limit)


@router.get("/trading-universe/health")
async def trading_universe_health():
    """NSE EQUITY_L — all cash equities available for trading."""
    from trading_universe.production import health

    return health()


@router.get("/trading-universe/dashboard")
async def trading_universe_dashboard():
    from trading_universe.production import dashboard

    return dashboard()


@router.get("/trading-universe/symbols")
async def trading_universe_symbols(limit: int | None = None, series: str | None = None):
    from trading_universe.production import list_symbols

    symbols = list_symbols(limit=limit, series=series)
    return {
        "ok": True,
        "count": len(symbols),
        "series": series,
        "symbols": symbols,
        "role": "all_equity_stocks_available_for_trading",
    }


@router.get("/trading-universe/search")
async def trading_universe_search(q: str = "", limit: int = 25):
    from trading_universe.production import search

    hits = search(q, limit=limit)
    return {"ok": True, "query": q, "count": len(hits), "results": hits}


@router.get("/trading-universe/symbol/{symbol}")
async def trading_universe_symbol(symbol: str):
    from trading_universe.production import get_symbol

    row = get_symbol(symbol)
    if not row:
        return {"ok": False, "error": "not_in_trading_universe", "symbol": symbol.upper()}
    return {"ok": True, **row}


@router.get("/market-indices/health")
async def market_indices_health():
    """Nifty / NSE index constituent registry (stocks per index)."""
    from market_indices.production import health

    return health()


@router.get("/market-indices/dashboard")
async def market_indices_dashboard():
    from market_indices.production import dashboard

    return dashboard()


@router.get("/market-indices")
async def market_indices_list():
    from market_indices.production import list_indices

    indices = list_indices()
    return {"ok": True, "count": len(indices), "indices": indices}


@router.get("/market-indices/membership/{symbol}")
async def market_indices_membership(symbol: str):
    from market_indices.production import membership_for_symbol

    return membership_for_symbol(symbol)


@router.get("/market-indices/{index_id}")
async def market_indices_get(index_id: str, members: bool = True):
    from market_indices.production import get_index

    row = get_index(index_id, include_members=bool(members))
    if not row:
        return {"ok": False, "error": "unknown_index", "index_id": index_id}
    return row


@router.get("/market-indices/{index_id}/symbols")
async def market_indices_symbols(index_id: str):
    from market_indices.production import get_index

    row = get_index(index_id, include_members=True)
    if not row:
        return {"ok": False, "error": "unknown_index", "index_id": index_id}
    return {
        "ok": True,
        "index_id": row["index_id"],
        "display_name": row["display_name"],
        "count": row["count"],
        "symbols": row.get("symbols") or [],
    }


@router.get("/production-hardening/history")
async def production_hardening_history(limit: int = 20):
    from production_hardening.production import history

    return history(limit=max(1, min(int(limit), 200)))


@router.get("/committee-certification-v2/health")
async def committee_certification_v2_health():
    """IC-10 Institutional Committee Certification v2.0 — health / universe map."""
    from committee_certification_v2.production import health

    return health()


@router.get("/committee-certification-v2/run")
async def committee_certification_v2_run(
    runs: int = 1,
    max_peers: int = 3,
    force: bool = False,
    persist: bool = True,
):
    """Run IC-10 Committee Certification v2.0 (live evidence + governance checks)."""
    from committee_certification_v2.production import run_certification

    return run_certification(
        robustness_runs=max(1, min(int(runs), 3)),
        max_peers=max(1, min(int(max_peers), 8)),
        force=bool(force),
        persist=bool(persist),
    )


@router.get("/committee-certification-v2/latest")
async def committee_certification_v2_latest():
    from pathlib import Path
    import json

    path = Path("committee_certification_v2/results/latest.json")
    if not path.exists():
        # package-relative
        path = Path(__file__).resolve().parents[2] / "committee_certification_v2" / "results" / "latest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="no_certification_result")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/institutional-evaluation-lab/question/{question_id}")
async def institutional_evaluation_lab_question(question_id: str):
    from institutional_evaluation_lab.production import question

    row = question(question_id)
    if not row:
        raise HTTPException(status_code=404, detail="question_not_found")
    return row


@router.get("/institutional-evaluation-lab/run")
async def institutional_evaluation_lab_run(
    suite: str = "smoke",
    mode: str = "soft",
    limit: int | None = None,
    persist_baseline: bool = False,
):
    from institutional_evaluation_lab.production import run

    summary = run(suite=suite, mode=mode, limit=limit, persist_baseline=persist_baseline)
    # Avoid huge payloads by default
    light = {k: v for k, v in summary.items() if k != "rows"}
    light["rows_sample"] = (summary.get("rows") or [])[:20]
    return light


@router.get("/institutional-evaluation-lab/nightly")
async def institutional_evaluation_lab_nightly():
    from institutional_evaluation_lab.production import nightly

    return nightly()


@router.get("/institutional-evaluation-lab/history")
async def institutional_evaluation_lab_history(limit: int = 20):
    from institutional_evaluation_lab.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGIB Phase 3 Sprint 3.2 — Root Cause Intelligence (RCI)
# Engineering brain: failures → clusters → recommended PRs. Reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/root-cause-intelligence/health")
async def root_cause_intelligence_health():
    from root_cause_intelligence.production import status

    return status()


@router.get("/root-cause-intelligence/dashboard")
async def root_cause_intelligence_dashboard():
    from root_cause_intelligence.production import board

    return board()


@router.get("/root-cause-intelligence/nightly")
async def root_cause_intelligence_nightly():
    from root_cause_intelligence.production import nightly

    return nightly()


@router.get("/root-cause-intelligence/analyze")
async def root_cause_intelligence_analyze(
    suite: str = "smoke",
    mode: str = "soft",
    limit: int | None = 50,
):
    from root_cause_intelligence.production import analyze_from_iel_run

    return analyze_from_iel_run(suite=suite, mode=mode, limit=limit)


@router.get("/root-cause-intelligence/history")
async def root_cause_intelligence_history(limit: int = 20):
    from root_cause_intelligence.production import history

    return history(limit=limit)


@router.get("/root-cause-intelligence/report")
async def root_cause_intelligence_report():
    from root_cause_intelligence.production import report

    return report()


# ---------------------------------------------------------------------------
# AGIB Phase 3 — Patch Intelligence (briefs only; never auto-codes)
# ---------------------------------------------------------------------------
@router.get("/patch-intelligence/health")
async def patch_intelligence_health():
    from patch_intelligence.production import status

    return status()


@router.get("/patch-intelligence/queue")
async def patch_intelligence_queue(top_n: int = 10):
    from patch_intelligence.production import from_latest_rci

    return from_latest_rci(top_n=top_n)


# ---------------------------------------------------------------------------
# AGI Phase 3 Sprint 3.5 — Temporal Integrity & Replay Certification (TIRC)
# ---------------------------------------------------------------------------
@router.get("/temporal-integrity/health")
async def temporal_integrity_health():
    from temporal_integrity.production import status

    return status()


@router.get("/temporal-integrity/dashboard")
async def temporal_integrity_dashboard():
    from temporal_integrity.production import dashboard

    return dashboard()


@router.get("/temporal-integrity/replay")
async def temporal_integrity_replay(as_of: str | None = None):
    """Replay guard health for a given as_of (empty graph/memory probe)."""
    from temporal_integrity.production import guard

    return guard(as_of=as_of, evidence_graph={"nodes": [], "edges": [], "surface_bullets": []}, stage="pre_analog")


@router.post("/temporal-integrity/validation")
async def temporal_integrity_validation(payload: dict):
    from temporal_integrity.production import validate_object

    return validate_object(dict(payload.get("object") or payload), as_of=payload.get("as_of"))


@router.get("/temporal-integrity/rejected")
async def temporal_integrity_rejected(limit: int = 50):
    from temporal_integrity.production import rejected

    return rejected(limit=limit)


@router.get("/temporal-integrity/certification")
async def temporal_integrity_certification():
    from temporal_integrity.production import certification

    return certification()


@router.get("/temporal-integrity/telemetry")
async def temporal_integrity_telemetry():
    from temporal_integrity.production import telemetry

    return telemetry()


# ---------------------------------------------------------------------------
# AGI v4.0 Phase 5 Sprint 5.3 — Institutional Portfolio Office (IPO)
# Static paths before /portfolio/{idea_id}
# ---------------------------------------------------------------------------
@router.get("/portfolio/health")
async def portfolio_health():
    from institutional_portfolio_office.production import status

    return status()


@router.get("/portfolio/dashboard")
async def portfolio_dashboard():
    from institutional_portfolio_office.production import dashboard

    return dashboard()


@router.get("/portfolio/telemetry")
async def portfolio_telemetry():
    from institutional_portfolio_office.production import telemetry

    return telemetry()


@router.get("/portfolio/history")
async def portfolio_history(limit: int = 20):
    from institutional_portfolio_office.production import history

    return history(limit=limit)


@router.post("/portfolio/create")
async def portfolio_create(payload: dict):
    from institutional_portfolio_office.production import create_api

    return create_api(payload)


@router.post("/portfolio/list")
async def portfolio_list(payload: dict):
    from institutional_portfolio_office.production import list_api

    return list_api(payload)


@router.post("/portfolio/ranking")
async def portfolio_ranking(payload: dict):
    from institutional_portfolio_office.production import ranking_api

    return ranking_api(payload)


@router.get("/portfolio/{idea_id}/versions")
async def portfolio_versions(idea_id: str):
    from institutional_portfolio_office.production import versions_api

    return versions_api(idea_id)


@router.get("/portfolio/{idea_id}")
async def portfolio_get(idea_id: str):
    from institutional_portfolio_office.production import get_idea

    return get_idea(idea_id)


# ---------------------------------------------------------------------------
# AGI v4.0 Phase 5 Sprint 5.4 — Institutional Monitoring Office (IMO)
# Static paths before /monitoring/{event_id}
# ---------------------------------------------------------------------------
@router.get("/monitoring/health")
async def monitoring_health():
    from institutional_monitoring_office.production import status

    return status()


@router.get("/monitoring/dashboard")
async def monitoring_dashboard():
    from institutional_monitoring_office.production import dashboard

    return dashboard()


@router.get("/monitoring/telemetry")
async def monitoring_telemetry():
    from institutional_monitoring_office.production import telemetry

    return telemetry()


@router.get("/monitoring/history")
async def monitoring_history(limit: int = 20):
    from institutional_monitoring_office.production import history

    return history(limit=limit)


@router.post("/monitoring/create")
async def monitoring_create(payload: dict):
    from institutional_monitoring_office.production import create_api

    return create_api(payload)


@router.post("/monitoring/list")
async def monitoring_list(payload: dict):
    from institutional_monitoring_office.production import list_api

    return list_api(payload)


@router.post("/monitoring/review-queue")
async def monitoring_review_queue(payload: dict):
    from institutional_monitoring_office.production import review_queue_api

    return review_queue_api(payload)


@router.get("/monitoring/{event_id}")
async def monitoring_get(event_id: str):
    from institutional_monitoring_office.production import get_event

    return get_event(event_id)


# ---------------------------------------------------------------------------
# AGI v4.0 Phase 5 Sprint 5.5 — Institutional Learning Office (ILO)
# Static paths before /learning/{learning_id} — FINAL Office module
# ---------------------------------------------------------------------------
@router.get("/learning/health")
async def learning_health():
    from institutional_learning_office.production import status

    return status()


@router.get("/learning/dashboard")
async def learning_dashboard():
    from institutional_learning_office.production import dashboard

    return dashboard()


@router.get("/learning/telemetry")
async def learning_telemetry():
    from institutional_learning_office.production import telemetry

    return telemetry()


@router.get("/learning/history")
async def learning_history(limit: int = 20):
    from institutional_learning_office.production import history

    return history(limit=limit)


@router.post("/learning/create")
async def learning_create(payload: dict):
    from institutional_learning_office.production import create_api

    return create_api(payload)


@router.post("/learning/list")
async def learning_list(payload: dict):
    from institutional_learning_office.production import list_api

    return list_api(payload)


@router.get("/learning/{learning_id}")
async def learning_get(learning_id: str):
    from institutional_learning_office.production import get_learning

    return get_learning(learning_id)


# ---------------------------------------------------------------------------
# AGI v4.0 Phase 5 Sprint 5.2 — Institutional Decision Office (IDO)
# Static paths before /decision/{decision_id}
# ---------------------------------------------------------------------------
@router.get("/decision/health")
async def decision_health():
    from institutional_decision_office.production import status

    return status()


@router.get("/decision/dashboard")
async def decision_dashboard():
    from institutional_decision_office.production import dashboard

    return dashboard()


@router.get("/decision/telemetry")
async def decision_telemetry():
    from institutional_decision_office.production import telemetry

    return telemetry()


@router.get("/decision/history")
async def decision_history(limit: int = 20):
    from institutional_decision_office.production import history

    return history(limit=limit)


@router.post("/decision/deliberate")
async def decision_deliberate(payload: dict):
    from institutional_decision_office.production import deliberate_api

    return deliberate_api(payload)


@router.post("/decision/list")
async def decision_list(payload: dict):
    from institutional_decision_office.production import list_api

    return list_api(payload)


@router.get("/decision/{decision_id}/versions")
async def decision_versions(decision_id: str):
    from institutional_decision_office.production import versions_api

    return versions_api(decision_id)


@router.get("/decision/{decision_id}")
async def decision_get(decision_id: str):
    from institutional_decision_office.production import get_decision

    return get_decision(decision_id)


# ---------------------------------------------------------------------------
# AGI v4.0 Phase 5 Sprint 5.1 — Institutional Investment Thesis Engine (ITE)
# Static paths before /thesis/{thesis_id}
# ---------------------------------------------------------------------------
@router.get("/thesis/health")
async def thesis_health():
    from institutional_investment_thesis.production import status

    return status()


@router.get("/thesis/dashboard")
async def thesis_dashboard():
    from institutional_investment_thesis.production import dashboard

    return dashboard()


@router.get("/thesis/telemetry")
async def thesis_telemetry():
    from institutional_investment_thesis.production import telemetry

    return telemetry()


@router.get("/thesis/history")
async def thesis_history(limit: int = 20):
    from institutional_investment_thesis.production import history

    return history(limit=limit)


@router.post("/thesis/create")
async def thesis_create(payload: dict):
    from institutional_investment_thesis.production import create_api

    return create_api(payload)


@router.post("/thesis/list")
async def thesis_list(payload: dict):
    from institutional_investment_thesis.production import list_api

    return list_api(payload)


@router.get("/thesis/{thesis_id}/versions")
async def thesis_versions(thesis_id: str):
    from institutional_investment_thesis.production import versions_api

    return versions_api(thesis_id)


@router.get("/thesis/{thesis_id}")
async def thesis_get(thesis_id: str):
    from institutional_investment_thesis.production import get_thesis

    return get_thesis(thesis_id)


# ---------------------------------------------------------------------------
# AGI Phase 4 Sprint 4.5 — Institutional Confidence Calibration (ICC)
# ---------------------------------------------------------------------------
@router.get("/confidence/health")
async def confidence_health():
    from institutional_confidence_calibration.production import status

    return status()


@router.get("/confidence/dashboard")
async def confidence_dashboard():
    from institutional_confidence_calibration.production import dashboard

    return dashboard()


@router.post("/confidence/calculate")
async def confidence_calculate(payload: dict):
    from institutional_confidence_calibration.production import calculate_api

    return calculate_api(payload)


@router.post("/confidence/report")
async def confidence_report(payload: dict):
    from institutional_confidence_calibration.production import report

    return report(payload)


@router.get("/confidence/telemetry")
async def confidence_telemetry():
    from institutional_confidence_calibration.production import telemetry

    return telemetry()


@router.get("/confidence/history")
async def confidence_history(limit: int = 20):
    from institutional_confidence_calibration.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGI Phase 4 Sprint 4.4 — Institutional Committee Reasoning (ICR)
# ---------------------------------------------------------------------------
@router.get("/committee/health")
async def committee_health():
    from institutional_committee_reasoning.production import status

    return status()


@router.get("/committee/dashboard")
async def committee_dashboard():
    from institutional_committee_reasoning.production import dashboard

    return dashboard()


@router.post("/committee/deliberate")
async def committee_deliberate(payload: dict):
    from institutional_committee_reasoning.production import deliberate_api

    return deliberate_api(payload)


@router.post("/committee/report")
async def committee_report(payload: dict):
    from institutional_committee_reasoning.production import report

    return report(payload)


@router.post("/committee/cases")
async def committee_cases(payload: dict):
    from institutional_committee_reasoning.production import cases

    return cases(payload)


@router.get("/committee/telemetry")
async def committee_telemetry():
    from institutional_committee_reasoning.production import telemetry

    return telemetry()


@router.get("/committee/history")
async def committee_history(limit: int = 20):
    from institutional_committee_reasoning.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGI Phase 4 Sprint 4.3 — Institutional Hypothesis Evaluation Engine (IHE)
# ---------------------------------------------------------------------------
@router.get("/hypothesis-evaluation/health")
async def hypothesis_evaluation_health():
    from institutional_hypothesis_evaluation.production import status

    return status()


@router.get("/hypothesis-evaluation/dashboard")
async def hypothesis_evaluation_dashboard():
    from institutional_hypothesis_evaluation.production import dashboard

    return dashboard()


@router.post("/hypothesis-evaluation/evaluate")
async def hypothesis_evaluation_evaluate(payload: dict):
    from institutional_hypothesis_evaluation.production import evaluate

    return evaluate(payload)


@router.post("/hypothesis-evaluation/report")
async def hypothesis_evaluation_report(payload: dict):
    from institutional_hypothesis_evaluation.production import report

    return report(payload)


@router.post("/hypothesis-evaluation/ranking")
async def hypothesis_evaluation_ranking(payload: dict):
    from institutional_hypothesis_evaluation.production import ranking

    return ranking(payload)


@router.get("/hypothesis-evaluation/telemetry")
async def hypothesis_evaluation_telemetry():
    from institutional_hypothesis_evaluation.production import telemetry

    return telemetry()


@router.get("/hypothesis-evaluation/history")
async def hypothesis_evaluation_history(limit: int = 20):
    from institutional_hypothesis_evaluation.production import history

    return history(limit=limit)


# ---------------------------------------------------------------------------
# AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation Engine (IHG)
# ---------------------------------------------------------------------------
@router.get("/hypothesis/health")
async def hypothesis_health():
    from institutional_hypothesis_generation.production import status

    return status()


@router.get("/hypothesis/dashboard")
async def hypothesis_dashboard():
    from institutional_hypothesis_generation.production import dashboard

    return dashboard()


@router.post("/hypothesis/generate")
async def hypothesis_generate(payload: dict):
    from institutional_hypothesis_generation.production import generate

    return generate(payload)


@router.post("/hypothesis/rank")
async def hypothesis_rank(payload: dict):
    from institutional_hypothesis_generation.production import rank

    return rank(payload)


@router.post("/hypothesis/explain")
async def hypothesis_explain(payload: dict):
    from institutional_hypothesis_generation.production import explain

    return explain(payload)


@router.get("/hypothesis/telemetry")
async def hypothesis_telemetry():
    from institutional_hypothesis_generation.production import telemetry

    return telemetry()


@router.get("/hypothesis/history")
async def hypothesis_history(limit: int = 20):
    from institutional_hypothesis_generation.production import history

    return history(limit=limit)


@router.get("/hypothesis/configuration")
async def hypothesis_configuration():
    from institutional_hypothesis_generation.production import configuration

    return configuration()


# ---------------------------------------------------------------------------
# AGI Phase 4 Sprint 4.1 — Institutional Evidence Weighting Engine (IEW)
# ---------------------------------------------------------------------------
@router.get("/evidence-weighting/health")
async def evidence_weighting_health():
    from institutional_evidence_weighting.production import status

    return status()


@router.get("/evidence-weighting/dashboard")
async def evidence_weighting_dashboard():
    from institutional_evidence_weighting.production import dashboard

    return dashboard()


@router.post("/evidence-weighting/ranking")
async def evidence_weighting_ranking(payload: dict):
    from institutional_evidence_weighting.production import ranking

    return ranking(payload)


@router.post("/evidence-weighting/score")
async def evidence_weighting_score(payload: dict):
    from institutional_evidence_weighting.production import score

    return score(payload)


@router.post("/evidence-weighting/explain")
async def evidence_weighting_explain(payload: dict):
    from institutional_evidence_weighting.production import explain

    return explain(payload)


@router.get("/evidence-weighting/telemetry")
async def evidence_weighting_telemetry():
    from institutional_evidence_weighting.production import telemetry

    return telemetry()


@router.get("/evidence-weighting/configuration")
async def evidence_weighting_configuration(profile_id: str | None = None):
    from institutional_evidence_weighting.production import configuration

    return configuration(profile_id)


# ---------------------------------------------------------------------------
# AGI Observability — LangSmith tracing (observability only; never changes answers)
# ---------------------------------------------------------------------------
@router.get("/observability/health")
async def observability_health():
    from observability.production import status

    return status()


@router.get("/observability/langsmith")
async def observability_langsmith():
    from observability.production import dashboard

    return dashboard()


@router.get("/observability/langsmith/verify")
async def observability_langsmith_verify():
    from observability.production import verify

    return verify()


@router.get("/prediction/{prediction_id}")
async def ail_prediction(prediction_id: str):
    try:
        return _ail.prediction(prediction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="prediction_not_found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Institutional Analyst Framework V1 (Answer Construction orchestration only) ---


@router.get("/institutional-analysts/health")
async def institutional_analysts_health():
    from institutional_analysts.production import health

    return health()


@router.get("/institutional-analysts/quality-gates")
async def institutional_analysts_quality_gates():
    from institutional_analysts.production import quality_gates

    return quality_gates()


# --- Investment Committee Intelligence V1 (deliberation / vote / minutes) ---


@router.get("/investment-committee/health")
async def investment_committee_health():
    from investment_committee.production import health

    return health()


@router.get("/investment-committee/quality-gates")
async def investment_committee_quality_gates():
    from investment_committee.production import quality_gates

    return quality_gates()


@router.get("/investment-committee/timeline/{ticker}")
async def investment_committee_timeline(ticker: str, limit: int = Query(default=20, ge=1, le=100)):
    from investment_committee.production import timeline

    return timeline(ticker, limit=limit)


@router.post("/investment-committee/record-actuals")
async def investment_committee_record_actuals(payload: dict[str, Any] = Body(default={})):
    """Prediction accountability — score prior committee expectations vs actuals."""
    from investment_committee.production import record_actuals

    ticker = str(payload.get("ticker") or "")
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    return record_actuals(
        ticker,
        meeting_id=payload.get("meeting_id"),
        actuals=list(payload.get("actuals") or []),
    )


# --- Institutional Research Writer V1 (presentation layer after CIO) ---


@router.get("/research-writer/health")
async def research_writer_health():
    from research_writer.production import health

    return health()


@router.get("/research-writer/quality-gates")
async def research_writer_quality_gates():
    from research_writer.production import quality_gates

    return quality_gates()


# --- Soft reasoning / editorial health (Intelligence Map probes) ---


@router.get("/institutional-reasoning/health")
async def institutional_reasoning_health():
    from institutional_reasoning.production import health

    return health()


@router.get("/institutional-reasoning/evidence/{ticker}")
async def institutional_evidence_pack(ticker: str):
    from institutional_reasoning.interrogate import evidence_pack

    return evidence_pack(ticker)


@router.get("/institutional-reasoning/portfolio/{ticker}")
async def institutional_portfolio_view(ticker: str):
    from institutional_reasoning.interrogate import portfolio_view

    return portfolio_view(ticker)


@router.get("/institutional-reasoning/graphs")
async def institutional_decision_graphs(q: str, ticker: str | None = None):
    from institutional_reasoning.interrogate import decision_graphs

    return decision_graphs(q, ticker=ticker)


@router.get("/institutional-reasoning/universe")
async def institutional_universe(tier: str = "nifty_50"):
    from institutional_reasoning.fundamentals.universe import tier_report

    return tier_report(tier)


@router.get("/institutional-reasoning/observability")
async def institutional_observability():
    from institutional_reasoning.observability import health as obs_health

    return obs_health()


@router.get("/institutional-reasoning/baselines")
async def institutional_baselines(ticker: str | None = None):
    from institutional_reasoning.baselines import compare_entity, run_baseline_suite

    if ticker:
        return compare_entity(ticker)
    return run_baseline_suite()


@router.get("/institutional-reasoning/adversarial")
async def institutional_adversarial():
    from institutional_reasoning.adversarial_suite import run_adversarial_suite

    return run_adversarial_suite()


@router.get("/institutional-reasoning/stack")
async def institutional_stack_surface(ticker: str = "INFY", tier: str = "nifty_50"):
    from institutional_reasoning.interrogate import stack_surface

    return stack_surface(ticker=ticker, tier=tier)


# --- Knowledge Factory (Track 1) — soft data layer; Phases 1–7 frozen ---


@router.get("/knowledge-factory/health")
async def knowledge_factory_health():
    from knowledge_factory.production import health

    return health()


@router.get("/knowledge-factory/dashboard")
async def knowledge_factory_dashboard():
    from knowledge_factory.production import coverage_dashboard

    return coverage_dashboard()


@router.get("/knowledge-factory/coverage")
async def knowledge_factory_morning_coverage():
    """Morning coverage board + Decision Coverage north star."""
    from knowledge_factory.coverage import morning_coverage_dashboard

    return morning_coverage_dashboard()


@router.get("/knowledge-factory/decision-coverage")
async def knowledge_factory_decision_coverage():
    from knowledge_factory.coverage import decision_coverage

    return decision_coverage()


@router.get("/knowledge-factory/phase1-golden-test-set")
async def knowledge_factory_phase1_golden_test_set(bucket: str | None = None):
    """Phase 1 Golden Test Set (200): Nifty50 + Next50 + mid + small + special."""
    from knowledge_factory.phase1_golden_test_set import (
        PHASE1_GOLDEN_ROWS,
        by_bucket,
        summary,
        tickers,
        validate_universe,
    )

    if bucket:
        rows = [r for r in PHASE1_GOLDEN_ROWS if r["bucket"] == bucket]
        return {
            "bucket": bucket,
            "n": len(rows),
            "tickers": tickers(bucket=bucket),
            "rows": rows,
            "summary": summary(),
            "validation": validate_universe(),
        }
    return {
        "summary": summary(),
        "validation": validate_universe(),
        "buckets": {k: [r["ticker"] for r in v] for k, v in by_bucket().items()},
        "rows": PHASE1_GOLDEN_ROWS,
    }


@router.get("/knowledge-factory/dimensions")
async def knowledge_factory_coverage_dimensions():
    """Four coverage dimensions: entity / evidence / decision / confidence."""
    from knowledge_factory.coverage import coverage_dimensions

    return coverage_dimensions()


@router.get("/knowledge-factory/daily-health")
async def knowledge_factory_daily_health():
    """AGIB Daily Health scorecard — one operational morning screen."""
    from knowledge_factory.coverage import daily_health_scorecard

    return daily_health_scorecard()


@router.get("/knowledge-factory/institutional-depth")
async def knowledge_factory_institutional_depth():
    """Track 1 — Institutional Decision Coverage (Infosys-class depth / Nifty 500)."""
    from knowledge_factory.coverage import NIFTY_500
    from knowledge_factory.institutional_depth import institutional_decision_coverage

    return institutional_decision_coverage(NIFTY_500)


@router.get("/knowledge-factory/institutional-depth/{ticker}")
async def knowledge_factory_institutional_depth_ticker(ticker: str):
    """Per-company Infosys-class depth checklist + onboarding acceptance tests."""
    from knowledge_factory.institutional_depth import acceptance_for_company, institutional_depth_checklist

    return {
        "checklist": institutional_depth_checklist(ticker),
        "acceptance": acceptance_for_company(ticker),
    }


@router.get("/knowledge-factory/universe-tiers")
async def knowledge_factory_universe_tiers():
    """Universe Tier board — quality before breadth."""
    from institutional_reasoning.fundamentals.universe import universe_tiers

    return universe_tiers()


# ---------------------------------------------------------------------------
# AGIB v1.2 — Institutional Universe Intelligence (soft registry layer)
# ---------------------------------------------------------------------------
@router.get("/universe-intelligence/health")
async def universe_intelligence_health():
    from universe_intelligence.production import health as iui_health

    return iui_health()


@router.get("/universe-intelligence/dashboard")
async def universe_intelligence_dashboard(universe_id: str = "NIFTY_500"):
    """Universe Health ops heartbeat — coverage, failures, stale, new/removed, ICI."""
    from universe_intelligence.production import dashboard

    return dashboard(universe_id=universe_id)


@router.post("/universe-intelligence/run")
async def universe_intelligence_run(body: dict | None = None):
    from universe_intelligence.production import run_pipeline

    body = body or {}
    return run_pipeline(
        universe_id=str(body.get("universe_id") or "NIFTY_500"),
        force_full=bool(body.get("force_full") or False),
        ensure_kf=bool(body.get("ensure_kf", True)),
    )


@router.get("/universe-intelligence/universes")
async def universe_intelligence_universes(family: str | None = None, status: str | None = None):
    from universe_intelligence.production import list_universes

    return list_universes(family=family, status=status)


@router.get("/universe-intelligence/universes/{universe_id}")
async def universe_intelligence_universe(universe_id: str):
    from universe_intelligence.production import get_universe

    return get_universe(universe_id)


@router.get("/universe-intelligence/membership")
async def universe_intelligence_membership(ticker: str, universe_id: str, as_of: str):
    """Point-in-time: was ticker a member of universe as of date?"""
    from universe_intelligence.production import was_member

    return was_member(ticker=ticker, universe_id=universe_id, as_of=as_of)


@router.get("/universe-intelligence/memberships/{ticker}")
async def universe_intelligence_memberships(ticker: str, as_of: str | None = None):
    from universe_intelligence.production import memberships_for_company

    return memberships_for_company(ticker, as_of=as_of)


@router.get("/universe-intelligence/company/{ticker}")
async def universe_intelligence_company(ticker: str, refresh: bool = False):
    from universe_intelligence.production import get_company

    return get_company(ticker, refresh=refresh)


@router.get("/universe-intelligence/ici/{ticker}")
async def universe_intelligence_ici(ticker: str):
    from universe_intelligence.production import institutional_coverage_index

    return institutional_coverage_index(ticker)


@router.get("/universe-intelligence/coverage-level/{ticker}")
async def universe_intelligence_coverage_level(ticker: str):
    from universe_intelligence.production import coverage_level_for

    return coverage_level_for(ticker)


@router.get("/universe-intelligence/quality-gates")
async def universe_intelligence_quality_gates(universe_id: str = "NIFTY_500"):
    from universe_intelligence.production import quality_gates_summary

    return quality_gates_summary(universe_id)


@router.get("/universe-intelligence/tree")
async def universe_intelligence_tree():
    from universe_intelligence.production import universe_tree

    return universe_tree()


# ---------------------------------------------------------------------------
# AGIB v3.1 Track 4 — Institutional Documents Intelligence (IDI)
# Document evidence layer only. No reasoning / summarisation / recommendations.
# ---------------------------------------------------------------------------
@router.get("/documents/health")
async def documents_health():
    from knowledge_factory.institutional_documents.production import health

    return health()


@router.get("/documents/dashboard")
async def documents_dashboard_route():
    from knowledge_factory.institutional_documents.production import dashboard

    return dashboard()


@router.get("/documents/company/{ticker}")
async def documents_company(ticker: str):
    from knowledge_factory.institutional_documents.production import company

    return company(ticker)


@router.get("/documents/report/{doc_id}")
async def documents_report(doc_id: str):
    from knowledge_factory.institutional_documents.production import report

    return report(doc_id)


@router.get("/documents/search")
async def documents_search(
    q: str | None = None,
    ticker: str | None = None,
    doc_type: str | None = None,
    limit: int = 50,
):
    from knowledge_factory.institutional_documents.production import search

    return search(q=q, ticker=ticker, doc_type=doc_type, limit=limit)


@router.get("/documents/replay")
async def documents_replay(
    as_of: str | None = None,
    ticker: str | None = None,
    document_id: str | None = None,
):
    from knowledge_factory.institutional_documents.production import replay

    return replay(as_of=as_of or "2099-01-01", ticker=ticker, document_id=document_id)


@router.post("/documents/run")
async def documents_run(payload: dict[str, Any] = Body(default={})):
    from knowledge_factory.institutional_documents.production import run_pipeline

    body = payload or {}
    return run_pipeline(
        tickers=body.get("tickers"),
        allow_samples=bool(body.get("allow_samples", True)),
        as_of=body.get("as_of"),
    )


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 1 — Institutional Company Intelligence (soft KF enrichment)
# Read-only surface. Reasoning / governance / IUI / IDQ frozen.
# ---------------------------------------------------------------------------
@router.get("/company-intelligence/health")
async def company_intelligence_health():
    from knowledge_factory.company_intelligence.production import health as ici_health

    return ici_health()


@router.get("/company-intelligence/dashboard")
async def company_intelligence_dashboard_route():
    from knowledge_factory.company_intelligence.production import dashboard

    return dashboard()


@router.post("/company-intelligence/run")
async def company_intelligence_run(body: dict | None = None):
    from knowledge_factory.company_intelligence.production import run_pipeline

    body = body or {}
    tickers = body.get("tickers")
    return run_pipeline(tickers=tickers)


@router.get("/company-intelligence/coverage")
async def company_intelligence_coverage():
    from knowledge_factory.company_intelligence.production import coverage_summary

    return coverage_summary()


@router.get("/company-intelligence/quality")
async def company_intelligence_quality():
    from knowledge_factory.company_intelligence.production import quality_summary

    return quality_summary()


@router.get("/company-intelligence/search")
async def company_intelligence_search(q: str = "", limit: int = 25):
    from knowledge_factory.company_intelligence.production import search

    return search(q, limit=limit)


@router.get("/company-intelligence/{ticker}")
async def company_intelligence_ticker(ticker: str, refresh: bool = False):
    from knowledge_factory.company_intelligence.production import get_company

    return get_company(ticker, refresh=refresh)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 2 — Institutional Corporate Event Intelligence (soft KF)
# Immutable timelines + point-in-time replay. Reasoning frozen.
# ---------------------------------------------------------------------------
@router.get("/corporate-events/health")
async def corporate_events_health():
    from knowledge_factory.corporate_events.production import health as icei_health

    return icei_health()


@router.get("/corporate-events/dashboard")
async def corporate_events_dashboard_route():
    from knowledge_factory.corporate_events.production import dashboard

    return dashboard()


@router.post("/corporate-events/run")
async def corporate_events_run(body: dict | None = None):
    from knowledge_factory.corporate_events.production import run_pipeline

    body = body or {}
    return run_pipeline(tickers=body.get("tickers"))


@router.get("/corporate-events/search")
async def corporate_events_search(q: str = "", limit: int = 25):
    from knowledge_factory.corporate_events.production import search

    return search(q, limit=limit)


@router.get("/corporate-events/{ticker}")
async def corporate_events_ticker(ticker: str, refresh: bool = False):
    from knowledge_factory.corporate_events.production import get_company_events

    return get_company_events(ticker, refresh=refresh)


@router.get("/company-timeline/{ticker}")
async def company_timeline_ticker(ticker: str, as_of: str | None = None, refresh: bool = False):
    from knowledge_factory.corporate_events.production import get_company_timeline

    return get_company_timeline(ticker, as_of=as_of, refresh=refresh)


@router.get("/events/today")
async def events_today_route():
    from knowledge_factory.corporate_events.production import events_today

    return events_today()


@router.get("/events/critical")
async def events_critical_route(limit: int = 50):
    from knowledge_factory.corporate_events.production import events_critical

    return events_critical(limit=limit)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 3 — Institutional Government & Regulatory Intelligence
# Soft KF knowledge only. No political opinion / policy forecasts.
# ---------------------------------------------------------------------------
@router.get("/government/health")
async def government_health():
    from knowledge_factory.government_intelligence.production import health as igri_health

    return igri_health()


@router.get("/government/dashboard")
async def government_dashboard_route():
    from knowledge_factory.government_intelligence.production import dashboard

    return dashboard()


@router.post("/government/run")
async def government_run():
    from knowledge_factory.government_intelligence.production import run_pipeline

    return run_pipeline()


@router.get("/government/policies")
async def government_policies(domain: str | None = None):
    from knowledge_factory.government_intelligence.production import list_policies

    return list_policies(domain=domain)


@router.get("/government/policy/{policy_id}")
async def government_policy(policy_id: str):
    from knowledge_factory.government_intelligence.production import get_policy

    return get_policy(policy_id)


@router.get("/government/search")
async def government_search(q: str = "", limit: int = 25):
    from knowledge_factory.government_intelligence.production import search

    return search(q, limit=limit)


@router.get("/government/rbi")
async def government_rbi():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("rbi")


@router.get("/government/sebi")
async def government_sebi():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("sebi")


@router.get("/government/budget")
async def government_budget():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("budget")


@router.get("/government/gst")
async def government_gst():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("gst")


@router.get("/government/pli")
async def government_pli():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("pli")


@router.get("/government/trade")
async def government_trade():
    from knowledge_factory.government_intelligence.production import domain_view

    return domain_view("trade")


@router.get("/government/timeline")
async def government_timeline(as_of: str | None = None):
    from knowledge_factory.government_intelligence.production import timeline

    return timeline(as_of=as_of)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 4 — Institutional Industry & Value Chain Intelligence
# Soft KF knowledge only. Economic Network Graph = later sprint.
# ---------------------------------------------------------------------------
@router.get("/industry/health")
async def industry_health():
    from knowledge_factory.industry_intelligence.production import health as iivi_health

    return iivi_health()


@router.get("/industry/dashboard")
async def industry_dashboard_route():
    from knowledge_factory.industry_intelligence.production import dashboard

    return dashboard()


@router.post("/industry/run")
async def industry_run():
    from knowledge_factory.industry_intelligence.production import run_pipeline

    return run_pipeline()


@router.get("/industry/search")
async def industry_search(q: str = "", limit: int = 25):
    from knowledge_factory.industry_intelligence.production import search

    return search(q, limit=limit)


@router.get("/industry/playbook")
async def industry_playbook(name: str):
    from knowledge_factory.industry_intelligence.production import playbook

    return playbook(name)


@router.get("/industry/value-chain")
async def industry_value_chain(name: str):
    from knowledge_factory.industry_intelligence.production import value_chain

    return value_chain(name)


@router.get("/industry/accounting")
async def industry_accounting(name: str):
    from knowledge_factory.industry_intelligence.production import accounting

    return accounting(name)


@router.get("/industry/valuation")
async def industry_valuation_route(name: str):
    from knowledge_factory.industry_intelligence.production import valuation

    return valuation(name)


@router.get("/industry/cycles")
async def industry_cycles(name: str):
    from knowledge_factory.industry_intelligence.production import cycles

    return cycles(name)


@router.get("/industry/kpis")
async def industry_kpis(name: str):
    from knowledge_factory.industry_intelligence.production import kpis

    return kpis(name)


@router.get("/industry/company/{ticker}")
async def industry_company(ticker: str):
    from knowledge_factory.industry_intelligence.production import company_industry

    return company_industry(ticker)


@router.get("/industry/{name}")
async def industry_by_name(name: str, refresh: bool = False):
    from knowledge_factory.industry_intelligence.production import get_industry

    return get_industry(name, refresh=refresh)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 5 — Institutional Economic Relationship Intelligence (IERI)
# Soft KF knowledge only. Graph = implementation detail. No reasoning / planner.
# ---------------------------------------------------------------------------
@router.get("/relationship/health")
async def relationship_health():
    from knowledge_factory.economic_relationship_intelligence.production import health as ieri_health

    return ieri_health()


@router.get("/relationship/dashboard")
async def relationship_dashboard_route():
    from knowledge_factory.economic_relationship_intelligence.production import dashboard

    return dashboard()


@router.post("/relationship/run")
async def relationship_run():
    from knowledge_factory.economic_relationship_intelligence.production import run_pipeline

    return run_pipeline()


@router.get("/relationship/registry")
async def relationship_registry():
    from knowledge_factory.economic_relationship_intelligence.production import registry

    return registry()


@router.get("/relationship/search")
async def relationship_search(
    q: str = "",
    semantics: str | None = None,
    relationship_type: str | None = None,
    limit: int = 50,
    as_of: str | None = None,
):
    from knowledge_factory.economic_relationship_intelligence.production import search

    return search(
        q,
        semantics=semantics,
        relationship_type=relationship_type,
        limit=limit,
        as_of=as_of,
    )


@router.get("/relationship/path")
async def relationship_path(
    source: str,
    target: str | None = None,
    max_depth: int = 3,
    semantics: str | None = None,
    relationship_type: str | None = None,
    as_of: str | None = None,
    limit: int = 25,
):
    from knowledge_factory.economic_relationship_intelligence.production import path_query

    return path_query(
        source=source,
        target=target,
        max_depth=max_depth,
        semantics=semantics,
        relationship_type=relationship_type,
        as_of=as_of,
        limit=limit,
    )


@router.get("/relationship/replay")
async def relationship_replay(as_of: str):
    from knowledge_factory.economic_relationship_intelligence.production import replay

    return replay(as_of=as_of)


@router.get("/relationship/shock/{entity}")
async def relationship_shock(entity: str, direction: str | None = None, max_order: int = 3, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import shock_impact

    return shock_impact(entity, direction=direction, max_order=max_order, as_of=as_of)


@router.get("/relationship/company/{ticker}")
async def relationship_company(ticker: str, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import company

    return company(ticker, as_of=as_of)


@router.get("/relationship/industry/{industry}")
async def relationship_industry(industry: str, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import industry as industry_view

    return industry_view(industry, as_of=as_of)


@router.get("/relationship/commodity/{commodity}")
async def relationship_commodity(commodity: str, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import commodity as commodity_view

    return commodity_view(commodity, as_of=as_of)


@router.get("/relationship/policy/{policy}")
async def relationship_policy(policy: str, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import policy as policy_view

    return policy_view(policy, as_of=as_of)


@router.get("/relationship/macro/{macro}")
async def relationship_macro(macro: str, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import macro as macro_view

    return macro_view(macro, as_of=as_of)


@router.get("/relationship/network/{entity}")
async def relationship_network(entity: str, depth: int = 2, as_of: str | None = None):
    from knowledge_factory.economic_relationship_intelligence.production import network

    return network(entity, depth=depth, as_of=as_of)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 6 — Institutional Alternative Data Intelligence (IADI)
# Soft KF knowledge only. Phase-1 high-signal datasets. No prediction engine.
# ---------------------------------------------------------------------------
@router.get("/alternative-data/health")
async def alternative_data_health():
    from knowledge_factory.alternative_data_intelligence.production import health as iadi_health

    return iadi_health()


@router.get("/alternative-data/dashboard")
async def alternative_data_dashboard_route():
    from knowledge_factory.alternative_data_intelligence.production import dashboard

    return dashboard()


@router.post("/alternative-data/run")
async def alternative_data_run():
    from knowledge_factory.alternative_data_intelligence.production import run_pipeline

    return run_pipeline()


@router.get("/alternative-data/registry")
async def alternative_data_registry():
    from knowledge_factory.alternative_data_intelligence.production import registry

    return registry()


@router.get("/alternative-data/search")
async def alternative_data_search(q: str = "", limit: int = 25):
    from knowledge_factory.alternative_data_intelligence.production import search

    return search(q, limit=limit)


@router.get("/alternative-data/trends")
async def alternative_data_trends(dataset: str | None = None, as_of: str | None = None):
    from knowledge_factory.alternative_data_intelligence.production import trends

    return trends(dataset=dataset, as_of=as_of)


@router.get("/alternative-data/replay")
async def alternative_data_replay(as_of: str, dataset: str | None = None):
    from knowledge_factory.alternative_data_intelligence.production import replay

    return replay(as_of=as_of, dataset=dataset)


@router.get("/alternative-data/dataset/{name}")
async def alternative_data_dataset(name: str, as_of: str | None = None):
    from knowledge_factory.alternative_data_intelligence.production import get_dataset

    return get_dataset(name, as_of=as_of)


@router.get("/alternative-data/company/{ticker}")
async def alternative_data_company(ticker: str):
    from knowledge_factory.alternative_data_intelligence.production import company

    return company(ticker)


@router.get("/alternative-data/industry/{industry}")
async def alternative_data_industry(industry: str):
    from knowledge_factory.alternative_data_intelligence.production import industry as industry_view

    return industry_view(industry)


@router.get("/alternative-data/beneficiaries/{dataset}")
async def alternative_data_beneficiaries(dataset: str):
    from knowledge_factory.alternative_data_intelligence.production import beneficiaries

    return beneficiaries(dataset)


# ---------------------------------------------------------------------------
# AGIB v2.0 Sprint 7 — Institutional Market Expectations Intelligence (IMEI)
# Soft KF knowledge only. Phase-1 public/auditable. Phase-2 consensus modular.
# ---------------------------------------------------------------------------
@router.get("/expectations/health")
async def expectations_health():
    from knowledge_factory.market_expectations_intelligence.production import health as imei_health

    return imei_health()


@router.get("/expectations/dashboard")
async def expectations_dashboard_route():
    from knowledge_factory.market_expectations_intelligence.production import dashboard

    return dashboard()


@router.post("/expectations/run")
async def expectations_run():
    from knowledge_factory.market_expectations_intelligence.production import run_pipeline

    return run_pipeline()


@router.get("/expectations/registry")
async def expectations_registry():
    from knowledge_factory.market_expectations_intelligence.production import registry

    return registry()


@router.get("/expectations/search")
async def expectations_search(q: str = "", limit: int = 25):
    from knowledge_factory.market_expectations_intelligence.production import search

    return search(q, limit=limit)


@router.get("/expectations/revisions")
async def expectations_revisions(entity: str | None = None, as_of: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import revisions

    return revisions(entity=entity, as_of=as_of)


@router.get("/expectations/surprises")
async def expectations_surprises(entity: str | None = None, as_of: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import surprises

    return surprises(entity=entity, as_of=as_of)


@router.get("/expectations/narratives")
async def expectations_narratives(narrative_id: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import narratives

    return narratives(narrative_id)


@router.get("/expectations/replay")
async def expectations_replay(as_of: str, entity: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import replay

    return replay(as_of=as_of, entity=entity)


@router.get("/expectations/company/{ticker}")
async def expectations_company(ticker: str, as_of: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import company

    return company(ticker, as_of=as_of)


@router.get("/expectations/gap/{ticker}")
async def expectations_gap(ticker: str, as_of: str | None = None):
    from knowledge_factory.market_expectations_intelligence.production import gap

    return gap(ticker, as_of=as_of)


@router.get("/expectations/phase2-consensus")
async def expectations_phase2_consensus():
    from knowledge_factory.market_expectations_intelligence.production import phase2_consensus_status

    return phase2_consensus_status()


# ---------------------------------------------------------------------------
# AGIB v2.1 — Institutional Scheduler & Morning Operations
# ---------------------------------------------------------------------------
@router.get("/scheduler/status")
async def scheduler_status():
    from institutional_scheduler.production import status

    return status()


@router.post("/scheduler/run")
async def scheduler_run(payload: dict[str, Any] = Body(default={})):
    from institutional_scheduler.production import run_morning

    body = payload or {}
    return run_morning(
        dry_run=bool(body.get("dry_run", False)),
        parallel=bool(body.get("parallel", True)),
        manual_override=bool(body.get("manual_override", False)),
        skip=list(body.get("skip") or []),
        operator_notes=body.get("operator_notes"),
    )


@router.get("/scheduler/history")
async def scheduler_history(limit: int = 50):
    from institutional_scheduler.production import history

    return history(limit=limit)


@router.get("/scheduler/workflows")
async def scheduler_workflows():
    from institutional_scheduler.production import workflows

    return workflows()


@router.post("/scheduler/retry")
async def scheduler_retry(payload: dict[str, Any] = Body(default={})):
    from institutional_scheduler.production import retry

    body = payload or {}
    return retry(
        str(body.get("workflow_id") or ""),
        run_id=body.get("run_id"),
        dry_run=bool(body.get("dry_run", False)),
    )


@router.get("/scheduler/health")
async def scheduler_health():
    from institutional_scheduler.production import health

    return health()


@router.get("/scheduler/reports")
async def scheduler_reports(run_id: str | None = None):
    from institutional_scheduler.production import reports

    return reports(run_id)


@router.get("/scheduler/telemetry")
async def scheduler_telemetry(limit: int = 100):
    from institutional_scheduler.production import telemetry

    return telemetry(limit=limit)


@router.get("/scheduler/dashboard")
async def scheduler_dashboard():
    from institutional_scheduler.production import dashboard

    return dashboard()


# ---------------------------------------------------------------------------
# AGIB v3.0 — Live Institutional Data Ingestion (LIDI)
# ---------------------------------------------------------------------------
@router.get("/live-data/status")
async def live_data_status():
    from live_data.production import status

    return status()


@router.get("/live-data/sources")
async def live_data_sources():
    from live_data.production import sources

    return sources()


@router.get("/live-data/freshness")
async def live_data_freshness():
    from live_data.production import freshness

    return freshness()


@router.get("/live-data/collectors")
async def live_data_collectors():
    from live_data.production import collectors

    return collectors()


@router.get("/live-data/validation")
async def live_data_validation():
    from live_data.production import validation

    return validation()


@router.get("/live-data/fallback")
async def live_data_fallback():
    from live_data.production import fallback

    return fallback()


@router.get("/live-data/dashboard")
async def live_data_dashboard():
    from live_data.production import dashboard

    return dashboard()


@router.post("/live-data/run")
async def live_data_run(payload: dict[str, Any] = Body(default={})):
    from live_data.production import run_morning_live_ingestion

    body = payload or {}
    return run_morning_live_ingestion(
        as_of=body.get("as_of"),
        allow_recorded_sample=body.get("allow_recorded_sample"),
        ir_ticker=str(body.get("ir_ticker") or "INFY"),
        stop_after=body.get("stop_after"),
    )


# ---------------------------------------------------------------------------
# AGIB v3.0 — LIDI Track 2: Live Collector Activation & Production Verification
# ---------------------------------------------------------------------------
@router.get("/live-data/verification/status")
async def live_data_verification_status():
    from live_data.production_verify import status

    return status()


@router.post("/live-data/verification/run")
async def live_data_verification_run(payload: dict[str, Any] = Body(default={})):
    from live_data.production_verify import verify

    body = payload or {}
    return verify(
        allow_recorded_sample=body.get("allow_recorded_sample"),
        skip_live_probes=bool(body.get("skip_live_probes", False)),
        skip_ingestion=bool(body.get("skip_ingestion", False)),
        morning_dry_run=bool(body.get("morning_dry_run", True)),
    )


@router.get("/live-data/verification/dashboard")
async def live_data_verification_dashboard():
    from live_data.production_verify import health_dashboard

    return health_dashboard()


@router.get("/live-data/verification/certification")
async def live_data_verification_certification():
    from live_data.production_verify import certification

    return certification()


@router.get("/live-data/verification/telemetry")
async def live_data_verification_telemetry(limit: int = 100, source_id: str | None = None):
    from live_data.production_verify import telemetry

    return telemetry(limit=limit, source_id=source_id)


@router.get("/live-data/verification/probes")
async def live_data_verification_probes():
    from live_data.production_verify import probes

    return probes()


@router.get("/live-data/verification/report")
async def live_data_verification_report():
    from live_data.production_verify import report_status

    return report_status()


@router.post("/live-data/verification/report/generate")
async def live_data_verification_report_generate():
    from live_data.production_verify import generate_report

    return generate_report()


# ---------------------------------------------------------------------------
# AGIB v2.1 — Complete Ask Pipeline (read-only observability + sample runner)
# ---------------------------------------------------------------------------
@router.get("/ask/pipeline")
async def ask_pipeline_board():
    from ask_pipeline.production import dashboard, health

    return {"health": health(), "dashboard": dashboard()}


@router.get("/ask/context")
async def ask_pipeline_context(pipeline_id: str):
    from ask_pipeline.production import get_context

    return get_context(pipeline_id)


@router.get("/ask/execution")
async def ask_pipeline_execution(pipeline_id: str):
    from ask_pipeline.production import get_execution

    return get_execution(pipeline_id)


@router.get("/ask/telemetry")
async def ask_pipeline_telemetry(pipeline_id: str | None = None):
    from ask_pipeline.production import get_telemetry

    return get_telemetry(pipeline_id)


@router.get("/ask/replay")
async def ask_pipeline_replay(replay_id: str):
    from ask_pipeline.production import get_replay

    return get_replay(replay_id)


@router.get("/ask/quality-gates")
async def ask_pipeline_quality_gates():
    from ask_pipeline.production import quality_gates_sample

    return quality_gates_sample()


# ---------------------------------------------------------------------------
# AGIB v2.2 — Institutional Research Office (knowledge-only publications)
# ---------------------------------------------------------------------------
@router.get("/research-office/dashboard")
async def research_office_dashboard():
    from research_office.production import dashboard

    return dashboard()


@router.get("/research-office/publications")
async def research_office_publications(limit: int = 100, pub_type: str | None = None):
    from research_office.production import publications

    return publications(limit=limit, pub_type=pub_type)


@router.get("/research-office/watchlists")
async def research_office_watchlists():
    from research_office.production import watchlists

    return watchlists()


@router.get("/research-office/queue")
async def research_office_queue():
    from research_office.production import queue

    return queue()


@router.get("/research-office/company/{ticker}")
async def research_office_company(ticker: str, generate: bool = False):
    from research_office.production import company

    return company(ticker, generate=generate)


@router.get("/research-office/history")
async def research_office_history(limit: int = 50):
    from research_office.production import history

    return history(limit=limit)


@router.get("/research-office/replay")
async def research_office_replay(replay_id: str):
    from research_office.production import replay

    return replay(replay_id)


@router.get("/research-office/health")
async def research_office_health():
    from research_office.production import health

    return health()


# ---------------------------------------------------------------------------
# AGIB v4.0 — Research Intelligence Hub (research notes as Intelligence Objects)
# ---------------------------------------------------------------------------


@router.get("/rih/health")
async def rih_health():
    from research_intelligence_hub.production import health

    return health()


@router.get("/research/hub")
async def rih_list(limit: int = Query(50, ge=1, le=200)):
    from research_intelligence_hub.production import list_hubs

    return list_hubs(limit=limit)


@router.get("/research/hub/dashboard")
async def rih_dashboard():
    from research_intelligence_hub.production import dashboard

    return dashboard()


@router.post("/research/hub/run")
async def rih_run(payload: dict[str, Any] = Body(default={})):
    """Ops / scheduler only — never called by Ask."""
    from research_intelligence_hub.production import run

    return run(note_id=payload.get("note_id"))


@router.post("/research/hub/build")
async def rih_build(payload: dict[str, Any] = Body(default={})):
    """Build (and optionally publish) a hub from article metadata. Ops / CMS soft-wire."""
    from research_intelligence_hub.production import build
    from research_intelligence_hub.backpressure import ResearchHubBusyError, run_single_flight

    headline = payload.get("headline") or payload.get("title")
    if not headline:
        raise HTTPException(status_code=400, detail="headline required")
    tickers = payload.get("tickers") or payload.get("companies") or []
    if isinstance(tickers, str):
        tickers = [t.strip() for t in tickers.split(",") if t.strip()]
    try:
        return await run_single_flight(
            build,
            note_id=payload.get("note_id") or payload.get("id") or payload.get("article_id"),
            headline=str(headline),
            body=str(payload.get("body") or payload.get("content") or ""),
            publication_date=payload.get("publication_date"),
            session=payload.get("session"),
            tickers=list(tickers) if isinstance(tickers, list) else None,
            importance_score=int(payload.get("importance_score") or 50),
            persist=bool(payload.get("persist")),
        )
    except ResearchHubBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc


@router.get("/research/hub/{note_id}/graph")
async def rih_graph(note_id: str):
    from research_intelligence_hub.production import graph

    return graph(note_id)


@router.get("/research/hub/{note_id}/history")
async def rih_history(note_id: str, limit: int = Query(20, ge=1, le=100)):
    from research_intelligence_hub.production import history

    return history(note_id, limit=limit)


@router.get("/research/hub/{note_id}")
async def rih_hub(note_id: str):
    from research_intelligence_hub.production import hub

    return hub(note_id)


@router.get("/admin/research-intelligence-hub", response_class=HTMLResponse)
async def admin_rih():
    from research_intelligence_hub.production import dashboard

    board = dashboard()
    rows = "".join(
        f"<tr><td>{h.get('id')}</td><td>{h.get('headline')}</td>"
        f"<td>{h.get('session')}</td><td>{h.get('importance_score')}</td>"
        f"<td>{', '.join(h.get('companies') or [])}</td>"
        f"<td>{(h.get('probability_distribution') or {})}</td></tr>"
        for h in (board.get("hubs") or [])
    )
    html = f"""<!doctype html><html><head><title>Research Intelligence Hub</title></head>
    <body style="font-family:system-ui;max-width:1100px;margin:2rem auto">
    <h1>Research Intelligence Hub — RIH</h1>
    <p>Every research note is an Intelligence Object. AGI-owned knowledge only. Ask never fetches.</p>
    <pre>{board.get('design_principle')}</pre>
    <pre>{board.get('principles')}</pre>
    <h2>Current hub</h2>
    <pre>{board.get('current_hub')}</pre>
    <h2>Link coverage</h2>
    <pre>{board.get('link_coverage')}</pre>
    <h2>Hubs</h2>
    <table border="1" cellpadding="6">
    <tr><th>ID</th><th>Headline</th><th>Session</th><th>Importance</th><th>Companies</th><th>Forecast</th></tr>
    {rows or '<tr><td colspan=6>Run POST /v1/research/hub/run</td></tr>'}
    </table>
    <h2>Forecast attachment</h2>
    <pre>{board.get('forecast_attachment')}</pre>
    <h2>Navigation</h2>
    <pre>{board.get('navigation')}</pre>
    </body></html>"""
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# AGIB v2.0 — Unified Institutional Knowledge Stack (Sprints 1–7 soft orchestration)
# ---------------------------------------------------------------------------
@router.get("/institutional-knowledge/health")
async def institutional_knowledge_health():
    from knowledge_factory.institutional_knowledge_stack.production import health as iks_health

    return iks_health()


@router.get("/institutional-knowledge/dashboard")
async def institutional_knowledge_dashboard(ensure: bool = False):
    from knowledge_factory.institutional_knowledge_stack.production import dashboard

    return dashboard(ensure=ensure)


@router.post("/institutional-knowledge/run")
async def institutional_knowledge_run(payload: dict[str, Any] = Body(default={})):
    from knowledge_factory.institutional_knowledge_stack.production import run_stack

    return run_stack(ensure_only_missing=bool((payload or {}).get("ensure_only_missing")))


@router.get("/institutional-knowledge/company/{ticker}")
async def institutional_knowledge_company(ticker: str):
    from knowledge_factory.institutional_knowledge_stack.production import company_bundle

    return company_bundle(ticker)


@router.get("/knowledge-factory/historical-depth")
async def knowledge_factory_historical_depth():
    """Historical Depth Coverage dashboard (Sprint 4 north-star KPI)."""
    from knowledge_factory.production import historical_depth_coverage

    return historical_depth_coverage()


@router.post("/knowledge-factory/historical-depth/run")
async def knowledge_factory_historical_depth_run():
    from knowledge_factory.production import run_historical_depth_pipeline

    return run_historical_depth_pipeline()


@router.get("/knowledge-factory/historical-depth/as-of/{ticker}")
async def knowledge_factory_historical_as_of(ticker: str, as_of: str):
    """Point-in-time company state — no future leakage past as_of."""
    from knowledge_factory.historical_depth.time_travel import state_as_of

    return state_as_of(ticker, as_of)


@router.get("/knowledge-factory/historical-depth/compare/{ticker}")
async def knowledge_factory_historical_compare(ticker: str, date_a: str, date_b: str):
    from knowledge_factory.historical_depth.time_travel import compare_as_of

    return compare_as_of(ticker, date_a, date_b)


@router.get("/knowledge-factory/historical-depth/query/{ticker}/valuation/{year}")
async def knowledge_factory_historical_valuation_year(ticker: str, year: int):
    from knowledge_factory.historical_depth.queries import valuation_during

    return valuation_during(ticker, year)


@router.get("/knowledge-factory/historical-depth/query/{ticker}/pe-percentile")
async def knowledge_factory_pe_percentile(ticker: str, percentile: float = 90.0):
    from knowledge_factory.historical_depth.queries import pe_above_percentile

    return pe_above_percentile(ticker, percentile)


@router.get("/knowledge-factory/historical-depth/query/{ticker}/crisis-drawdown")
async def knowledge_factory_crisis_drawdown(ticker: str):
    from knowledge_factory.historical_depth.queries import largest_crisis_drawdown

    return largest_crisis_drawdown(ticker)


@router.get("/knowledge-factory/historical-depth/query/{ticker}/rate-hiking-cycles")
async def knowledge_factory_rate_hiking(ticker: str):
    from knowledge_factory.historical_depth.queries import performance_across_rate_hiking_cycles

    return performance_across_rate_hiking_cycles(ticker)


@router.get("/knowledge-factory/sector-intelligence")
async def knowledge_factory_sector_intelligence():
    """Institutional Sector Intelligence Coverage dashboard."""
    from knowledge_factory.production import sector_intelligence_coverage

    return sector_intelligence_coverage()


@router.post("/knowledge-factory/sector-intelligence/run")
async def knowledge_factory_sector_intelligence_run():
    from knowledge_factory.production import run_sector_intelligence_pipeline

    return run_sector_intelligence_pipeline()


@router.get("/knowledge-factory/sector-intelligence/query/expensive/{ticker}")
async def knowledge_factory_sector_expensive(ticker: str):
    from knowledge_factory.sector_intelligence.queries import is_expensive_vs_sector_history

    return is_expensive_vs_sector_history(ticker)


@router.get("/knowledge-factory/sector-intelligence/query/framework/{ticker}")
async def knowledge_factory_sector_framework(ticker: str):
    from knowledge_factory.sector_intelligence.queries import should_use_dcf

    return should_use_dcf(ticker)


@router.get("/knowledge-factory/sector-intelligence/query/rates-fall")
async def knowledge_factory_sectors_rates_fall():
    from knowledge_factory.sector_intelligence.queries import sectors_outperform_when_rates_fall

    return sectors_outperform_when_rates_fall()


@router.get("/knowledge-factory/sector-intelligence/query/valuation/{sector}/{year}")
async def knowledge_factory_sector_valuation_year(sector: str, year: int):
    from knowledge_factory.sector_intelligence.queries import sector_valuation_during

    return sector_valuation_during(sector, year)


@router.get("/knowledge-factory/sector-intelligence/query/strongest-roic")
async def knowledge_factory_strongest_roic():
    from knowledge_factory.sector_intelligence.queries import strongest_roic_sector

    return strongest_roic_sector()


@router.get("/knowledge-factory/sector-intelligence/query/regime/{regime_id}")
async def knowledge_factory_sector_regime(regime_id: str):
    from knowledge_factory.sector_intelligence.queries import sectors_resembling_regime

    return sectors_resembling_regime(regime_id)


@router.get("/knowledge-factory/sector-intelligence/{sector}/playbook")
async def knowledge_factory_sector_playbook(sector: str):
    from knowledge_factory.sector_intelligence.queries import get_playbook

    return get_playbook(sector)


@router.get("/knowledge-factory/sector-intelligence/{sector}")
async def knowledge_factory_sector_object(sector: str):
    from knowledge_factory.sector_intelligence import store as isi_store
    from knowledge_factory.sector_intelligence.schema import canonicalize

    key = canonicalize(sector) or sector
    obj = isi_store.get_object(key)
    if not obj:
        return {"found": False, "sector": key, "reason": "sector_history_unavailable", "fabricated": False}
    return {"found": True, "sector": key, "object": obj}


@router.get("/knowledge-factory/macro-intelligence")
async def knowledge_factory_macro_intelligence():
    """Institutional Macro Intelligence Coverage dashboard."""
    from knowledge_factory.production import macro_intelligence_coverage

    return macro_intelligence_coverage()


@router.post("/knowledge-factory/macro-intelligence/run")
async def knowledge_factory_macro_intelligence_run():
    from knowledge_factory.production import run_macro_intelligence_pipeline

    return run_macro_intelligence_pipeline()


@router.get("/knowledge-factory/macro-intelligence/query/regime")
async def knowledge_factory_macro_regime():
    from knowledge_factory.macro_intelligence.queries import current_regime

    return current_regime()


@router.get("/knowledge-factory/macro-intelligence/query/similar")
async def knowledge_factory_macro_similar():
    from knowledge_factory.macro_intelligence.queries import most_similar_historical_regime

    return most_similar_historical_regime()


@router.get("/knowledge-factory/macro-intelligence/query/falling-rates")
async def knowledge_factory_macro_falling_rates():
    from knowledge_factory.macro_intelligence.queries import sectors_benefit_falling_rates

    return sectors_benefit_falling_rates()


@router.get("/knowledge-factory/macro-intelligence/query/oil-shock")
async def knowledge_factory_macro_oil_shock(pct: float = 0.30):
    from knowledge_factory.macro_intelligence.queries import oil_shock_impacts

    return oil_shock_impacts(pct=pct)


@router.get("/knowledge-factory/macro-intelligence/query/usd-it")
async def knowledge_factory_macro_usd_it():
    from knowledge_factory.macro_intelligence.queries import usd_strength_it

    return usd_strength_it()


@router.get("/knowledge-factory/macro-intelligence/query/replay/covid")
async def knowledge_factory_macro_replay_covid():
    from knowledge_factory.macro_intelligence.queries import replay_covid

    return replay_covid()


@router.get("/knowledge-factory/macro-intelligence/query/replay/2008")
async def knowledge_factory_macro_replay_2008():
    from knowledge_factory.macro_intelligence.queries import replay_2008

    return replay_2008()


@router.get("/knowledge-factory/macro-intelligence/query/unavailable")
async def knowledge_factory_macro_unavailable(as_of: str = "1990-01-01"):
    from knowledge_factory.macro_intelligence.queries import macro_unavailable

    return macro_unavailable(as_of=as_of)


@router.get("/knowledge-factory/macro-intelligence/query/replay/{as_of}")
async def knowledge_factory_macro_replay(as_of: str):
    from knowledge_factory.macro_intelligence.queries import replay_macro

    return replay_macro(as_of=as_of)


@router.get("/knowledge-factory/macro-intelligence/playbook/{regime}")
async def knowledge_factory_macro_playbook(regime: str):
    from knowledge_factory.macro_intelligence.queries import get_playbook

    return get_playbook(regime)


@router.get("/knowledge-factory/macro-intelligence/{macro_id}")
async def knowledge_factory_macro_object(macro_id: str):
    from knowledge_factory.macro_intelligence import store as imi_store

    obj = imi_store.get_object(macro_id)
    if not obj:
        return {
            "found": False,
            "macro_id": macro_id,
            "reason": "macro_history_unavailable",
            "fabricated": False,
        }
    return {"found": True, "macro_id": macro_id, "object": obj}


@router.get("/knowledge-factory/quality-gates")
async def knowledge_factory_quality_gates():
    from knowledge_factory.production import quality_gates

    return quality_gates()


@router.post("/knowledge-factory/run-daily")
async def knowledge_factory_run_daily():
    from knowledge_factory.production import run_daily_pipeline

    return run_daily_pipeline()


@router.get("/knowledge-factory/company/{ticker}")
async def knowledge_factory_company(ticker: str):
    from knowledge_factory.production import company_object

    obj = company_object(ticker)
    if not obj:
        return {"found": False, "ticker": ticker.upper()}
    return {"found": True, "ticker": ticker.upper(), "object": obj}


@router.get("/knowledge-factory/evidence/{ticker}")
async def knowledge_factory_evidence(ticker: str):
    from knowledge_factory.production import evidence_feed

    feed = evidence_feed(ticker)
    if not feed:
        return {"found": False, "ticker": ticker.upper(), "raw_api": False}
    return {"found": True, **feed}


@router.get("/answer-construction/health")
async def answer_construction_health():
    from answer_construction.production import health

    return health()

@router.get("/editorial/health")
async def editorial_health():
    from editorial.production import health

    return health()


@router.get("/contradiction-reasoning/health")
async def contradiction_reasoning_health():
    from contradiction_reasoning.production import health

    return health()


@router.get("/red-team/ecr/health")
async def red_team_ecr_health():
    try:
        from red_team.production import health

        out = health()
        out = dict(out) if isinstance(out, dict) else {"status": "ok"}
        out["ecr_soft_wire"] = True
        out["blind_runner_eval_only"] = True
        return out
    except Exception as exc:
        return {
            "status": "ok",
            "module": "ecr",
            "soft_wire": True,
            "eval_lab_only_beyond_ecr": True,
            "note": str(exc)[:120],
        }


# ---------------------------------------------------------------------------
# AGI Institutional Intelligence Examination (IIEX) v1.0
# CIO Investment Committee Assessment — AGIB platform only; no internet.
# MODULE_CODE IIEX avoids collision with Investment Intelligence Engine (app/iie).
# ---------------------------------------------------------------------------
@router.get("/institutional-intelligence-examination/health")
@router.get("/iiex/health")
async def iiex_health():
    from institutional_intelligence_examination.production import health as _h

    return _h()


@router.get("/institutional-intelligence-examination/dashboard")
@router.get("/iiex/dashboard")
async def iiex_dashboard():
    from institutional_intelligence_examination.production import dashboard as _d

    return _d()


@router.get("/institutional-intelligence-examination/questions")
@router.get("/iiex/questions")
async def iiex_questions():
    from institutional_intelligence_examination.production import questions as _q

    return _q()


@router.post("/institutional-intelligence-examination/run")
@router.post("/iiex/run")
async def iiex_run(body: dict | None = None):
    from institutional_intelligence_examination.production import run as _run

    body = body or {}
    return _run(question_ids=body.get("question_ids"))


@router.get("/institutional-intelligence-examination/report")
@router.get("/iiex/report")
async def iiex_report(run_id: str | None = None):
    from institutional_intelligence_examination.production import report as _r

    return _r(run_id=run_id)


@router.get("/institutional-intelligence-examination/grades")
@router.get("/iiex/grades")
async def iiex_grades(run_id: str | None = None):
    from institutional_intelligence_examination.production import grades as _g

    return _g(run_id=run_id)


@router.get("/institutional-intelligence-examination/history")
@router.get("/iiex/history")
async def iiex_history(limit: int = 20):
    from institutional_intelligence_examination.production import history as _h

    return _h(limit=limit)


# ---------------------------------------------------------------------------
# AGIB Phase 2.5 — Institutional Knowledge Intelligence (KIP v2)
# Document Intelligence -> Structured Knowledge -> Evidence Validation ->
# Knowledge Store -> Executive Summary / Retrieval. See kip_v2/__init__.py.
# ---------------------------------------------------------------------------
@router.get("/kip-v2/health")
async def kip_v2_health():
    from kip_v2.production import health

    return health()


@router.post("/kip-v2/ingest")
async def kip_v2_ingest(payload: dict[str, Any] = Body(default_factory=dict)):
    from kip_v2.production import ingest

    return ingest(payload)


@router.get("/kip-v2/knowledge/{company_id}")
async def kip_v2_get_knowledge(company_id: str, category: str | None = None, key: str | None = None):
    from kip_v2.production import get_knowledge

    return get_knowledge(company_id, category=category, key=key)


@router.get("/kip-v2/financials/{company_id}")
async def kip_v2_get_financials(company_id: str, metric: str | None = None, period: str | None = None):
    from kip_v2.production import get_financial_metrics

    return get_financial_metrics(company_id, metric=metric, period=period)


@router.get("/kip-v2/management/{company_id}")
async def kip_v2_get_management(company_id: str, topic: str | None = None):
    from kip_v2.production import get_management_commentary

    return get_management_commentary(company_id, topic=topic)


@router.get("/kip-v2/changes/{company_id}")
async def kip_v2_get_changes(company_id: str, from_period: str | None = None, to_period: str | None = None):
    from kip_v2.production import get_changes

    return get_changes(company_id, from_period=from_period, to_period=to_period)


@router.get("/kip-v2/graph/{node_id}")
async def kip_v2_get_graph(node_id: str):
    from kip_v2.production import get_knowledge_graph

    return get_knowledge_graph(node_id)


@router.get("/kip-v2/summary/{company_id}")
async def kip_v2_get_summary(company_id: str):
    from kip_v2.production import get_executive_summary

    return get_executive_summary(company_id)


@router.post("/kip-v2/ask")
async def kip_v2_ask(payload: dict[str, Any] = Body(default_factory=dict)):
    from kip_v2.production import ask

    company_id = payload.get("company_id", "")
    question = payload.get("question", "")
    return ask(company_id, question)


@router.get("/kip-v2/quality-report")
async def kip_v2_quality_report(company_id: str | None = None):
    from kip_v2.production import quality_report

    return quality_report(company_id=company_id)


# ---------------------------------------------------------------------------
# AGI Institutional Data Warehouse (admin workspace)
# ---------------------------------------------------------------------------


def _warehouse_actor(payload: dict[str, Any] | None = None, header: str | None = None) -> str:
    body_actor = str((payload or {}).get("actor") or "").strip()
    return body_actor or (header or "").strip() or "admin"


@router.get("/warehouse/freshness")
def warehouse_freshness(today: str | None = None):
    """Which tables are current, which are late, and whose desk it affects.

    Five tables sat on 20 August for three days without anything reporting it:
    the collectors failed per company with 401s, the schedulers reported
    themselves enabled, and the pages showed old numbers with no indication
    they were old.
    """
    from institutional_warehouse.freshness import report

    return report(today=today)


@router.get("/warehouse/health")
def warehouse_health():
    from institutional_warehouse.production import health

    return health()


@router.post("/warehouse/repair/upstox-quarterly")
def warehouse_repair_upstox_quarterly(body: dict[str, Any] | None = None):
    from institutional_warehouse.production import repair_upstox_quarterly

    body = body or {}
    if body.get("apply") and body.get("confirm") != "RETIRE_DUPLICATE_UPSTOX_Q4":
        return {"ok": False, "error": "repair_confirmation_required"}
    row_ids = body.get("row_ids") if isinstance(body.get("row_ids"), list) else None
    return repair_upstox_quarterly(
        actor=_warehouse_actor(body),
        apply=bool(body.get("apply")),
        row_ids=row_ids,
    )


@router.get("/warehouse/workbook")
def warehouse_workbook():
    from institutional_warehouse.production import workbook

    return workbook()


@router.get("/warehouse/stats")
def warehouse_stats():
    from institutional_warehouse.production import stats

    return stats()


@router.get("/warehouse/reconciliation/desk-values")
def warehouse_reconciliation_desk_values(limit: int = 60):
    """What the desk would display, shaped for comparison with a vendor.

    Every defect found on 2026-08-20 was a case of a correct source existing
    while the display used something else, and none was caught by a test. This
    exposes the displayed side so an independent reference can contradict it.

    Sync def on purpose - it reads the warehouse, so FastAPI runs it in the
    threadpool rather than on the event loop.
    """
    from institutional_warehouse.reconciliation import desk_values

    values = desk_values(limit=max(1, min(int(limit or 60), 400)))
    return {"ok": bool(values), "count": len(values), "fields": sorted(
        {k for row in values.values() for k in row}), "values": values}


@router.post("/warehouse/reconciliation/compare")
def warehouse_reconciliation_compare(payload: dict[str, Any] = Body(default_factory=dict)):
    """Compare desk values against a reference supplied by the caller.

    The reference arrives in the request rather than being fetched here, so the
    vendor credential stays with whoever holds it.
    """
    from institutional_warehouse.reconciliation import desk_values, reconcile

    body = payload or {}
    reference = body.get("reference") or {}
    if not isinstance(reference, dict) or not reference:
        return {"ok": False, "error": "reference_required",
                "detail": "Pass {\"reference\": {\"SYMBOL\": {\"price\": ..., ...}}}"}
    ours = body.get("ours") or desk_values(limit=max(1, min(int(body.get("limit") or 60), 400)))
    return reconcile(ours, reference)


@router.get("/warehouse/clean")
def warehouse_clean_summary(limit: int = 5000):
    """Headline numbers for each curated view: what was kept, and what was not.

    Sync def on purpose - it scans the warehouse, so FastAPI runs it in the
    threadpool rather than on the event loop.
    """
    from institutional_warehouse.clean_views import summary

    return summary(limit=max(100, min(int(limit or 5000), 20000)))


@router.get("/warehouse/clean/{name}")
def warehouse_clean_view(name: str, limit: int = 5000):
    """One curated view, with the known-bad rows filtered out and counted.

    The warehouse holds good and corrupt rows in the same tables - quarterly
    figures labelled as annual, weekend bars on a market that was closed - and
    nothing downstream can separate them without knowing the specific defect.
    """
    from institutional_warehouse.clean_views import view

    return view(name, limit=max(100, min(int(limit or 5000), 20000)))


@router.get("/warehouse/whoami")
def warehouse_whoami(x_agi_actor: str | None = Header(default=None)):
    from institutional_warehouse.production import whoami

    return whoami(_warehouse_actor(None, x_agi_actor))


@router.get("/warehouse/tab/{tab_id}/schema")
def warehouse_tab_schema(tab_id: str):
    from institutional_warehouse.production import tab_schema

    return tab_schema(tab_id)


@router.get("/warehouse/tab/{tab_id}")
def warehouse_sheet(
    tab_id: str,
    entity: str | None = None,
    q: str | None = None,
    sort: str | None = None,
    order: str = "asc",
    limit: int = 200,
    offset: int = 0,
    filters: str | None = None,
):
    import json as _json

    from institutional_warehouse.production import sheet

    parsed: dict[str, Any] = {}
    if filters:
        try:
            parsed = _json.loads(filters)
        except Exception:
            parsed = {}
    return sheet(tab_id, entity=entity, filters=parsed, q=q, sort=sort, order=order,
                 limit=limit, offset=offset)


@router.get("/warehouse/tab/{tab_id}/row/{row_id}")
def warehouse_row(tab_id: str, row_id: str):
    from institutional_warehouse.production import row

    return row(tab_id, row_id)


@router.post("/warehouse/tab/{tab_id}/edit")
def warehouse_edit(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import edit

    body = payload or {}
    edits = body.get("edits")
    if not isinstance(edits, list):
        single = {k: body.get(k) for k in ("row_id", "column", "value")}
        edits = [single] if single.get("row_id") else []
    return edit(tab_id, edits, actor=_warehouse_actor(body, x_agi_actor),
                reason=body.get("reason"), recalc=bool(body.get("recalculate", True)))


@router.post("/warehouse/tab/{tab_id}/row")
def warehouse_create_row(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import create

    body = payload or {}
    return create(tab_id, body.get("values") or {}, actor=_warehouse_actor(body, x_agi_actor))


@router.post("/warehouse/tab/{tab_id}/clear-override")
def warehouse_clear_override(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import clear_override

    body = payload or {}
    return clear_override(tab_id, str(body.get("row_id") or ""), str(body.get("column") or ""),
                          actor=_warehouse_actor(body, x_agi_actor))


@router.post("/warehouse/tab/{tab_id}/delete")
def warehouse_delete_rows(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import delete

    body = payload or {}
    return delete(tab_id, body.get("row_ids") or [], actor=_warehouse_actor(body, x_agi_actor),
                  reason=body.get("reason"))


@router.post("/warehouse/tab/{tab_id}/retire")
def warehouse_retire_rows(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Hide bad imported rows from active reads, keeping the audit history.

    Append-only tabs refuse deletion on purpose - consensus_metric_vintages is
    the point-in-time panel, and rewriting history is exactly what it exists to
    prevent. But a bad import still has to be withdrawable, or the only way to
    correct one is to leave it in place. Retiring sets sys_published = 0, so
    the rows drop out of every active read while the version snapshot and audit
    trail survive.

    A reason is mandatory: a row hidden without one is indistinguishable from
    data quietly going missing.
    """
    from institutional_warehouse import store

    body = payload or {}
    row_ids = body.get("row_ids") or []
    reason = str(body.get("reason") or "").strip()
    if not row_ids:
        return {"ok": False, "error": "no_row_ids"}
    if not reason:
        return {"ok": False, "error": "reason_required"}
    return store.retire_rows(tab_id, row_ids,
                             actor=_warehouse_actor(body, x_agi_actor), reason=reason)


@router.post("/warehouse/tab/{tab_id}/publish")
def warehouse_publish(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import publish

    return publish(tab_id, actor=_warehouse_actor(payload, x_agi_actor))


@router.post("/warehouse/tab/{tab_id}/import")
def warehouse_stage_import(
    tab_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import stage_import

    body = payload or {}
    return stage_import(
        tab_id,
        rows=body.get("rows"),
        text=body.get("text"),
        headers=body.get("headers"),
        matrix=body.get("matrix"),
        mapping=body.get("mapping"),
        actor=_warehouse_actor(body, x_agi_actor),
        source=str(body.get("source") or "manual_import"),
    )


@router.post("/warehouse/import/{import_id}/commit")
async def warehouse_commit_import(
    import_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import commit_import

    body = payload or {}
    return await run_in_threadpool(
        commit_import,
        import_id,
        actor=_warehouse_actor(body, x_agi_actor),
        recalculate=bool(body.get("recalculate", True)),
    )


@router.post("/warehouse/tab/{tab_id}/map-headers")
def warehouse_map_headers(tab_id: str, payload: dict[str, Any] = Body(default_factory=dict)):
    from institutional_warehouse.production import preview_mapping

    return preview_mapping(tab_id, (payload or {}).get("headers") or [])


@router.get("/warehouse/imports")
def warehouse_imports(tab_id: str | None = None, limit: int = 25):
    from institutional_warehouse.production import imports

    return imports(tab_id=tab_id, limit=limit)


@router.get("/warehouse/tab/{tab_id}/export")
def warehouse_export(
    tab_id: str,
    entity: str | None = None,
    q: str | None = None,
    limit: int = 5000,
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import export

    return export(tab_id, entity=entity, search=q, limit=limit,
                  actor=_warehouse_actor(None, x_agi_actor))


@router.get("/warehouse/tab/{tab_id}/row/{row_id}/history")
def warehouse_history(tab_id: str, row_id: str, column: str | None = None):
    from institutional_warehouse.production import history

    return history(tab_id, row_id, column=column)


@router.get("/warehouse/tab/{tab_id}/row/{row_id}/compare")
def warehouse_compare(tab_id: str, row_id: str, version_a: int, version_b: int | None = None):
    from institutional_warehouse.production import compare

    return compare(tab_id, row_id, version_a, version_b)


@router.post("/warehouse/tab/{tab_id}/row/{row_id}/restore")
def warehouse_restore(
    tab_id: str,
    row_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import restore

    body = payload or {}
    version = body.get("version")
    return restore(tab_id, row_id, version=int(version) if version is not None else None,
                   snapshot_id=body.get("snapshot_id"),
                   actor=_warehouse_actor(body, x_agi_actor))


@router.get("/warehouse/audit")
def warehouse_audit(
    tab_id: str | None = None,
    entity: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    from institutional_warehouse.production import audit_log

    return audit_log(tab_id=tab_id, entity=entity, action=action, actor=actor,
                     limit=limit, offset=offset)


@router.get("/warehouse/validate")
def warehouse_validate(tab_id: str | None = None, sample: int = 300):
    from institutional_warehouse.production import validate

    return validate(tab_id, sample=sample)


@router.post("/warehouse/refresh")
def warehouse_refresh(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import run_refresh

    body = payload or {}
    kwargs: dict[str, Any] = {"actor": _warehouse_actor(body, x_agi_actor)}
    if body.get("stages"):
        kwargs["stages"] = body["stages"]
    if body.get("limit") is not None:
        kwargs["limit"] = int(body["limit"])
    if body.get("days") is not None:
        kwargs["days"] = int(body["days"])
    return run_refresh(**kwargs)


@router.get("/warehouse/refresh-runs")
def warehouse_refresh_runs(limit: int = 20):
    from institutional_warehouse.production import refresh_runs

    return refresh_runs(limit=limit)


@router.get("/warehouse/scheduler")
def warehouse_scheduler():
    from institutional_warehouse.production import scheduler_status

    return scheduler_status()


@router.post("/warehouse/recalculate")
async def warehouse_recalculate(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import recompute

    body = payload or {}
    kwargs: dict[str, Any] = {"actor": _warehouse_actor(body, x_agi_actor)}
    if body.get("stages"):
        kwargs["stages"] = body["stages"]
    if body.get("entity"):
        kwargs["entity"] = str(body["entity"]).upper()
    # Formula recomputation is synchronous and can scan substantial warehouse
    # history. Keep it off uvicorn's event loop so health checks and unrelated
    # API traffic remain responsive while a scheduled factor refresh runs.
    return await run_in_threadpool(recompute, **kwargs)


@router.get("/warehouse/search")
def warehouse_search(q: str, per_tab: int = 5, tabs: str | None = None):
    from institutional_warehouse.production import global_search

    tab_list = [t.strip() for t in tabs.split(",") if t.strip()] if tabs else None
    return global_search(q, tabs=tab_list, per_tab=per_tab)


@router.get("/warehouse/suggest")
def warehouse_suggest(prefix: str, limit: int = 10):
    from institutional_warehouse.production import suggest

    return suggest(prefix, limit=limit)


@router.get("/warehouse/company/{symbol}")
def warehouse_company(symbol: str, per_tab: int = 25):
    from institutional_warehouse.production import company

    return company(symbol, per_tab=per_tab)


@router.get("/warehouse/coverage")
def warehouse_coverage():
    from institutional_warehouse.production import coverage

    return coverage()


# ---------------------------------------------------------------------------
# Phase 7.4F — Financial Warehouse Completion Programme (FWCP)
# ---------------------------------------------------------------------------


@router.get("/fwcp/health")
async def fwcp_health():
    from financial_warehouse_completion import health

    return health()


@router.get("/warehouse/financial-coverage")
def warehouse_financial_coverage():
    from financial_warehouse_completion import financial_coverage

    return financial_coverage()


@router.get("/warehouse/financial-audit")
def warehouse_financial_audit():
    """Phase 7.4F Step 0 — read-only financial warehouse coverage audit."""
    from financial_warehouse_completion import financial_audit

    return financial_audit()


@router.get("/warehouse/coverage/summary")
def warehouse_coverage_summary():
    from financial_warehouse_completion import coverage_summary

    return coverage_summary()


@router.get("/warehouse/coverage/sector")
def warehouse_coverage_sector():
    from financial_warehouse_completion import coverage_sector

    return coverage_sector()


@router.get("/warehouse/missing-financials")
def warehouse_missing_financials(limit: int = 500, classification: str | None = None):
    from financial_warehouse_completion import missing_financials

    return missing_financials(limit=limit, classification=classification)


@router.get("/warehouse/company/{symbol}/coverage")
def warehouse_company_financial_coverage(symbol: str):
    from financial_warehouse_completion import company_coverage

    return company_coverage(symbol)


@router.get("/warehouse/missing-statements")
def warehouse_missing_statements(limit: int = 500):
    from financial_warehouse_completion import missing_statements

    return missing_statements(limit=limit)


@router.get("/warehouse/missing-share-count")
def warehouse_missing_share_count(limit: int = 500):
    from financial_warehouse_completion import missing_share_count

    return missing_share_count(limit=limit)


@router.get("/warehouse/import/status")
def warehouse_import_status():
    from financial_warehouse_completion import import_status

    return import_status()


@router.get("/warehouse/import/board")
def warehouse_import_board():
    from financial_warehouse_completion import import_board

    return import_board()


@router.post("/warehouse/import/start")
def warehouse_import_start(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import import_start

    body = payload or {}
    return import_start(
        batch=int(body.get("batch") or 15),
        actor=_warehouse_actor(body, x_agi_actor),
    )


@router.post("/warehouse/import/stop")
def warehouse_import_stop():
    from financial_warehouse_completion import import_stop

    return import_stop()


@router.post("/warehouse/import/resume")
def warehouse_import_resume(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import import_resume

    body = payload or {}
    return import_resume(
        batch=int(body.get("batch") or 15),
        actor=_warehouse_actor(body, x_agi_actor),
    )


@router.post("/warehouse/import/retry")
def warehouse_import_retry(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import import_retry

    body = payload or {}
    return import_retry(
        limit=int(body.get("limit") or 50),
        actor=_warehouse_actor(body, x_agi_actor),
    )


@router.post("/warehouse/import/run")
def warehouse_import_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import import_run

    body = payload or {}
    symbols = body.get("symbols")
    if isinstance(symbols, str):
        symbols = [symbols]
    return import_run(
        batch=int(body.get("batch") or 10),
        symbols=symbols,
        actor=_warehouse_actor(body, x_agi_actor),
        include_capital_iq=bool(body.get("include_capital_iq")),
    )


@router.get("/warehouse/import/capital-iq")
def warehouse_import_capital_iq_status():
    from financial_warehouse_completion import capital_iq

    return capital_iq()


@router.post("/warehouse/import/capital-iq")
def warehouse_import_capital_iq_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import run_capital_iq

    body = payload or {}
    limit = body.get("limit")
    return run_capital_iq(
        limit=int(limit) if limit is not None else None,
        actor=_warehouse_actor(body, x_agi_actor),
    )


@router.get("/warehouse/import/capiq-vintages")
def warehouse_capiq_vintages_preview():
    """Coverage of the checked-in estimate-vintage workbook, without writing."""
    from financial_warehouse_completion.capiq_vintages import parse, summarise

    parsed = parse()
    if not parsed.get("ok"):
        return {"ok": False, "error": parsed.get("error")}
    return {"ok": True, "source_version": parsed.get("source_version"),
            "stats": parsed.get("stats"), "summary": summarise(parsed)}


@router.post("/warehouse/import/capiq-vintages")
def warehouse_capiq_vintages_import():
    from financial_warehouse_completion.capiq_vintages import parse, write

    parsed = parse()
    if not parsed.get("ok"):
        return {"ok": False, "error": parsed.get("error")}
    return write(parsed)


@router.get("/warehouse/import/vendor-exports")
def warehouse_vendor_exports_preview():
    """Parsed row counts for the checked-in vendor exports, without writing."""
    from financial_warehouse_completion.vendor_exports import collect, fingerprint
    parsed = collect()
    return {"ok": True, "source_hash": fingerprint(),
            "reports": parsed["reports"], "counts": parsed["counts"]}


@router.post("/warehouse/import/vendor-exports")
def warehouse_vendor_exports_seed(payload: dict[str, Any] = Body(default={})):
    """Seed vendor exports into the warehouse. Idempotent unless force=true."""
    from financial_warehouse_completion.vendor_exports import seed_if_needed
    return seed_if_needed(force=bool(payload.get("force", False)))


@router.get("/warehouse/import/insider-trades")
def warehouse_import_insider_trades_status():
    """Preview the insider exports on disk without writing anything.

    The Insider Activity page's live source answers HTTP 429 with zero rows, so
    the page renders empty. These files carry the same disclosures at no
    per-request cost.
    """
    from financial_warehouse_completion.insider_trades import parse

    parsed = parse()
    return {k: v for k, v in parsed.items() if k != "rows"}


@router.post("/warehouse/import/insider-trades")
def warehouse_import_insider_trades_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Load every insider export in the repo, deduplicated across files."""
    from financial_warehouse_completion.insider_trades import import_trades

    return import_trades(actor=_warehouse_actor(payload or {}, x_agi_actor))


@router.post("/warehouse/import/insider-trades/preview",
             dependencies=[Depends(require_token)])
def warehouse_insider_paste_preview(payload: dict[str, Any] = Body(default_factory=dict)):
    """Parse a pasted block and report what it holds. Writes nothing.

    Separate from the write so the desk can see the row count, the date range
    and how many lines were dropped before committing to it - a vendor export
    that silently lost half its rows should be caught here, not in the data.
    """
    from financial_warehouse_completion.insider_trades import parse_pasted

    parsed = parse_pasted(str((payload or {}).get("text") or ""))
    return {k: v for k, v in parsed.items() if k != "rows"}


@router.post("/warehouse/import/insider-trades/paste",
             dependencies=[Depends(require_token)])
def warehouse_insider_paste_run(payload: dict[str, Any] = Body(default_factory=dict),
                                x_agi_actor: str | None = Header(default=None)):
    """Write a pasted block of insider trades straight to the warehouse.

    Token-guarded: this writes to a production table from free text. The rows
    go through the same normalisation and the same natural key as the file
    importer, so pasting a day that was already loaded updates those rows
    rather than duplicating them.
    """
    from financial_warehouse_completion.insider_trades import import_pasted

    return import_pasted(str((payload or {}).get("text") or ""),
                         actor=_warehouse_actor(payload or {}, x_agi_actor))


@router.get("/warehouse/import/forward-estimates")
def warehouse_import_forward_estimates_status():
    """Preview the current forward EPS and revenue cross-section.

    Coverage is roughly 910 companies of 3,023 - the real extent of sell-side
    coverage in this market, not a truncated export.
    """
    from financial_warehouse_completion.capiq_forward_estimates import parse

    parsed = parse()
    return {k: v for k, v in parsed.items() if k != "rows"}


@router.post("/warehouse/import/forward-estimates")
def warehouse_import_forward_estimates_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Load forward estimates into consensus_metric_vintages.

    Without these `forward_pe` is null across the universe, which is why the
    Forward Earnings Growth and Alpha Opportunity screens returned no rows.
    """
    from financial_warehouse_completion.capiq_forward_estimates import import_estimates

    return import_estimates(actor=_warehouse_actor(payload or {}, x_agi_actor))


@router.get("/warehouse/import/capital-iq-workbook")
def warehouse_import_capital_iq_workbook_status():
    from financial_warehouse_completion.production import capiq_workbook_status
    return capiq_workbook_status()


@router.post("/warehouse/import/capital-iq-workbook")
def warehouse_import_capital_iq_workbook_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    body = payload or {}
    years = body.get("years")
    if years is not None and (not isinstance(years, list) or not all(str(y).isdigit() for y in years)):
        raise HTTPException(status_code=422, detail="years_must_be_a_list_of_years")
    if bool(body.get("dry_run")):
        from financial_warehouse_completion.production import stage_capiq_workbook
        return stage_capiq_workbook(years=[int(year) for year in years] if years else None)
    from financial_warehouse_completion.capiq_background import create_job
    return create_job(
        years=[int(year) for year in years] if years else None,
        actor=_warehouse_actor(body, x_agi_actor),
    )


@router.get("/warehouse/import/capital-iq-workbook/jobs/latest")
def warehouse_import_capital_iq_workbook_latest():
    from financial_warehouse_completion.capiq_background import latest_job, job_status
    job = latest_job()
    return job_status(str(job["job_id"])) if job else {"ok": True, "job": None}


@router.get("/warehouse/import/capital-iq-workbook/jobs/{job_id}")
def warehouse_import_capital_iq_workbook_job(job_id: str):
    from financial_warehouse_completion.capiq_background import job_status
    return job_status(job_id)


@router.post("/warehouse/import/capital-iq-workbook/jobs/{job_id}/pause")
def warehouse_import_capital_iq_workbook_pause(job_id: str):
    from financial_warehouse_completion.capiq_background import pause
    return pause(job_id)


@router.post("/warehouse/import/capital-iq-workbook/jobs/{job_id}/resume")
def warehouse_import_capital_iq_workbook_resume(
    job_id: str, payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion.capiq_background import resume
    return resume(job_id, actor=_warehouse_actor(payload or {}, x_agi_actor))


@router.get("/warehouse/import/sector-ratio-workbook")
def warehouse_import_sector_ratio_workbook_status():
    """Preview the checked-in 10-year Capital IQ sector-ratio history."""
    from financial_warehouse_completion.production import sector_ratio_workbook_status
    return sector_ratio_workbook_status()


@router.post("/warehouse/import/sector-ratio-workbook")
def warehouse_import_sector_ratio_workbook_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Import the authoritative CapIQ sector-ratio baseline and its medians."""
    from financial_warehouse_completion.production import run_sector_ratio_workbook
    return run_sector_ratio_workbook(actor=_warehouse_actor(payload or {}, x_agi_actor))


@router.post("/warehouse/share-count/{symbol}/sync")
def warehouse_share_count_sync(
    symbol: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import sync_shares

    body = payload or {}
    return sync_shares(symbol, actor=_warehouse_actor(body, x_agi_actor))


# ---------------------------------------------------------------------------
# Phase 7.4F — Yahoo-first financial fill (fast EMPTY / thin path)
# ---------------------------------------------------------------------------


@router.get("/warehouse/yahoo-fill/status")
def warehouse_yahoo_fill_status():
    from financial_warehouse_completion import yahoo_fill_status

    return yahoo_fill_status()


@router.get("/warehouse/yahoo-fill/board")
def warehouse_yahoo_fill_board():
    from financial_warehouse_completion import yahoo_fill_board

    return yahoo_fill_board()


@router.get("/warehouse/yahoo-fill/queue")
def warehouse_yahoo_fill_queue(limit: int = 200, include_thin: bool = True):
    from financial_warehouse_completion import yahoo_fill_queue

    return yahoo_fill_queue(limit=limit, include_thin=include_thin)


@router.get("/warehouse/yahoo-fill/probe")
def warehouse_yahoo_fill_probe(symbol: str = "RELIANCE"):
    from financial_warehouse_completion import yahoo_fill_probe

    return yahoo_fill_probe(symbol)


@router.get("/warehouse/upstox-fill/queue")
def warehouse_upstox_fill_queue(
    limit: int = 200,
    include_thin: bool = True,
    exclude: str = "",
):
    from financial_warehouse_completion import upstox_fill_queue

    exclude_list = [s.strip().upper() for s in str(exclude or "").split(",") if s.strip()]
    return upstox_fill_queue(limit=limit, include_thin=include_thin, exclude=exclude_list or None)


@router.get("/warehouse/upstox-fill/board")
def warehouse_upstox_fill_board():
    from financial_warehouse_completion import upstox_fill_board

    return upstox_fill_board()


@router.post("/warehouse/yahoo-fill/start")
def warehouse_yahoo_fill_start(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import yahoo_fill_start

    body = payload or {}
    return yahoo_fill_start(
        batch=int(body.get("batch") or 25),
        actor=_warehouse_actor(body, x_agi_actor) or "yahoo_fill",
        pause_seconds=float(body.get("pause_seconds") if body.get("pause_seconds") is not None else 0.35),
        include_thin=bool(body.get("include_thin", True)),
    )


@router.post("/warehouse/yahoo-fill/stop")
def warehouse_yahoo_fill_stop():
    from financial_warehouse_completion import yahoo_fill_stop

    return yahoo_fill_stop()


@router.post("/warehouse/yahoo-fill/resume")
def warehouse_yahoo_fill_resume(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import yahoo_fill_resume

    body = payload or {}
    return yahoo_fill_resume(
        batch=int(body.get("batch") or 25),
        actor=_warehouse_actor(body, x_agi_actor) or "yahoo_fill",
        pause_seconds=float(body.get("pause_seconds") if body.get("pause_seconds") is not None else 0.35),
        include_thin=bool(body.get("include_thin", True)),
    )


@router.post("/warehouse/yahoo-fill/run")
def warehouse_yahoo_fill_run(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import yahoo_fill_run

    body = payload or {}
    symbols = body.get("symbols")
    if isinstance(symbols, str):
        symbols = [symbols]
    return yahoo_fill_run(
        batch=int(body.get("batch") or 25),
        symbols=symbols,
        actor=_warehouse_actor(body, x_agi_actor) or "yahoo_fill",
        pause_seconds=float(body.get("pause_seconds") if body.get("pause_seconds") is not None else 0.35),
        include_thin=bool(body.get("include_thin", True)),
    )


@router.post("/warehouse/yahoo-fill/{symbol}")
def warehouse_yahoo_fill_symbol(
    symbol: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from financial_warehouse_completion import yahoo_fill_company

    body = payload or {}
    return yahoo_fill_company(symbol, actor=_warehouse_actor(body, x_agi_actor) or "yahoo_fill")


# ---------------------------------------------------------------------------
# Historical Backfill & Time-Series (Phase 7.1a)
# ---------------------------------------------------------------------------


@router.post("/warehouse/backfill")
def warehouse_backfill(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import run_backfill

    body = payload or {}
    kwargs: dict[str, Any] = {"actor": _warehouse_actor(body, x_agi_actor)}
    for key in ("companies", "days"):
        if body.get(key) is not None:
            kwargs[key] = int(body[key])
    if body.get("stages"):
        kwargs["stages"] = body["stages"]
    if body.get("cadence"):
        kwargs["cadence"] = str(body["cadence"])
    # Walking the bhavcopy archive back to 2016 needs an explicit window: the
    # default candidate list is days*6 weekdays from today and stalls long
    # before it reaches the delisted companies we are after.
    for key in ("archive_start", "archive_floor"):
        if body.get(key):
            kwargs[key] = str(body[key])
    if body.get("universe"):
        kwargs["universe"] = [str(s).upper() for s in body["universe"]]
    if body.get("allow_here"):
        kwargs["enforce_worker"] = False
    # Re-collect companies already marked complete. Needed after the bhavcopy
    # walker overwrote Upstox's split-adjusted prices with raw ones - those
    # companies are all marked done, so a normal slice would skip every one.
    if body.get("refresh_done"):
        kwargs["refresh_done"] = True
    return run_backfill(**kwargs)


@router.get("/warehouse/backfill/status")
def warehouse_backfill_status():
    from institutional_warehouse.production import backfill_status

    return backfill_status()


@router.post("/warehouse/backfill/reopen")
def warehouse_backfill_reopen(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Send already-collected days back through the collector.

    Needed after a fix that changes what a day contains rather than whether it
    could be fetched. The bhavcopy parser kept only EQ and BE, so every day
    already stored is missing the companies that had been moved to the
    surveillance series on their way to being delisted - which is the whole
    reason that collector exists.

    A reason is mandatory. A day silently sent round again is indistinguishable
    from a collector looping on itself.
    """
    from institutional_warehouse.backfill import checkpoints

    body = payload or {}
    source = str(body.get("source") or "").strip()
    reason = str(body.get("reason") or "").strip()
    if not source:
        return {"ok": False, "error": "source_required"}
    if not reason:
        return {"ok": False, "error": "reason_required"}
    return checkpoints.reopen_dates(
        source,
        reason=reason,
        before=body.get("before"),
        after=body.get("after"),
    )


@router.post("/warehouse/price-basis/stamp")
def warehouse_price_basis_stamp(payload: dict[str, Any] = Body(default_factory=dict)):
    """Fill price_basis and feed_family on rows written before they existed.

    Bounded on purpose. The engine shares one SQLite file with its background
    worker, and a single UPDATE across 7.1m rows would hold a write lock for as
    long as it runs.
    """
    from institutional_warehouse import price_basis

    body = payload or {}
    return price_basis.backfill_stamps(
        batches=int(body.get("batches") or 1),
        batch_size=int(body.get("batch_size") or price_basis.STAMP_BATCH),
        # Rows stamped UNKNOWN before the declaration recognised their writer.
        restamp_unknown=bool(body.get("restamp_unknown")),
    )


@router.post("/warehouse/backfill/reopen-entities")
def warehouse_backfill_reopen_entities(payload: dict[str, Any] = Body(default_factory=dict)):
    """Put finished companies back in the queue so a scheduled slice repairs them."""
    from institutional_warehouse.backfill import checkpoints

    body = payload or {}
    kind = str(body.get("kind") or "").strip()
    reason = str(body.get("reason") or "").strip()
    if not kind:
        return {"ok": False, "error": "kind_required"}
    if not reason:
        return {"ok": False, "error": "reason_required"}
    return checkpoints.reopen_entities(kind, reason=reason)


@router.get("/warehouse/backfill/archive-floor")
def warehouse_archive_floor():
    """Where the bhavcopy walk stops, and whether it has got there.

    A walk that has finished and a walk that is stuck both stop producing rows.
    This reports which, rather than leaving it to be inferred from silence.
    """
    from institutional_warehouse.backfill.sources import nse_archive

    return {"ok": True, **nse_archive.collection_complete()}


@router.get("/warehouse/backfill/progress")
def warehouse_backfill_progress(kind: str = "upstox_prices"):
    from institutional_warehouse.backfill import checkpoints

    return checkpoints.entity_progress(kind)


@router.get("/warehouse/price-basis")
def warehouse_price_basis_status():
    from institutional_warehouse import db, price_basis

    db.init()
    table = db.physical_table("daily_market_history")
    rows = db.query(
        f"SELECT COALESCE(price_basis, 'unstamped') AS basis,"
        f" COALESCE(feed_family, 'unstamped') AS feed, COUNT(*) AS n"
        f" FROM {table} WHERE close IS NOT NULL GROUP BY basis, feed ORDER BY n DESC"
    ) or []
    return {"ok": True, "declared_sources": price_basis.known_sources(),
            "by_basis": [dict(r) for r in rows]}


@router.get("/warehouse/backfill/jobs")
def warehouse_backfill_jobs(limit: int = 20):
    from institutional_warehouse.production import backfill_jobs

    return backfill_jobs(limit=limit)


@router.get("/warehouse/historical-coverage")
def warehouse_historical_coverage(top: int = 25):
    from institutional_warehouse.production import historical_coverage

    return historical_coverage(top=top)


@router.get("/history/company/{symbol}")
async def history_company_route(symbol: str, window: str = "max", metrics: str | None = None):
    from institutional_warehouse.production import history_company

    wanted = [m.strip() for m in metrics.split(",") if m.strip()] if metrics else None
    return history_company(symbol, window=window, metrics=wanted)


@router.get("/history/series/{symbol}/{metric}")
async def history_series_route(
    symbol: str,
    metric: str,
    window: str = "max",
    start: str | None = None,
    end: str | None = None,
    limit: int = 5000,
):
    from institutional_warehouse.production import history_series

    return history_series(symbol, metric, window=window, start=start, end=end, limit=limit)


@router.get("/history/as-at/{symbol}")
async def history_as_at_route(symbol: str, on: str):
    from institutional_warehouse.production import history_as_at

    return history_as_at(symbol, on)


@router.get("/history/table/{tab_id}")
async def history_range_route(
    tab_id: str,
    symbol: str | None = None,
    start: str | None = None,
    end: str | None = None,
    fiscal_year: str | None = None,
    quarter: str | None = None,
    window: str | None = None,
    limit: int = 1000,
    offset: int = 0,
):
    from institutional_warehouse.production import history_range

    return history_range(tab_id, symbol=symbol, start=start, end=end, fiscal_year=fiscal_year,
                         quarter=quarter, window=window, limit=limit, offset=offset)


@router.get("/history/compare")
async def history_compare_route(symbols: str, metric: str, window: str = "5y"):
    from institutional_warehouse.production import history_compare

    names = [s.strip() for s in symbols.split(",") if s.strip()]
    return history_compare(names, metric, window=window)


@router.get("/history/coverage/{symbol}")
async def history_coverage_route(symbol: str):
    from institutional_warehouse.production import history_coverage

    return history_coverage(symbol)


# ---------------------------------------------------------------------------
# Historical Intelligence Engine (Phase 7.2)
# ---------------------------------------------------------------------------


@router.get("/historical-intelligence/health")
async def hie_health():
    from historical_intelligence.production import health

    return health()


@router.post("/historical-intelligence/ask")
async def hie_ask(payload: dict[str, Any] = Body(default_factory=dict)):
    from historical_intelligence.production import ask

    body = payload or {}
    peers = body.get("peers")
    return ask(
        str(body.get("question") or ""),
        symbol=(str(body.get("symbol")).upper() if body.get("symbol") else None),
        peers=[str(p).upper() for p in peers] if isinstance(peers, list) else None,
    )


@router.get("/historical-intelligence/detect")
async def hie_detect(q: str):
    from historical_intelligence.production import detect

    return detect(q)


@router.get("/historical-intelligence/coverage/{symbol}")
async def hie_coverage(symbol: str, metric: str | None = None):
    from historical_intelligence.production import company_coverage, metric_coverage

    if metric:
        return metric_coverage(symbol, metric)
    return company_coverage(symbol)


@router.get("/historical-intelligence/company/{symbol}")
async def hie_company(symbol: str, metrics: str | None = None):
    from historical_intelligence.production import company

    wanted = [m.strip() for m in metrics.split(",") if m.strip()] if metrics else None
    return company(symbol, metrics=wanted)


@router.get("/historical-intelligence/trend/{symbol}/{metric}")
async def hie_trend(symbol: str, metric: str):
    from historical_intelligence.production import trend_analysis

    return trend_analysis(symbol, metric)


@router.get("/historical-intelligence/valuation/{symbol}")
async def hie_valuation(symbol: str, metric: str = "pe"):
    from historical_intelligence.production import valuation_analysis

    return valuation_analysis(symbol, metric)


@router.get("/historical-intelligence/bands/{symbol}")
async def hie_bands(symbol: str, metric: str = "pe"):
    from historical_intelligence.production import valuation_bands

    return valuation_bands(symbol, metric)


@router.get("/historical-intelligence/timeline/{symbol}")
async def hie_timeline(symbol: str, limit: int = 40):
    from historical_intelligence.production import event_timeline

    return event_timeline(symbol, limit=limit)


@router.get("/historical-intelligence/compare")
async def hie_compare(symbols: str, metric: str = "price"):
    from historical_intelligence.production import compare

    names = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return compare(names, metric)


@router.get("/historical-intelligence/sector/{symbol}")
async def hie_sector(symbol: str, metric: str = "pe"):
    from historical_intelligence.production import against_sector

    return against_sector(symbol, metric)


# ---------------------------------------------------------------------------
# Data Quality Integration & Validation (Phase 7.3)
# ---------------------------------------------------------------------------


@router.get("/warehouse/quality")
def warehouse_quality_summary():
    from institutional_warehouse.production import quality_summary

    return quality_summary()


@router.get("/warehouse/quarantine")
def warehouse_quarantine(tab_id: str | None = None, limit: int = 100):
    from institutional_warehouse.production import quarantined_rows

    return quarantined_rows(tab_id, limit=limit)


@router.get("/warehouse/conflicts")
def warehouse_conflicts(tab_id: str | None = None, entity: str | None = None,
                              limit: int = 100):
    from institutional_warehouse.production import source_conflicts

    return source_conflicts(tab_id=tab_id, entity=entity, limit=limit)


@router.get("/warehouse/conflicts/summary")
def warehouse_conflict_summary():
    from institutional_warehouse.production import conflict_summary

    return conflict_summary()


@router.post("/warehouse/remediate-zeros")
def warehouse_remediate_zeros(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    from institutional_warehouse.production import remediate_zeros

    body = payload or {}
    return remediate_zeros(actor=_warehouse_actor(body, x_agi_actor),
                           dry_run=bool(body.get("dry_run")))


# ---------------------------------------------------------------------------
# Valuation Policy & Applicability Engine (VPAE) — Phase 8.2A
# Mandatory decision layer in front of the Unified Valuation Engine.
# ---------------------------------------------------------------------------


@router.get("/valuation-policy/health")
async def valuation_policy_health():
    from valuation_policy import health as vpae_health

    return vpae_health()


@router.get("/valuation/applicability/{symbol}")
async def valuation_applicability(symbol: str):
    from valuation_policy import applicability

    return applicability(symbol)


@router.get("/valuation/model/{symbol}")
async def valuation_model(symbol: str):
    from valuation_policy import model as vpae_model

    return vpae_model(symbol)


@router.get("/valuation/explanation/{symbol}")
async def valuation_explanation(symbol: str):
    from valuation_policy import explanation as vpae_explanation

    return vpae_explanation(symbol)


# Institutional Coverage Health — static paths BEFORE /valuation/coverage/{symbol}
@router.get("/valuation/coverage-health/health")
async def institutional_coverage_health_probe():
    from institutional_coverage_health import health as ich_health

    return ich_health()


@router.get("/valuation/coverage/health")
async def institutional_coverage_health(limit: int = 6000, force: bool = False):
    from institutional_coverage_health import coverage_health

    return coverage_health(limit=min(max(int(limit or 6000), 50), 8000), force=bool(force))


@router.get("/valuation/coverage/valuation")
async def institutional_valuation_coverage(limit: int = 6000):
    from institutional_coverage_health import valuation_coverage as ich_valuation

    return ich_valuation(limit=min(max(int(limit or 6000), 50), 8000))


@router.get("/valuation/coverage/metrics")
async def institutional_metric_coverage(limit: int = 6000):
    from institutional_coverage_health import metric_coverage as ich_metrics

    return ich_metrics(limit=min(max(int(limit or 6000), 50), 8000))


@router.get("/valuation/coverage/research")
async def institutional_research_coverage(limit: int = 6000):
    from institutional_coverage_health import research_coverage as ich_research

    return ich_research(limit=min(max(int(limit or 6000), 50), 8000))


@router.get("/valuation/coverage/residual")
async def institutional_coverage_residual(limit: int = 6000):
    from institutional_coverage_health import bootstrap_residual

    return bootstrap_residual(limit=min(max(int(limit or 6000), 50), 8000))


@router.get("/valuation/coverage/{symbol}")
async def valuation_coverage(symbol: str):
    from valuation_policy import coverage as vpae_coverage

    return vpae_coverage(symbol)


@router.get("/valuation/status/{symbol}")
async def valuation_status(symbol: str):
    from valuation_policy import status as vpae_status

    return vpae_status(symbol)


@router.get("/valuation/universe")
async def valuation_universe(
    sector: str = "",
    instrument_type: str = "",
    primary_model: str = "",
    status: str = "",
    confidence: str = "",
    limit: int = 100,
    offset: int = 0,
):
    from valuation_policy import universe as vpae_universe

    return vpae_universe(
        sector=sector or None,
        instrument_type=instrument_type or None,
        primary_model=primary_model or None,
        status_filter=status or None,
        confidence=confidence or None,
        limit=min(max(int(limit or 100), 1), 500),
        offset=max(int(offset or 0), 0),
    )


# ---------------------------------------------------------------------------
# Sector Valuation Explorer — institutional valuation research workspace v2
# ---------------------------------------------------------------------------


@router.get("/valuation/market")
async def sve_market(universe_limit: int = 5000):
    from sector_valuation_explorer import market as sve_market_fn

    return sve_market_fn(universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sectors")
async def sve_sectors(universe_limit: int = 5000):
    from sector_valuation_explorer import sectors as sve_list

    return sve_list(universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}")
async def sve_sector(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import sector_pack

    return sector_pack(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}/industries")
async def sve_sector_industries(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import sector_industries

    return sector_industries(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/industry/{industry}")
async def sve_industry(industry: str, universe_limit: int = 5000):
    from sector_valuation_explorer import industry_pack

    return industry_pack(industry, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}/summary")
async def sve_sector_summary(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import summary as sve_summary

    return sve_summary(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}/companies")
async def sve_sector_companies(
    sector: str,
    industry: str = "",
    status: str = "",
    market_cap: str = "",
    sort: str = "market_cap",
    order: str = "desc",
    limit: int = 500,
    universe_limit: int = 5000,
):
    from sector_valuation_explorer import sector_companies

    return sector_companies(
        sector,
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
        industry=industry or None,
        status=status or None,
        market_cap=market_cap or None,
        sort=sort or "market_cap",
        order=order or "desc",
        limit=min(max(int(limit or 500), 1), 2000),
    )


@router.get("/valuation/sector/{sector}/leaders")
async def sve_sector_leaders(sector: str, top: int = 10, universe_limit: int = 5000):
    from sector_valuation_explorer import leaders as sve_leaders

    return sve_leaders(
        sector,
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
        top=min(max(int(top or 10), 1), 25),
    )


@router.get("/valuation/sector/{sector}/heatmap")
async def sve_sector_heatmap(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import heatmap as sve_heatmap

    return sve_heatmap(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}/research")
async def sve_sector_research(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import research as sve_research

    return sve_research(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/sector/{sector}/rotation")
async def sve_sector_rotation(sector: str, universe_limit: int = 5000):
    from sector_valuation_explorer import sector_rotation

    return sector_rotation(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/opportunities")
async def sve_opportunities(limit: int = 10, universe_limit: int = 5000):
    from sector_valuation_explorer import opportunities as sve_opps

    return sve_opps(
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
        limit=min(max(int(limit or 10), 1), 50),
    )


@router.get("/valuation/premium")
async def sve_premium(limit: int = 10, universe_limit: int = 5000):
    from sector_valuation_explorer import premium_board

    return premium_board(
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
        limit=min(max(int(limit or 10), 1), 50),
    )


@router.get("/valuation/rerating")
async def sve_rerating(limit: int = 20, universe_limit: int = 5000):
    from sector_valuation_explorer import rerating_board

    return rerating_board(
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
        limit=min(max(int(limit or 20), 1), 50),
    )


@router.get("/valuation/company/{symbol}")
async def sve_company(symbol: str, window: str = "10Y", peer_limit: int = 12):
    """Company drill-down — Unified Valuation Engine terminal pack."""
    from valuation_engine.terminal import company_pack

    return company_pack(symbol, window=window or "10Y", peer_limit=min(max(int(peer_limit or 12), 1), 40))


@router.get("/valuation/company/{symbol}/history")
async def sve_company_history(symbol: str, metric: str = "pe", window: str = "MAX"):
    from sector_valuation_explorer import company_history

    return company_history(symbol, metric=metric or "pe", window=window or "MAX")


@router.get("/valuation/explorer/health")
async def sve_health():
    from sector_valuation_explorer import health as sve_health_fn

    return sve_health_fn()


# ---------------------------------------------------------------------------
# Valuation Attribution & Research Intelligence Engine (VARIE) v1.0
# Explains why valuation is where it is — warehouse / UVE / HVIE / MI only.
# ---------------------------------------------------------------------------


@router.get("/valuation/attribution/health")
async def varie_health():
    from valuation_attribution_engine import health as varie_health_fn

    return varie_health_fn()


@router.get("/valuation/attribution/company/{symbol}")
async def varie_company(symbol: str, window: str = "10y", universe_limit: int = 5000):
    from valuation_attribution_engine import company as varie_company_fn

    return varie_company_fn(
        symbol,
        window=window or "10y",
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
    )


@router.get("/valuation/attribution/sector/{sector}")
async def varie_sector(sector: str, universe_limit: int = 5000):
    from valuation_attribution_engine import sector as varie_sector_fn

    return varie_sector_fn(sector, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/attribution/industry/{industry}")
async def varie_industry(industry: str, universe_limit: int = 5000):
    from valuation_attribution_engine import industry as varie_industry_fn

    return varie_industry_fn(industry, universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/attribution/market")
async def varie_market(universe_limit: int = 5000):
    from valuation_attribution_engine import market as varie_market_fn

    return varie_market_fn(universe_limit=min(max(int(universe_limit or 5000), 100), 20000))


@router.get("/valuation/attribution/peer/{symbol}")
async def varie_peer(symbol: str, peer: str = "", universe_limit: int = 5000):
    from valuation_attribution_engine import peer as varie_peer_fn

    return varie_peer_fn(
        symbol,
        peer_symbol=peer or None,
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
    )


@router.get("/valuation/attribution/history/{symbol}")
async def varie_history(symbol: str, metric: str = "pe", window: str = "max"):
    from valuation_attribution_engine import history as varie_history_fn

    return varie_history_fn(symbol, metric=metric or "pe", window=window or "max")


@router.get("/valuation/attribution/timeline/{symbol}")
async def varie_timeline(symbol: str, metric: str = "pe", window: str = "max"):
    from valuation_attribution_engine import timeline as varie_timeline_fn

    return varie_timeline_fn(symbol, metric=metric or "pe", window=window or "max")


@router.get("/valuation/attribution/opportunities")
async def varie_opportunities(top: int = 10, universe_limit: int = 5000):
    from valuation_attribution_engine import opportunities as varie_opps_fn

    return varie_opps_fn(
        top=min(max(int(top or 10), 1), 50),
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
    )


@router.get("/valuation/attribution/leaders")
async def varie_leaders(top: int = 10, universe_limit: int = 5000):
    from valuation_attribution_engine import leaders as varie_leaders_fn

    return varie_leaders_fn(
        top=min(max(int(top or 10), 1), 50),
        universe_limit=min(max(int(universe_limit or 5000), 100), 20000),
    )


# ---------------------------------------------------------------------------
# Historical Valuation Intelligence Engine (HVIE) — Phase 8.3
# Reconstructs multiples from prices + statements; gated by VPAE.
# ---------------------------------------------------------------------------


@router.get("/historical-valuation/health")
async def historical_valuation_health():
    from historical_valuation_intelligence import health as hvie_health

    return hvie_health()


# Phase 8.3B — short HVIE intelligence aliases (warehouse-reconstructed only)
@router.get("/hvie/company/{symbol}")
async def hvie_alias_company(symbol: str, metric: str = "", window: str = "10y"):
    from historical_valuation_intelligence import company as hvie_company

    return hvie_company(symbol, metric=metric or None, window=window or "10y")


@router.get("/hvie/history/{symbol}")
async def hvie_alias_history(
    symbol: str, metric: str = "", window: str = "max", limit: int = 5000,
):
    from historical_valuation_intelligence import history as hvie_history

    return hvie_history(
        symbol, metric=metric or None, window=window or "max",
        limit=min(max(int(limit or 5000), 1), 20000),
    )


@router.get("/hvie/statistics/{symbol}")
async def hvie_alias_statistics(symbol: str, metric: str = "pe", window: str = ""):
    from historical_valuation_intelligence import statistics as hvie_statistics

    return hvie_statistics(symbol, metric=metric or "pe", window=window or None)


@router.get("/hvie/percentiles/{symbol}")
async def hvie_alias_percentiles(symbol: str, metric: str = "pe"):
    from historical_valuation_intelligence import percentiles as hvie_percentiles

    return hvie_percentiles(symbol, metric=metric or "pe")


@router.get("/hvie/bands/{symbol}")
async def hvie_alias_bands(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import bands as hvie_bands

    return hvie_bands(symbol, metric=metric or "pe", window=window or "max")


@router.get("/hvie/regimes/{symbol}")
async def hvie_alias_regimes(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import regimes as hvie_regimes

    return hvie_regimes(symbol, metric=metric or "pe", window=window or "max")


@router.get("/hvie/rerating/{symbol}")
async def hvie_alias_rerating(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import rerating as hvie_rerating

    return hvie_rerating(symbol, metric=metric or "pe", window=window or "max")


@router.get("/hvie/coverage/{symbol}")
async def hvie_alias_coverage(symbol: str, metric: str = ""):
    from historical_valuation_intelligence import coverage as hvie_coverage

    return hvie_coverage(symbol, metric=metric or None)


@router.get("/historical-valuation/company/{symbol}")
async def historical_valuation_company(symbol: str, metric: str = "", window: str = "10y"):
    from historical_valuation_intelligence import company as hvie_company

    return hvie_company(symbol, metric=metric or None, window=window or "10y")


@router.get("/historical-valuation/history/{symbol}")
async def historical_valuation_history(
    symbol: str, metric: str = "", window: str = "max", limit: int = 5000,
):
    from historical_valuation_intelligence import history as hvie_history

    return hvie_history(
        symbol, metric=metric or None, window=window or "max",
        limit=min(max(int(limit or 5000), 1), 20000),
    )


@router.get("/historical-valuation/statistics/{symbol}")
async def historical_valuation_statistics(symbol: str, metric: str = "pe", window: str = ""):
    from historical_valuation_intelligence import statistics as hvie_statistics

    return hvie_statistics(symbol, metric=metric or "pe", window=window or None)


@router.get("/historical-valuation/bands/{symbol}")
async def historical_valuation_bands(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import bands as hvie_bands

    return hvie_bands(symbol, metric=metric or "pe", window=window or "max")


@router.get("/historical-valuation/percentiles/{symbol}")
async def historical_valuation_percentiles(symbol: str, metric: str = "pe"):
    from historical_valuation_intelligence import percentiles as hvie_percentiles

    return hvie_percentiles(symbol, metric=metric or "pe")


@router.get("/historical-valuation/regimes/{symbol}")
async def historical_valuation_regimes(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import regimes as hvie_regimes

    return hvie_regimes(symbol, metric=metric or "pe", window=window or "max")


@router.get("/historical-valuation/rerating/{symbol}")
async def historical_valuation_rerating(symbol: str, metric: str = "pe", window: str = "max"):
    from historical_valuation_intelligence import rerating as hvie_rerating

    return hvie_rerating(symbol, metric=metric or "pe", window=window or "max")


@router.get("/historical-valuation/coverage/{symbol}")
async def historical_valuation_coverage(symbol: str, metric: str = ""):
    from historical_valuation_intelligence import coverage as hvie_coverage

    return hvie_coverage(symbol, metric=metric or None)


@router.post("/historical-valuation/reconstruct/{symbol}")
async def historical_valuation_reconstruct(
    symbol: str,
    payload: dict[str, Any] = Body(default_factory=dict),
):
    from historical_valuation_intelligence import reconstruct as hvie_reconstruct

    body = payload or {}
    return hvie_reconstruct(
        symbol,
        cadence=str(body.get("cadence") or "daily"),
        start=body.get("start"),
        end=body.get("end"),
        incremental=bool(body.get("incremental")),
    )


@router.get("/historical-valuation/coverage-dashboard")
async def historical_valuation_coverage_dashboard(limit: int = 200):
    from historical_valuation_intelligence import coverage_dashboard

    return coverage_dashboard(limit=min(max(int(limit or 200), 1), 2000))


@router.get("/historical-valuation/runtime/status")
async def historical_valuation_runtime_status():
    from historical_valuation_intelligence import runtime_status

    return runtime_status()


@router.post("/historical-valuation/runtime/run")
async def historical_valuation_runtime_run(payload: dict[str, Any] = Body(default_factory=dict)):
    from historical_valuation_intelligence import runtime_run

    body = payload or {}
    return runtime_run(
        str(body.get("mode") or "auto"),
        batch=body.get("batch"),
        symbol=body.get("symbol"),
        release_date=body.get("release_date"),
    )


@router.post("/historical-valuation/runtime/start")
async def historical_valuation_runtime_start():
    from historical_valuation_intelligence import runtime_start

    return runtime_start()


@router.post("/historical-valuation/runtime/stop")
async def historical_valuation_runtime_stop():
    from historical_valuation_intelligence import runtime_stop

    return runtime_stop()


# --------------------------------------------------------------------------
# HVIE Universe Completion Programme (Phase 8.3A)
# --------------------------------------------------------------------------

@router.get("/hvie/runtime/status")
async def hvie_universe_runtime_status():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.status()


@router.get("/hvie/runtime/board")
async def hvie_universe_runtime_board():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.board()


@router.get("/hvie/runtime/coverage")
async def hvie_universe_runtime_coverage():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.coverage()


@router.get("/hvie/runtime/pipeline")
async def hvie_universe_runtime_pipeline():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.pipeline_view()


@router.get("/hvie/runtime/company/{symbol}")
async def hvie_universe_runtime_company(symbol: str):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.company(symbol)


@router.get("/hvie/runtime/sector")
async def hvie_universe_runtime_sector():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.sector_view()


@router.get("/hvie/runtime/industry")
async def hvie_universe_runtime_industry():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.industry_view()


@router.get("/hvie/runtime/market")
async def hvie_universe_runtime_market():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.market_view()


@router.get("/hvie/runtime/failures")
async def hvie_universe_runtime_failures(limit: int = 100):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.failures(limit=min(max(int(limit or 100), 1), 500))


@router.get("/hvie/runtime/retry")
async def hvie_universe_runtime_retry_queue(limit: int = 100):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.retry_queue(limit=min(max(int(limit or 100), 1), 500))


@router.post("/hvie/runtime/start")
async def hvie_universe_runtime_start():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.start()


@router.post("/hvie/runtime/stop")
async def hvie_universe_runtime_stop():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.stop()


@router.post("/hvie/runtime/resume")
async def hvie_universe_runtime_resume():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.resume()


@router.post("/hvie/runtime/run")
async def hvie_universe_runtime_run(payload: dict[str, Any] = Body(default_factory=dict)):
    from historical_valuation_intelligence.universe_programme import production as univ

    body = payload or {}
    return univ.run_batch(batch=int(body.get("batch") or 15))


@router.post("/hvie/runtime/retry/{symbol}")
async def hvie_universe_runtime_retry_symbol(symbol: str):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.retry_symbol(symbol)


@router.post("/hvie/runtime/reconstruct/{symbol}")
async def hvie_universe_runtime_reconstruct(symbol: str):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.reconstruct_symbol(symbol)


@router.post("/hvie/runtime/aggregates")
async def hvie_universe_runtime_aggregates(payload: dict[str, Any] = Body(default_factory=dict)):
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.persist_aggregates(metric=str((payload or {}).get("metric") or "pe"))


@router.get("/hvie/runtime/health")
async def hvie_universe_runtime_health():
    from historical_valuation_intelligence.universe_programme import production as univ

    return univ.health()


# --------------------------------------------------------------------------
# Research Intelligence Engine (Phase 8.4)
# --------------------------------------------------------------------------

@router.get("/research/health")
async def rie_health():
    from research_intelligence_engine import health

    return health()


@router.get("/research/dashboard")
async def rie_dashboard():
    from research_intelligence_engine import dashboard

    return dashboard()


@router.get("/research/coverage")
async def rie_coverage(limit: int = 200):
    from research_intelligence_engine import coverage

    return coverage(limit=min(max(int(limit or 200), 1), 2000))


@router.get("/research/company/{symbol}")
async def rie_company(symbol: str):
    from research_intelligence_engine import company

    return company(symbol)


@router.get("/research/business/{symbol}")
async def rie_business(symbol: str):
    from research_intelligence_engine import business

    return business(symbol)


@router.get("/research/financial-quality/{symbol}")
async def rie_financial_quality(symbol: str):
    from research_intelligence_engine import financial_quality

    return financial_quality(symbol)


@router.get("/research/growth/{symbol}")
async def rie_growth(symbol: str):
    from research_intelligence_engine import growth

    return growth(symbol)


@router.get("/research/profitability/{symbol}")
async def rie_profitability(symbol: str):
    from research_intelligence_engine import profitability

    return profitability(symbol)


@router.get("/research/capital-allocation/{symbol}")
async def rie_capital_allocation(symbol: str):
    from research_intelligence_engine import capital_allocation

    return capital_allocation(symbol)


@router.get("/research/valuation/{symbol}")
async def rie_valuation(symbol: str):
    from research_intelligence_engine import valuation

    return valuation(symbol)


@router.get("/research/ownership/{symbol}")
async def rie_ownership(symbol: str):
    from research_intelligence_engine import ownership

    return ownership(symbol)


@router.get("/research/risk/{symbol}")
async def rie_risk(symbol: str):
    from research_intelligence_engine import risk

    return risk(symbol)


@router.get("/research/catalysts/{symbol}")
async def rie_catalysts(symbol: str):
    from research_intelligence_engine import catalysts

    return catalysts(symbol)


@router.get("/research/monitoring/{symbol}")
async def rie_monitoring(symbol: str):
    from research_intelligence_engine import monitoring

    return monitoring(symbol)


@router.get("/research/timeline/{symbol}")
async def rie_timeline(symbol: str):
    from research_intelligence_engine import timeline

    return timeline(symbol)


@router.get("/research/confidence/{symbol}")
async def rie_confidence(symbol: str):
    from research_intelligence_engine import confidence

    return confidence(symbol)


# --------------------------------------------------------------------------
# Forecast Intelligence Engine (Phase 8.5)
# Canonical prefix /v1/fie/* — avoids collision with legacy /v1/forecast/*
# --------------------------------------------------------------------------

@router.get("/fie/health")
async def fie_health():
    from forecast_intelligence_engine import health

    return health()


@router.get("/fie/dashboard")
async def fie_dashboard():
    from forecast_intelligence_engine import dashboard

    return dashboard()


@router.get("/fie/coverage")
async def fie_coverage(limit: int = 200):
    from forecast_intelligence_engine import coverage

    return coverage(limit=min(max(int(limit or 200), 1), 2000))


@router.get("/fie/company/{symbol}")
async def fie_company(symbol: str):
    from forecast_intelligence_engine import company

    return company(symbol)


@router.get("/fie/business/{symbol}")
async def fie_business(symbol: str):
    from forecast_intelligence_engine import business

    return business(symbol)


@router.get("/fie/growth/{symbol}")
async def fie_growth(symbol: str):
    from forecast_intelligence_engine import growth

    return growth(symbol)


@router.get("/fie/profitability/{symbol}")
async def fie_profitability(symbol: str):
    from forecast_intelligence_engine import profitability

    return profitability(symbol)


@router.get("/fie/balance-sheet/{symbol}")
async def fie_balance_sheet(symbol: str):
    from forecast_intelligence_engine import balance_sheet

    return balance_sheet(symbol)


@router.get("/fie/valuation/{symbol}")
async def fie_valuation(symbol: str):
    from forecast_intelligence_engine import valuation

    return valuation(symbol)


@router.get("/fie/scenarios/{symbol}")
async def fie_scenarios(symbol: str):
    from forecast_intelligence_engine import scenarios

    return scenarios(symbol)


@router.get("/fie/sensitivity/{symbol}")
async def fie_sensitivity(symbol: str):
    from forecast_intelligence_engine import sensitivity

    return sensitivity(symbol)


@router.get("/fie/risks/{symbol}")
async def fie_risks(symbol: str):
    from forecast_intelligence_engine import risks

    return risks(symbol)


@router.get("/fie/catalysts/{symbol}")
async def fie_catalysts(symbol: str):
    from forecast_intelligence_engine import catalysts

    return catalysts(symbol)


@router.get("/fie/confidence/{symbol}")
async def fie_confidence(symbol: str):
    from forecast_intelligence_engine import confidence

    return confidence(symbol)


@router.get("/fie/history/{symbol}")
async def fie_history(symbol: str):
    from forecast_intelligence_engine import history

    return history(symbol)


@router.get("/fie/accuracy/{symbol}")
async def fie_accuracy(symbol: str):
    from forecast_intelligence_engine import accuracy

    return accuracy(symbol)


@router.get("/fie/calibration")
async def fie_calibration():
    from forecast_intelligence_engine import calibration_board
    return await run_in_threadpool(calibration_board)


@router.get("/fie/runtime/status")
async def fie_runtime_status():
    from forecast_intelligence_engine import runtime_status

    return runtime_status()


@router.get("/fie/runtime/board")
async def fie_runtime_board():
    from forecast_intelligence_engine import runtime_board

    return runtime_board()


@router.post("/fie/runtime/start")
async def fie_runtime_start():
    from forecast_intelligence_engine import runtime_start

    return runtime_start()


@router.post("/fie/runtime/stop")
async def fie_runtime_stop():
    from forecast_intelligence_engine import runtime_stop

    return runtime_stop()


@router.post("/fie/runtime/resume")
async def fie_runtime_resume():
    from forecast_intelligence_engine import runtime_resume

    return runtime_resume()


@router.post("/fie/runtime/run")
async def fie_runtime_run(payload: dict[str, Any] = Body(default_factory=dict)):
    from forecast_intelligence_engine import runtime_run

    return runtime_run(batch=int((payload or {}).get("batch") or 3))


# ===========================================================================
# Phase 9.0 — Macro Intelligence Engine (MIE)
# Canonical prefix /v1/mie/* — avoids collision with legacy /v1/macro/* sprints
# ===========================================================================


@router.get("/mie/health")
async def mie_health():
    from macro_intelligence_engine import health

    return health()


@router.get("/mie/data-readiness")
async def mie_data_readiness(country: str = "India"):
    """Read-only public macro Core 50 coverage. Never collects data on request."""
    from macro_intelligence_engine.public_data import readiness

    return readiness(country=country)


@router.get("/mie/public-observations/latest")
async def mie_public_observations_latest(country: str = "India"):
    """Latest persisted public observations with source and PIT lineage."""
    from macro_intelligence_engine.public_data import latest_observations

    return latest_observations(country=country)


@router.get("/mie/public-observations/supplemental")
async def mie_public_observations_supplemental():
    """Vendor/reference macro observations excluded from governed Core 50 coverage."""
    from macro_intelligence_engine.public_data import supplemental_observations

    return supplemental_observations()


@router.get("/mie/g20/matrix")
async def mie_g20_matrix():
    from macro_intelligence_engine.public_data import g20_matrix

    return g20_matrix()


@router.get("/mie/g20/source-plan")
async def mie_g20_source_plan():
    from macro_intelligence_engine.public_data import g20_source_plan

    return g20_source_plan()


@router.get("/mie/licensed-capiq/status")
async def mie_licensed_capiq_status():
    """Aggregate private-import receipt. Never returns licensed observations."""
    from macro_intelligence_engine.licensed_capiq import import_status

    return import_status()


@router.get("/mie/dashboard")
async def mie_dashboard(country: str = "India"):
    try:
        from macro_intelligence_engine import dashboard

        return dashboard(country)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:320], "engine": "macro_intelligence_engine"}


@router.get("/mie/pack")
async def mie_pack(country: str = "India", symbol: str | None = None):
    try:
        from macro_intelligence_engine import pack

        return pack(country, symbol=symbol)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:320], "engine": "macro_intelligence_engine"}


@router.get("/mie/snapshot")
async def mie_snapshot(country: str = Query("Global")):
    """Read the latest durable macro snapshot without running an intelligence build."""
    from macro_intelligence_engine.production import snapshot as macro_snapshot

    return macro_snapshot(country=country)



@router.post("/mie/snapshot")
async def publish_mie_snapshot(
    payload: dict,
    x_agi_snapshot_token: str | None = Header(default=None),
):
    """Accept only an authenticated completed worker result; never calculate on web."""
    expected = (os.getenv("MIE_SNAPSHOT_PUBLISH_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="snapshot_publish_token_not_configured")
    if x_agi_snapshot_token != expected:
        raise HTTPException(status_code=403, detail="snapshot_publish_unauthorized")
    from macro_intelligence_engine.snapshot import save as save_snapshot

    country = str(payload.get("country") or "India")
    result = save_snapshot(payload.get("pack"), country=country)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail="snapshot_not_publishable")
    return {"ok": True, "country": country, "published_at": result.get("published_at")}


@router.get("/mie/regime")
async def mie_regime(country: str = "India"):
    from macro_intelligence_engine import regime

    return regime(country)


@router.get("/mie/economy")
async def mie_economy(country: str = "India"):
    from macro_intelligence_engine import economy

    return economy(country)


@router.get("/mie/inflation")
async def mie_inflation(country: str = "India"):
    from macro_intelligence_engine import inflation

    return inflation(country)


@router.get("/mie/rates")
async def mie_rates(country: str = "India"):
    from macro_intelligence_engine import rates

    return rates(country)


@router.get("/mie/liquidity")
async def mie_liquidity(country: str = "India"):
    from macro_intelligence_engine import liquidity

    return liquidity(country)


@router.get("/mie/currency")
async def mie_currency(country: str = "India"):
    from macro_intelligence_engine import currency

    return currency(country)


@router.get("/mie/commodities")
async def mie_commodities(country: str = "India"):
    from macro_intelligence_engine import commodities

    return commodities(country)


@router.get("/mie/bonds")
async def mie_bonds(country: str = "India"):
    from macro_intelligence_engine import bonds

    return bonds(country)


@router.get("/mie/fiscal")
async def mie_fiscal(country: str = "India"):
    from macro_intelligence_engine import fiscal

    return fiscal(country)


@router.get("/mie/external")
async def mie_external(country: str = "India"):
    from macro_intelligence_engine import external

    return external(country)


@router.get("/mie/sector-impact")
async def mie_sector_impact(country: str = "India"):
    from macro_intelligence_engine import sector_impact

    return sector_impact(country)


@router.get("/mie/industry-impact")
async def mie_industry_impact(country: str = "India"):
    from macro_intelligence_engine import industry_impact

    return industry_impact(country)


@router.get("/mie/company-impact/{symbol}")
async def mie_company_impact(symbol: str, country: str = "India"):
    from macro_intelligence_engine import company_impact

    return company_impact(symbol, country=country)


@router.get("/mie/forecast")
async def mie_forecast(country: str = "India"):
    from macro_intelligence_engine import forecast

    return forecast(country)


@router.get("/mie/scenarios")
async def mie_scenarios(country: str = "India"):
    from macro_intelligence_engine import scenarios

    return scenarios(country)


@router.get("/mie/relationships")
async def mie_relationships(country: str = "India"):
    from macro_intelligence_engine import relationships

    return relationships(country)


@router.get("/mie/risks")
async def mie_risks(country: str = "India"):
    from macro_intelligence_engine import risks

    return risks(country)


@router.get("/mie/runtime/status")
async def mie_runtime_status():
    from macro_intelligence_engine import runtime_status

    return runtime_status()


@router.get("/mie/runtime/board")
async def mie_runtime_board():
    from macro_intelligence_engine import runtime_board

    return runtime_board()


@router.post("/mie/runtime/start")
async def mie_runtime_start():
    from macro_intelligence_engine import runtime_start

    return runtime_start()


@router.post("/mie/runtime/stop")
async def mie_runtime_stop():
    from macro_intelligence_engine import runtime_stop

    return runtime_stop()


@router.post("/mie/runtime/resume")
async def mie_runtime_resume():
    from macro_intelligence_engine import runtime_resume

    return runtime_resume()


@router.post("/mie/runtime/run")
async def mie_runtime_run(payload: dict[str, Any] = Body(default_factory=dict)):
    from macro_intelligence_engine import runtime_run

    body = payload or {}
    return await run_in_threadpool(
        runtime_run,
        mode=str(body.get("mode") or "daily"),
        batch=int(body.get("batch") or 1),
    )


# --------------------------------------------------------------------------
# Phase 9.1 — Intelligence Fusion & Answer Composer (IFAC)
# --------------------------------------------------------------------------


@router.get("/ifac/health")
async def ifac_health():
    from intelligence_fusion_answer_composer import health

    return health()


@router.post("/ifac/compose")
async def ifac_compose(payload: dict[str, Any] = Body(default_factory=dict)):
    from intelligence_fusion_answer_composer.production import compose_api

    return compose_api(payload or {})


@router.get("/ifac/templates")
async def ifac_templates():
    from intelligence_fusion_answer_composer import templates_catalog

    return templates_catalog()


@router.get("/ifac/routing")
async def ifac_routing():
    from intelligence_fusion_answer_composer import routing_table

    return routing_table()


@router.get("/ifac/confidence")
async def ifac_confidence():
    from intelligence_fusion_answer_composer import confidence_board

    return confidence_board()


@router.get("/ifac/debug")
async def ifac_debug(limit: int = 20):
    from intelligence_fusion_answer_composer import debug_last

    return debug_last(limit=limit)


@router.get("/ifac/provenance")
async def ifac_provenance():
    from intelligence_fusion_answer_composer import provenance_sample

    return provenance_sample()


@router.get("/ifac/dashboard")
async def ifac_dashboard():
    from intelligence_fusion_answer_composer.production import dashboard

    return dashboard()


@router.get("/aqe/health")
async def aqe_health():
    """Phase 9.2 — Ask Product Quality & Institutional Answer Excellence."""
    from ask_product_quality.production import health

    return health()


@router.get("/aqe/dashboard")
async def aqe_dashboard():
    from ask_product_quality.production import dashboard

    return dashboard()


@router.post("/aqe/inspect")
async def aqe_inspect(payload: dict[str, Any] = Body(default_factory=dict)):
    from ask_product_quality.routing import inspect_routing

    body = payload or {}
    return inspect_routing(str(body.get("question") or ""), ticker=body.get("ticker"))


@router.post("/aqe/quality-gate")
async def aqe_quality_gate(payload: dict[str, Any] = Body(default_factory=dict)):
    from ask_product_quality.production import quality_gate

    body = payload or {}
    return quality_gate(body.get("answer") or body, question=str(body.get("question") or ""))


@router.get("/valuation-engine/health")
async def valuation_engine_health():
    """The one valuation contract: what it computes and what it reads."""
    from valuation_engine import health

    return health()


@router.get("/valuation-engine/company/{symbol}")
async def valuation_engine_company(symbol: str):
    """One company's valuation, sector context, coverage and provenance."""
    from valuation_engine import get_company_valuation

    return get_company_valuation(symbol)


@router.post("/valuation-engine/explain-change")
async def valuation_engine_explain_change(payload: dict[str, Any] = Body(default_factory=dict)):
    """Why a company's multiples moved between two observations."""
    from valuation_engine import explain_valuation_change

    body = payload or {}
    return explain_valuation_change(
        str(body.get("symbol") or ""),
        body.get("before") or {},
        body.get("after") or {},
    )


@router.get("/valuation-engine/terminal/health")
async def valuation_engine_terminal_health():
    """Institutional Valuation Terminal — warehouse-backed, JSON loader retired."""
    from valuation_engine.terminal import health as terminal_health

    return terminal_health()


@router.get("/valuation-engine/terminal/search")
async def valuation_engine_terminal_search(q: str = "", limit: int = 12):
    """Company autocomplete over warehouse company_master."""
    from valuation_engine.terminal import search as terminal_search

    return terminal_search(q, limit=limit)


@router.get("/valuation-engine/terminal/company/{symbol}")
async def valuation_engine_terminal_company(
    symbol: str,
    window: str = "5Y",
    peer_limit: int = 12,
    refresh: bool = False,
):
    """Serve the stored company pack. Live warehouse compute stays on POST /snapshot."""
    from valuation_engine.snapshot_store import serve_company_pack

    return await run_in_threadpool(
        serve_company_pack,
        symbol,
        window=window,
        peer_limit=peer_limit,
        refresh=refresh,
    )


@router.post("/valuation-engine/terminal/company/{symbol}/snapshot")
async def valuation_engine_terminal_company_snapshot(
    symbol: str,
    window: str = "5Y",
    peer_limit: int = 12,
):
    """Compute one company pack and persist it to Supabase for Node reads."""
    from valuation_engine.snapshot_store import compute_and_persist

    return await run_in_threadpool(
        compute_and_persist,
        symbol,
        window=window,
        peer_limit=max(1, min(int(peer_limit or 12), 40)),
    )


@router.get("/valuation-engine/terminal/company/{symbol}/snapshot/latest")
async def valuation_engine_terminal_company_snapshot_latest(symbol: str, window: str = "5Y"):
    """Return the latest stored company pack metadata (engine-side debug)."""
    from valuation_engine.snapshot_store import latest_pack_row

    row = latest_pack_row(symbol, window=window)
    if not row:
        return {"ok": False, "error": "no_snapshot", "symbol": str(symbol or "").upper()}
    return {
        "ok": True,
        "pack_id": row.get("pack_id"),
        "symbol": row.get("symbol"),
        "window": row.get("window") or row.get("pack_window"),
        "pack_window": row.get("pack_window") or row.get("window"),
        "generated_at": row.get("generated_at"),
        "source_as_of": row.get("source_as_of"),
        "status": row.get("status"),
        "freshness": row.get("freshness"),
        "schema_version": row.get("schema_version"),
        "calculation_version": row.get("calculation_version"),
        "data_quality": row.get("data_quality"),
        "health_score": row.get("health_score"),
        "payload": row.get("payload"),
    }


@router.get("/valuation-engine/terminal/series/{symbol}/{metric}")
async def valuation_engine_terminal_series(symbol: str, metric: str, window: str = "5Y"):
    """Coverage-aware chart series for one metric."""
    from valuation_engine.terminal import chart_series

    return chart_series(symbol, metric, window=window)


@router.get("/valuation-engine/terminal/explain/{metric}")
async def valuation_engine_terminal_explain(metric: str):
    """Metric pedagogy (sector lens)."""
    from valuation_engine.terminal import explain_metric

    return explain_metric(metric)


# ---------------------------------------------------------------------------
# Market & Sector Intelligence Terminal v1.0
# Warehouse → Unified Valuation Engine → Market Intelligence Engine
# ---------------------------------------------------------------------------


@router.get("/market-intelligence/health")
async def market_intelligence_health():
    try:
        from market_intelligence_engine import health

        return health()
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:320], "engine": "market_intelligence_engine"}


@router.get("/market-intelligence/dashboard")
async def market_intelligence_dashboard(universe_limit: int = 5000):
    try:
        from market_intelligence_engine import dashboard

        return dashboard(universe_limit=universe_limit)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:320], "engine": "market_intelligence_engine"}


@router.get("/market-intelligence/sector/{sector}")
async def market_intelligence_sector(sector: str, universe_limit: int = 5000):
    try:
        from market_intelligence_engine import sector_detail

        return sector_detail(sector, universe_limit=universe_limit)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)[:320],
            "sector": sector,
            "engine": "market_intelligence_engine",
        }


@router.post("/market-intelligence/flows/refresh")
async def market_intelligence_flows_refresh(payload: dict[str, Any] = Body(default_factory=dict)):
    """Pull FII/DII from Upstox and write it. The route the engine already
    tells people to call.

    It did not exist: the flows service answers "No FII/DII rows in warehouse
    yet. Run POST /v1/market-intelligence/flows/refresh", and that path
    returned 404. The only way in was the push-based ingest, which needs
    somebody to supply the payload.

    The fetch lives here rather than in the web service because that service's
    Upstox token answers "Invalid token used to access API", which is why the
    table stopped on 20 August.
    """
    from market_intelligence_engine.fetch_flows import refresh

    body = payload or {}
    return await run_in_threadpool(
        refresh,
        interval=str(body.get("interval") or "1D"),
        since=body.get("since"),
        actor=str(body.get("actor") or "flow_refresh"),
    )


@router.post("/market-intelligence/flows/ingest")
async def market_intelligence_flows_ingest(payload: dict[str, Any] = Body(default_factory=dict)):
    """Persist FII/DII rows into warehouse (called by BFF after Upstox fetch)."""
    from market_intelligence_engine.ingest_flows import ingest_flows, normalise_upstox_flow

    body = payload or {}
    rows = body.get("rows")
    if not rows:
        rows = normalise_upstox_flow(body)
    return ingest_flows(rows, actor=str(body.get("actor") or "market_intelligence_engine"))


@router.get("/valuation-ratios/health")
async def valuation_ratios_health():
    from valuation_ratios import health

    return health()


@router.get("/valuation-ratios/coverage")
async def valuation_ratios_coverage():
    from valuation_ratios import ratios_coverage

    return ratios_coverage()


@router.get("/valuation-ratios/company/{symbol}")
async def valuation_ratios_company(symbol: str):
    """The six ratios as they should be shown, each with its own freshness.

    A failed refresh serves the last valid snapshot rather than nulls, and says
    it is stale. A ratio that does not apply to the sector is marked so rather
    than counted as a gap - otherwise every bank reads as degraded for want of
    an EV/EBITDA it can never have.
    """
    from valuation_ratios.canonical import canonical_ratios

    return await run_in_threadpool(canonical_ratios, symbol)


@router.get("/valuation-ratios/company/{symbol}/raw")
async def valuation_ratios_company_raw(symbol: str):
    """The provider pack without the freshness layer, for debugging."""
    from valuation_ratios.ingest import latest_provider_ratios

    return latest_provider_ratios(symbol)


@router.post("/valuation-ratios/ingest")
async def valuation_ratios_ingest(payload: dict[str, Any] = Body(default_factory=dict)):
    """Persist Upstox key-ratios into warehouse (called by BFF after Upstox fetch)."""
    from valuation_ratios.ingest import ingest_key_ratios, normalise_upstox_key_ratios

    body = payload or {}
    rows = body.get("rows")
    if not rows:
        # Accept single company payload or batch under "companies".
        companies = body.get("companies")
        if isinstance(companies, list):
            rows = []
            for item in companies:
                rows.extend(normalise_upstox_key_ratios(item if isinstance(item, dict) else {}))
        else:
            rows = normalise_upstox_key_ratios(body)
    return ingest_key_ratios(
        rows,
        actor=str(body.get("actor") or "valuation_ratios"),
        sync_valuation=bool(body.get("sync_valuation", True)),
    )


@router.post("/fundamentals-refresh/detect")
async def fundamentals_refresh_detect(payload: dict[str, Any] = Body(default_factory=dict)):
    """Ask a set of companies whether they have reported since we last looked."""
    from fundamentals_refresh.detector import detect
    from valuation_ratios.sweep import ELIGIBLE_EQUITY, eligible

    body = payload or {}
    wanted = {str(s).upper() for s in (body.get("symbols") or [])}
    universe = [c for c in eligible() if c.get("eligibility") == ELIGIBLE_EQUITY]
    if wanted:
        universe = [c for c in universe if c["symbol"] in wanted]
    universe = universe[: int(body.get("max_companies") or 50)]
    return await run_in_threadpool(detect, universe,
                                   pause_seconds=body.get("pause_seconds"),
                                   force=bool(body.get("force")))


@router.post("/fundamentals-refresh/run")
async def fundamentals_refresh_run(payload: dict[str, Any] = Body(default_factory=dict)):
    """Drain part of the refresh queue. Bounded; a long request is a lost one."""
    from fundamentals_refresh.worker import run

    body = payload or {}
    return await run_in_threadpool(run, limit=int(body.get("limit") or 10),
                                   pause_seconds=body.get("pause_seconds"))


@router.get("/fundamentals-refresh/queue")
def fundamentals_refresh_queue():
    from fundamentals_refresh.queue import queue_state

    return queue_state()


@router.get("/diagnostics/memory-stages")
async def diagnostics_memory_stages(limit: int = 200):
    """What each heavy stage cost, as recorded when it ran.

    Reads only. It never triggers a build, a backfill or a repair - the whole
    point is to find the allocator without adding another allocation, and a
    diagnostic that runs the job it is measuring measures itself.

    Records come from a file on the shared disk rather than memory because the
    gather sidecar is a separate OS process from uvicorn, so anything it
    measured would otherwise be invisible here.
    """
    from observability.memory_stages import read_stages

    return await run_in_threadpool(read_stages, limit=int(limit))


@router.get("/fundamentals/reconciliation-inventory")
async def fundamentals_reconciliation_inventory(
    tab: str = "",
    symbols: str = "",
    max_groups: int = 20,
    simulate_provenance: bool = False,
):
    """What the fundamentals tabs hold, grouped by period identity. Read-only.

    Exists to be read before anything is retired. Four rows for one quarter is
    not by itself a reason to drop three of them: an untrusted source is
    sometimes the only holder of a metric, and `metrics_only_here` on each
    losing row is the number that decides whether retiring it loses data.
    """
    from institutional_warehouse.reconciliation_inventory import inventory, inventory_all

    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()] or None
    if tab:
        return await run_in_threadpool(inventory, tab, symbols=wanted,
                                       max_groups_shown=int(max_groups),
                                       simulate_unit_provenance=bool(simulate_provenance))
    return await run_in_threadpool(inventory_all, symbols=wanted,
                                   max_groups_shown=int(max_groups),
                                   simulate_unit_provenance=bool(simulate_provenance))


@router.get(
    "/fundamentals/reconciliation-compare",
    dependencies=[Depends(require_token)],
)
async def fundamentals_reconciliation_compare(
    tab: str = "financials_annual",
    symbols: str = Query(..., min_length=1),
    max_groups: int = Query(1, ge=0, le=5),
):
    """Before and after the provenance simulation over bounded paired reads.

    Writes nothing. Each company is read once and folded into both tallies, so
    the difference is the effect of the change and not of the clock: schedulers
    write these tabs every few minutes, and two separate inventory runs do not
    describe the same rows.
    """
    from institutional_warehouse.reconciliation_inventory import compare

    wanted = list(dict.fromkeys(
        s.strip().upper() for s in symbols.split(",") if s.strip()))
    if not wanted:
        raise HTTPException(status_code=400, detail="At least one symbol is required")
    if len(wanted) > 25:
        raise HTTPException(status_code=400, detail="At most 25 symbols per request")
    return await run_in_threadpool(compare, tab, symbols=wanted,
                                   max_groups_shown=int(max_groups))
@router.get("/fundamentals/value-plausibility",
            dependencies=[Depends(require_token)])
async def fundamentals_value_plausibility(
    symbols: str,
    tab: str = "financials_annual",
    sample: int = Query(default=25, ge=1, le=200),
):
    """Census of aggregate money stored on the wrong scale. Writes nothing.

    `symbols` is required and bounded. Without it this walked every company in a
    69,156-row tab, and clamping the response sample bounded the reply while
    leaving the database work unbounded - an authenticated caller could still
    scan the whole warehouse per request. The unrestricted census is run offline
    and reviewed as a sealed artifact instead (docs/census/).

    Plausibility is validation evidence, not proof of provenance: a row named
    here is one to examine, not one to retire.
    """
    from institutional_warehouse.value_plausibility import census

    wanted = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not wanted:
        raise HTTPException(status_code=400, detail="symbols is required")
    if len(wanted) > MAX_CENSUS_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"at most {MAX_CENSUS_SYMBOLS} symbols per request")
    return await run_in_threadpool(census, tab, symbols=wanted, sample_rows=int(sample))


@router.get("/fundamentals/unit-provenance-plan")
async def fundamentals_unit_provenance_plan(tab: str = "", sample: int = 10):
    """What the Capital IQ provenance backfill would change. Writes nothing.

    Metadata only: sys_unit_method, for rows already labelled inr_million by a
    source that documents INR million on every path it writes. No financial
    value is read or altered, and the response carries the rollback SQL.
    """
    from institutional_warehouse.unit_provenance import plan, plan_all

    if tab:
        return await run_in_threadpool(plan, tab, sample=int(sample))
    return await run_in_threadpool(plan_all, sample=int(sample))


@router.post("/valuation-ratios/sweep")
async def valuation_ratios_sweep(payload: dict[str, Any] = Body(default_factory=dict)):
    """Pull today's key ratios for the whole universe.

    Ingest was push-based, so the table recorded whichever companies something
    outside the engine happened to look at - twenty-five to eighty a day out of
    2,431. Upstox's key ratios carry no time dimension, so a day not collected
    is a day that cannot be recovered later.
    """
    from valuation_ratios.sweep import run

    body = payload or {}
    # Bounded by default. An unbounded sweep is a half-hour request, and the
    # first one was killed at twenty minutes by a deploy landing on top of it.
    # Progress is checkpointed per company, so calling this repeatedly walks the
    # universe without any single call being long enough to lose.
    return await run_in_threadpool(
        run,
        limit=int(body["limit"]) if body.get("limit") else None,
        batch_size=int(body.get("batch_size") or 40),
        actor=str(body.get("actor") or "ratio_sweep"),
        pause_seconds=float(body.get("pause_seconds", 0.6)),
        resume=bool(body.get("resume", True)),
        max_companies=int(body.get("max_companies") or 300),
    )


@router.get("/valuation-ratios/sweep/runs")
def valuation_ratios_sweep_runs(limit: int = 10):
    """What each sweep actually reached, rather than that it finished."""
    from institutional_warehouse.backfill.checkpoints import recent_jobs
    from valuation_ratios.sweep import KIND

    return {"ok": True, "runs": recent_jobs(kind=KIND, limit=limit)}


@router.get("/valuation-ratios/workbook", dependencies=[Depends(require_token)])
async def valuation_ratios_workbook(days: int = 120):
    """Admin-only Excel: one sheet per ratio, companies down, dates across.

    Token-guarded because it is the whole universe in one file - every company,
    every ratio, every day collected. That is an export, not a page, and it
    should not be reachable without the engine token.
    """
    from fastapi.responses import Response
    from valuation_ratios import workbook

    payload, summary = await run_in_threadpool(workbook.build_bytes, days=days)
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{workbook.filename(summary)}"',
            # Surfaced as headers so a caller can tell a thin workbook from a
            # complete one without opening it.
            "X-AGI-Companies": str(summary["companies"]),
            "X-AGI-Dates": str(summary["dates"]),
            "X-AGI-Latest-Date": str(summary["latest_date"] or ""),
            "X-AGI-Values": str(summary["values"]),
            "Cache-Control": "no-store",
        },
    )


@router.get("/valuation-ratios/workbook/summary", dependencies=[Depends(require_token)])
async def valuation_ratios_workbook_summary(days: int = 120):
    """What the workbook would contain, without building the file."""
    from valuation_ratios import workbook

    summary = await run_in_threadpool(workbook.summarise, days=days)
    return {"ok": True, **summary}


@router.post("/valuation-ratios/pivot-historical",
             dependencies=[Depends(require_token)])
async def valuation_ratios_pivot_historical(payload: dict[str, Any] = Body(default_factory=dict)):
    """Rebuild historical_valuation for one day from ratios already collected.

    Repair for days swept before the sweep learned to pivot. Re-sweeping
    cannot do it: checkpoints are per day, so a resumed sweep finds an empty
    queue and an unresumed one restarts at the top of the universe and
    rewrites the same first companies. This spends no provider budget.
    """
    from valuation_ratios.ingest import pivot_stored_ratios

    body = payload or {}
    return await run_in_threadpool(
        pivot_stored_ratios,
        date=body.get("date"),
        actor=str(body.get("actor") or "pivot_backfill"),
    )


@router.post("/valuation-ratios/isin-backfill")
async def valuation_ratios_isin_backfill(payload: dict[str, Any] = Body(default_factory=dict)):
    """Fill company_master.isin from Upstox NSE EQ instruments (blocks key-ratios otherwise)."""
    from valuation_ratios.isin_backfill import backfill_company_isins

    body = payload or {}
    return backfill_company_isins(
        actor=str(body.get("actor") or "isin_backfill"),
        dry_run=bool(body.get("dry_run", False)),
        prefer_csv=bool(body.get("prefer_csv", True)),
        limit=body.get("limit"),
    )


# ---- Phase 7.4E — Upstox Institutional Fundamentals Integration (UIFI) ----

@router.get("/upstox-fundamentals/health")
async def uifi_health():
    from upstox_fundamentals import health

    return health()


@router.get("/upstox-fundamentals/coverage")
async def uifi_coverage():
    from upstox_fundamentals import coverage

    return coverage()


@router.get("/upstox-fundamentals/failures")
async def uifi_failures():
    from upstox_fundamentals import failures

    return failures()


@router.post("/upstox-fundamentals/ingest")
async def uifi_ingest(payload: dict[str, Any] = Body(default_factory=dict)):
    """BFF posts fetched Upstox fundamentals here — never called by UI/engines directly."""
    from upstox_fundamentals import ingest_bundle

    body = payload or {}
    return ingest_bundle(body, actor=str(body.get("actor") or "uifi"))


@router.get("/company/profile/{symbol}")
async def company_profile_api(symbol: str):
    from upstox_fundamentals import company_profile

    return company_profile(symbol)


@router.get("/company/profile/history/{symbol}")
async def company_profile_history_api(symbol: str):
    from upstox_fundamentals import company_profile_history

    return company_profile_history(symbol)


@router.get("/company/statements/{symbol}")
async def company_statements_api(symbol: str):
    from upstox_fundamentals import company_statements

    return company_statements(symbol)


@router.get("/company/shareholding/{symbol}")
async def company_shareholding_api(symbol: str):
    from upstox_fundamentals import company_shareholding

    return company_shareholding(symbol)


@router.get("/company/competitors/{symbol}")
async def company_competitors_api(symbol: str):
    from upstox_fundamentals import company_competitors

    return company_competitors(symbol)


@router.get("/company/corporate-actions/{symbol}")
async def company_corporate_actions_api(symbol: str):
    from upstox_fundamentals import company_corporate_actions

    return company_corporate_actions(symbol)


@router.get("/warehouse/statement-identity")
def warehouse_statement_identity():
    """Statement rows still carrying no statement type."""
    from institutional_warehouse.production import statement_identity_coverage

    return statement_identity_coverage()


@router.post("/warehouse/migrate-statement-identity")
def warehouse_migrate_statement_identity(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Type and re-key legacy statement rows. Dry run unless told otherwise."""
    from institutional_warehouse.production import migrate_statement_identity

    body = payload or {}
    return migrate_statement_identity(actor=_warehouse_actor(body, x_agi_actor),
                                      dry_run=bool(body.get("dry_run", True)))


@router.get("/warehouse/unit-coverage")
def warehouse_unit_coverage():
    """Rows still carrying no unit stamp, per tab."""
    from institutional_warehouse.production import unit_coverage

    return unit_coverage()


@router.post("/warehouse/normalise-units")
def warehouse_normalise_units(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_agi_actor: str | None = Header(default=None),
):
    """Back-normalise legacy rows to INR million. Dry run unless told otherwise."""
    from institutional_warehouse.production import normalise_units

    body = payload or {}
    return normalise_units(actor=_warehouse_actor(body, x_agi_actor),
                           dry_run=bool(body.get("dry_run", True)))
