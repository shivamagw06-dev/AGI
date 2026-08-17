import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft, RefreshCw, Sparkles } from 'lucide-react';
import { InlineAsk, OpportunityTable } from '@/pages/hedgeFundTerminal';
import API_ORIGIN from '@/config';
import './hedgeFundLab.css';

const PAGES = {
  alpha: {
    eyebrow: 'AGI Alpha Intelligence',
    title: 'Alpha Opportunities',
    description: 'A focused research queue where value, quality, growth, technical confirmation and consensus agree. Every score is evidence-led and requires risk review.',
    question: 'Which companies have the strongest multi-factor evidence, and what could invalidate the thesis?',
    icon: Sparkles,
  },
};

export default function HedgeFundSignalPage({ kind }) {
  const page = PAGES[kind] || PAGES.alpha;
  const Icon = page.icon;
  return (
    <div className="hfl-root hfs-root">
      <header className="hfl-header hfs-header">
        <Link to="/hedge-fund" className="hfl-back"><ArrowLeft size={14} /> Hedge Fund hub</Link>
        <div className="hfs-title-row">
          <div>
            <div className="hfs-eyebrow"><Icon size={14} /> {page.eyebrow}</div>
            <h1>{page.title}</h1>
            <p>{page.description}</p>
          </div>
          <span className="hfs-switch">Technical confirmation is included in the Alpha score</span>
        </div>
      </header>
      <main className="hfl-body hfs-body">
        <ResearchConfluence />
        <OpportunityTable scan={kind} label={page.title} researchQuestion={page.question} />
        <section className="hfl-module hfs-method">
          <h3>How to use this page</h3>
          <p>
            Expand a company to inspect the calculation chain, data sources, catalysts and risks. A scanner result is a research priority—not a buy, sell, or probability of return.
          </p>
        </section>
        <InlineAsk />
      </main>
    </div>
  );
}

const score = (value) => value == null ? '—' : Number(value).toFixed(0);
const classLabel = (value) => String(value || 'DEVELOPING').replaceAll('_', ' ');

function ResearchConfluence() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true); setError('');
    try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const response = await fetch(`${API_ORIGIN}/api/market/research-confluence?limit=15`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`Research Confluence is unavailable (${response.status}).`);
      const type = response.headers.get('content-type') || '';
      if (!type.includes('application/json')) throw new Error('Research Confluence returned an invalid response.');
      setData(await response.json());
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const items = data?.items || [];
  return <section className="hfs-confluence">
    <header><div><span>Shared evidence contract</span><h2>Daily Analyst Research Queue</h2><p>AGI fundamentals, valuation, end-of-day evidence, live evidence and catalysts remain independently visible.</p></div><button type="button" onClick={load} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh</button></header>
    {error ? <div className="hfs-confluence-error"><AlertCircle size={16} />{error}</div> : null}
    {!error && loading && !data ? <p className="hft-dim">Assembling normalized evidence…</p> : null}
    {!error && !loading && !items.length ? <p className="hft-dim">No candidates have enough current evidence for the queue.</p> : null}
    {items.length ? <div className="hft-table-wrap"><table className="hft-table"><thead><tr><th>#</th><th>Company</th><th>State</th><th>Priority</th><th>Fundamental</th><th>Valuation</th><th>AGI EOD</th><th>AGI Live</th><th>Catalyst</th><th>Completeness</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.symbol}><td>{index + 1}</td><td><strong>{item.symbol}</strong><div className="hft-dim">{item.sector || '—'}</div></td><td><span className={`hfs-state ${String(item.confluence_class).toLowerCase()}`}>{classLabel(item.confluence_class)}</span></td><td><strong>{score(item.research_priority_score)}</strong></td><td>{score(item.scores?.fundamental_score)}</td><td>{score(item.scores?.valuation_score)}</td><td>{score(item.scores?.eod_confirmation_score)}</td><td>{score(item.scores?.live_confirmation_score)}</td><td>{score(item.scores?.catalyst_relevance_score)}</td><td>{item.flags?.incomplete_research_evidence ? <span className="hfs-incomplete">Incomplete</span> : 'Complete'}</td></tr>)}</tbody></table></div> : null}
    {data?.evidence_health ? <footer>Evidence populated: {data.evidence_health.populated?.fundamental || 0} fundamental · {data.evidence_health.populated?.valuation || 0} valuation · {data.evidence_health.populated?.catalyst || 0} catalyst · {data.evidence_health.errors?.length || 0} source errors</footer> : null}
  </section>;
}
