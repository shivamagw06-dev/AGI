from __future__ import annotations

from typing import Type

from app.agents.base import BaseAgent
from app.core.logging import get_logger

log = get_logger(__name__)

_REGISTRY: dict[str, Type[BaseAgent]] = {}
_INSTANCES: dict[str, BaseAgent] = {}


def register_agent(cls: Type[BaseAgent]) -> Type[BaseAgent]:
    agent_id = getattr(cls, "agent_id", None)
    if not agent_id:
        raise ValueError(f"Agent class {cls.__name__} missing agent_id")
    _REGISTRY[agent_id] = cls
    return cls


def get_agent(agent_id: str) -> BaseAgent:
    if agent_id not in _INSTANCES:
        if agent_id not in _REGISTRY:
            raise KeyError(f"Unknown agent: {agent_id}")
        _INSTANCES[agent_id] = _REGISTRY[agent_id]()
    return _INSTANCES[agent_id]


def list_agents() -> list[str]:
    return sorted(_REGISTRY.keys())


def bootstrap_registry() -> None:
    # Import side-effects register agents
    from app.agents import stubs  # noqa: F401
    from app.agents.cio_desk import news_analyst, macro_economist, market_analyst, risk_manager  # noqa: F401
    from app.agents.cio_synthesizer import ChiefInvestmentOfficer  # noqa: F401
    from app.agents import portfolio_desk  # noqa: F401
    from app.agents import investment_office_desk  # noqa: F401

    log.info("agent_registry_ready", extra={"agents": list_agents()})
