import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { ArrowLeft, Download } from 'lucide-react';
import { PeFirmAnalytics } from '@/components/private-equity/PeDashboard';
import { usePeFirm } from '@/hooks/usePeIntelligence';
import { useIntelligenceEntity } from '@/hooks/useIntelligencePlatform';
import KnowledgeGraph from '@/components/intelligence/KnowledgeGraph';
import EntityIntelligencePanel from '@/components/intelligence/EntityIntelligencePanel';
import EntityTimeline from '@/components/intelligence/EntityTimeline';
import EntityCard from '@/components/intelligence/EntityCard';
import '@/components/private-equity/editorial/peEditorial.css';

const TABS = [
  'Overview', 'Portfolio', 'Criteria', 'Transactions', 'Funds', 'Team', 'News', 'Case Studies', 'ESG', 'Analytics', 'AI Insights',
];

function exportCsv(rows) {
  if (!rows.length) return;
  const headers = ['Company', 'Industry', 'Country', 'Region', 'Investment Year', 'Status', 'Asset Class', 'Website'];
  const lines = [headers.join(',')];
  rows.forEach((r) => {
    lines.push([
      r.company, r.industry, r.country, r.region, r.investmentYear, r.status, r.assetClass, r.website,
    ].map((v) => `"${String(v || '').replace(/"/g, '""')}"`).join(','));
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'portfolio.csv';
  a.click();
}

export default function PrivateEquityFirmPage() {
  const { slug } = useParams();
  const { data, loading, error } = usePeFirm(slug);
  const { data: entityData } = useIntelligenceEntity(slug, { full: true });
  const [tab, setTab] = useState('Overview');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('company');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const filteredPortfolio = useMemo(() => {
    let rows = data?.portfolio || [];
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter((r) =>
        [r.company, r.industry, r.country, r.region].some((f) => String(f).toLowerCase().includes(q))
      );
    }
    return [...rows].sort((a, b) => String(a[sortKey] || '').localeCompare(String(b[sortKey] || '')));
  }, [data, search, sortKey]);

  const paged = filteredPortfolio.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(filteredPortfolio.length / pageSize) || 1;

  if (loading) {
    return (
      <div className="pe-editorial pe-loading py-24 text-center text-[var(--pe-muted)]">
        Loading firm intelligence…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="pe-editorial pe-editorial-inner py-16">
        <Link to="/private-markets" className="inline-flex items-center gap-2 text-sm text-[var(--pe-muted)] no-underline mb-6">
          <ArrowLeft size={16} /> Private Markets Intelligence
        </Link>
        <p>Firm not found.</p>
      </div>
    );
  }

  return (
    <div className="pe-editorial">
      <Helmet>
        <title>{data.name} | Private Markets Intelligence | AGI</title>
      </Helmet>
      <div className="pe-editorial-inner py-10">
        <Link to="/private-markets" className="inline-flex items-center gap-2 text-sm text-[var(--pe-muted)] no-underline mb-8 hover:text-[var(--pe-accent)]">
          <ArrowLeft size={16} /> Private Markets Intelligence
        </Link>

        <section className="pe-card p-6 md:p-10 mb-8">
          <div className="flex flex-wrap items-start gap-6">
            <img src={data.logo} alt="" className="w-16 h-16 rounded object-contain bg-[#f5f5f5] p-2" />
            <div className="flex-1 min-w-0">
              <p className="pe-tag">{data.hq} · Founded {data.founded}</p>
              <h1 className="font-serif text-3xl md:text-4xl font-semibold mt-2">{data.name}</h1>
              <p className="text-[var(--pe-muted)] text-lg mt-3 max-w-2xl leading-relaxed">{data.strategy}</p>
              {data.dataSource === 'live_crawler' && (
                <span className="pe-tag mt-3 inline-block border border-[var(--pe-border)] px-2 py-1">Structured data · Live portfolio</span>
              )}
            </div>
            <div className="text-right">
              <div className="text-2xl font-semibold text-[var(--pe-accent)]">{data.aum}</div>
              <div className="text-xs uppercase tracking-wider text-[var(--pe-muted)] mt-1">Assets under management</div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-8">
            {[
              { l: 'Portfolio', v: data.portfolioTotal },
              { l: 'Funds', v: data.fundCount },
              { l: 'Exits', v: data.exitCount },
              { l: 'Offices', v: data.offices },
              { l: 'Focus', v: data.geoFocus?.[0] },
            ].map((s) => (
              <div key={s.l} className="border border-[var(--pe-border)] p-3 text-center bg-[#fafafa]">
                <div className="font-semibold">{s.v}</div>
                <div className="text-[10px] uppercase tracking-wider text-[var(--pe-muted)] mt-1">{s.l}</div>
              </div>
            ))}
          </div>
        </section>

        {entityData?.entity?.ai_summary && (
          <section className="pe-card p-6 md:p-8 mb-8 border-l-4 border-l-[var(--pe-accent)]">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--pe-accent)] mb-3">
              AI Intelligence Summary
            </p>
            <p className="text-base leading-relaxed text-[var(--pe-text)]">{entityData.entity.ai_summary}</p>
            {entityData.intelligence && (
              <p className="text-xs text-[var(--pe-muted)] mt-3">
                Intelligence Score: {entityData.intelligence.score}/100 · {entityData.intelligence.label}
              </p>
            )}
          </section>
        )}

        <section className="mb-8">
          <h2 className="font-serif text-2xl font-semibold mb-5">Knowledge Graph</h2>
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
            <KnowledgeGraph entitySlug={slug} />
            {entityData?.entity && (
              <EntityIntelligencePanel
                entity={entityData.entity}
                intelligence={entityData.intelligence}
                related={entityData.related}
                timeline={entityData.timeline}
                lastRefresh={entityData.last_refresh}
              />
            )}
          </div>
        </section>

        <div className="flex flex-wrap gap-2 mb-6 border-b border-[var(--pe-border)] pb-4">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium rounded-sm border ${
                tab === t
                  ? 'bg-[var(--pe-accent)] text-white border-[var(--pe-accent)]'
                  : 'bg-white text-[var(--pe-muted)] border-[var(--pe-border)] hover:border-[var(--pe-accent)]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === 'Overview' && (
          <div className="space-y-6">
            <div className="pe-card p-6 space-y-4 text-[17px] leading-relaxed text-[var(--pe-muted)]">
              <p className="text-[var(--pe-text)]">{data.overview.history}</p>
              <p><strong className="text-[var(--pe-text)]">Philosophy:</strong> {data.overview.philosophy}</p>
              <p><strong className="text-[var(--pe-text)]">Positioning:</strong> {data.overview.positioning}</p>
              <div className="flex flex-wrap gap-2 pt-2">
                {data.industries.map((i) => <span key={i} className="pe-tag">{i}</span>)}
              </div>
            </div>
            {entityData?.timeline?.length > 0 && (
              <div className="pe-card p-6">
                <EntityTimeline events={entityData.timeline} title="Institutional Timeline" />
              </div>
            )}
            {entityData?.related?.comparables?.length > 0 && (
              <div className="pe-card p-6">
                <h2 className="font-serif text-xl font-semibold mb-4">Comparable Firms</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {entityData.related.comparables.slice(0, 4).map((item) => (
                    <EntityCard key={item.id} entity={item} compact />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'Portfolio' && (
          <div>
            <div className="flex flex-wrap gap-3 mb-4">
              <input
                type="search"
                placeholder="Search portfolio…"
                className="pe-search max-w-xs border border-[var(--pe-border)] px-3 py-2 text-sm rounded-sm"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              />
              <select
                className="border border-[var(--pe-border)] px-3 py-2 text-sm rounded-sm"
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value)}
              >
                <option value="company">Sort: Company</option>
                <option value="industry">Sort: Industry</option>
                <option value="investmentYear">Sort: Year</option>
                <option value="region">Sort: Region</option>
              </select>
              <button type="button" className="pe-btn flex items-center gap-2" onClick={() => exportCsv(filteredPortfolio)}>
                <Download size={14} /> Export CSV
              </button>
            </div>
            <div className="pe-card overflow-x-auto">
              <table className="pe-table-editorial">
                <thead>
                  <tr>
                    <th>Company</th><th>Industry</th><th>Country</th><th>Region</th><th>Year</th><th>Status</th><th>Asset Class</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.map((r) => (
                    <tr key={`${r.company}-${r.investmentYear}`}>
                      <td className="font-medium">{r.company}</td>
                      <td>{r.industry}</td>
                      <td>{r.country}</td>
                      <td>{r.region}</td>
                      <td>{r.investmentYear}</td>
                      <td><span className="pe-tag">{r.status}</span></td>
                      <td>{r.assetClass}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex justify-between items-center mt-4 text-sm text-[var(--pe-muted)]">
              <span>{filteredPortfolio.length} companies</span>
              <div className="flex gap-2 items-center">
                <button type="button" className="pe-btn py-1 px-3" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
                <span>{page} / {totalPages}</span>
                <button type="button" className="pe-btn py-1 px-3" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
              </div>
            </div>
          </div>
        )}

        {tab === 'Criteria' && data.investmentCriteria && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(data.investmentCriteria).map(([k, v]) => (
              <div key={k} className="pe-card p-5">
                <div className="text-xs uppercase tracking-wider text-[var(--pe-muted)]">{k.replace(/([A-Z])/g, ' $1')}</div>
                <div className="mt-2 font-medium">{Array.isArray(v) ? v.join(', ') : v}</div>
              </div>
            ))}
          </div>
        )}

        {tab === 'Transactions' && (
          <div className="pe-card overflow-x-auto">
            <table className="pe-table-editorial">
              <thead><tr><th>Buyer</th><th>Target</th><th>Value</th><th>Industry</th><th>Date</th><th>Status</th></tr></thead>
              <tbody>
                {(data.transactions?.length ? data.transactions : []).map((t) => (
                  <tr key={t.id || t.target}>
                    <td>{t.buyer}</td><td>{t.target}</td><td className="text-[var(--pe-accent)]">{t.dealValue}</td>
                    <td>{t.industry}</td><td>{t.date}</td><td><span className="pe-tag">{t.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'Funds' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(data.funds?.length ? data.funds : [{ id: 'x', name: `${data.name} Flagship`, vintage: '—', fundSize: '—', strategy: data.strategy.slice(0, 60), status: 'Investing' }]).map((f) => (
              <div key={f.id} className="pe-card p-5">
                <span className="pe-tag">{f.status}</span>
                <h4 className="font-serif text-lg font-semibold mt-2">{f.name}</h4>
                <p className="text-sm text-[var(--pe-muted)] mt-2">Vintage {f.vintage} · {f.fundSize}</p>
                <p className="text-sm mt-2">{f.strategy}</p>
              </div>
            ))}
          </div>
        )}

        {tab === 'Team' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.team.map((m) => (
              <div key={m.name} className="pe-card p-5">
                <div className="font-semibold">{m.name}</div>
                <div className="text-sm text-[var(--pe-accent)]">{m.title}</div>
                <p className="text-sm text-[var(--pe-muted)] mt-2">{m.office} · {m.bio}</p>
              </div>
            ))}
          </div>
        )}

        {tab === 'News' && (
          <div className="space-y-4">
            {(data.news?.length ? data.news : []).map((n) => (
              <div key={n.id} className="pe-card p-5">
                <span className="pe-tag">{n.category}</span>
                <h4 className="font-semibold mt-2">{n.headline}</h4>
                <p className="text-sm text-[var(--pe-muted)] mt-1">{n.summary}</p>
              </div>
            ))}
            {!data.news?.length && <p className="text-[var(--pe-muted)]">No firm-specific news in feed yet.</p>}
          </div>
        )}

        {tab === 'Case Studies' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(data.caseStudies?.length ? data.caseStudies : [{ id: 'd', title: 'Value creation playbook', thesis: data.strategy }]).map((c) => (
              <div key={c.id} className="pe-card p-5">
                <h4 className="font-serif font-semibold">{c.title}</h4>
                <p className="text-sm text-[var(--pe-muted)] mt-2">{c.thesis}</p>
              </div>
            ))}
          </div>
        )}

        {tab === 'ESG' && data.esg && (
          <div className="pe-card p-6 space-y-3 text-[var(--pe-muted)]">
            <p>{data.esg.framework}</p>
            <p><strong className="text-[var(--pe-text)]">Goals:</strong> {data.esg.goals}</p>
            <ul className="list-disc pl-5">
              {data.esg.initiatives.map((i) => <li key={i}>{i}</li>)}
            </ul>
          </div>
        )}

        {tab === 'Analytics' && (
          <div className="[&_.pe-glass]:pe-card [&_.pe-glass]:bg-white">
            <PeFirmAnalytics analytics={data.analytics} />
          </div>
        )}

        {tab === 'AI Insights' && (
          <div className="pe-card p-5">
            {Object.values(data.aiInsights || {}).map((item) => (
              <div key={item.label} className="py-3 border-b border-[var(--pe-border)] last:border-0">
                <div className="text-xs text-[var(--pe-muted)]">{item.label}</div>
                <div className="font-medium mt-1">{item.value}</div>
                <div className="text-sm text-[var(--pe-muted)]">{item.detail}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
