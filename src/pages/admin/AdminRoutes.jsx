import React, { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import RequireAdmin from '@/components/admin/RequireAdmin';
import AdminLayout from '@/pages/admin/AdminLayout';

const AdminDashboard = lazy(() => import('@/pages/admin/Dashboard'));
const ArticleEditor = lazy(() => import('@/pages/admin/ArticleEditor'));
const CategoryManager = lazy(() => import('@/pages/admin/CategoryManager'));
const KnowledgeFoundation = lazy(() => import('@/pages/admin/KnowledgeFoundation'));
const OpenIntelligence = lazy(() => import('@/pages/admin/OpenIntelligence'));
const Evidence = lazy(() => import('@/pages/admin/Evidence'));
const InvestmentIntelligence = lazy(() => import('@/pages/admin/InvestmentIntelligence'));
const Forecasting = lazy(() => import('@/pages/admin/Forecasting'));
const Events = lazy(() => import('@/pages/admin/Events'));
const ContextAssembly = lazy(() => import('@/pages/admin/ContextAssembly'));
const IntelligenceBus = lazy(() => import('@/pages/admin/IntelligenceBus'));
const Valuation = lazy(() => import('@/pages/admin/Valuation'));
const Models = lazy(() => import('@/pages/admin/Models'));
const FinanceAcademy = lazy(() => import('@/pages/admin/FinanceAcademy'));
const LiveEvidence = lazy(() => import('@/pages/admin/LiveEvidence'));
const CompanyDossiers = lazy(() => import('@/pages/admin/CompanyDossiers'));
const YahooProvider = lazy(() => import('@/pages/admin/YahooProvider'));
const DataQuality = lazy(() => import('@/pages/admin/DataQuality'));
const EvidenceCompletion = lazy(() => import('@/pages/admin/EvidenceCompletion'));
const CompanyAnalysis = lazy(() => import('@/pages/admin/CompanyAnalysis'));
const CompanyMonitor = lazy(() => import('@/pages/admin/CompanyMonitor'));
const InvestmentOfficeAdmin = lazy(() => import('@/pages/admin/InvestmentOffice'));
const MissionControl = lazy(() => import('@/pages/admin/MissionControl'));
const InstitutionalStack = lazy(() => import('@/pages/admin/InstitutionalStack'));
const ReleaseHealth = lazy(() => import('@/pages/admin/ReleaseHealth'));
const AccountingIntelligence = lazy(() => import('@/pages/admin/AccountingIntelligence'));
const FinancialStatementsEngine = lazy(() => import('@/pages/admin/FinancialStatementsEngine'));
const FinancialKnowledgeBase = lazy(() => import('@/pages/admin/FinancialKnowledgeBase'));
const PortfolioIntelligence = lazy(() => import('@/pages/admin/PortfolioIntelligence'));
const CausalIntelligence = lazy(() => import('@/pages/admin/CausalIntelligence'));
const ForecastIntelligence = lazy(() => import('@/pages/admin/ForecastIntelligence'));
const KnowledgeGraph = lazy(() => import('@/pages/admin/KnowledgeGraph'));
const InstitutionalMemory = lazy(() => import('@/pages/admin/InstitutionalMemory'));
const SimulationLab = lazy(() => import('@/pages/admin/SimulationLab'));
const DecisionEngineV2 = lazy(() => import('@/pages/admin/DecisionEngineV2'));
const InstitutionalIntelligence = lazy(() => import('@/pages/admin/InstitutionalIntelligence'));
const IntelligenceMap = lazy(() => import('@/pages/admin/IntelligenceMap'));
const IntentIntelligence = lazy(() => import('@/pages/admin/IntentIntelligence'));
const EntityResolution = lazy(() => import('@/pages/admin/EntityResolution'));
const ResearchPlanner = lazy(() => import('@/pages/admin/ResearchPlanner'));
const AnalystRouter = lazy(() => import('@/pages/admin/AnalystRouter'));
const ContextIntelligence = lazy(() => import('@/pages/admin/ContextIntelligence'));
const LayerRouter = lazy(() => import('@/pages/admin/LayerRouter'));
const AcquisitionPlanner = lazy(() => import('@/pages/admin/AcquisitionPlanner'));
const BlueprintEngine = lazy(() => import('@/pages/admin/BlueprintEngine'));
const ValidationEngine = lazy(() => import('@/pages/admin/ValidationEngine'));
const ResearchExecution = lazy(() => import('@/pages/admin/ResearchExecution'));
const HypothesisEngine = lazy(() => import('@/pages/admin/HypothesisEngine'));
const ResearchQuestions = lazy(() => import('@/pages/admin/ResearchQuestions'));
const HypothesisTesting = lazy(() => import('@/pages/admin/HypothesisTesting'));
const BeliefEngine = lazy(() => import('@/pages/admin/BeliefEngine'));
const ThesisConstruction = lazy(() => import('@/pages/admin/ThesisConstruction'));
const InstitutionalDebate = lazy(() => import('@/pages/admin/InstitutionalDebate'));
const DecisionReadiness = lazy(() => import('@/pages/admin/DecisionReadiness'));
const ReasoningAudit = lazy(() => import('@/pages/admin/ReasoningAudit'));
const KnowledgeOperations = lazy(() => import('@/pages/admin/KnowledgeOperations'));
const ValuationIntelligence = lazy(() => import('@/pages/admin/ValuationIntelligence'));
const ValuationTerminal = lazy(() => import('@/pages/admin/ValuationTerminal'));
const DataWarehouse = lazy(() => import('@/pages/admin/DataWarehouse'));
const HistoricalCoverage = lazy(() => import('@/pages/admin/HistoricalCoverage'));
const UpstoxBootstrap = lazy(() => import('@/pages/admin/UpstoxBootstrap'));
const UpstoxFundamentals = lazy(() => import('@/pages/admin/UpstoxFundamentals'));
const ValuationPolicy = lazy(() => import('@/pages/admin/ValuationPolicy'));
const HistoricalValuation = lazy(() => import('@/pages/admin/HistoricalValuation'));
const HvieRuntime = lazy(() => import('@/pages/admin/HvieRuntime'));
const FinancialWarehouse = lazy(() => import('@/pages/admin/FinancialWarehouse'));
const FinancialCoverage = lazy(() => import('@/pages/admin/FinancialCoverage'));
const CompanyFinancials = lazy(() => import('@/pages/admin/CompanyFinancials'));
const ResearchIntelligence = lazy(() => import('@/pages/admin/ResearchIntelligence'));
const ForecastRuntime = lazy(() => import('@/pages/admin/ForecastRuntime'));
const MacroRuntime = lazy(() => import('@/pages/admin/MacroRuntime'));
const IfacComposer = lazy(() => import('@/pages/admin/IfacComposer'));
const AskProductQuality = lazy(() => import('@/pages/admin/AskProductQuality'));
const KulDashboard = lazy(() => import('@/pages/admin/KulDashboard'));
const MarketResearchNote = lazy(() => import('@/pages/admin/MarketResearchNote'));
const StrategyLab = lazy(() => import('@/pages/admin/StrategyLab'));
const IntelligenceCmsRoutes = lazy(() => import('@/pages/admin/intelligence/IntelligenceCmsRoutes'));

function AdminPageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center bg-[#0b0e14] p-8 text-center text-sm text-slate-400">
      Loading admin…
    </div>
  );
}

export default function AdminRoutes() {
  return (
    <RequireAdmin>
      <Suspense fallback={<AdminPageFallback />}>
        <Routes>
          {/* Full-bleed Institutional Knowledge Operations Center — not CMS chrome */}
          <Route path="knowledge-operations" element={<KnowledgeOperations />} />
          {/* Full-bleed Valuation Intelligence — Institutional Consensus Dashboard */}
          <Route path="valuation-intelligence" element={<ValuationIntelligence />} />
          {/* Full-bleed Institutional Valuation Terminal */}
          <Route path="valuation-terminal" element={<ValuationTerminal />} />
          {/* Full-bleed Institutional Data Warehouse — the workbook every engine reads */}
          <Route path="data-warehouse" element={<DataWarehouse />} />
          <Route path="sector-evidence-audit" element={<DataWarehouse initialTabId="sector_evidence_matrix" focused />} />
          {/* Full-bleed Historical Coverage — how deep the warehouse actually goes */}
          <Route path="historical-coverage" element={<HistoricalCoverage />} />
          {/* Full-bleed Upstox full-universe valuation bootstrap (Phase 7.4d) */}
          <Route path="upstox-bootstrap" element={<UpstoxBootstrap />} />
          {/* Full-bleed Upstox Institutional Fundamentals Integration (Phase 7.4E) */}
          <Route path="upstox-fundamentals" element={<UpstoxFundamentals />} />
          {/* Full-bleed Valuation Policy & Applicability Engine (Phase 8.2A) */}
          <Route path="valuation-policy" element={<ValuationPolicy />} />
          {/* Full-bleed Historical Valuation Intelligence Engine (Phase 8.3) */}
          <Route path="historical-valuation" element={<HistoricalValuation />} />
          <Route path="hvie-runtime" element={<HvieRuntime />} />
          {/* Full-bleed Financial Warehouse Completion (Phase 7.4F) */}
          <Route path="financial-warehouse" element={<FinancialWarehouse />} />
          {/* Phase 7.4F Step 0 — read-only financial coverage audit */}
          <Route path="financial-coverage" element={<FinancialCoverage />} />
          <Route path="research-intelligence" element={<ResearchIntelligence />} />
          <Route path="forecast-runtime" element={<ForecastRuntime />} />
          <Route path="macro-runtime" element={<MacroRuntime />} />
          <Route path="market-research-note" element={<MarketResearchNote />} />
          <Route path="strategy-lab" element={<StrategyLab />} />
          <Route path="ifac" element={<IfacComposer />} />
          <Route path="aqe" element={<AskProductQuality />} />
          <Route path="kul" element={<KulDashboard />} />
          {/* Full-bleed Institutional Morning Office — daily investment desk */}
          <Route path="investment-office" element={<InvestmentOfficeAdmin />} />
          {/* Intelligence CMS — structured data modules (Valuation Monitor first) */}
          <Route path="intelligence/*" element={<IntelligenceCmsRoutes />} />
          <Route element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="company-financials" element={<CompanyFinancials />} />
            <Route path="articles" element={<AdminDashboard />} />
            <Route path="articles/new" element={<ArticleEditor />} />
            <Route path="articles/edit/:slug" element={<ArticleEditor />} />
            <Route path="categories" element={<CategoryManager />} />
            <Route path="knowledge" element={<KnowledgeFoundation />} />
            <Route path="open-intelligence" element={<OpenIntelligence />} />
            <Route path="evidence" element={<Evidence />} />
            <Route path="live-evidence" element={<LiveEvidence />} />
            <Route path="company-dossiers" element={<CompanyDossiers />} />
            <Route path="yahoo-provider" element={<YahooProvider />} />
            <Route path="data-quality" element={<DataQuality />} />
            <Route path="evidence-completion" element={<EvidenceCompletion />} />
            <Route path="company-analysis" element={<CompanyAnalysis />} />
            <Route path="institutional-stack" element={<InstitutionalStack />} />
            <Route path="release-health" element={<ReleaseHealth />} />
            <Route path="accounting-intelligence" element={<AccountingIntelligence />} />
            <Route path="financial-statements" element={<FinancialStatementsEngine />} />
            <Route path="financial-knowledge" element={<FinancialKnowledgeBase />} />
            <Route path="portfolio-intelligence" element={<PortfolioIntelligence />} />
            <Route path="causal-intelligence" element={<CausalIntelligence />} />
            <Route path="forecast-intelligence" element={<ForecastIntelligence />} />
            <Route path="knowledge-graph" element={<KnowledgeGraph />} />
            <Route path="institutional-memory" element={<InstitutionalMemory />} />
            <Route path="simulation-lab" element={<SimulationLab />} />
            <Route path="decision-engine-v2" element={<DecisionEngineV2 />} />
            <Route path="institutional-intelligence" element={<InstitutionalIntelligence />} />
            <Route path="company-monitor" element={<CompanyMonitor />} />
            <Route path="mission-control" element={<MissionControl />} />
            <Route path="intelligence-map" element={<IntelligenceMap />} />
            <Route path="intent-intelligence" element={<IntentIntelligence />} />
            <Route path="entity-resolution" element={<EntityResolution />} />
            <Route path="research-planner" element={<ResearchPlanner />} />
            <Route path="context-intelligence" element={<ContextIntelligence />} />
            <Route path="analyst-router" element={<AnalystRouter />} />
            <Route path="layer-router" element={<LayerRouter />} />
            <Route path="acquisition-planner" element={<AcquisitionPlanner />} />
            <Route path="blueprint-engine" element={<BlueprintEngine />} />
            <Route path="validation-engine" element={<ValidationEngine />} />
            <Route path="research-execution" element={<ResearchExecution />} />
            <Route path="hypothesis-engine" element={<HypothesisEngine />} />
            <Route path="research-questions" element={<ResearchQuestions />} />
            <Route path="hypothesis-testing" element={<HypothesisTesting />} />
            <Route path="belief-engine" element={<BeliefEngine />} />
            <Route path="thesis-construction" element={<ThesisConstruction />} />
            <Route path="institutional-debate" element={<InstitutionalDebate />} />
            <Route path="decision-readiness" element={<DecisionReadiness />} />
            <Route path="reasoning-audit" element={<ReasoningAudit />} />
            <Route path="system" element={<MissionControl />} />
            <Route path="investment-intelligence" element={<InvestmentIntelligence />} />
            <Route path="forecasting" element={<Forecasting />} />
            <Route path="events" element={<Events />} />
            <Route path="context" element={<ContextAssembly />} />
            <Route path="intelligence-bus" element={<IntelligenceBus />} />
            <Route path="valuation" element={<Valuation />} />
            <Route path="models" element={<Models />} />
            <Route path="academy" element={<FinanceAcademy />} />
            <Route path="*" element={<Navigate to="/admin" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </RequireAdmin>
  );
}
