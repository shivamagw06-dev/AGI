"""AWS service — unified institutional workspace over existing platforms."""

from __future__ import annotations

from typing import Any

from app.aws.adapters import dump, engine_state, portfolio_weight, soft
from app.aws.flags import AwsFlags
from app.aws.models import (
    AWS_VERSION,
    AwsDashboard,
    CompanyWorkspace,
    CopilotContext,
    CreWorkspace,
    KnowledgeExplorer,
    MacroWorkspace,
    PortfolioWorkspace,
    ReplayWorkspace,
    ResearchWorkspace,
    SearchHit,
    SearchResponse,
    SectorWorkspace,
    ThemeWorkspace,
    WorkspaceMeta,
)
from app.core.config import get_settings


class AwsService:
    """Internal Bloomberg-style terminal. Aggregates only — no research engines."""

    def __init__(
        self,
        flags: AwsFlags | None = None,
        *,
        kip: Any | None = None,
        rsp: Any | None = None,
        rms: Any | None = None,
        cre: Any | None = None,
        validation: Any | None = None,
        e01: Any | None = None,
        e02: Any | None = None,
        e03: Any | None = None,
        e04: Any | None = None,
        e05: Any | None = None,
        e08: Any | None = None,
        e09: Any | None = None,
        e10: Any | None = None,
        e11: Any | None = None,
        e13: Any | None = None,
        e14: Any | None = None,
        l4: Any | None = None,
    ) -> None:
        self.flags = flags or AwsFlags.from_settings(get_settings())
        self.kip = kip
        self.rsp = rsp
        self.rms = rms
        self.cre = cre
        self.validation = validation
        self.e01 = e01
        self.e02 = e02
        self.e03 = e03
        self.e04 = e04
        self.e05 = e05
        self.e08 = e08
        self.e09 = e09
        self.e10 = e10
        self.e11 = e11
        self.e13 = e13
        self.e14 = e14
        self.l4 = l4

    def company(self, ticker: str, *, as_of: str | None = None) -> CompanyWorkspace:
        self._require()
        t = ticker.upper()
        sources = ["KIP", "L4", "E01", "E02", "E03", "E04", "E05", "E08", "E09", "E10", "E11", "E13", "E14", "Replay", "CRE"]

        house = dump(soft(self.kip.house_view, t)) if self.kip else None
        dossier = dump(soft(self.kip.company_dossier, t)) if self.kip else None
        timeline = dump(soft(self.kip.timeline, t)) if self.kip else None
        graph = dump(soft(self.kip.graph, t)) if self.kip else None
        preds = soft(self.kip.predictions, t, default=[]) if self.kip else []
        pred_hist = [dump(p) for p in (preds or []) if dump(p)]

        history = dump(soft(self.kip.research_history, t)) if self.kip else None
        agi_articles = (history or {}).get("agi_reports") or []
        broker_research = (history or {}).get("broker_reports") or []

        # News via KIP search
        news_hits = []
        if self.kip:
            sr = soft(self.kip.search, t, mode="hybrid", limit=5, ticker=t)
            if sr and getattr(sr, "hits", None):
                for h in sr.hits:
                    d = dump(h) or {}
                    if d.get("document_type") == "market_news" or "news" in str(d.get("document_type", "")):
                        news_hits.append(d)
                if not news_hits:
                    news_hits = [dump(h) for h in sr.hits[:3] if dump(h)]

        port = dump(soft(self.e10.get_portfolio, as_of)) if self.e10 else None
        weight = portfolio_weight(port, t)

        # Replay stats from validation latest run dashboard if available
        replay_stats = None
        if self.validation:
            runs = soft(self.validation.list_runs, 5, default=[]) or []
            if runs:
                rid = getattr(runs[0], "run_id", None) or (runs[0].get("run_id") if isinstance(runs[0], dict) else None)
                if rid:
                    replay_stats = soft(self.validation.get_dashboard, rid)

        return CompanyWorkspace(
            meta=WorkspaceMeta(workspace="company", sources=sources),
            ticker=t,
            house_view=house,
            l4_opinion=dump(soft(self.l4.get_opinion, t, as_of=as_of)) if self.l4 else None,
            macro=engine_state(self.e01, as_of=as_of),
            factors=engine_state(self.e02, symbol=t, as_of=as_of),
            technical=engine_state(self.e03, symbol=t, as_of=as_of),
            fundamental=(
                engine_state(self.e13, symbol=t, as_of=as_of)
                or (dump(soft(self.e13.get_fundamental, t, as_of=as_of)) if self.e13 else None)
            ),
            volatility=engine_state(self.e08, symbol=t, as_of=as_of),
            trend=engine_state(self.e09, symbol=t, as_of=as_of),
            relative_value=self._relative_value(t, as_of=as_of),
            events=(
                engine_state(self.e05, symbol=t, as_of=as_of)
                or (dump(soft(self.e05.get_event_state, t, as_of=as_of)) if self.e05 else None)
            ),
            sentiment=(
                engine_state(self.e11, symbol=t, as_of=as_of)
                or (dump(soft(self.e11.get_sentiment_state, t, as_of=as_of)) if self.e11 else None)
            ),
            risk=engine_state(self.e14, as_of=as_of),
            portfolio_weight=weight,
            portfolio=port,
            replay_statistics=replay_stats if isinstance(replay_stats, dict) else None,
            prediction_history=[p for p in pred_hist if p],
            research_timeline=timeline,
            latest_news=news_hits,
            broker_research=broker_research if isinstance(broker_research, list) else [],
            agi_articles=agi_articles if isinstance(agi_articles, list) else [],
            knowledge_graph=graph,
            dossier=dossier,
        )

    def theme(self, theme_id: str) -> ThemeWorkspace:
        self._require()
        theme = dump(soft(self.kip.get_theme, theme_id)) if self.kip else None
        graph = dump(soft(self.kip.graph, theme_id)) if self.kip else None
        hits = []
        if self.kip:
            sr = soft(self.kip.search, theme_id, mode="theme", theme=theme_id, limit=10)
            if sr:
                hits = [dump(h) for h in sr.hits if dump(h)]
        return ThemeWorkspace(
            meta=WorkspaceMeta(workspace="theme", sources=["KIP"]),
            theme_id=theme_id,
            theme=theme,
            related_companies=list((theme or {}).get("tickers") or []),
            documents=list((theme or {}).get("documents") or []),
            knowledge_graph=graph,
            search_hits=hits,
        )

    def sector(self, sector_id: str) -> SectorWorkspace:
        self._require()
        docs: list[dict[str, Any]] = []
        coverage: dict[str, int] = {}
        rms_rows: list[dict[str, Any]] = []
        if self.kip:
            sr = soft(self.kip.search, sector_id, mode="sector", sector=sector_id, limit=20)
            if sr:
                for h in sr.hits:
                    d = dump(h)
                    if d:
                        docs.append(d)
                        for t in d.get("tickers") or []:
                            coverage[str(t).upper()] = coverage.get(str(t).upper(), 0) + 1
        if self.rms:
            dash = dump(soft(self.rms.dashboard)) or {}
            company_cov = dash.get("company_coverage") or {}
            for t, n in company_cov.items():
                coverage[str(t).upper()] = coverage.get(str(t).upper(), 0) + int(n)
            for r in soft(self.rms.store.list_all, default=[]) or []:
                sectors = getattr(r, "sectors", None) or []
                if any(sector_id.lower() in str(s).lower() for s in sectors):
                    rms_rows.append(
                        {
                            "research_id": r.research_id,
                            "title": r.title,
                            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                            "tickers": r.tickers,
                        }
                    )
        port = dump(soft(self.e10.get_portfolio)) if self.e10 else None
        return SectorWorkspace(
            meta=WorkspaceMeta(workspace="sector", sources=["KIP", "RMS", "E10"]),
            sector_id=sector_id,
            company_coverage=coverage,
            documents=docs,
            portfolio_exposure={"portfolio": port} if port else None,
            rms_research=rms_rows,
        )

    def macro(self, *, as_of: str | None = None) -> MacroWorkspace:
        self._require()
        macro_docs: list[dict[str, Any]] = []
        themes: list[str] = []
        if self.kip:
            sr = soft(self.kip.search, "macro rates inflation rbi fed", mode="hybrid", limit=10)
            if sr:
                for h in sr.hits:
                    d = dump(h)
                    if d:
                        macro_docs.append(d)
                        themes.extend(d.get("themes") or [])
        return MacroWorkspace(
            meta=WorkspaceMeta(workspace="macro", sources=["E01", "E14", "KIP"]),
            e01=engine_state(self.e01, as_of=as_of),
            e14=engine_state(self.e14, as_of=as_of),
            macro_documents=macro_docs,
            themes=sorted(set(themes)),
        )

    def portfolio(self, *, as_of: str | None = None) -> PortfolioWorkspace:
        self._require()
        current = dump(soft(self.e10.get_portfolio, as_of)) if self.e10 else None
        hist = []
        if self.e10:
            for s in soft(self.e10.history, 20, default=[]) or []:
                d = dump(s)
                if d:
                    hist.append(d)
        risk = engine_state(self.e14, as_of=as_of)
        l4_book = None
        if self.l4:
            opinions = soft(self.l4.list_opinions, as_of=as_of, default={}) or {}
            l4_book = {k: dump(v) for k, v in opinions.items() if dump(v)}

        sector_exp = {}
        country_exp = {}
        if current:
            sector_exp = current.get("sector_exposure") or current.get("sectors") or {}
            country_exp = current.get("country_exposure") or current.get("countries") or {}
            # derive simple exposure from weights if missing
            if not sector_exp and isinstance(current.get("weights"), dict):
                sector_exp = {"raw_weights": current["weights"]}

        perf = None
        attr = None
        if self.flags.aws_cre and self.cre:
            card = dump(soft(self.cre.get_scorecard, "E10"))
            perf = card
            attr = dump(soft(self.cre.get_composite))

        return PortfolioWorkspace(
            meta=WorkspaceMeta(workspace="portfolio", sources=["E10", "E14", "L4", "CRE"]),
            current_portfolio=current,
            historical_portfolio=hist,
            risk=risk,
            sector_exposure=sector_exp if isinstance(sector_exp, dict) else {},
            country_exposure=country_exp if isinstance(country_exp, dict) else {},
            performance=perf,
            attribution=attr,
            l4_book=l4_book,
        )

    def research(self, research_id: str | None = None) -> ResearchWorkspace:
        self._require()
        current = dump(soft(self.rms.get_research, research_id)) if self.rms and research_id else None
        dash = dump(soft(self.rms.dashboard)) if self.rms else None
        evidence = (current or {}).get("evidence_package")
        reasoning = (current or {}).get("reasoning_package")
        supporting = []
        conflicting = []
        if isinstance(evidence, dict):
            supporting = list(evidence.get("documents_retrieved") or evidence.get("agi_research_used") or [])
        if isinstance(reasoning, dict):
            conflicting = list(reasoning.get("contradictions") or [])
            val = reasoning.get("validation") or {}
            supporting = supporting or list(val.get("supporting_documents") or [])

        status = (current or {}).get("status")
        review_status = status if status in {"internal_review", "compliance_review", "revision_requested"} else None
        approval_status = status if status in {"approved", "rejected"} else None
        publishing_status = status if status in {"published", "approved"} else None

        timeline = None
        if current and current.get("tickers") and self.kip:
            timeline = dump(soft(self.kip.timeline, current["tickers"][0]))

        return ResearchWorkspace(
            meta=WorkspaceMeta(workspace="research", sources=["RMS", "RSP", "KIP"]),
            research_id=research_id,
            current_draft=current,
            evidence_package=evidence if isinstance(evidence, dict) else None,
            reasoning_package=reasoning if isinstance(reasoning, dict) else None,
            research_timeline=timeline,
            supporting_documents=[str(x) for x in supporting][:40],
            conflicting_evidence=[c if isinstance(c, dict) else {"summary": str(c)} for c in conflicting][:20],
            review_status=review_status or (status if current else None),
            approval_status=approval_status,
            publishing_status=publishing_status,
            draft_queue=list((dash or {}).get("draft_queue") or []),
            review_queue=list((dash or {}).get("review_queue") or []),
        )

    def replay(self, as_of: str) -> ReplayWorkspace:
        self._require()
        if not self.flags.aws_replay:
            raise RuntimeError("AWS_REPLAY is disabled")
        day = str(as_of)[:10]
        engines = {
            "e01": engine_state(self.e01, as_of=day),
            "e02": None,  # symbol-scoped; omitted at book level
            "e14": engine_state(self.e14, as_of=day),
            "e10": dump(soft(self.e10.get_portfolio, day)) if self.e10 else None,
        }
        l4 = None
        if self.l4:
            opinions = soft(self.l4.list_opinions, as_of=day, default={}) or {}
            l4 = {k: dump(v) for k, v in opinions.items() if dump(v)}

        # Find validation replay run covering date
        replay_run = None
        performance = None
        if self.validation:
            runs = soft(self.validation.list_runs, 50, default=[]) or []
            for r in runs:
                d = dump(r) or {}
                # match by generated_at / dataset window heuristics
                gen = str(d.get("generated_at") or d.get("created_at") or "")
                if day in gen or d.get("dataset_id"):
                    replay_run = d
                    rid = d.get("run_id")
                    if rid:
                        performance = soft(self.validation.get_dashboard, rid)
                    if day in gen:
                        break

        research = []
        if self.rms:
            for r in soft(self.rms.store.list_all, default=[]) or []:
                pub = getattr(r, "published_at", None)
                if pub and str(pub)[:10] == day:
                    research.append({"research_id": r.research_id, "title": r.title, "status": str(getattr(r.status, "value", r.status))})

        predictions = []
        if self.kip:
            for p in soft(self.kip.store.list_predictions, default=[]) or []:
                if str(getattr(p, "predicted_at", ""))[:10] == day:
                    predictions.append(dump(p))

        return ReplayWorkspace(
            meta=WorkspaceMeta(workspace="replay", sources=["Replay", "E01", "E14", "E10", "L4", "RMS", "KIP"]),
            as_of=day,
            engine_outputs={k: v for k, v in engines.items() if v is not None},
            l4=l4,
            portfolio=engines.get("e10"),
            research=research,
            predictions=[p for p in predictions if p],
            performance=performance if isinstance(performance, dict) else None,
            replay_run=replay_run,
        )

    def cre_workspace(self) -> CreWorkspace:
        self._require()
        if not self.flags.aws_cre:
            raise RuntimeError("AWS_CRE is disabled")
        scorecards = []
        if self.cre:
            for c in soft(self.cre.list_scorecards, default=[]) or []:
                d = dump(c)
                if d:
                    scorecards.append(d)
        return CreWorkspace(
            meta=WorkspaceMeta(workspace="cre", sources=["CRE"]),
            dashboard=dump(soft(self.cre.get_dashboard)) if self.cre else None,
            scorecards=scorecards,
            composite=dump(soft(self.cre.get_composite)) if self.cre else None,
            alerts=soft(self.cre.get_alerts) if self.cre else None,
            promotion=dump(soft(self.cre.get_promotion)) if self.cre else None,
        )

    def knowledge_explorer(self, entity: str) -> KnowledgeExplorer:
        self._require()
        graph = dump(soft(self.kip.graph, entity)) if self.kip else None
        companies, themes, industries, macros, rels = [], [], [], [], []
        if graph:
            for n in graph.get("nodes") or []:
                kind = n.get("kind")
                label = n.get("label") or n.get("node_id")
                if kind == "company":
                    companies.append(str(label))
                elif kind == "theme":
                    themes.append(str(label))
                elif kind == "industry":
                    industries.append(str(label))
                elif kind == "macro":
                    macros.append(str(label))
            for e in graph.get("edges") or []:
                if e.get("relation") in {"RELATED_RESEARCH", "RELATED_AGI_RESEARCH", "RELATED_BROKER_RESEARCH", "SUPERSEDES"}:
                    rels.append(e)
        return KnowledgeExplorer(
            meta=WorkspaceMeta(workspace="knowledge_explorer", sources=["KIP"]),
            entity=entity,
            graph=graph,
            company_links=sorted(set(companies)),
            themes=sorted(set(themes)),
            industries=sorted(set(industries)),
            macro_drivers=sorted(set(macros)),
            research_relationships=rels[:40],
        )

    def dashboard(self) -> AwsDashboard:
        self._require()
        health = {
            "kip": soft(self.kip.health) if self.kip else None,
            "rsp": soft(self.rsp.health) if self.rsp else None,
            "rms": soft(self.rms.health) if self.rms else None,
            "cre": soft(self.cre.health) if self.cre else None,
            "validation": soft(self.validation.health) if self.validation else None,
            "e01": soft(self.e01.health) if self.e01 else None,
            "e10": soft(self.e10.health) if self.e10 else None,
            "l4": soft(self.l4.health) if self.l4 else None,
        }
        recent = []
        if self.rms:
            rows = sorted(
                soft(self.rms.store.list_all, default=[]) or [],
                key=lambda r: getattr(r, "updated_at", None) or getattr(r, "created_at", None),
                reverse=True,
            )[:10]
            for r in rows:
                recent.append(
                    {
                        "research_id": r.research_id,
                        "title": r.title,
                        "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                        "tickers": r.tickers,
                    }
                )
        return AwsDashboard(
            meta=WorkspaceMeta(
                workspace="dashboard",
                sources=["KIP", "RSP", "RMS", "CRE", "E01", "E10", "L4", "Replay"],
            ),
            platform_health=health,
            portfolio=dump(soft(self.e10.get_portfolio)) if self.e10 else None,
            cre=dump(soft(self.cre.get_dashboard)) if self.cre and self.flags.aws_cre else None,
            rms=dump(soft(self.rms.dashboard)) if self.rms else None,
            kip_stats=(soft(self.kip.health) or {}).get("stats") if self.kip else None,
            rsp_stats=(soft(self.rsp.health) or {}).get("stats") if self.rsp else None,
            recent_research=recent,
        )

    def search(self, query: str, *, limit: int = 20) -> SearchResponse:
        self._require()
        q = (query or "").strip()
        hits: list[SearchHit] = []
        if self.kip and q:
            sr = soft(self.kip.search, q, mode="hybrid", limit=limit)
            if sr:
                for h in sr.hits:
                    d = dump(h) or {}
                    kind = "report"
                    dtype = str(d.get("document_type") or "")
                    if dtype.startswith("agi_"):
                        kind = "research"
                    elif "broker" in dtype:
                        kind = "broker"
                    elif dtype == "market_news":
                        kind = "report"
                    hits.append(
                        SearchHit(
                            kind=kind,
                            id=str(d.get("document_id") or ""),
                            title=str(d.get("title") or d.get("document_id") or ""),
                            score=float(d.get("score") or 0),
                            ticker=(d.get("tickers") or [None])[0],
                            snippet=str(d.get("snippet") or "")[:240],
                            source="KIP",
                        )
                    )
            # theme / company entity search
            th = soft(self.kip.get_theme, q.lower())
            if th and getattr(th, "documents", None):
                hits.append(
                    SearchHit(
                        kind="theme",
                        id=th.theme_id,
                        title=th.theme,
                        score=0.9,
                        snippet=f"{len(th.documents)} documents",
                        source="KIP",
                    )
                )
            if q.isupper() or (len(q) <= 12 and q.replace(".", "").isalnum()):
                co = soft(self.kip.get_company, q.upper())
                if co and getattr(co, "documents", None):
                    hits.append(
                        SearchHit(
                            kind="company",
                            id=co.ticker,
                            title=co.ticker,
                            score=1.0,
                            ticker=co.ticker,
                            snippet=(co.latest_thesis or "")[:240],
                            source="KIP",
                        )
                    )
        if self.rms and q:
            for r in soft(self.rms.store.list_all, default=[]) or []:
                blob = f"{r.title} {' '.join(r.tickers)} {r.owner}".lower()
                if q.lower() in blob:
                    hits.append(
                        SearchHit(
                            kind="research",
                            id=r.research_id,
                            title=r.title,
                            score=0.85,
                            ticker=r.tickers[0] if r.tickers else None,
                            snippet=f"status={r.status.value} owner={r.owner}",
                            source="RMS",
                        )
                    )
                if q.lower() in (r.owner or "").lower() or q.lower() in (r.reviewer or "").lower():
                    hits.append(
                        SearchHit(
                            kind="people",
                            id=r.owner or r.reviewer,
                            title=r.owner or r.reviewer,
                            score=0.5,
                            snippet=f"research={r.research_id}",
                            source="RMS",
                        )
                    )
        if self.kip and q:
            for p in soft(self.kip.store.list_predictions, default=[]) or []:
                if q.upper() in p.ticker or q.lower() in (p.thesis or "").lower():
                    hits.append(
                        SearchHit(
                            kind="prediction",
                            id=p.prediction_id,
                            title=f"{p.ticker} prediction",
                            score=0.7,
                            ticker=p.ticker,
                            snippet=(p.thesis or "")[:200],
                            source="KIP",
                        )
                    )
        # de-dupe by kind+id
        seen: set[str] = set()
        uniq: list[SearchHit] = []
        for h in sorted(hits, key=lambda x: x.score, reverse=True):
            key = f"{h.kind}:{h.id}"
            if not h.id or key in seen:
                continue
            seen.add(key)
            uniq.append(h)
        return SearchResponse(query=q, hits=uniq[:limit])

    def copilot(
        self,
        *,
        workspace: str = "company",
        question: str = "",
        ticker: str | None = None,
        theme_id: str | None = None,
        sector_id: str | None = None,
        research_id: str | None = None,
        as_of: str | None = None,
    ) -> CopilotContext:
        self._require()
        if not self.flags.aws_copilot:
            raise RuntimeError("AWS_COPILOT is disabled")

        ws = (workspace or "company").lower()
        kip_ctx = None
        house = None
        rsp_ctx = None
        l4 = None
        port = dump(soft(self.e10.get_portfolio, as_of)) if self.e10 else None
        research = None
        engines: dict[str, Any] = {}

        if ticker and self.kip:
            kip_ctx = soft(self.kip.research_context, question or ticker, ticker=ticker.upper())
            house = dump(soft(self.kip.house_view, ticker.upper()))
        if ticker and self.l4:
            l4 = dump(soft(self.l4.get_opinion, ticker.upper(), as_of=as_of))
        if ticker and self.rsp:
            rsp_ctx = soft(self.rsp.reason_for_writer, question or f"{ticker} workspace", ticker=ticker.upper())
        if research_id and self.rms:
            research = dump(soft(self.rms.get_research, research_id))
        elif ws == "research" and self.rms:
            dash = dump(soft(self.rms.dashboard)) or {}
            qid = (dash.get("draft_queue") or dash.get("review_queue") or [None])[0]
            if qid:
                research = dump(soft(self.rms.get_research, qid))

        if ticker:
            engines = {
                "e01": engine_state(self.e01, as_of=as_of),
                "e13": engine_state(self.e13, symbol=ticker.upper(), as_of=as_of),
                "e14": engine_state(self.e14, as_of=as_of),
                "e11": engine_state(self.e11, symbol=ticker.upper(), as_of=as_of),
            }

        # Ensure never-empty context
        if not any([kip_ctx, rsp_ctx, l4, port, research, house]):
            kip_ctx = {
                "note": "No institutional context loaded yet — workspace bootstrap",
                "workspace": ws,
                "ticker": ticker,
                "theme_id": theme_id,
                "sector_id": sector_id,
            }

        return CopilotContext(
            workspace=ws,
            ticker=ticker.upper() if ticker else None,
            theme_id=theme_id,
            sector_id=sector_id,
            research_id=research_id or (research or {}).get("research_id"),
            as_of=as_of,
            question=question or f"Assist with {ws} workspace",
            kip=kip_ctx if isinstance(kip_ctx, dict) else None,
            rsp=rsp_ctx if isinstance(rsp_ctx, dict) else None,
            l4=l4,
            portfolio=port,
            research=research,
            house_view=house,
            engines={k: v for k, v in engines.items() if v},
            answer_policy="context_aware_never_empty",
        )

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.aws else "disabled",
            "platform": "AWS",
            "name": "AGI Analyst Workspace",
            "aws_version": AWS_VERSION,
            "flags": self.flags.as_dict(),
            "public_website": False,
            "creates_research_logic": False,
            "consumes": [
                "KIP",
                "RSP",
                "E01",
                "E02",
                "E03",
                "E04",
                "E05",
                "E08",
                "E09",
                "E10",
                "E11",
                "E13",
                "E14",
                "L4",
                "Replay",
                "CRE",
                "RMS",
            ],
            "workspaces": [
                "company",
                "sector",
                "theme",
                "macro",
                "portfolio",
                "research",
                "replay",
                "cre",
            ],
            "out_of_scope": [
                "research_engine_changes",
                "trading",
                "oms",
                "broker_execution",
                "architecture_amendments",
            ],
        }

    def _relative_value(self, ticker: str, *, as_of: str | None) -> dict[str, Any] | None:
        if self.e04 is None:
            return None
        # E04 is pair-scoped; do not invent RV logic — expose health/hint only
        health = soft(self.e04.health)
        state = soft(self.e04.get_state, ticker, as_of=as_of)
        return {
            "symbol_hint": ticker,
            "as_of": as_of,
            "state": dump(state),
            "note": "pair-scoped engine; open pair id for full relative-value state",
            "health": health,
        }

    def _require(self) -> None:
        if not self.flags.aws:
            raise RuntimeError("AWS is disabled")
