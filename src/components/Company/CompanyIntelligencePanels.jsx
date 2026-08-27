/**
 * Flagship company intelligence panels — extends existing page styling.
 * Does not expose internal engine names.
 */
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import { trackProductEvent } from '@/lib/productAnalytics';
import { trackFirstMeaningfulAction } from '@/lib/funnelAnalytics';

function Card({ title, children }) {
  return (
    <article className="border border-[#dde1e6] bg-white p-5">
      <h2 className="text-sm font-bold text-[#18202b]">{title}</h2>
      <div className="mt-2 text-sm leading-relaxed text-[#4b5563]">{children}</div>
    </article>
  );
}

function asText(value) {
  if (value == null) return null;
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return String(value);
  if (typeof value === 'object') {
    return (
      value.label ||
      value.summary ||
      value.thesis ||
      value.regime ||
      value.risk_level ||
      value.status ||
      null
    );
  }
  return null;
}

function DocList({ items }) {
  const rows = (items || []).slice(0, 5);
  if (!rows.length) return <p className="text-xs text-[#929292]">No items yet.</p>;
  return (
    <ul className="space-y-2">
      {rows.map((item, idx) => (
        <li key={item.id || item.title || idx} className="border-b border-[#edf0f2] pb-2 last:border-0">
          <p className="text-sm font-bold text-[#18202b]">{item.title || item.id || String(item)}</p>
          {item.snippet && <p className="text-xs text-[#667085] mt-1 line-clamp-2">{item.snippet}</p>}
        </li>
      ))}
    </ul>
  );
}

export default function CompanyIntelligencePanels({ data }) {
  useEffect(() => {
    if (data?.ticker) {
      trackProductEvent('company_viewed', { ticker: data.ticker });
      trackFirstMeaningfulAction('company_analysis_opened', { ticker: data.ticker });
    }
  }, [data?.ticker]);

  if (!data) return null;
  const overview = data.overview || {};
  const mi = data.market_intelligence || {};
  const research = data.research || {};
  const evidence = data.evidence || {};
  const portfolio = data.portfolio || {};
  const meta = data.product_meta || {};
  const valuation = data.valuation_snapshot || {};
  const kg = data.knowledge_graph?.buckets || {};

  const intelRows = [
    ['Technical Summary', asText(mi.technical_summary)],
    ['Fundamental Summary', asText(mi.fundamental_summary)],
    ['Macro Context', asText(mi.macro_context)],
    ['Risk Summary', asText(mi.risk_summary)],
    ['Volatility Summary', asText(mi.volatility_summary)],
    ['Trend Summary', asText(mi.trend_summary)],
    ['Event Summary', asText(mi.event_summary)],
    ['Sentiment Summary', asText(mi.sentiment_summary)],
  ].filter(([, v]) => v);

  return (
    <div className="mt-6 space-y-6">
      <section className="border border-[#dde1e6] bg-white p-5 sm:p-8">
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#274c77]">Overview</p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">House View</p>
            <p className="mt-1 text-sm font-bold text-[#18202b]">{overview.house_view || overview.composite_label || 'Under review'}</p>
          </div>
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Confidence</p>
            <p className="mt-1 text-sm font-bold text-[#18202b]">
              {overview.confidence != null
                ? `${Math.round(Number(overview.confidence) * (Number(overview.confidence) <= 1 ? 100 : 1))}%`
                : '—'}
            </p>
          </div>
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Last Updated</p>
            <p className="mt-1 text-sm font-bold text-[#18202b]">{overview.last_updated || meta.last_updated || '—'}</p>
          </div>
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Freshness</p>
            <p className="mt-1 text-sm font-bold text-[#18202b] capitalize">
              {overview.freshness_indicator || meta.freshness_indicator || '—'}
            </p>
          </div>
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Evidence</p>
            <p className="mt-1 text-sm font-bold text-[#18202b]">
              {overview.evidence_count ?? meta.evidence_count ?? 0}
            </p>
          </div>
          <div className="border border-[#edf0f2] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Research</p>
            <p className="mt-1 text-sm font-bold text-[#18202b]">
              {overview.research_count ?? meta.research_count ?? 0}
            </p>
          </div>
        </div>
        {overview.investment_thesis && (
          <div className="mt-5 border-l-4 border-[#274c77] bg-[#f8fafb] p-4">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#737982]">Investment Thesis</p>
            <p className="mt-2 text-sm leading-relaxed text-[#374151]">{overview.investment_thesis}</p>
          </div>
        )}
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card title="What's Changed">
            <DocList
              items={(overview.whats_changed || []).map((x) => ({ title: String(x) }))}
            />
          </Card>
          <Card title="Current Risks">
            <DocList
              items={(overview.current_risks || []).map((x) => ({ title: String(x) }))}
            />
          </Card>
          <Card title="Current Catalysts">
            <DocList
              items={(overview.current_catalysts || []).map((x) => ({ title: String(x) }))}
            />
          </Card>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            to={`/ask?q=${encodeURIComponent(`What is AGI's view on ${data.ticker}?`)}`}
            className="text-xs font-bold text-[#274c77] hover:underline"
          >
            Ask AGI about {data.ticker} →
          </Link>
          <Link to="/predictions" className="text-xs font-bold text-[#274c77] hover:underline">
            Prediction Centre →
          </Link>
          <Link to="/workspace" className="text-xs font-bold text-[#274c77] hover:underline">
            Save to workspace →
          </Link>
        </div>
      </section>

      {(Object.keys(valuation).length > 0 || (data.prediction_timeline || []).length > 0) && (
        <section>
          <h2 className="text-sm font-bold text-[#18202b] mb-3">Valuation & Predictions</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Valuation Snapshot">
              {Object.keys(valuation).length ? (
                <ul className="space-y-1 text-xs">
                  {Object.entries(valuation).slice(0, 8).map(([k, v]) => (
                    <li key={k} className="flex justify-between gap-3 border-b border-[#edf0f2] py-1">
                      <span className="text-[#737982]">{k.replace(/_/g, ' ')}</span>
                      <span className="font-bold text-[#18202b]">{typeof v === 'object' ? asText(v) || '—' : String(v)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[#929292]">Valuation context loads with coverage.</p>
              )}
            </Card>
            <Card title="Prediction Timeline">
              <DocList
                items={(data.prediction_timeline || portfolio.prediction_history || []).map((p) => ({
                  title: `${p.ticker || data.ticker} · ${p.current_status || p.status || 'open'}`,
                  snippet: p.thesis || p.target_horizon || p.horizon || '',
                }))}
              />
            </Card>
          </div>
        </section>
      )}

      {intelRows.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#18202b] mb-3">Market Intelligence</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {intelRows.map(([title, value]) => (
              <Card key={title} title={title}>
                {value}
              </Card>
            ))}
          </div>
        </section>
      )}

      {(data.institutional_stack || data.management_trust || data.accounting_trust) && (
        <section>
          <h2 className="text-sm font-bold text-[#18202b] mb-3">Institutional Intelligence</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card title="Management Trust">
              {data.management_trust?.dna ||
                data.institutional_stack?.summary?.management_dna ||
                '—'}
              {(data.management_trust?.confidence ??
                data.institutional_stack?.summary?.management_confidence) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Score{' '}
                  {data.management_trust?.confidence ??
                    data.institutional_stack?.summary?.management_confidence}
                </p>
              ) : null}
            </Card>
            <Card title="Accounting Trust">
              {data.accounting_trust?.behaviour ||
                data.institutional_stack?.summary?.accounting_behaviour ||
                '—'}
              {(data.accounting_trust?.quality_score ??
                data.institutional_stack?.summary?.accounting_quality_score) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Quality{' '}
                  {data.accounting_trust?.quality_score ??
                    data.institutional_stack?.summary?.accounting_quality_score}
                  {(data.accounting_trust?.manipulation_risk ||
                    data.institutional_stack?.summary?.manipulation_risk)
                    ? ` · ${
                        data.accounting_trust?.manipulation_risk ||
                        data.institutional_stack?.summary?.manipulation_risk
                      }`
                    : ''}
                </p>
              ) : null}
            </Card>
            <Card title="Filing Memory">
              {data.institutional_stack?.summary?.filing_found ? 'Official filings loaded' : 'Building'}
            </Card>
            <Card title="What Changed">
              {data.institutional_stack?.summary?.material_change_signal
                ? 'Material change signal active'
                : 'No material FDI signal'}
            </Card>
            <Card title="Portfolio Fit">
              {data.institutional_stack?.summary?.portfolio_net_effect ||
                data.portfolio_fit?.net_effect ||
                '—'}
              {(data.institutional_stack?.summary?.portfolio_quality ??
                data.portfolio_fit?.portfolio_quality) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  PQE{' '}
                  {data.institutional_stack?.summary?.portfolio_quality ??
                    data.portfolio_fit?.portfolio_quality}
                  {data.institutional_stack?.summary?.portfolio_grade
                    ? ` · grade ${data.institutional_stack.summary.portfolio_grade}`
                    : ''}
                </p>
              ) : null}
            </Card>
            <Card title="Causal Why">
              {data.institutional_stack?.summary?.causal_why ||
                data.causal_why?.summary ||
                (Array.isArray(data.institutional_stack?.summary?.causal_upstream)
                  ? data.institutional_stack.summary.causal_upstream.slice(0, 3).join(' → ')
                  : null) ||
                '—'}
              {data.institutional_stack?.summary?.causal_confidence != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Confidence {data.institutional_stack.summary.causal_confidence}
                </p>
              ) : null}
            </Card>
            <Card title="Forecast Path">
              {data.institutional_stack?.summary?.forecast_most_likely ||
                data.forecast_path?.most_likely ||
                '—'}
              {(data.institutional_stack?.summary?.forecast_confidence ??
                data.forecast_path?.confidence) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Confidence{' '}
                  {data.institutional_stack?.summary?.forecast_confidence ??
                    data.forecast_path?.confidence}
                  {' · not a price target'}
                </p>
              ) : null}
            </Card>
            <Card title="Connected To">
              {data.institutional_stack?.summary?.knowledge_relationship_count != null
                ? `${data.institutional_stack.summary.knowledge_relationship_count} links`
                : data.knowledge_links?.count != null
                  ? `${data.knowledge_links.count} links`
                  : '—'}
              {(data.institutional_stack?.summary?.knowledge_confidence ??
                data.knowledge_links?.confidence) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Confidence{' '}
                  {data.institutional_stack?.summary?.knowledge_confidence ??
                    data.knowledge_links?.confidence}
                </p>
              ) : null}
            </Card>
            <Card title="What We Learned">
              {data.institutional_stack?.summary?.memory_lesson_count != null
                ? `${data.institutional_stack.summary.memory_lesson_count} lessons`
                : data.institutional_learning?.lesson_count != null
                  ? `${data.institutional_learning.lesson_count} lessons`
                  : '—'}
              {(data.institutional_stack?.summary?.memory_mistake_count ??
                data.institutional_learning?.mistake_count) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  {data.institutional_stack?.summary?.memory_mistake_count ??
                    data.institutional_learning?.mistake_count}{' '}
                  classified mistakes
                  {(data.institutional_stack?.summary?.memory_thinking_improved ??
                    data.institutional_learning?.thinking_improved) != null
                    ? ` · thinking ${
                        (
                          data.institutional_stack?.summary?.memory_thinking_improved ??
                          data.institutional_learning?.thinking_improved
                        )
                          ? 'improved'
                          : 'not yet'
                      }`
                    : ''}
                </p>
              ) : null}
            </Card>
            <Card title="If We Decide">
              {data.institutional_stack?.summary?.simulation_scenario_id ||
                data.simulation_lab?.scenario_id ||
                '—'}
              {(data.institutional_stack?.summary?.simulation_expected_return ??
                data.simulation_lab?.expected_return) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  E[r]{' '}
                  {data.institutional_stack?.summary?.simulation_expected_return ??
                    data.simulation_lab?.expected_return}
                  {(data.institutional_stack?.summary?.simulation_confidence ??
                    data.simulation_lab?.confidence) != null
                    ? ` · conf ${
                        data.institutional_stack?.summary?.simulation_confidence ??
                        data.simulation_lab?.confidence
                      }`
                    : ''}
                  {' · experiment first'}
                </p>
              ) : null}
            </Card>
            <Card title="Decision Readiness">
              {data.institutional_stack?.summary?.decision_status ||
                data.decision_engine_v2?.recommendation_status ||
                '—'}
              {(data.institutional_stack?.summary?.decision_confidence ??
                data.decision_engine_v2?.confidence) != null ? (
                <p className="text-xs text-[#667085] mt-1">
                  Confidence{' '}
                  {data.institutional_stack?.summary?.decision_confidence ??
                    data.decision_engine_v2?.confidence}
                  {' · constitutional · not a trade ticket'}
                </p>
              ) : null}
            </Card>
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm font-bold text-[#18202b] mb-3">Research</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card title="Latest AGI Articles">
            <DocList items={research.latest_agi_articles} />
          </Card>
          <Card title="Broker Research">
            <DocList items={research.broker_research} />
          </Card>
          <Card title="Earnings">
            <DocList items={research.earnings} />
          </Card>
          <Card title="Filings">
            <DocList items={research.filings} />
          </Card>
        </div>
        {(research.knowledge_timeline || []).length > 0 && (
          <div className="mt-4">
            <Card title="Knowledge Timeline">
              <DocList items={research.knowledge_timeline} />
            </Card>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-sm font-bold text-[#18202b] mb-3">Evidence</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card title="Supporting Research">
            <DocList items={evidence.supporting_research} />
          </Card>
          <Card title="Conflicting Research">
            <DocList items={evidence.conflicting_research} />
          </Card>
          <Card title="Evidence Confidence">
            {evidence.evidence_confidence != null
              ? `${Math.round(Number(evidence.evidence_confidence) * (Number(evidence.evidence_confidence) <= 1 ? 100 : 1))}%`
              : '—'}
          </Card>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold text-[#18202b] mb-3">Portfolio</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card title="Current Portfolio Exposure">
            {portfolio.current_exposure != null ? String(portfolio.current_exposure) : 'No active exposure'}
          </Card>
          <Card title="Prediction History">
            <DocList items={portfolio.prediction_history} />
          </Card>
          <Card title="House View Evolution">
            {Array.isArray(portfolio.house_view_evolution?.points) ? (
              <DocList
                items={portfolio.house_view_evolution.points.map((p) => ({
                  title: `${p.as_of}: ${p.label}`,
                  snippet: p.changed ? `Changed from ${p.prior_label || 'prior'}` : 'Stable',
                }))}
              />
            ) : (
              <DocList items={portfolio.house_view_evolution} />
            )}
          </Card>
        </div>
        <div className="mt-3">
          <Link to="/portfolio" className="text-xs font-bold text-[#274c77] hover:underline">
            Open portfolio desk →
          </Link>
        </div>
      </section>

      {Object.keys(kg).length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-[#18202b] mb-3">Related Network</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Object.entries(kg).slice(0, 6).map(([key, vals]) => (
              <Card key={key} title={key.replace(/_/g, ' ')}>
                <div className="flex flex-wrap gap-1">
                  {(vals || []).slice(0, 5).map((v) => (
                    <Link
                      key={v}
                      to={
                        key.includes('theme') || key.includes('macro')
                          ? `/themes/${encodeURIComponent(v)}`
                          : key.includes('sector') || key.includes('industry')
                            ? `/sectors/${encodeURIComponent(v)}`
                            : `/research/stocks/${encodeURIComponent(v)}`
                      }
                      className="text-[11px] border border-[#ddd] px-1.5 py-0.5 hover:text-[#ff6600]"
                    >
                      {v}
                    </Link>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {(data.follow_up_questions || []).length > 0 && (
        <section className="border border-[#dde1e6] bg-white p-5">
          <h2 className="text-sm font-bold text-[#18202b]">Ask AGI about this company</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {(data.follow_up_questions || []).map((q) => (
              <Link
                key={q}
                to={`/ask?q=${encodeURIComponent(q)}`}
                className="text-[11px] border border-[#ddd] px-2.5 py-1.5 hover:border-[#111] hover:text-[#ff6600]"
              >
                {q}
              </Link>
            ))}
          </div>
        </section>
      )}

      <DiscoveryRail discovery={data.discovery} />
    </div>
  );
}
