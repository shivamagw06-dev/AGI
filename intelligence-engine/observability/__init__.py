"""AGI Observability — LangSmith tracing (observability only; never changes answers)."""

from observability.production import dashboard, status, verify
from observability.schema import (
    COMPANY,
    MODULE_CODE,
    OBSERVABILITY_VERSION,
    PROGRAMME,
    config,
    is_enabled,
)
from observability.tracing import flush, llm_span, span, traced, wrap_openai

__all__ = [
    "OBSERVABILITY_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "COMPANY",
    "config",
    "is_enabled",
    "span",
    "traced",
    "llm_span",
    "wrap_openai",
    "flush",
    "status",
    "dashboard",
    "verify",
]
