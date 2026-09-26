"""Phase 1 Institutional Acceptance Test — baseline qualification exam."""

from institutional_evaluation_lab.iat.production import health, run_iat
from institutional_evaluation_lab.iat.schema import IAT_VERSION, PROGRAMME

__all__ = ["IAT_VERSION", "PROGRAMME", "health", "run_iat"]
