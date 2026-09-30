import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getNseScreenerUniverse } from '@/lib/nifty500ResearchApi';
import { matchScreenerItem, SCREENER_CATEGORIES, SCREENER_PRESETS, sortScreenerItems } from './screenerLogic';
import './screeners.css';

const PAGE_SIZE = 40;
const FILTER_KEYS = ['search', 'coverage', 'sentiment', 'minScore', 'maxScore', 'minConfidence', 'minRisks', 'minChange', 'maxChange', 'minPrice', 'maxPrice', 'minVolume'];

function formatDate(value) {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(date);
}

function sentimentTone(value) {
  if (value?.includes('Bullish')) return 'positive';
  if (value?.includes('Bearish')) return 'negative';
  return 'neutral';
}

function exportCsv(items) {
  const header = ['Symbol', 'Company', 'ISIN', 'Last price (INR)', 'Change (%)', 'Volume', 'Research available', 'Sentiment', 'AGI research score', 'Confidence (%)', 'Risk factors', 'Supporting factors'];
  const rows = items.map((item) => [
    item.symbol,
    item.name,
    item.isin,
    item.lastPrice,
    item.changePercent,
    item.volume,
    item.hasResearch ? 'Yes' : 'No',
    item.overallSentiment,
    item.agiResearchScore,
    item.aiConfidencePercent,
    item.riskFactors?.length || 0,
    item.supportingFactors?.length || 0,
  ]);
  const csv = [header, ...rows].map((row) => row.map((value) => {
    const text = String(value ?? '');
    const safe = /^[=+@\-\t\r]/.test(text) ? `'${text}` : text;
    return `"${safe.replaceAll('"', '""')}"`;
  }).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'agi-research-screen.csv';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function ScreenersPage() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ run: null, items: [], quoteCount: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [reload, setReload] = useState(0);
  const [saved, setSaved] = useState(() => {
    try { return JSON.parse(localStorage.getItem('agi-saved-screens-v1') || '[]'); }
    catch { return []; }
  });

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    getNseScreenerUniverse()
      .then((result) => { if (active) setData(result || { run: null, items: [] }); })
      .catch((err) => { if (active) setError(err.message || 'Unable to load research screens.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [reload]);

  const presetId = params.get('preset') || 'all';
  const activePreset = SCREENER_PRESETS.find((item) => item.id === presetId) || SCREENER_PRESETS[0];
  const category = params.get('category') || activePreset.category;
  const filters = useMemo(() => Object.fromEntries(FILTER_KEYS.map((key) => [key, params.get(key) ?? ''])), [params]);
  const sort = params.get('sort') || 'symbol-asc';

  const filtered = useMemo(() => sortScreenerItems((data.items || []).filter((item) => matchScreenerItem(item, filters)), sort), [data.items, filters, sort]);
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  function selectPreset(preset) {
    const next = new URLSearchParams();
    next.set('preset', preset.id);
    next.set('category', preset.category);
    Object.entries(preset.filters).forEach(([key, value]) => next.set(key, String(value)));
    setParams(next);
    setPage(1);
  }

  function setField(key, value) {
    const next = new URLSearchParams(params);
    if (value === '') next.delete(key);
    else next.set(key, value);
    if (key !== 'sort') next.set('preset', 'custom');
    setParams(next);
    setPage(1);
  }

  function saveScreen() {
    const entry = {
      id: String(Date.now()),
      title: presetId === 'custom' ? `Custom screen · ${new Date().toLocaleDateString('en-IN')}` : activePreset.title,
      query: params.toString(),
    };
    const next = [entry, ...saved].slice(0, 12);
    setSaved(next);
    localStorage.setItem('agi-saved-screens-v1', JSON.stringify(next));
  }

  function deleteSaved(id) {
    const next = saved.filter((item) => item.id !== id);
    setSaved(next);
    localStorage.setItem('agi-saved-screens-v1', JSON.stringify(next));
  }

  return (
    <div className="agi-screeners">
      <div className="agi-screener-heading">
        <div>
          <div className="agi-screener-kicker">AGI RESEARCH / INDIA</div>
          <h1>Stock screeners</h1>
          <p>Screen the NSE equity list by price activity and explore AGI research where it is available.</p>
        </div>
        <div className="agi-screener-run">
          <span>NSE equity universe</span>
          <strong>{(data.items?.length || 0).toLocaleString('en-IN')} names</strong>
          <small>{data.researchCount || 0} with AGI research · updated {formatDate(data.instrumentAsOf)}</small>
        </div>
      </div>

      <div className="agi-screener-layout">
        <aside className="agi-screener-side" aria-label="Screener categories">
          <div className="agi-screener-side-title">BROWSE BY TYPE</div>
          {SCREENER_CATEGORIES.map((item) => (
            <button key={item.id} type="button" className={category === item.id ? 'selected' : ''} onClick={() => {
              if (item.id === 'all') selectPreset(SCREENER_PRESETS[0]);
              else {
                const first = SCREENER_PRESETS.find((preset) => preset.category === item.id);
                if (first) selectPreset(first);
              }
            }}>{item.label}<span>›</span></button>
          ))}
          {saved.length > 0 && <div className="agi-screener-side-title saved-title">SAVED IN THIS BROWSER</div>}
          {saved.map((item) => <div className="agi-screener-saved" key={item.id}>
            <button type="button" onClick={() => { setParams(new URLSearchParams(item.query)); setPage(1); }}>{item.title}</button>
            <button type="button" aria-label={`Remove ${item.title}`} title="Remove saved screen" onClick={() => deleteSaved(item.id)}>×</button>
          </div>)}
        </aside>

        <main className="agi-screener-main">
          <div className="agi-screener-section-top">
            <div><span className="agi-screener-eyebrow">PRESET SCREENS</span><h2>{SCREENER_CATEGORIES.find((item) => item.id === category)?.label || 'All screens'}</h2></div>
            <span className="agi-screener-small-note">NSE instrument list and market quotes via Upstox · AGI scores where published</span>
          </div>
          <div className="agi-screener-presets">
            {SCREENER_PRESETS.filter((item) => category === 'all' || item.category === category).map((item) => {
              const count = (data.items || []).filter((stock) => matchScreenerItem(stock, item.filters)).length;
              return <button type="button" key={item.id} className={`agi-screener-preset${presetId === item.id ? ' active' : ''}`} onClick={() => selectPreset(item)}>
                <span className="agi-screener-preset-top"><strong>{item.title}</strong><b>{loading ? '…' : count}</b></span>
                <span>{item.description}</span>
                <em>Open screen ↗</em>
              </button>;
            })}
          </div>

          <section className="agi-screener-results" aria-label="Screen results">
            <div className="agi-screener-results-head">
              <div><span className="agi-screener-eyebrow">SCREEN RESULTS</span><h2>{presetId === 'custom' ? 'Custom screen' : activePreset.title}</h2><p>{loading ? 'Loading NSE coverage…' : `${filtered.length.toLocaleString('en-IN')} matching names · ${(data.items?.length || 0).toLocaleString('en-IN')} NSE equities · ${data.quoteCount || 0} with quotes`}</p></div>
              <div className="agi-screener-actions"><button type="button" onClick={saveScreen} disabled={!data.items?.length}>Save screen</button><button type="button" onClick={() => exportCsv(filtered)} disabled={!filtered.length}>Export CSV</button></div>
            </div>

            {data.quotesAsOf && <p className="agi-screener-data-status">Market snapshot: {new Date(data.quotesAsOf).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST. Quotes are cached and may be delayed.</p>}
            {data.dailyRefresh?.lastRun && <p className="agi-screener-data-status">Post-market market-data refresh ({data.dailyRefresh.lastRun.date}): {data.dailyRefresh.lastRun.ok ? 'quote batches fetched' : 'incomplete'} · {data.dailyRefresh.lastRun.instruments || 0} instruments · {data.dailyRefresh.lastRun.quoted || 0} available quotes. Research scores update separately.</p>}
            {data.quoteError && <p className="agi-screener-data-status">{data.quoteError} Price and volume screens only include stocks with available quotes.</p>}

            <div className="agi-screener-filters">
              <label className="agi-screener-search">Search symbol or company<input type="search" value={filters.search} onChange={(event) => setField('search', event.target.value)} placeholder="e.g. TCS or Tata" /></label>
              <label>Coverage<select value={filters.coverage} onChange={(event) => setField('coverage', event.target.value)}><option value="">All NSE equities</option><option value="research">With AGI research</option></select></label>
              <label>Sentiment<select value={filters.sentiment} onChange={(event) => setField('sentiment', event.target.value)}><option value="">Any</option><option>Strong Bullish</option><option>Bullish side</option><option>Neutral</option><option>Bearish side</option><option>Strong Bearish</option></select></label>
              <label>Min. price ₹<input type="number" min="0" value={filters.minPrice} onChange={(event) => setField('minPrice', event.target.value)} placeholder="Any" /></label>
              <label>Max. price ₹<input type="number" min="0" value={filters.maxPrice} onChange={(event) => setField('maxPrice', event.target.value)} placeholder="Any" /></label>
              <label>Min. change %<input type="number" step="0.1" value={filters.minChange} onChange={(event) => setField('minChange', event.target.value)} placeholder="Any" /></label>
              <label>Max. change %<input type="number" step="0.1" value={filters.maxChange} onChange={(event) => setField('maxChange', event.target.value)} placeholder="Any" /></label>
              <label>Min. volume<input type="number" min="0" value={filters.minVolume} onChange={(event) => setField('minVolume', event.target.value)} placeholder="Shares" /></label>
              <label>Min. score<input type="number" min="0" max="100" value={filters.minScore} onChange={(event) => setField('minScore', event.target.value)} placeholder="0–100" /></label>
              <label>Max. score<input type="number" min="0" max="100" value={filters.maxScore} onChange={(event) => setField('maxScore', event.target.value)} placeholder="0–100" /></label>
              <label>Min. confidence<input type="number" min="0" max="100" value={filters.minConfidence} onChange={(event) => setField('minConfidence', event.target.value)} placeholder="0–100%" /></label>
              <label>Min. risk factors<input type="number" min="0" max="20" value={filters.minRisks} onChange={(event) => setField('minRisks', event.target.value)} placeholder="Any" /></label>
              <label>Sort by<select value={sort} onChange={(event) => setField('sort', event.target.value)}><option value="symbol-asc">Symbol A–Z</option><option value="change-desc">Change · highest</option><option value="change-asc">Change · lowest</option><option value="volume-desc">Volume · highest</option><option value="price-desc">Price · highest</option><option value="score-desc">Score · high to low</option><option value="score-asc">Score · low to high</option><option value="confidence-desc">Confidence</option><option value="risk-desc">Risk factors</option></select></label>
            </div>

            {error && <div className="agi-screener-message error" role="alert">{error} <button type="button" onClick={() => setReload((value) => value + 1)}>Try again</button></div>}
            {!error && !loading && filtered.length === 0 && <div className="agi-screener-message">No names match these filters. Try a wider range or a different screen.</div>}
            {!error && filtered.length > 0 && <div className="agi-screener-table-wrap"><table><thead><tr><th>Company</th><th>Last price</th><th>Change</th><th>Volume</th><th>Research view</th><th>Score</th><th>Confidence</th><th>Factors</th><th>Research note</th></tr></thead><tbody>
              {visible.map((item) => <tr key={item.symbol}><td><Link to={`/agi/companies/${encodeURIComponent(item.symbol)}`}>{item.symbol} <span>↗</span></Link><small className="agi-screener-company-name">{item.name}</small></td><td>{item.lastPrice == null ? '—' : `₹${Number(item.lastPrice).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}</td><td className={item.changePercent >= 0 ? 'agi-screener-up' : 'agi-screener-down'}>{item.changePercent == null ? '—' : `${item.changePercent >= 0 ? '+' : ''}${Number(item.changePercent).toFixed(2)}%`}</td><td>{item.volume == null ? '—' : Number(item.volume).toLocaleString('en-IN')}</td><td>{item.hasResearch ? <span className={`agi-screener-sentiment ${sentimentTone(item.overallSentiment)}`}>{item.overallSentiment}</span> : <span className="agi-screener-uncovered">No AGI research</span>}</td><td>{item.hasResearch ? <><strong>{Number(item.agiResearchScore).toFixed(1)}</strong><div className="agi-screener-score-track"><i style={{ width: `${Math.max(0, Math.min(100, Number(item.agiResearchScore)))}%` }} /></div></> : '—'}</td><td>{item.hasResearch ? `${item.aiConfidencePercent}%` : '—'}</td><td>{item.hasResearch ? <><span className="agi-screener-factor positive">+{item.supportingFactors?.length || 0}</span><span className="agi-screener-factor negative">−{item.riskFactors?.length || 0}</span></> : '—'}</td><td className="agi-screener-note">{item.researchSummary || 'Research not published for this stock'}</td></tr>)}
            </tbody></table></div>}
            {!error && filtered.length > PAGE_SIZE && <div className="agi-screener-pagination"><span>Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}</span><div><button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>{page} / {pageCount}</span><button type="button" disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Next</button></div></div>}
          </section>
          <p className="agi-screener-footnote">Universe: NSE_EQ instruments classified as EQ in the Upstox daily file. Market snapshots are cached for 15 minutes when a data token is available. AGI scores cover only the published research subset. Neither snapshot nor score is an investment recommendation.</p>
        </main>
      </div>
    </div>
  );
}
