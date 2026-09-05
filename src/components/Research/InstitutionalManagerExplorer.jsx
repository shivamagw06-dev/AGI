import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, ExternalLink, FileClock, Loader2, MapPin, Search } from 'lucide-react';
import { getInstitutionalFund } from '@/lib/institutionalHoldingsApi';

const PAGE_SIZE = 50;

const money = (value) => {
  const amount = Number(value || 0);
  if (amount >= 1e12) return `$${(amount / 1e12).toFixed(2)}T`;
  if (amount >= 1e9) return `$${(amount / 1e9).toFixed(2)}B`;
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
  return `$${Math.round(amount).toLocaleString('en-US')}`;
};

const number = (value) => Number(value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
const percent = (value) => `${Number(value || 0).toFixed(2)}%`;

function ManagerMark({ manager }) {
  const mark = String(manager.display_name || 'AGI').split(/\s+/).map((word) => word[0]).join('').slice(0, 3);
  return (
    <div className="relative grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl border border-cyan-100/15 bg-gradient-to-br from-[#174c5c] to-[#071e2b] font-serif text-xs font-bold text-white shadow-[0_8px_22px_rgba(5,31,42,.2)]">
      <span className="absolute inset-x-2 top-1.5 h-px bg-[#d9a766]" />
      {mark}
    </div>
  );
}

function ChangeBadge({ change }) {
  const type = change?.change_type || 'held';
  const tones = {
    new: 'bg-emerald-100 text-emerald-800',
    increased: 'bg-cyan-100 text-cyan-800',
    reduced: 'bg-amber-100 text-amber-800',
    exited: 'bg-rose-100 text-rose-800',
    held: 'bg-slate-100 text-slate-600',
  };
  return <span className={`rounded-full px-2.5 py-1 text-[9px] font-extrabold uppercase tracking-[.1em] ${tones[type] || tones.held}`}>{type}</span>;
}

export default function InstitutionalManagerExplorer({ funds = [] }) {
  const [expandedSlug, setExpandedSlug] = useState('');
  const [details, setDetails] = useState({});
  const [loadingSlug, setLoadingSlug] = useState('');
  const [loadError, setLoadError] = useState('');
  const [holdingQuery, setHoldingQuery] = useState('');
  const [holdingPage, setHoldingPage] = useState(1);

  const toggle = async (fund) => {
    if (expandedSlug === fund.slug) {
      setExpandedSlug('');
      return;
    }
    setExpandedSlug(fund.slug);
    setHoldingQuery('');
    setHoldingPage(1);
    setLoadError('');
    if (details[fund.slug]) return;
    setLoadingSlug(fund.slug);
    try {
      const result = await getInstitutionalFund(fund.slug);
      setDetails((current) => ({ ...current, [fund.slug]: result }));
    } catch (error) {
      setLoadError(error.message || 'Unable to load this portfolio.');
    } finally {
      setLoadingSlug('');
    }
  };

  return (
    <div className="mt-7 overflow-hidden rounded-[26px] border border-white bg-white/90 shadow-[0_20px_55px_rgba(12,48,59,.08)]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] text-left">
          <thead className="bg-[#0b2d3a] text-[9px] font-extrabold uppercase tracking-[.15em] text-[#a9c3ca]">
            <tr>
              <th className="w-12 px-4 py-4" aria-label="Expand holdings" />
              <th className="px-3 py-4">Institutional manager</th>
              <th className="px-3 py-4">Latest 13F</th>
              <th className="px-3 py-4">Earliest coverage</th>
              <th className="px-3 py-4">Location</th>
              <th className="px-3 py-4 text-right">13F value</th>
              <th className="px-3 py-4 text-right">Holdings</th>
              <th className="px-5 py-4">Filing status</th>
            </tr>
          </thead>
          <tbody>
            {funds.map((fund) => {
              const expanded = expandedSlug === fund.slug;
              const detail = details[fund.slug];
              const changes = new Map((detail?.changes || []).map((row) => [row.cusip, row]));
              const filtered = (detail?.holdings || []).filter((row) => `${row.ticker || ''} ${row.issuer_name || ''} ${row.cusip || ''}`.toLowerCase().includes(holdingQuery.toLowerCase()));
              const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
              const pageRows = filtered.slice((holdingPage - 1) * PAGE_SIZE, holdingPage * PAGE_SIZE);
              const location = [fund.city, fund.state, fund.country].filter(Boolean).join(', ');
              return [
                <tr key={fund.slug} className={`border-t border-[#e5ecea] transition ${expanded ? 'bg-[#edf5f3]' : 'hover:bg-[#f7faf9]'}`}>
                  <td className="px-4 py-4 align-middle">
                    <button onClick={() => toggle(fund)} className="grid h-8 w-8 place-items-center rounded-lg border border-[#d3dfdc] bg-white text-[#174d5c] transition hover:border-[#4a9da1]" aria-expanded={expanded} aria-label={`${expanded ? 'Hide' : 'Show'} ${fund.display_name} holdings`}>
                      <ChevronRight className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
                    </button>
                  </td>
                  <td className="px-3 py-4">
                    <div className="flex items-center gap-3"><ManagerMark manager={fund} /><div><Link to={`/institutional-holdings/funds/${fund.slug}`} className="font-serif text-base font-bold text-[#0a3341] hover:text-[#14747b]">{fund.display_name}</Link><p className="mt-1 text-[10px] text-[#75868b]">{fund.manager_type || fund.strategy}</p></div></div>
                  </td>
                  <td className="px-3 py-4 text-xs font-bold text-[#314f59]">{fund.latest_filing?.report_date || 'Pending'}</td>
                  <td className="px-3 py-4 text-xs text-[#65777d]">{fund.earliest_report_date || 'Pending'}</td>
                  <td className="px-3 py-4"><div className="flex max-w-[210px] items-start gap-2 text-xs text-[#65777d]"><MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#a56e3d]" /><span>{location || 'SEC address pending'}{fund.postal_code ? ` ${fund.postal_code}` : ''}</span></div></td>
                  <td className="px-3 py-4 text-right font-serif text-base font-bold text-[#102f3c]">{fund.latest_filing ? money(fund.latest_filing.total_value_usd) : '--'}</td>
                  <td className="px-3 py-4 text-right text-sm font-bold">{fund.position_count || 0}</td>
                  <td className="px-5 py-4"><span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[9px] font-extrabold uppercase tracking-[.1em] ${fund.last_refresh_status === 'success' ? 'bg-emerald-100 text-emerald-800' : fund.last_refresh_status === 'error' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{fund.last_refresh_status || 'queued'}</span></td>
                </tr>,
                expanded ? (
                  <tr key={`${fund.slug}-holdings`} className="border-t border-[#cfddda] bg-[#f4f8f7]">
                    <td colSpan="8" className="p-0">
                      <div className="border-l-4 border-[#2a9c99] px-5 py-6 sm:px-8">
                        {loadingSlug === fund.slug ? <div className="flex items-center justify-center gap-3 py-14 text-sm text-[#63777e]"><Loader2 className="h-5 w-5 animate-spin" /> Loading latest SEC holdings</div> : loadError && !detail ? <p className="py-10 text-center text-sm text-rose-700">{loadError}</p> : detail ? (
                          <>
                            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                              <div><p className="text-[9px] font-extrabold uppercase tracking-[.18em] text-[#a56e3d]">Taken from latest 13F filing</p><h3 className="mt-2 font-serif text-2xl font-bold">{fund.display_name} holdings</h3><p className="mt-1 text-xs text-[#6f8085]">Report quarter {detail.latest_filing?.report_date} · Public {String(detail.latest_filing?.filed_at || '').slice(0, 10)} · {filtered.length} matching positions</p></div>
                              <div className="flex flex-col gap-3 sm:flex-row">
                                <label className="flex items-center gap-2 rounded-xl border border-[#cfdbd8] bg-white px-3"><Search className="h-4 w-4 text-[#71858a]" /><input value={holdingQuery} onChange={(event) => { setHoldingQuery(event.target.value); setHoldingPage(1); }} placeholder="Filter ticker or company" className="w-56 bg-transparent py-3 text-xs outline-none" /></label>
                                <Link to={`/institutional-holdings/funds/${fund.slug}`} className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0c3544] px-4 py-3 text-xs font-bold text-white">Full manager profile <ExternalLink className="h-3.5 w-3.5" /></Link>
                              </div>
                            </div>
                            <div className="mt-5 overflow-x-auto rounded-xl border border-[#d7e1df] bg-white">
                              <table className="w-full min-w-[1060px] text-left">
                                <thead className="bg-[#152f39] text-[9px] font-extrabold uppercase tracking-[.13em] text-[#b8c9ce]"><tr><th className="px-4 py-3">Security</th><th className="px-4 py-3">Class</th><th className="px-4 py-3 text-right">Shares</th><th className="px-4 py-3 text-right">Market value</th><th className="px-4 py-3 text-right">Portfolio</th><th className="px-4 py-3 text-right">Previous</th><th className="px-4 py-3 text-right">Rank</th><th className="px-4 py-3 text-right">Share change</th><th className="px-4 py-3 text-right">Change %</th><th className="px-4 py-3">Signal</th></tr></thead>
                                <tbody>{pageRows.map((row, index) => { const change = changes.get(row.cusip); return <tr key={`${row.id || row.cusip}-${index}`} className="border-t border-[#e8eeec] text-xs hover:bg-[#f6f9f8]"><td className="px-4 py-3"><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="font-bold text-[#0d6670] hover:underline">{row.ticker || row.cusip}</Link><span className="block max-w-[220px] truncate text-[10px] text-[#7c8b90]">{row.issuer_name}</span></td><td className="px-4 py-3 text-[#607279]">{row.title_of_class || 'Security'}{row.put_call ? ` / ${row.put_call}` : ''}</td><td className="px-4 py-3 text-right font-medium">{number(row.shares)}</td><td className="px-4 py-3 text-right font-bold">{money(row.value_usd)}</td><td className="px-4 py-3 text-right font-bold">{percent(row.portfolio_weight)}</td><td className="px-4 py-3 text-right text-[#718187]">{change ? percent(change.previous_weight) : '--'}</td><td className="px-4 py-3 text-right font-bold">{(holdingPage - 1) * PAGE_SIZE + index + 1}</td><td className={`px-4 py-3 text-right font-bold ${Number(change?.share_change || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{change ? number(change.share_change) : '--'}</td><td className="px-4 py-3 text-right">{change?.share_change_pct == null ? '--' : percent(change.share_change_pct)}</td><td className="px-4 py-3"><ChangeBadge change={change} /></td></tr>; })}</tbody>
                              </table>
                              {!pageRows.length ? <div className="flex items-center justify-center gap-2 py-12 text-sm text-[#708187]"><FileClock className="h-4 w-4" /> No holdings match this filter.</div> : null}
                            </div>
                            <div className="mt-4 flex flex-col gap-3 text-xs text-[#6b7d82] sm:flex-row sm:items-center sm:justify-between"><span>Rows {(holdingPage - 1) * PAGE_SIZE + (pageRows.length ? 1 : 0)}–{Math.min(holdingPage * PAGE_SIZE, filtered.length)} of {filtered.length}</span><div className="flex items-center gap-2"><button disabled={holdingPage <= 1} onClick={() => setHoldingPage((page) => Math.max(1, page - 1))} className="rounded-lg border border-[#cad8d5] bg-white px-3 py-2 font-bold disabled:opacity-40">Previous</button><span className="px-2 font-bold">{holdingPage} / {pageCount}</span><button disabled={holdingPage >= pageCount} onClick={() => setHoldingPage((page) => Math.min(pageCount, page + 1))} className="rounded-lg border border-[#cad8d5] bg-white px-3 py-2 font-bold disabled:opacity-40">Next</button></div></div>
                          </>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ) : null,
              ];
            })}
          </tbody>
        </table>
      </div>
      {!funds.length ? <p className="p-10 text-center text-sm text-[#708187]">No institutional managers match this search.</p> : null}
    </div>
  );
}
