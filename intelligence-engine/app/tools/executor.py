"""Governed execution runtime for AGI tools.

Handlers are explicitly injected by trusted application code. Registry handler
strings are descriptive metadata and are never imported or executed.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field, is_dataclass
import inspect
import time
from typing import Any, Callable

from app.tools.registry import ToolSpec, ToolValidationError, get_tool, validate_tool_input


class ToolExecutionError(RuntimeError):
    """A safe, caller-visible governed tool failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class ToolExecutionContext:
    allow_proposals: bool = False
    allow_controlled_writes: bool = False
    max_searches: int = 5
    max_documents: int = 20
    max_runtime_seconds: float = 30.0
    timeout_seconds: float = 10.0
    started_at: float = field(default_factory=time.monotonic)
    calls: dict[str, int] = field(default_factory=dict)
    searches: int = 0
    documents: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)


Handler = Callable[..., Any]
_SEARCH_TOOLS = {"SEARCH_RESEARCH", "SEARCH_WEB", "SEARCH_NEWS", "GET_LATEST_EVENTS"}


def _normalise(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _normalise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _result_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return {"result_type": "list", "result_count": len(value)}
    if isinstance(value, dict):
        return {"result_type": "object", "result_count": len(value)}
    return {"result_type": type(value).__name__, "result_count": 1 if value is not None else 0}


class GovernedToolExecutor:
    def __init__(self, handlers: dict[str, Handler] | None = None):
        self._handlers = {str(name).upper(): handler for name, handler in (handlers or {}).items()}

    @property
    def bound_tools(self) -> list[str]:
        return sorted(self._handlers)

    async def execute(
        self,
        name: str,
        payload: dict[str, Any],
        context: ToolExecutionContext,
    ) -> Any:
        started = time.monotonic()
        tool: ToolSpec | None = None
        clean: dict[str, Any] = {}
        status = "error"
        error_code: str | None = None
        result: Any = None
        try:
            tool = get_tool(name)
            clean = validate_tool_input(tool.name, payload)
            self._authorize(tool, context)
            self._reserve_budget(tool, context)
            handler = self._handlers.get(tool.name)
            if handler is None:
                raise ToolExecutionError("tool_handler_unavailable")
            result = handler(**clean)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=context.timeout_seconds)
            result = _normalise(result)
            status = "success"
            return result
        except asyncio.TimeoutError as exc:
            error_code = "tool_timeout"
            raise ToolExecutionError(error_code) from exc
        except ToolValidationError as exc:
            error_code = f"tool_input_invalid:{exc}"
            raise ToolExecutionError(error_code) from exc
        except ToolExecutionError as exc:
            error_code = exc.code
            raise
        except Exception as exc:
            error_code = "tool_execution_failed"
            raise ToolExecutionError(error_code) from exc
        finally:
            trace = {
                "tool": tool.name if tool else str(name or "").upper(),
                "version": tool.version if tool else None,
                "permission": tool.permission if tool else None,
                "status": status,
                "error_code": error_code,
                "input_keys": sorted(clean),
                "latency_ms": int((time.monotonic() - started) * 1000),
            }
            if status == "success":
                trace.update(_result_summary(result))
            context.trace.append(trace)

    @staticmethod
    def _authorize(tool: ToolSpec, context: ToolExecutionContext) -> None:
        if tool.permission == "propose" and not context.allow_proposals:
            raise ToolExecutionError("proposal_permission_denied")
        if tool.permission == "controlled_write" and not context.allow_controlled_writes:
            raise ToolExecutionError("controlled_write_permission_denied")

    @staticmethod
    def _reserve_budget(tool: ToolSpec, context: ToolExecutionContext) -> None:
        if time.monotonic() - context.started_at > context.max_runtime_seconds:
            raise ToolExecutionError("runtime_budget_exceeded")
        calls = context.calls.get(tool.name, 0)
        if calls >= tool.max_calls:
            raise ToolExecutionError("tool_call_budget_exceeded")
        if tool.name in _SEARCH_TOOLS and context.searches >= context.max_searches:
            raise ToolExecutionError("search_budget_exceeded")
        if tool.name == "GET_DOCUMENT" and context.documents >= context.max_documents:
            raise ToolExecutionError("document_budget_exceeded")
        context.calls[tool.name] = calls + 1
        if tool.name in _SEARCH_TOOLS:
            context.searches += 1
        if tool.name == "GET_DOCUMENT":
            context.documents += 1


def build_core_read_executor(
    *,
    kip: Any | None = None,
    kf: Any | None = None,
    market: Any | None = None,
    mee: Any | None = None,
    thesis: Any | None = None,
) -> GovernedToolExecutor:
    """Bind existing AGI services without dynamic imports or hidden fallbacks."""

    handlers: dict[str, Handler] = {}
    if kip is not None:
        handlers["SEARCH_RESEARCH"] = lambda query, limit=10, **filters: kip.search(
            query, limit=limit, ticker=filters.get("company"), sector=filters.get("industry")
        )
        handlers["GET_DOCUMENT"] = kip.get_document
    if kf is not None:
        handlers["GET_COMPANY"] = lambda company_id, fields=None: kf.get_company(company_id)
        handlers["GET_INDUSTRY"] = lambda industry_id, fields=None: kf.get_sector(industry_id)
    if market is not None:
        handlers["GET_MARKET_DATA"] = lambda symbol, data_type=None: market.get_quote(symbol)
    if mee is not None:
        handlers["GET_LATEST_EVENTS"] = mee.search
    if thesis is not None:
        handlers["GET_THESIS"] = lambda company=None, industry=None, topic=None: thesis.get(
            company or industry or topic
        )
    return GovernedToolExecutor(handlers)
