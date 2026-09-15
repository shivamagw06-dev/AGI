"""Financial Intelligence Model Library (FIML) v1.0 — shared institutional domain models.

FIML is NOT an intelligence engine. It is a reusable library consumed by existing engines.
"""

from models.registry import ModelRegistry, get_registry

__all__ = ["ModelRegistry", "get_registry"]
