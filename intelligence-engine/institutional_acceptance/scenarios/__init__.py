"""PAT-01 scenario phases (P01–P12, plus shared case helpers)."""

from __future__ import annotations

from institutional_acceptance.scenarios.ask_agi import run_ask_agi
from institutional_acceptance.scenarios.data_layer import run_data_layer
from institutional_acceptance.scenarios.intelligence import run_intelligence
from institutional_acceptance.scenarios.knowledge_graph import run_knowledge_graph
from institutional_acceptance.scenarios.multi_portfolio import run_multi_portfolio
from institutional_acceptance.scenarios.observability import run_observability
from institutional_acceptance.scenarios.performance import run_performance
from institutional_acceptance.scenarios.publishing import run_publishing
from institutional_acceptance.scenarios.rc01 import run_rc01
from institutional_acceptance.scenarios.research_workspace import run_research_workspace
from institutional_acceptance.scenarios.security import run_security
from institutional_acceptance.scenarios.system_boot import run_system_boot

PHASE_RUNNERS = {
    "system_boot": run_system_boot,
    "data_layer": run_data_layer,
    "knowledge_graph": run_knowledge_graph,
    "intelligence": run_intelligence,
    "ask_agi": run_ask_agi,
    "research_workspace": run_research_workspace,
    "publishing": run_publishing,
    "multi_portfolio": run_multi_portfolio,
    "security": run_security,
    "performance": run_performance,
    "observability": run_observability,
    "rc01": run_rc01,
}

__all__ = ["PHASE_RUNNERS"]
