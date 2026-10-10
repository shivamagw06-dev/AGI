"""KUL knowledge providers — thin wrappers over existing engines. No new knowledge."""

from __future__ import annotations

from knowledge_unification.providers.academy import AcademyProvider
from knowledge_unification.providers.business_intelligence import BusinessIntelligenceProvider
from knowledge_unification.providers.capiq_ikt import CapIqIktProvider
from knowledge_unification.providers.cgl import ContinuousGatherProvider
from knowledge_unification.providers.company_memory import CompanyMemoryProvider
from knowledge_unification.providers.financial_concepts import FinancialConceptsProvider
from knowledge_unification.providers.financial_foundations import FinancialFoundationsProvider
from knowledge_unification.providers.financial_statement_intelligence import (
    FinancialStatementIntelligenceProvider,
)
from knowledge_unification.providers.financial_statement_warehouse import (
    FinancialStatementWarehouseProvider,
)
from knowledge_unification.providers.hedge_fund_screens import HedgeFundScreenProvider
from knowledge_unification.providers.historical_intelligence import (
    HistoricalIntelligenceProvider,
)
from knowledge_unification.providers.historical_valuation_intelligence import (
    HistoricalValuationIntelligenceProvider,
)
from knowledge_unification.providers.ikl import IklProvider
from knowledge_unification.providers.institutional_warehouse import (
    InstitutionalWarehouseProvider,
)
from knowledge_unification.providers.industry_intelligence import IndustryIntelligenceProvider
from knowledge_unification.providers.investment_intelligence import InvestmentIntelligenceProvider
from knowledge_unification.providers.knowledge_factory import KnowledgeFactoryProvider
from knowledge_unification.providers.legacy_kip import LegacyKipProvider
from knowledge_unification.providers.market_intelligence_engine import (
    MarketIntelligenceEngineProvider,
)
from knowledge_unification.providers.portfolio_intelligence import PortfolioIntelligenceProvider
from knowledge_unification.providers.research_intelligence import ResearchIntelligenceProvider
from knowledge_unification.providers.research_intelligence_engine import (
    ResearchIntelligenceEngineProvider,
)
from knowledge_unification.providers.forecast_intelligence_engine import (
    ForecastIntelligenceEngineProvider,
)
from knowledge_unification.providers.macro_intelligence_engine import (
    MacroIntelligenceEngineProvider,
)
from knowledge_unification.providers.unified_valuation_engine import (
    UnifiedValuationEngineProvider,
)
from knowledge_unification.providers.valuation_attribution_engine import (
    ValuationAttributionEngineProvider,
)
from knowledge_unification.providers.valuation_consensus import ValuationConsensusProvider
from knowledge_unification.providers.valuation_policy_engine import (
    ValuationPolicyEngineProvider,
)
from knowledge_unification.providers.valuation_terminal import ValuationTerminalProvider

ALL_PROVIDERS = (
    HistoricalIntelligenceProvider,
    HistoricalValuationIntelligenceProvider,
    UnifiedValuationEngineProvider,
    ValuationAttributionEngineProvider,
    ValuationPolicyEngineProvider,
    MarketIntelligenceEngineProvider,
    MacroIntelligenceEngineProvider,
    ResearchIntelligenceEngineProvider,
    ForecastIntelligenceEngineProvider,
    InstitutionalWarehouseProvider,
    ResearchIntelligenceProvider,
    PortfolioIntelligenceProvider,
    InvestmentIntelligenceProvider,
    IndustryIntelligenceProvider,
    BusinessIntelligenceProvider,
    ValuationConsensusProvider,
    ValuationTerminalProvider,
    HedgeFundScreenProvider,
    FinancialStatementWarehouseProvider,
    CapIqIktProvider,
    IklProvider,
    CompanyMemoryProvider,
    KnowledgeFactoryProvider,
    ContinuousGatherProvider,
    FinancialConceptsProvider,
    FinancialFoundationsProvider,
    FinancialStatementIntelligenceProvider,
    AcademyProvider,
    LegacyKipProvider,
)

__all__ = ["ALL_PROVIDERS"]
