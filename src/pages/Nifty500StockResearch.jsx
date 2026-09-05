import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, BrainCircuit, CalendarClock, ShieldAlert } from 'lucide-react';
import { getNifty500StockResearch } from '@/lib/nifty500ResearchApi';
import { getUiCompany } from '@/lib/uiApi';
import { getInstitutionalStackCompany } from '@/lib/intelligenceApi';
import CompanyIntelligencePanels from '@/components/Company/CompanyIntelligencePanels';
import CompanyValuationPanel from '@/components/Company/CompanyValuationPanel';

function tone(sentiment = '') {
  if (/bullish/i.test(sentiment)) return 'bg-[#ecfdf3] text-[#087443] border-[#b7ebcc]';
  if (/bearish/i.test(sentiment)) return 'bg-[#fff1f0] text-[#b42318] border-[#f7c5c0]';
  return 'bg-[#fff8e8] text-[#966a00] border-[#f4d99d]';
}

function AnalysisCard({ title, children }) {
  return (
    <article className="border border-[#dde1e6] bg-white p-5">
      <h2 className="text-sm font-bold text-[#18202b]">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-[#4b5563]">{children}</p>
    </article>
  );
}

function FactorList({ title, items, danger = false }) {
  return (
    <article className="border border-[#dde1e6] bg-white p-5">
      <h2 className="text-sm font-bold text-[#18202b]">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm leading-relaxed text-[#4b5563]">
        {(items || []).map((item) => <li key={item} className="flex gap-2"><span className={danger ? 'text-[#b42318]' : 'text-[#087443]'}>•</span><span>{item}</span></li>)}
      </ul>
    </article>
  );
}

export default function Nifty500StockResearch() {
  const { symbol } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [companyIntel, setCompanyIntel] = useState(null);

  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: null });
    setCompanyIntel(null);
    getNifty500StockResearch(symbol)
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    Promise.allSettled([
      getUiCompany(symbol),
      getInstitutionalStackCompany(symbol).catch(() => null),
    ]).then(([uiRes, stackRes]) => {
      if (!active) return;
      const ui = uiRes.status === 'fulfilled' ? uiRes.value : null;
      const stack = stackRes.status === 'fulfilled' ? stackRes.value : null;
      if (!ui && !stack) {
        setCompanyIntel(null);
        return;
      }
      setCompanyIntel({
        ...(ui || { ticker: String(symbol || '').toUpperCase() }),
        institutional_stack: stack || undefined,
        management_trust: stack?.summary
          ? {
              dna: stack.summary.management_dna,
              confidence: stack.summary.management_confidence,
              source: 'management_intelligence',
            }
          : undefined,
        accounting_trust: stack?.summary
          ? {
              behaviour: stack.summary.accounting_behaviour,
              confidence: stack.summary.accounting_confidence,
              quality_score: stack.summary.accounting_quality_score,
              manipulation_risk: stack.summary.manipulation_risk,
              source: 'accounting_intelligence',
            }
          : undefined,
        portfolio_fit: stack?.summary
          ? {
              net_effect: stack.summary.portfolio_net_effect,
              portfolio_quality: stack.summary.portfolio_quality,
              grade: stack.summary.portfolio_grade,
              fit: stack.summary.portfolio_fit,
              portfolio_id: stack.summary.portfolio_id,
              source: 'portfolio_intelligence',
            }
          : undefined,
        causal_why: stack?.summary
          ? {
              summary: stack.summary.causal_why,
              upstream: stack.summary.causal_upstream,
              confidence: stack.summary.causal_confidence,
              source: 'causal_intelligence',
            }
          : undefined,
        forecast_path: stack?.summary
          ? {
              most_likely: stack.summary.forecast_most_likely,
              confidence: stack.summary.forecast_confidence,
              distribution: stack.summary.forecast_distribution,
              summary: stack.summary.forecast_summary,
              source: 'forecast_intelligence',
            }
          : undefined,
        knowledge_links: stack?.summary
          ? {
              count: stack.summary.knowledge_relationship_count,
              confidence: stack.summary.knowledge_confidence,
              canonical_id: stack.summary.knowledge_canonical_id,
              summary: stack.summary.knowledge_summary,
              source: 'knowledge_graph',
            }
          : undefined,
        institutional_learning: stack?.summary
          ? {
              lesson_count: stack.summary.memory_lesson_count,
              mistake_count: stack.summary.memory_mistake_count,
              thinking_improved: stack.summary.memory_thinking_improved,
              summary: stack.summary.memory_summary,
              source: 'institutional_memory',
            }
          : undefined,
        simulation_lab: stack?.summary
          ? {
              scenario_id: stack.summary.simulation_scenario_id,
              expected_return: stack.summary.simulation_expected_return,
              confidence: stack.summary.simulation_confidence,
              summary: stack.summary.simulation_summary,
              source: 'simulation_lab',
            }
          : undefined,
        decision_engine_v2: stack?.summary
          ? {
              recommendation_status: stack.summary.decision_status,
              confidence: stack.summary.decision_confidence,
              audit_id: stack.summary.decision_audit_id,
              summary: stack.summary.decision_summary,
              source: 'decision_engine_v2',
            }
          : undefined,
      });
    });
    return () => {
      active = false;
    };
  }, [symbol]);

  const research = state.data?.research;
  const run = state.data?.run;

  return (
    <div className="min-h-screen bg-[#f8fafb]">
      <Helmet>
        <title>{research ? `${research.symbol} Research | AGI` : 'Nifty 500 Research | AGI'}</title>
        <meta name="description" content="AGI’s derived technical research for Nifty 500 companies. Informational only, not investment advice." />
      </Helmet>
      <main className="mx-auto max-w-[1200px] px-4 py-7 sm:px-6 sm:py-10">
        <Link to="/india-stock-intelligence" className="inline-flex items-center gap-2 text-xs font-bold text-[#274c77] hover:underline">
          <ArrowLeft className="h-4 w-4" /> Back to India Stock Intelligence
        </Link>

        {state.loading && !companyIntel ? (
          <div className="mt-6 h-72 animate-pulse border border-[#dde1e6] bg-white" />
        ) : (
          <>
            <section className="mt-6 border border-[#dde1e6] bg-white p-5 sm:p-8">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[#274c77]">
                    <BrainCircuit className="h-4 w-4" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.12em]">
                      {research ? 'Nifty 500 technical research' : 'Company intelligence'}
                    </span>
                  </div>
                  <h1 className="mt-3 text-3xl font-bold tracking-tight text-[#18202b]">
                    {research?.symbol || symbol?.toUpperCase()}
                  </h1>
                  <p className="mt-2 text-sm text-[#667085]">
                    {research
                      ? 'Derived market-structure assessment, updated after the latest completed research run.'
                      : 'Institutional house view, market intelligence, evidence and portfolio context.'}
                  </p>
                </div>
                {research?.overallSentiment && (
                  <span className={`w-fit border px-3 py-2 text-xs font-bold uppercase tracking-wide ${tone(research.overallSentiment)}`}>
                    {research.overallSentiment}
                  </span>
                )}
              </div>
              {research && (
                <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="border border-[#edf0f2] p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Research score</p><p className="mt-1 text-xl font-bold text-[#18202b]">{research.agiResearchScore}/100</p></div>
                  <div className="border border-[#edf0f2] p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Model confidence</p><p className="mt-1 text-xl font-bold text-[#18202b]">{research.aiConfidencePercent}%</p></div>
                  <div className="border border-[#edf0f2] p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Research updated</p><p className="mt-1 flex items-center gap-1 text-xs font-bold text-[#18202b]"><CalendarClock className="h-3.5 w-3.5" />{new Date(research.lastUpdated).toLocaleDateString('en-IN')}</p></div>
                </div>
              )}
            </section>

            <CompanyValuationPanel symbol={symbol} />

            <CompanyIntelligencePanels data={companyIntel} />

            {research ? (
              <>
                <section className="mt-6 border-l-4 border-[#274c77] bg-white p-5">
                  <h2 className="text-sm font-bold text-[#18202b]">AGI Research Summary</h2>
                  <p className="mt-3 whitespace-pre-line text-sm leading-7 text-[#374151]">{research.researchSummary}</p>
                </section>

                <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <AnalysisCard title="Trend Analysis">{research.trendAnalysis}</AnalysisCard>
                  <AnalysisCard title="Momentum Analysis">{research.momentumAnalysis}</AnalysisCard>
                  <AnalysisCard title="Volume Analysis">{research.volumeAnalysis}</AnalysisCard>
                  <AnalysisCard title="Volatility Analysis">{research.volatilityAnalysis}</AnalysisCard>
                  <AnalysisCard title="Market Structure">{research.marketStructureAnalysis}</AnalysisCard>
                  <AnalysisCard title="Relative Strength">{research.relativeStrengthAnalysis}</AnalysisCard>
                  <FactorList title="Supporting Factors" items={research.supportingFactors} />
                  <FactorList title="Risk Factors" items={research.riskFactors} danger />
                </section>

                <section className="mt-6 border border-[#dde1e6] bg-white p-5">
                  <h2 className="text-sm font-bold text-[#18202b]">Key Observations</h2>
                  <ul className="mt-3 grid grid-cols-1 gap-2 text-sm text-[#4b5563] sm:grid-cols-2">
                    {(research.keyObservations || []).map((item) => <li key={item} className="border border-[#edf0f2] p-3">{item}</li>)}
                  </ul>
                </section>
              </>
            ) : !companyIntel ? (
              <section className="mt-6 border border-dashed border-[#cbd2da] bg-white p-8 text-center">
                <ShieldAlert className="mx-auto h-6 w-6 text-[#966a00]" />
                <h1 className="mt-3 text-xl font-bold text-[#18202b]">Research record unavailable</h1>
                <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-[#667085]">
                  This symbol does not yet have a published technical research record or live company intelligence pack.
                </p>
              </section>
            ) : null}

            <section className="mt-6 border border-[#f2d7a0] bg-[#fffaf0] p-5 text-xs leading-relaxed text-[#6f5a2e]">
              <p className="font-bold uppercase tracking-wide">Important disclosure</p>
              <p className="mt-2">{run?.disclaimer || 'This research is for informational purposes only. It is not investment advice or a recommendation to buy or sell securities.'}</p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
