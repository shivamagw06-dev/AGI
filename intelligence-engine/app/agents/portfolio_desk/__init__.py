"""Portfolio Office packaging agents — register on import."""

from app.agents.portfolio_desk import health as health  # noqa: F401
from app.agents.portfolio_desk import recommendations as recommendations  # noqa: F401
from app.agents.portfolio_desk import risk as risk  # noqa: F401
from app.agents.portfolio_desk import summary as summary  # noqa: F401

__all__ = ["health", "risk", "recommendations", "summary"]
