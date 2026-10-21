"""Knowledge Freshness Engine (KFE) — every KO knows when it was last updated."""

__all__ = ["KnowledgeFreshnessEngine", "evaluate_object_freshness", "format_age"]


def __getattr__(name: str):
    if name in {"KnowledgeFreshnessEngine", "evaluate_object_freshness", "format_age"}:
        from app.kfe import engine as _engine

        return getattr(_engine, name)
    raise AttributeError(name)
