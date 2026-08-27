"""FKB-01 — Institutional Financial Knowledge Base."""

from financial_knowledge.production import dashboard, health
from financial_knowledge.registry import knowledge

__all__ = ["knowledge", "health", "dashboard"]
