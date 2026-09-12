from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.cio_synthesizer import ChiefInvestmentOfficer
from app.agents.registry import get_agent
from app.core.logging import get_logger
from app.engines.citation import CitationEngine
from app.engines.confidence import ConfidenceEngine
from app.engines.debate import DebateEngine
from app.engines.evidence import EvidenceEngine
from app.memory.store import ResearchStore
from app.portfolio.pack import attach_portfolio_to_run, package_from_metadata
from app.investment_office.pack import (
    attach_office_to_run,
    build_investment_office_package,
)
from app.schemas.models import (
    DeskType,
    DirectorPlan,
    InvestmentOfficeRequest,
    ResearchRun,
    ResearchRunCreate,
    RunStatus,
)
from app.tools.agib_client import AgibClient

log = get_logger(__name__)

DESK_PLANS: dict[DeskType, list[str]] = {
    DeskType.SMOKE: ["smoke_analyst"],
    DeskType.CIO_MORNING: [
        "macro_economist",
        "news_analyst",
        "market_analyst",
        "risk_manager",
    ],
    DeskType.EQUITY: ["smoke_analyst"],  # Phase 3 expands
    DeskType.PORTFOLIO: [
        "portfolio_health",
        "portfolio_risk",
        "portfolio_recommendations",
        "portfolio_summary",
    ],
    DeskType.INVESTMENT_OFFICE: [
        "investment_brief",
        "investment_queue_calendar",
        "investment_knowledge",
        "investment_summary",
    ],
    DeskType.CUSTOM: ["smoke_analyst"],
}


class ResearchDirector:
    """Orchestrates agents only. Does not write the investment thesis."""

    def __init__(
        self,
        store: ResearchStore | None = None,
        kip: Any | None = None,
        rsp: Any | None = None,
    ):
        self.store = store or ResearchStore()
        self.kip = kip
        self.rsp = rsp
        self.evidence_engine = EvidenceEngine()
        self.confidence_engine = ConfidenceEngine()
        self.citation_engine = CitationEngine()
        self.debate_engine = DebateEngine()
        self.cio = ChiefInvestmentOfficer()
        self.agib = AgibClient()

    def plan(self, desk: DeskType, query: str | None = None) -> DirectorPlan:
        agent_ids = DESK_PLANS.get(desk, DESK_PLANS[DeskType.SMOKE])
        return DirectorPlan(
            desk=desk,
            agent_ids=agent_ids,
            rationale=f"Desk {desk.value} requires {', '.join(agent_ids)}",
            require_all=False,
        )

    async def execute(self, request: ResearchRunCreate) -> ResearchRun:
        run = ResearchRun(
            desk=request.desk,
            status=RunStatus.RUNNING,
            query=request.query,
            symbols=request.symbols,
            metadata=request.metadata,
        )
        run.director_plan = self.plan(request.desk, request.query)
        await self.store.save_run(run)
        log.info("director_start", extra={"run_id": run.run_id, "desk": run.desk.value})

        context: dict[str, Any] = {
            "run_id": run.run_id,
            "desk": run.desk,
            "query": run.query,
            "symbols": run.symbols,
            "metadata": run.metadata,
        }

        # Portfolio Office: build package before agent loop (packaging only)
        if run.desk == DeskType.PORTFOLIO:
            try:
                package = package_from_metadata(run.metadata)
                if package is None:
                    # Default model portfolio so desk is always exercisable
                    package = package_from_metadata(
                        {
                            "source": "model",
                            "model_id": "balanced_india",
                            "name": run.query or "Model Portfolio",
                        }
                    )
                if package is not None:
                    attach_portfolio_to_run(run, package)
                    context["portfolio_pack"] = package
                    if not run.symbols:
                        run.symbols = [h.symbol for h in package.portfolio.holdings]
            except Exception as exc:
                run.errors.append(f"portfolio_package: {exc}")
                log.exception("portfolio_package_failed", extra={"run_id": run.run_id})

        # Investment Office: operational layer over existing capabilities
        if run.desk == DeskType.INVESTMENT_OFFICE:
            try:
                similar_for_office: list[dict[str, Any]] = []
                try:
                    similar_for_office = await self.store.similar_runs("investment_office", limit=5)
                    similar_for_office += await self.store.similar_runs("cio_morning", limit=3)
                    similar_for_office += await self.store.similar_runs("portfolio", limit=3)
                except Exception:
                    similar_for_office = []

                macro = await self.agib.macro_briefing()
                market = await self.agib.market_briefing()
                pre = await self.agib.pre_market_briefing()

                meta = run.metadata or {}
                block = meta.get("investment_office") if isinstance(meta.get("investment_office"), dict) else {}
                req = InvestmentOfficeRequest(
                    user_id=block.get("user_id") or meta.get("user_id"),
                    watchlist=block.get("watchlist")
                    or meta.get("watchlist")
                    or run.symbols
                    or ["INFY", "RELIANCE", "HDFCBANK"],
                    symbols=block.get("symbols") or meta.get("symbols") or run.symbols or [],
                    sectors=block.get("sectors") or meta.get("sectors") or [],
                    portfolio=block.get("portfolio") or meta.get("portfolio"),
                    journal_seed=block.get("journal_seed") or meta.get("journal_seed") or [],
                    prior_runs=block.get("prior_runs") or meta.get("prior_runs") or [],
                    query=run.query or block.get("query") or "Investment Office daily package",
                )
                office = build_investment_office_package(
                    req,
                    macro=macro,
                    market=market,
                    pre_market=pre,
                    similar_runs=similar_for_office,
                )
                attach_office_to_run(run, office)
                context["investment_office_pack"] = office
                if not run.symbols:
                    run.symbols = [i.symbol for i in office.research_queue if i.symbol][:12]
            except Exception as exc:
                run.errors.append(f"investment_office_package: {exc}")
                log.exception("investment_office_package_failed", extra={"run_id": run.run_id})

        # Memory retrieval (similar past runs) — soft fail
        try:
            similar = await self.store.similar_runs(run.desk.value, limit=3)
            context["similar_runs"] = similar
        except Exception as exc:
            run.errors.append(f"memory_retrieve: {exc}")

        # KIP retrieves — soft fail; never redesigns research engines
        ticker = run.symbols[0] if run.symbols else None
        q = run.query or " ".join(run.symbols) or run.desk.value
        try:
            kip = getattr(self, "kip", None)
            if kip is not None and getattr(getattr(kip, "flags", None), "kip", False):
                context["kip_research_context"] = kip.research_context(q, ticker=ticker)
        except Exception as exc:
            run.errors.append(f"kip_retrieve: {exc}")

        # RSP reasons — LLM must write from ReasoningPackage, not raw retrieval
        try:
            rsp = getattr(self, "rsp", None)
            if rsp is not None and getattr(getattr(rsp, "flags", None), "rsp", False):
                context["rsp_reasoning_package"] = rsp.reason_for_writer(q, ticker=ticker)
                # Do not expose raw KIP document bodies to the writer path
                context.pop("kip_raw_documents", None)
        except Exception as exc:
            run.errors.append(f"rsp_reason: {exc}")

        outputs = []
        for agent_id in run.director_plan.agent_ids:
            try:
                agent = get_agent(agent_id)
                output = await agent.run(context)
                outputs.append(output)
            except Exception as exc:
                run.errors.append(f"{agent_id}: {exc}")
                log.exception("director_agent_error", extra={"run_id": run.run_id, "agent_id": agent_id})

        run.agent_outputs = outputs
        validation_errors = self.evidence_engine.validate_outputs(outputs)
        run.errors.extend(validation_errors)

        evidence = self.evidence_engine.collect(outputs)
        confidence = self.confidence_engine.combine(outputs, evidence)
        debate = self.debate_engine.debate(outputs, evidence)
        run.debate = debate

        # Continuous Gather→Learn: soft historical accuracy memory before CIO synthesis.
        # Does not change Ask API; never blocks the desk if CGL/ILO/FLE are unavailable.
        historical_learning: dict = {}
        try:
            from continuous_gather_learn.flags import director_learning_inject
            from continuous_gather_learn.production import director_learning

            if director_learning_inject():
                historical_learning = director_learning(query=str(run.query or ""), limit=8) or {}
                context["historical_learning"] = historical_learning
        except Exception as exc:
            run.errors.append(f"historical_learning: {exc}")
            historical_learning = {}

        try:
            report = await self.cio.synthesize(
                {
                    "desk": run.desk,
                    "agent_outputs": outputs,
                    "debate": debate,
                    "confidence": confidence,
                    "evidence": evidence,
                    "query": run.query,
                    "historical_learning": historical_learning,
                    "opinion_weights": (historical_learning or {}).get("opinion_weights") or [],
                }
            )
            citations = self.citation_engine.build_citation_map(outputs, evidence)
            report = self.citation_engine.attach(report, citations)
            run.report = report
            run.cio_thesis = report.executive_summary
            run.status = RunStatus.COMPLETED if not run.errors else RunStatus.PARTIAL
        except Exception as exc:
            run.errors.append(f"cio_synthesize: {exc}")
            run.status = RunStatus.FAILED if not outputs else RunStatus.PARTIAL
            log.exception("cio_failed", extra={"run_id": run.run_id})

        run.updated_at = datetime.now(timezone.utc)
        run.completed_at = run.updated_at
        await self.store.save_run(run)
        if run.report:
            await self.store.save_report_embedding(run)
            # Self-learning: published AGI research becomes institutional knowledge
            try:
                kip = getattr(self, "kip", None)
                if kip is not None:
                    kip.ingest_research_run(run)
            except Exception as exc:
                run.errors.append(f"kip_ingest: {exc}")
                await self.store.save_run(run)
        log.info("director_complete", extra={"run_id": run.run_id, "status": run.status.value})
        return run
