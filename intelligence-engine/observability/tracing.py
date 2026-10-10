"""LangSmith tracing helpers — fail-open, no-op unless explicitly configured.

Rules for this module:
  * Never change a caller's return value or raise a new exception.
  * Zero overhead when tracing is disabled (decorators return the original fn).
  * Frozen modules (reasoning / KF / frameworks / intent) are never edited; the
    Ask pipeline wraps their call sites with `span()` instead.
"""

from __future__ import annotations

import functools
import inspect
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from observability.schema import is_enabled, project

_MAX_STR = 4000


def _safe(value: Any, _depth: int = 0) -> Any:
    """Best-effort JSON-ish projection; never raises, never huge."""
    if _depth > 3:
        return "…"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= _MAX_STR else value[:_MAX_STR] + "…"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in list(value.items())[:40]:
            try:
                out[str(k)] = _safe(v, _depth + 1)
            except Exception:
                out[str(k)] = "<unserializable>"
        return out
    if isinstance(value, (list, tuple, set)):
        return [_safe(v, _depth + 1) for v in list(value)[:40]]
    try:
        return str(value)[:_MAX_STR]
    except Exception:
        return "<unserializable>"


class _NoopSpan:
    """Handle returned when tracing is off — accepts calls and does nothing."""

    active = False

    def end(self, **_kwargs: Any) -> None:
        return None

    def add_metadata(self, **_kwargs: Any) -> None:
        return None


class _LangSmithSpan:
    def __init__(self, run_tree: Any) -> None:
        self._rt = run_tree
        self.active = True

    def end(self, *, outputs: Any = None, error: str | None = None) -> None:
        try:
            if outputs is not None:
                self._rt.end(outputs=_wrap_outputs(outputs))
            if error:
                self._rt.end(error=str(error)[:2000])
        except Exception:
            return None

    def add_metadata(self, **kwargs: Any) -> None:
        try:
            self._rt.add_metadata(_safe(kwargs))
        except Exception:
            return None


def _wrap_outputs(outputs: Any) -> dict[str, Any]:
    safe = _safe(outputs)
    return safe if isinstance(safe, dict) else {"output": safe}


@contextmanager
def span(
    name: str,
    *,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Trace a block of work. No-op (and never raises) when tracing is disabled."""
    if not is_enabled():
        yield _NoopSpan()
        return

    try:
        from langsmith import trace as ls_trace
    except Exception:
        yield _NoopSpan()
        return

    try:
        cm = ls_trace(
            name=name,
            run_type=run_type,
            inputs=_safe(inputs or {}),
            tags=list(tags or []),
            metadata=_safe(metadata or {}),
            project_name=project(),
        )
    except Exception:
        yield _NoopSpan()
        return

    try:
        with cm as run_tree:
            yield _LangSmithSpan(run_tree)
    except Exception:
        # Tracing must never break the caller: degrade to a no-op span.
        yield _NoopSpan()


def _call_inputs(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    if args:
        inputs["args"] = _safe(list(args))
    for k, v in kwargs.items():
        if v is not None:
            inputs[k] = _safe(v)
    return inputs


def traced(
    name: str | None = None,
    *,
    run_type: str = "chain",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator form. Returns the original function untouched when disabled."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        run_name = name or getattr(fn, "__name__", "agi_run")

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not is_enabled():
                    return await fn(*args, **kwargs)
                with span(
                    run_name,
                    run_type=run_type,
                    inputs=_call_inputs(args, kwargs),
                    tags=tags,
                    metadata=metadata,
                ) as sp:
                    result = await fn(*args, **kwargs)
                    sp.end(outputs=result)
                    return result

            return async_wrapper

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not is_enabled():
                return fn(*args, **kwargs)
            with span(
                run_name,
                run_type=run_type,
                inputs=_call_inputs(args, kwargs),
                tags=tags,
                metadata=metadata,
            ) as sp:
                result = fn(*args, **kwargs)
                sp.end(outputs=result)
                return result

        return wrapper

    return decorator


def llm_span(
    *,
    provider: str,
    model: str,
    prompt: Any,
    system: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
):
    """Span for a raw HTTP LLM call (Gemini / OpenAI REST) — run_type='llm'."""
    inputs: dict[str, Any] = {"model": model, "provider": provider, "prompt": prompt}
    if system:
        inputs["system"] = system
    return span(
        f"{provider}:{model}",
        run_type="llm",
        inputs=inputs,
        tags=(tags or []) + ["llm", provider],
        metadata={**(metadata or {}), "provider": provider, "model": model},
    )


def wrap_openai(client: Any) -> Any:
    """Wrap an OpenAI SDK client so every call is traced. Returns client as-is on failure."""
    if not is_enabled():
        return client
    try:
        from langsmith.wrappers import wrap_openai as _wrap

        return _wrap(client)
    except Exception:
        return client


def flush() -> None:
    """Best-effort flush of queued traces (serverless / short-lived processes)."""
    if not is_enabled():
        return
    try:
        from langsmith import Client

        Client().flush()
    except Exception:
        return
