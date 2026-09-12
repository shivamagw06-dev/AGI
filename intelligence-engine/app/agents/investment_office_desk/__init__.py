"""Investment Office packaging agents — register on import."""

from app.agents.investment_office_desk import brief as brief  # noqa: F401
from app.agents.investment_office_desk import knowledge as knowledge  # noqa: F401
from app.agents.investment_office_desk import queue_calendar as queue_calendar  # noqa: F401
from app.agents.investment_office_desk import summary as summary  # noqa: F401

__all__ = ["brief", "queue_calendar", "knowledge", "summary"]
