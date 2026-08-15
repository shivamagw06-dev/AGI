"""Versioned, governed registry over AGI's existing intelligence capabilities.

This registry describes and validates tools. It never exposes arbitrary Python,
SQL, URLs, or credentials to a reasoning model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Literal

Permission = Literal["read", "propose", "controlled_write"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    permission: Permission
    description: str
    handler: str
    input_schema: dict[str, dict[str, Any]]
    max_calls: int = 1
    freshness_sensitive: bool = False

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _field(kind: str, *, required: bool = False, limit: int | None = None) -> dict[str, Any]:
    return {"type": kind, "required": required, **({"limit": limit} if limit else {})}


_TOOLS = (
    ToolSpec("SEARCH_RESEARCH", "1.0", "read", "Hybrid search over AGI institutional research and validated memory.", "app.kip.service.KipService.search", {"query": _field("str", required=True, limit=500), "company": _field("str", limit=80), "industry": _field("str", limit=120), "date_from": _field("str", limit=32), "date_to": _field("str", limit=32), "document_type": _field("str", limit=80), "limit": _field("int", limit=30)}, max_calls=3),
    ToolSpec("SEARCH_WEB", "1.0", "read", "Provider-independent external discovery; results remain evidence, not knowledge.", "app.faa.connectors.search_api", {"query": _field("str", required=True, limit=500), "date_range": _field("str", limit=80), "domains": _field("list", limit=12), "max_results": _field("int", limit=10)}, max_calls=5, freshness_sensitive=True),
    ToolSpec("SEARCH_NEWS", "1.0", "read", "Search recent attributable financial news.", "app.faa.connectors.news", {"query": _field("str", required=True, limit=500), "date_from": _field("str", limit=32), "max_results": _field("int", limit=10)}, max_calls=3, freshness_sensitive=True),
    ToolSpec("GET_DOCUMENT", "1.0", "read", "Retrieve one known KIP document with provenance.", "app.kip.service.KipService.get_document", {"document_id": _field("str", required=True, limit=160)}),
    ToolSpec("GET_COMPANY", "1.0", "read", "Retrieve structured company identity and institutional knowledge.", "app.kf.service.KnowledgeFactoryService.get_company", {"company_id": _field("str", required=True, limit=80), "fields": _field("list", limit=30)}),
    ToolSpec("GET_COMPANY_ANALYSIS", "1.0", "read", "Resolve company classification, industry models, required KPIs, warehouse/AFE coverage and research protocol.", "company_intelligence_resolver.CompanyIntelligenceResolver.resolve", {"company_id": _field("str", required=True, limit=80), "period": _field("str", limit=40), "as_of_date": _field("str", limit=32), "segments": _field("list", limit=20)}, max_calls=3),
    ToolSpec("GET_INDUSTRY", "1.0", "read", "Retrieve industry DNA, drivers, KPIs and risks.", "app.kf.service.KnowledgeFactoryService.get_sector", {"industry_id": _field("str", required=True, limit=120), "fields": _field("list", limit=30)}),
    ToolSpec("GET_FINANCIALS", "1.0", "read", "Retrieve reported or estimated warehouse financial observations.", "app.kaip_client.client.KAIPClient.get_company_profile", {"company": _field("str", required=True, limit=80), "metrics": _field("list", limit=40), "period": _field("str", limit=40), "frequency": _field("str", limit=20)}),
    ToolSpec("GET_MARKET_DATA", "1.0", "read", "Retrieve point-in-time market observations through governed providers.", "app.market_data.client.MarketDataClient.get_quote", {"symbol": _field("str", required=True, limit=40), "data_type": _field("str", limit=40)}, freshness_sensitive=True),
    ToolSpec("GET_CAUSAL_GRAPH", "1.0", "read", "Retrieve evidence-backed causal chains and counter-effects.", "causal_graph.production", {"entity": _field("str", limit=80), "industry": _field("str", limit=120), "event": _field("str", limit=240), "depth": _field("int", limit=6)}),
    ToolSpec("GET_CAUSAL_RESEARCH", "1.0", "read", "Retrieve point-in-time governed causal research context from existing AGI relationship systems.", "causal_research_engine.service.ask_context", {"entity": _field("str", required=True, limit=80), "question": _field("str", limit=500), "industry": _field("str", limit=120), "depth": _field("int", limit=6), "analysis_as_of": _field("str", limit=32)}, max_calls=3),
    ToolSpec("GET_BANK_VALUATION", "1.0", "read", "Evaluate a classified commercial bank using point-in-time inputs, bank-appropriate methods and execution-blocking evidence gates.", "financials_valuation.service.evaluate_bank", {"company": _field("dict", required=True, limit=30), "inputs": _field("dict", required=True, limit=80), "as_of": _field("str", required=True, limit=32), "peers": _field("list", limit=50), "history": _field("list", limit=100), "scenarios": _field("dict", limit=3)}, max_calls=3),
    ToolSpec("GET_FINANCIAL_VALUATION", "1.0", "read", "Route a financial institution to its authoritative subsector model with PIT evidence and execution-blocking gates.", "financials_valuation.facade.evaluate_financial_institution", {"company": _field("dict", required=True, limit=30), "inputs": _field("dict", required=True, limit=100), "as_of": _field("str", required=True, limit=32), "peers": _field("list", limit=50), "history": _field("list", limit=100), "scenarios": _field("dict", limit=3)}, max_calls=3),
    ToolSpec("GET_TECHNOLOGY_VALUATION", "2K.0", "read", "Evaluate all governed Technology & Digital subsectors using point-in-time evidence, deterministic sector economics and execution-blocking gates.", "technology_valuation.service.evaluate_technology_company", {"company": _field("dict", required=True, limit=30), "inputs": _field("dict", required=True, limit=100), "as_of": _field("str", required=True, limit=32), "peers": _field("list", limit=50), "history": _field("list", limit=100), "scenarios": _field("dict", limit=3)}, max_calls=3),
    ToolSpec("GET_CONSUMER_VALUATION", "3.0", "read", "Evaluate governed Consumer subsectors using point-in-time evidence, unit economics, deterministic AFE calculations and execution-blocking gates.", "consumer_valuation.service.evaluate_consumer_company", {"company": _field("dict", required=True, limit=40), "inputs": _field("dict", required=True, limit=120), "as_of": _field("str", required=True, limit=32), "peers": _field("list", limit=50), "history": _field("list", limit=100), "scenarios": _field("dict", limit=3)}, max_calls=3),
    ToolSpec("GET_INDUSTRIAL_VALUATION", "4.0", "read", "Evaluate governed industrial, manufacturing and real-asset subsectors using PIT evidence, cycle normalization and deterministic AFE calculations.", "industrial_valuation.service.evaluate_industrial_company", {"company": _field("dict", required=True, limit=50), "inputs": _field("dict", required=True, limit=140), "as_of": _field("str", required=True, limit=32), "peers": _field("list", limit=50), "history": _field("list", limit=100), "scenarios": _field("dict", limit=3)}, max_calls=3),
    ToolSpec("GET_THESIS", "1.0", "read", "Retrieve current and historical thesis versions.", "app.ail.thesis_engine", {"company": _field("str", limit=80), "industry": _field("str", limit=120), "topic": _field("str", limit=240)}),
    ToolSpec("GET_LATEST_EVENTS", "1.0", "read", "Retrieve latest validated company, industry or macro events.", "app.mee.service.MarketEventEngineService.search", {"query": _field("str", required=True, limit=500), "limit": _field("int", limit=20)}, freshness_sensitive=True),
    ToolSpec("CALCULATE", "1.2", "read", "Run AFE from explicit inputs or resolve verified company inputs from the canonical warehouse.", "financial_engine.calculate", {"operation": _field("str", required=True, limit=60), "inputs": _field("dict", limit=50), "company": _field("str", limit=80), "period": _field("str", limit=40), "as_of_date": _field("str", limit=32), "currency": _field("str", limit=12), "unit": _field("str", limit=30)}, max_calls=15),
    ToolSpec("COMPARE", "1.0", "read", "Compare governed company, peer, financial or thesis objects.", "app.iie.service.InvestmentIntelligenceService.compare", {"entities": _field("list", required=True, limit=20), "dimensions": _field("list", limit=20)}),
    ToolSpec("CREATE_MONITOR", "1.0", "propose", "Propose a monitoring indicator; cannot activate it.", "intelligence_learning_candidates", {"thesis_id": _field("str", limit=160), "indicator": _field("dict", required=True, limit=30)}),
    ToolSpec("PROPOSE_KNOWLEDGE", "1.0", "propose", "Store candidate knowledge for validation; cannot promote trust.", "intelligence_learning_candidates", {"document_id": _field("str", required=True, limit=160), "payload": _field("dict", required=True, limit=100)}),
    ToolSpec("APPROVE_KNOWLEDGE", "1.0", "controlled_write", "Promote validated candidate knowledge through an authorized review gate.", "intelligence_learning_candidates", {"candidate_id": _field("str", required=True, limit=160), "review_reason": _field("str", required=True, limit=1000)}),
)

_BY_NAME = {tool.name: tool for tool in _TOOLS}
_CURRENT_RE = re.compile(r"\b(today|latest|current|recent|now|after|changed|outlook)\b", re.I)
_CAUSAL_RE = re.compile(r"\b(why|how|impact|affect|transmit|mean for|what happens)\b", re.I)
_THESIS_RE = re.compile(r"\b(view|thesis|outlook|changed the view|invalidate)\b", re.I)
_FINANCIAL_RE = re.compile(r"\b(revenue|margins?|ebitda|profits?|cash flows?|valuation|roe|roa|roic|nim|npa|loans?|deposits?|financials?|financially|invest|investment|expensive|cheap)\b", re.I)
_BANK_RE = re.compile(r"\b(bank|nim|casa|gnpa|nnpa|credit cost|deposit|cet1|crar|price.to.book|p/b)\b", re.I)
_TECHNOLOGY_RE = re.compile(r"\b(tcs|infosys|infy|hcltech|hcl tech|wipro|tech mahindra|techm|it services|outsourcing|utilization|billing rate|attrition|deal wins|tcv|book.to.bill|software|saas|annual recurring revenue|arr|nrr|grr|churn|cac|rule of 40|ev.arr|internet platform|marketplace|gmv|take rate|active buyers|active sellers|order frequency|network effect|contribution margin|ev.gmv|consumer internet|digital commerce|e.?commerce|online retail|active customers|average order value|aov|repeat rate|return rate|inventory turns|advertising arpu|semiconductor|chip|fabless|foundry|atmp|osat|wafer|yield rate|design win|telecom|wireless|broadband|fiber|subscriber|arpu|spectrum|tariff|5g|4g|telecom tower|tower infrastructure|passive infrastructure|tenancy ratio|tenant additions|ev.site|energy pass.through|engineering services|er.d|electronics manufacturing|technology hardware|data cent(?:re|er)|operational mw|pue|fintech|payments|tpv|merchant|cybersecurity|cloud infrastructure|rpo)\b", re.I)
_CONSUMER_RE = re.compile(r"\b(fmcg|consumer durables?|retail|same.store sales|sssg|footfall|sales density|qsr|restaurant|store additions?|hotel|hospitality|occupancy|adr|revpar|textiles?|apparel|cotton|footwear|pairs sold|jewell?ery|gold price|making charges?|premiumization|volume growth|price.mix)\b", re.I)
_INDUSTRIAL_RE = re.compile(r"\b(capital goods|industrial machinery|epc|infrastructure|construction|cement|steel|metals?|mining|chemicals?|specialty chemicals?|auto components?|automobile|defen[cs]e|aerospace|railways?|electrical equipment|renewable equipment|packaging|paper|pulp|order book|order inflow|capacity utilization|commodity spread|book.to.bill)\b", re.I)


class ToolValidationError(ValueError):
    pass


def list_tools(*, permissions: set[Permission] | None = None) -> list[dict[str, Any]]:
    return [tool.public() for tool in _TOOLS if permissions is None or tool.permission in permissions]


def get_tool(name: str) -> ToolSpec:
    tool = _BY_NAME.get(str(name or "").strip().upper())
    if tool is None:
        raise ToolValidationError("unknown_tool")
    return tool


def validate_tool_input(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    tool = get_tool(name)
    if not isinstance(payload, dict):
        raise ToolValidationError("tool_input_must_be_object")
    unknown = set(payload) - set(tool.input_schema)
    if unknown:
        raise ToolValidationError(f"unknown_tool_arguments:{','.join(sorted(unknown))}")
    clean: dict[str, Any] = {}
    for key, rule in tool.input_schema.items():
        value = payload.get(key)
        if rule.get("required") and value in (None, "", [], {}):
            raise ToolValidationError(f"missing_required_argument:{key}")
        if value is None:
            continue
        expected = {"str": str, "int": int, "list": list, "dict": dict}[rule["type"]]
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise ToolValidationError(f"invalid_argument_type:{key}")
        limit = rule.get("limit")
        if expected is str:
            value = value.strip()
            if limit and len(value) > limit:
                raise ToolValidationError(f"argument_too_long:{key}")
        elif expected is int and limit and value > limit:
            raise ToolValidationError(f"argument_above_limit:{key}")
        elif expected in {list, dict} and limit and len(value) > limit:
            raise ToolValidationError(f"argument_too_large:{key}")
        clean[key] = value
    return clean


def plan_tools(question: str, *, ticker_hint: str | None = None) -> dict[str, Any]:
    query = str(question or "").strip()[:2_000]
    selected = ["SEARCH_RESEARCH"]
    reasons = {"SEARCH_RESEARCH": "institutional_memory_first"}
    if ticker_hint:
        selected.extend(["GET_COMPANY", "GET_COMPANY_ANALYSIS", "GET_FINANCIALS"])
        reasons.update({"GET_COMPANY": "resolved_company", "GET_COMPANY_ANALYSIS": "industry_kpi_coverage", "GET_FINANCIALS": "company_financial_context"})
    if _CURRENT_RE.search(query):
        selected.extend(["GET_LATEST_EVENTS", "SEARCH_WEB"])
        reasons.update({"GET_LATEST_EVENTS": "freshness_required", "SEARCH_WEB": "current_world_check"})
    if _CAUSAL_RE.search(query):
        selected.extend(["GET_CAUSAL_GRAPH", "GET_CAUSAL_RESEARCH"])
        reasons["GET_CAUSAL_GRAPH"] = "causal_question"
        reasons["GET_CAUSAL_RESEARCH"] = "governed_causal_context"
    if _THESIS_RE.search(query):
        selected.append("GET_THESIS"); reasons["GET_THESIS"] = "view_or_thesis_question"
    if _FINANCIAL_RE.search(query):
        selected.extend(["GET_FINANCIALS", "CALCULATE"])
        reasons.update({"GET_FINANCIALS": "financial_transmission", "CALCULATE": "deterministic_math_only"})
    if ticker_hint and _BANK_RE.search(query):
        selected.append("GET_BANK_VALUATION")
        reasons["GET_BANK_VALUATION"] = "bank_specific_point_in_time_valuation"
    if ticker_hint and _FINANCIAL_RE.search(query) and not _TECHNOLOGY_RE.search(query) and not _CONSUMER_RE.search(query) and not _INDUSTRIAL_RE.search(query):
        selected.append("GET_FINANCIAL_VALUATION")
        reasons["GET_FINANCIAL_VALUATION"] = "authoritative_financial_subsector_valuation"
    if ticker_hint and _TECHNOLOGY_RE.search(query):
        selected.append("GET_TECHNOLOGY_VALUATION")
        reasons["GET_TECHNOLOGY_VALUATION"] = "authoritative_technology_subsector_valuation"
    if ticker_hint and _CONSUMER_RE.search(query):
        selected.append("GET_CONSUMER_VALUATION")
        reasons["GET_CONSUMER_VALUATION"] = "authoritative_consumer_subsector_unit_economics_and_valuation"
    if ticker_hint and _INDUSTRIAL_RE.search(query):
        selected.append("GET_INDUSTRIAL_VALUATION")
        reasons["GET_INDUSTRIAL_VALUATION"] = "authoritative_industrial_cycle_and_valuation"
    names = list(dict.fromkeys(selected))
    tools = [get_tool(name) for name in names]
    return {
        "registry_version": "agi-tools-v1",
        "tools": [{"name": tool.name, "version": tool.version, "permission": tool.permission,
                   "max_calls": tool.max_calls, "freshness_sensitive": tool.freshness_sensitive,
                   "reason": reasons[tool.name]} for tool in tools],
        "budgets": {"max_searches": 5, "max_documents": 20, "max_runtime_seconds": 30},
        "controlled_writes_allowed": False,
    }
