from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from observability.tracing import llm_span, wrap_openai
from app.schemas.models import (
    AgentOutput,
    ConfidenceBreakdown,
    DebatePackage,
    DeskType,
    EvidenceItem,
    Finding,
    InstitutionalReport,
    ScenarioCase,
    SourceType,
)


@register_agent
class ChiefInvestmentOfficer(BaseAgent):
    """
    CIO synthesizes only. It does not orchestrate agents.
    Research Director supplies the evidence package + debate.
    """

    agent_id = "cio"
    mission = "Weigh competing analyst views and produce the final institutional investment thesis."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        # CIO also exposes synthesize() used by the Director; analyze() kept for registry completeness.
        report = await self.synthesize(context)
        evidence = report.supporting_evidence[:1] or [
            EvidenceItem(
                claim="CIO synthesis completed",
                source_id="internal:cio",
                source_type=SourceType.INTERNAL,
                reliability=0.6,
            )
        ]
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=[
                Finding(
                    statement=report.executive_summary[:400],
                    evidence_ids=[evidence[0].evidence_id],
                    confidence=report.confidence.score,
                )
            ],
            evidence=evidence if isinstance(evidence, list) else [evidence],
            confidence=report.confidence,
            assumptions=["Analyst evidence package is complete enough for synthesis"],
            invalidators=["Material new evidence that reverses the debate balance"],
        )

    async def synthesize(self, context: dict[str, Any]) -> InstitutionalReport:
        desk = context.get("desk") or DeskType.SMOKE
        desk_enum = desk if isinstance(desk, DeskType) else DeskType(str(desk))
        if desk_enum == DeskType.PORTFOLIO:
            return await self._synthesize_portfolio(context)
        if desk_enum == DeskType.INVESTMENT_OFFICE:
            return await self._synthesize_investment_office(context)

        outputs: list[AgentOutput] = context.get("agent_outputs") or []
        debate: DebatePackage | None = context.get("debate")
        confidence: ConfidenceBreakdown = context.get("confidence") or ConfidenceBreakdown(
            score=50,
            supports=[],
            challenges=["Missing confidence package"],
            rationale="Default confidence because no combined score was provided.",
        )
        evidence: list[EvidenceItem] = context.get("evidence") or []

        key_findings = []
        for output in outputs:
            for finding in output.findings[:2]:
                key_findings.append(finding.statement)

        bull_points = next((p.points for p in (debate.positions if debate else []) if p.side == "bull"), [])
        bear_points = next((p.points for p in (debate.positions if debate else []) if p.side == "bear"), [])
        base_points = next((p.points for p in (debate.positions if debate else []) if p.side == "base"), [])

        thesis = (
            f"AGI CIO synthesizes a {confidence.score}% confidence institutional view because "
            f"{len(outputs)} analyst packages and {len(evidence)} evidence items were provided. "
        )
        if debate and debate.unresolved_conflicts:
            thesis += "Unresolved conflicts remain and are treated as scenario risk rather than settled facts. "
        if key_findings:
            thesis += f"Lead finding: {key_findings[0]}"

        # Optional OpenAI enrichment — fails soft to deterministic synthesis
        enriched = await self._maybe_enrich(thesis, key_findings, debate, confidence)
        executive = enriched or thesis

        return InstitutionalReport(
            desk=desk_enum,
            title="AGI Institutional Research Note",
            executive_summary=executive,
            key_findings=key_findings[:8],
            macro_view=next((o.findings[0].statement for o in outputs if o.agent_id == "macro_economist" and o.findings), None),
            market_view=next((o.findings[0].statement for o in outputs if o.agent_id == "market_analyst" and o.findings), None),
            sector_view=None,
            company_view=None,
            technical_view=None,
            valuation_view=None,
            catalysts=[p for p in base_points[:4]],
            risks=[p for p in bear_points[:4]] + [c for c in confidence.challenges[:3]],
            bull_case=ScenarioCase(
                label="Bull",
                probability=max(10, min(40, 100 - confidence.score)),
                detail="; ".join(bull_points[:3]) or "Upside requires confirmation from breadth and macro transmission.",
                is_prediction=True,
            ),
            base_case=ScenarioCase(
                label="Base",
                probability=confidence.score,
                detail="; ".join(base_points[:3]) or executive[:240],
                is_prediction=True,
            ),
            bear_case=ScenarioCase(
                label="Bear",
                probability=max(10, min(40, 100 - confidence.score)),
                detail="; ".join(bear_points[:3]) or "Downside if invalidators in the evidence package trigger.",
                is_prediction=True,
            ),
            confidence=confidence,
            supporting_evidence=evidence[:20],
            action_items=[
                "Monitor evidence invalidators listed by analysts",
                "Re-run desk if AGIB cache freshness deteriorates",
                "Treat scenario cases as probabilities, not forecasts of fact",
            ],
        )

    async def _synthesize_portfolio(self, context: dict[str, Any]) -> InstitutionalReport:
        """CIO Summary for Portfolio Office — Neutral / Review language only. Never Buy/Sell/Execute."""
        outputs: list[AgentOutput] = context.get("agent_outputs") or []
        confidence: ConfidenceBreakdown = context.get("confidence") or ConfidenceBreakdown(
            score=50,
            supports=[],
            challenges=["Missing confidence package"],
            rationale="Default portfolio confidence.",
        )
        evidence: list[EvidenceItem] = context.get("evidence") or []
        pack = context.get("portfolio_pack")
        pack_data = pack.model_dump() if pack is not None and hasattr(pack, "model_dump") else (pack or {})

        portfolio = pack_data.get("portfolio") or {}
        name = portfolio.get("name") or "Client Portfolio"
        n_holdings = len(portfolio.get("holdings") or [])
        health = pack_data.get("health_score")
        recs = pack_data.get("recommendations") or []
        high = [r for r in recs if r.get("priority") == "high"]
        withheld = pack_data.get("withheld") or []

        key_findings: list[str] = []
        for output in outputs:
            for finding in output.findings[:2]:
                key_findings.append(finding.statement)

        thesis = (
            f"AGI Portfolio Office CIO Summary for '{name}' ({n_holdings} holdings). "
            f"Portfolio Health Score: {health if health is not None else 'withheld'}. "
            f"{len(high)} high-priority review item(s) in the Action Center. "
            "Stance is Neutral / Review — guidance uses Review, Research, Monitor, Consider, and Investigate only. "
        )
        if withheld:
            thesis += f"Withheld (not fabricated): {withheld[0]}. "
        if key_findings:
            thesis += f"Lead packaging finding: {key_findings[0]}"

        enriched = await self._maybe_enrich(
            thesis,
            key_findings,
            context.get("debate"),
            confidence,
            portfolio_mode=True,
        )
        executive = enriched or thesis

        action_items = [
            f"{r.get('verb')}: {r.get('title')}" for r in recs[:6]
        ] or [
            "Review portfolio concentration in Action Center",
            "Investigate holdings lacking research coverage",
            "Monitor withheld forecast/risk layers until engines are attached",
        ]

        return InstitutionalReport(
            desk=DeskType.PORTFOLIO,
            title=f"AGI Portfolio Office — {name}",
            executive_summary=executive,
            key_findings=key_findings[:8],
            macro_view=None,
            market_view=None,
            sector_view=str((pack_data.get("sector_exposure") or {}))[:240] or None,
            company_view=None,
            technical_view=None,
            valuation_view=None,
            catalysts=[
                "Deepen equity research coverage",
                "Attach Forecast Layer when available",
                "Compare timeline baselines once stored",
            ],
            risks=[w for w in withheld[:4]]
            + [r.get("title") for r in high[:3]],
            bull_case=ScenarioCase(
                label="Constructive review path",
                probability=max(10, min(40, confidence.score // 2)),
                detail="Research coverage improves and concentration recommendations are investigated — not a buy signal.",
                is_prediction=True,
            ),
            base_case=ScenarioCase(
                label="Monitor / Review",
                probability=confidence.score,
                detail=executive[:240],
                is_prediction=True,
            ),
            bear_case=ScenarioCase(
                label="Elevated review urgency",
                probability=max(10, min(40, 100 - confidence.score)),
                detail="Concentration or research gaps widen — investigate and monitor; not a sell instruction.",
                is_prediction=True,
            ),
            confidence=confidence,
            supporting_evidence=evidence[:20],
            action_items=action_items,
        )

    async def _synthesize_investment_office(self, context: dict[str, Any]) -> InstitutionalReport:
        """CIO Summary for Investment Office — Neutral / Review only. Never trade instructions."""
        outputs: list[AgentOutput] = context.get("agent_outputs") or []
        confidence: ConfidenceBreakdown = context.get("confidence") or ConfidenceBreakdown(
            score=50,
            supports=[],
            challenges=["Missing confidence package"],
            rationale="Default investment office confidence.",
        )
        evidence: list[EvidenceItem] = context.get("evidence") or []
        pack = context.get("investment_office_pack")
        pack_data = pack.model_dump() if pack is not None and hasattr(pack, "model_dump") else (pack or {})
        brief = pack_data.get("daily_brief") or {}
        queue = pack_data.get("research_queue") or []
        high = [q for q in queue if q.get("priority") == "high"]
        withheld = pack_data.get("withheld") or []

        key_findings: list[str] = []
        for output in outputs:
            for finding in output.findings[:2]:
                key_findings.append(finding.statement)

        thesis = (
            "AGI Investment Office CIO Summary. "
            f"{brief.get('executive_summary') or 'Daily brief packaged.'} "
            f"{len(high)} high-priority research item(s) deserve attention. "
            "Stance is Neutral / Review — guidance uses Review, Research, Monitor, Consider, and Investigate only. "
        )
        if withheld:
            thesis += f"Withheld (not fabricated): {withheld[0]}. "
        if key_findings:
            thesis += f"Lead packaging finding: {key_findings[0]}"

        enriched = await self._maybe_enrich(
            thesis,
            key_findings,
            context.get("debate"),
            confidence,
            investment_office_mode=True,
        )
        executive = enriched or thesis
        action_items = [
            f"{'Research' if q.get('priority')=='high' else 'Review'}: {q.get('title')} — {q.get('reason')}"
            for q in queue[:6]
        ] or [
            "Review Today's Brief for market story and risks",
            "Work Research Queue high-priority names",
            "Open Scenario Center only with evidenced assumptions",
        ]

        return InstitutionalReport(
            desk=DeskType.INVESTMENT_OFFICE,
            title="AGI Investment Office — Daily CIO",
            executive_summary=executive,
            key_findings=key_findings[:8],
            macro_view=str(brief.get("outlook") or "") or None,
            market_view=str(brief.get("todays_market_story"))[:240]
            if not isinstance(brief.get("todays_market_story"), dict)
            else (brief.get("todays_market_story") or {}).get("note"),
            sector_view=None,
            company_view=", ".join(
                str(x) for x in (brief.get("companies_to_research") or [])[:6] if x
            )
            or None,
            technical_view=None,
            valuation_view=None,
            catalysts=list(brief.get("research_priorities") or [])[:4],
            risks=[w for w in withheld[:3]]
            + [str((r or {}).get("title")) for r in (brief.get("top_risks") or [])[:3]],
            bull_case=ScenarioCase(
                label="Constructive research path",
                probability=max(10, min(40, confidence.score // 2)),
                detail="High-priority queue items are researched and assumptions re-checked — not a trade signal.",
                is_prediction=True,
            ),
            base_case=ScenarioCase(
                label="Monitor / Review",
                probability=confidence.score,
                detail=executive[:240],
                is_prediction=True,
            ),
            bear_case=ScenarioCase(
                label="Elevated attention",
                probability=max(10, min(40, 100 - confidence.score)),
                detail="Macro or forecast uncertainty rises — investigate and monitor; not a liquidation instruction.",
                is_prediction=True,
            ),
            confidence=confidence,
            supporting_evidence=evidence[:20],
            action_items=action_items,
        )

    async def _maybe_enrich(
        self,
        thesis: str,
        findings: list[str],
        debate: DebatePackage | None,
        confidence: ConfidenceBreakdown,
        portfolio_mode: bool = False,
        investment_office_mode: bool = False,
    ) -> str | None:
        from app.core.config import get_settings

        settings = get_settings()
        system = (
            "You are AGIB Institutional Intelligence — CIO / PM / equity research voice. "
            "Be concise, evidence-based, and institutional. Maximum 60 words unless the user "
            "explicitly asks for detailed analysis. Never invent company-specific facts. "
            "If evidence is insufficient, state that explicitly. Never exaggerate certainty. "
            "For stock recommendations use: Recommendation (Buy/Hold/Sell/Accumulate/Avoid), "
            "Reason (one sentence), Risk (single biggest risk), Investment Horizon "
            "(Short/Medium/Long Term). No retail-blog tone. No buy/sell without evidence."
        )
        user = str(
            {
                "draft": thesis,
                "findings": findings,
                "debate": debate.model_dump() if debate else None,
                "confidence": confidence.model_dump(),
            }
        )

        gemini_key = (settings.gemini_api_key or "").strip()
        if gemini_key:
            try:
                import httpx

                model = (settings.gemini_model or "gemini-flash-latest").strip()
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                with llm_span(
                    provider="gemini",
                    model=model,
                    prompt=user,
                    system=system,
                    tags=["cio_synthesis"],
                ) as _llm:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            url,
                            params={"key": gemini_key},
                            json={
                                "systemInstruction": {"parts": [{"text": system}]},
                                "contents": [{"role": "user", "parts": [{"text": user}]}],
                                "generationConfig": {"temperature": 0.2},
                            },
                        )
                    if response.is_success:
                        _llm.end(outputs={"status_code": response.status_code})
                    else:
                        _llm.end(error=f"gemini_http_{response.status_code}")
                if response.is_success:
                    payload = response.json()
                    parts = (((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
                    text = "".join(str(part.get("text") or "") for part in parts).strip()
                    if text:
                        return text
            except Exception:
                pass

        if not settings.openai_api_key:
            return None
        try:
            from openai import AsyncOpenAI

            client = wrap_openai(AsyncOpenAI(api_key=settings.openai_api_key))
            response = await client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = response.choices[0].message.content
            return text.strip() if text else None
        except Exception:
            return None
