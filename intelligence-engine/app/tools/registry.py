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
        selected.append("GET_CAUSAL_GRAPH"); reasons["GET_CAUSAL_GRAPH"] = "causal_question"
    if _THESIS_RE.search(query):
        selected.append("GET_THESIS"); reasons["GET_THESIS"] = "view_or_thesis_question"
    if _FINANCIAL_RE.search(query):
        selected.extend(["GET_FINANCIALS", "CALCULATE"])
        reasons.update({"GET_FINANCIALS": "financial_transmission", "CALCULATE": "deterministic_math_only"})
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
