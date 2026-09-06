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

const MANAGER_DOMAINS = {
  'Akre Capital Management': 'akrecapital.com',
  Alphabet: 'abc.xyz',
  'Altimeter Capital Management': 'altimeter.com',
  Appaloosa: 'appaloosamanagement.com',
  'AQR Capital Management': 'aqr.com',
  'Atreides Management': 'atreidesmgmt.com',
  'Baillie Gifford & Company': 'bailliegifford.com',
  'Baker Bros Advisors': 'bakerbros.com',
  'Berkshire Hathaway': 'berkshirehathaway.com',
  BlackRock: 'blackrock.com',
  'Bridgewater Associates': 'bridgewater.com',
  'Citadel Advisors': 'citadel.com',
  'Coatue Management': 'coatue.com',
  'D1 Capital Partners': 'd1.com',
  'Durable Capital Partners': 'durablecapital.com',
  'Fidelity Investments Money Management': 'fidelity.com',
  Fundsmith: 'fundsmith.co.uk',
  'Gates Foundation Trust': 'gatesfoundation.org',
  'Goldman Sachs Group': 'goldmansachs.com',
  'Himalaya Capital Management': 'himalayacapital.com',
  'Jane Street Group': 'janestreet.com',
  'JPMorgan Chase & Company': 'jpmorganchase.com',
  'Lone Pine Capital': 'lonepinecapital.com',
  'Maverick Capital': 'maverickcap.com',
  'Millennium Management': 'mlp.com',
  'National Pension Service': 'nps.or.kr',
  'Norges Bank': 'nbim.no',
  'NVIDIA Corp': 'nvidia.com',
  'Perceptive Advisors': 'perceptivelife.com',
  'Pershing Square Capital Management': 'pershingsquareholdings.com',
  'RA Capital Management': 'racap.com',
  'Renaissance Technologies': 'rentec.com',
  'Situational Awareness': 'situational-awareness.ai',
  'Soros Fund Management': 'sorosfundmgmt.com',
  'Surgocap Partners': 'surgocap.com',
  'TCI Fund Management': 'tcifund.com',
  'The Baupost Group': 'baupost.com',
  'The Vanguard Group': 'vanguard.com',
  'Thiel Macro': 'thielcapital.com',
  'Third Point': 'thirdpoint.com',
  'Tiger Global Management': 'tigerglobal.com',
  'Valley Forge Capital Management': 'valleyforgecapital.com',
  'Viking Global Investors': 'vikingglobal.com',
  'Whale Rock Capital Management': 'whalerockcapital.com',
};

const MANAGER_HIERARCHY = [
  'Situational Awareness', 'Berkshire Hathaway', 'Duquesne Family Office', 'BlackRock',
  'Pershing Square Capital Management', 'Scion Asset Management', 'TCI Fund Management',
  'Bridgewater Associates', 'National Pension Service', 'Altimeter Capital Management',
  'Atreides Management', 'Renaissance Technologies', 'Appaloosa', 'NVIDIA Corp',
  'Himalaya Capital Management', 'Coatue Management', 'Tiger Global Management',
  'Baker Bros Advisors', 'The Baupost Group', 'Citadel Advisors', 'Whale Rock Capital Management',
  'The Vanguard Group', 'D1 Capital Partners', 'Baillie Gifford & Company', 'Lone Pine Capital',
  'Soros Fund Management', 'Praetorian PR', 'Dalal Street', 'Viking Global Investors', 'Alphabet',
  'JPMorgan Chase & Company', 'Millennium Management', 'H&H International Investment',
  'Third Point', 'Surgocap Partners', 'Thiel Macro', 'RA Capital Management', 'Fundsmith',
  'Jane Street Group', 'Gates Foundation Trust', 'Goldman Sachs Group', 'Durable Capital Partners',
  'Value Aligned Research Advisors', 'Akre Capital Management', 'Valley Forge Capital Management',
  'Fidelity Investments Money Management', 'Maverick Capital', 'Norges Bank', 'Perceptive Advisors',
  'AQR Capital Management',
];

const MANAGER_RANK = new Map(MANAGER_HIERARCHY.map((name, index) => [name, index]));

function ManagerMark({ manager }) {
  const mark = String(manager.display_name || 'AGI').split(/\s+/).map((word) => word[0]).join('').slice(0, 3);
  const domain = MANAGER_DOMAINS[manager.display_name];
  return (
    <div className="relative grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl border border-cyan-100/15 bg-gradient-to-br from-[#444444] to-[#222222] text-xs font-bold text-white shadow-[0_8px_22px_rgba(5,31,42,.2)]">
      <span className="absolute inset-x-2 top-1.5 h-px bg-[#aaaaaa]" />
      <span aria-hidden="true">{mark}</span>
      {domain ? (
        <img
          src={`https://www.google.com/s2/favicons?domain_url=https://${domain}&sz=128`}
          alt={`${manager.display_name} logo`}
          loading="lazy"
          referrerPolicy="no-referrer"
          className="absolute inset-0 h-full w-full bg-white object-contain p-1.5"
          onError={(event) => { event.currentTarget.style.display = 'none'; }}
        />
      ) : null}
    </div>
  );
}

function AumSparkline({ history = [] }) {
  const [hovered, setHovered] = useState(null);
  const source = history.filter((row) => Number.isFinite(Number(row?.total_value_usd))).slice(-12);
  if (!source.length) return <span className="text-[10px] text-slate-400">No history</span>;

  const width = 154;
  const height = 48;
  const pad = 5;
  const values = source.map((row) => Number(row.total_value_usd));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || Math.max(max, 1);
  const points = source.map((row, index) => ({
    row,
    x: source.length === 1 ? width / 2 : pad + (index * (width - pad * 2)) / (source.length - 1),
    y: height - pad - ((Number(row.total_value_usd) - min) / range) * (height - pad * 2),
  }));
  const line = points.map((point, index) => `${index ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ');
  const area = `${line} L ${points.at(-1).x} ${height - pad} L ${points[0].x} ${height - pad} Z`;
  const active = hovered === null ? null : points[hovered];

  return (
    <div className="relative w-[154px]" onMouseLeave={() => setHovered(null)}>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-12 w-full overflow-visible" role="img" aria-label="Quarterly 13F assets under management">
        <path d={area} fill="rgba(58,170,171,.13)" />
        <path d={line} fill="none" stroke="#999999" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((point, index) => (
          <circle key={`${point.row.report_date}-${index}`} cx={point.x} cy={point.y} r={hovered === index ? 4 : 6} fill={hovered === index ? '#aaaaaa' : 'transparent'} stroke={hovered === index ? '#fff' : 'transparent'} strokeWidth="2" className="cursor-crosshair" onMouseEnter={() => setHovered(index)} />
        ))}
      </svg>
      {active ? (
        <div className="pointer-events-none absolute bottom-[54px] z-30 min-w-[112px] -translate-x-1/2 rounded border border-[#aaaaaa]/40 bg-[#222222] px-2.5 py-2 text-left shadow-xl" style={{ left: `${Math.min(82, Math.max(18, (active.x / width) * 100))}%` }}>
          <div className="text-[9px] font-bold uppercase tracking-[.16em] text-[#aaaaaa]">{active.row.report_date}</div>
          <div className="mt-1 text-xs font-bold text-white">{money(active.row.total_value_usd)}</div>
          <div className="text-[9px] text-slate-400">{number(active.row.holdings_count)} holdings</div>
        </div>
      ) : null}
    </div>
  );
}

function PortfolioDonut({ positions = [] }) {
  const [hovered, setHovered] = useState(null);
  const colors = ['#999999', '#aaaaaa', '#777777', '#444444'];
  const named = positions.slice(0, 3).map((position) => ({ label: position.ticker || position.issuer_name || 'Position', value: Math.max(0, Number(position.portfolio_weight) || 0) }));
  if (!named.length) return <span className="text-[10px] text-slate-400">No positions</span>;

  const used = Math.min(100, named.reduce((sum, item) => sum + item.value, 0));
  const segments = [...named, { label: 'Other', value: Math.max(0, 100 - used) }].filter((item) => item.value > 0);
  const circumference = 2 * Math.PI * 17;
  let offset = 0;
  const active = hovered === null ? null : segments[hovered];

  return (
    <div className="relative flex w-[94px] justify-center" onMouseLeave={() => setHovered(null)}>
      <svg viewBox="0 0 44 44" className="h-12 w-12 -rotate-90" role="img" aria-label="Portfolio concentration by top positions">
        {segments.map((segment, index) => {
          const dash = (Math.min(segment.value, 100) / 100) * circumference;
          const dashOffset = -offset;
          offset += dash;
          return <circle key={`${segment.label}-${index}`} cx="22" cy="22" r="17" fill="none" stroke={colors[index]} strokeWidth={hovered === index ? 10 : 8} strokeDasharray={`${dash} ${circumference - dash}`} strokeDashoffset={dashOffset} className="cursor-pointer transition-all" onMouseEnter={() => setHovered(index)} />;
        })}
      </svg>
      {active ? (
        <div className="pointer-events-none absolute bottom-[54px] z-30 min-w-[104px] rounded border border-[#aaaaaa]/40 bg-[#222222] px-2.5 py-2 text-center shadow-xl">
          <div className="text-[9px] font-bold uppercase tracking-[.12em] text-[#aaaaaa]">{active.label}</div>
          <div className="mt-1 text-xs font-bold text-white">{active.value.toFixed(1)}%</div>
        </div>
      ) : null}
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
        <table className="w-full min-w-[1320px] text-left">
          <thead className="bg-[#333333] text-[9px] font-extrabold uppercase tracking-[.15em] text-[#bbbbbb]">
            <tr>
              <th className="w-12 px-4 py-4" aria-label="Expand holdings" />
              <th className="px-3 py-4">Institutional manager</th>
              <th className="px-3 py-4">Latest 13F</th>
              <th className="px-3 py-4">Earliest coverage</th>
              <th className="px-3 py-4">Location</th>
              <th className="px-3 py-4 text-right">13F AUM</th>
              <th className="px-3 py-4 text-center">Concentration</th>
              <th className="px-3 py-4 text-right">Holdings</th>
              <th className="px-5 py-4">Filing status</th>
            </tr>
          </thead>
          <tbody>
            {[...funds].sort((a, b) => (MANAGER_RANK.get(a.display_name) ?? 999) - (MANAGER_RANK.get(b.display_name) ?? 999)).map((fund) => {
              const expanded = expandedSlug === fund.slug;
              const detail = details[fund.slug];
              const changes = new Map((detail?.changes || []).map((row) => [row.cusip, row]));
              const filtered = (detail?.holdings || []).filter((row) => `${row.ticker || ''} ${row.issuer_name || ''} ${row.cusip || ''}`.toLowerCase().includes(holdingQuery.toLowerCase()));
              const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
              const pageRows = filtered.slice((holdingPage - 1) * PAGE_SIZE, holdingPage * PAGE_SIZE);
              const location = [fund.city, fund.state, fund.country].filter(Boolean).join(', ');
              return [
                <tr key={fund.slug} className={`border-t border-[#eeeeee] transition ${expanded ? 'bg-[#eeeeee]' : 'hover:bg-[#ffffff]'}`}>
                  <td className="px-4 py-4 align-middle">
                    <button onClick={() => toggle(fund)} className="grid h-8 w-8 place-items-center rounded-lg border border-[#dddddd] bg-white text-[#444444] transition hover:border-[#888888]" aria-expanded={expanded} aria-label={`${expanded ? 'Hide' : 'Show'} ${fund.display_name} holdings`}>
                      <ChevronRight className={`h-4 w-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
                    </button>
                  </td>
                  <td className="px-3 py-4">
                    <div className="flex items-center gap-3"><ManagerMark manager={fund} /><div><Link to={`/institutional-holdings/funds/${fund.slug}`} className="text-base font-bold text-[#333333] hover:text-[#666666]">{fund.display_name}</Link><p className="mt-1 text-[10px] text-[#888888]">{fund.manager_type || fund.strategy}</p></div></div>
                  </td>
                  <td className="px-3 py-4 text-xs font-bold text-[#444444]">{fund.latest_filing?.report_date || 'Pending'}</td>
                  <td className="px-3 py-4 text-xs text-[#777777]">{fund.earliest_report_date || 'Pending'}</td>
                  <td className="px-3 py-4"><div className="flex max-w-[210px] items-start gap-2 text-xs text-[#777777]"><MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#777777]" /><span>{location || 'SEC address pending'}{fund.postal_code ? ` ${fund.postal_code}` : ''}</span></div></td>
                  <td className="px-3 py-4"><div className="flex flex-col items-end"><span className="mb-1 text-[10px] font-bold text-[#333333]">{fund.latest_filing ? money(fund.latest_filing.total_value_usd) : '--'}</span><AumSparkline history={fund.filing_history} /></div></td>
                  <td className="px-3 py-4"><PortfolioDonut positions={fund.top_positions} /></td>
                  <td className="px-3 py-4 text-right text-sm font-bold">{fund.position_count || 0}</td>
                  <td className="px-5 py-4"><span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[9px] font-extrabold uppercase tracking-[.1em] ${fund.last_refresh_status === 'success' ? 'bg-emerald-100 text-emerald-800' : fund.last_refresh_status === 'error' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{fund.last_refresh_status || 'queued'}</span></td>
                </tr>,
                expanded ? (
                  <tr key={`${fund.slug}-holdings`} className="border-t border-[#dddddd] bg-[#ffffff]">
                    <td colSpan="9" className="p-0">
                      <div className="border-l-4 border-[#888888] px-5 py-6 sm:px-8">
                        {loadingSlug === fund.slug ? <div className="flex items-center justify-center gap-3 py-14 text-sm text-[#777777]"><Loader2 className="h-5 w-5 animate-spin" /> Loading latest SEC holdings</div> : loadError && !detail ? <p className="py-10 text-center text-sm text-rose-700">{loadError}</p> : detail ? (
                          <>
                            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                              <div><p className="text-[9px] font-extrabold uppercase tracking-[.18em] text-[#777777]">Taken from latest 13F filing</p><h3 className="mt-2 text-2xl font-bold">{fund.display_name} holdings</h3><p className="mt-1 text-xs text-[#777777]">Report quarter {detail.latest_filing?.report_date} · Public {String(detail.latest_filing?.filed_at || '').slice(0, 10)} · {filtered.length} matching positions</p></div>
                              <div className="flex flex-col gap-3 sm:flex-row">
                                <label className="flex items-center gap-2 rounded-xl border border-[#dddddd] bg-white px-3"><Search className="h-4 w-4 text-[#888888]" /><input value={holdingQuery} onChange={(event) => { setHoldingQuery(event.target.value); setHoldingPage(1); }} placeholder="Filter ticker or company" className="w-56 bg-transparent py-3 text-xs outline-none" /></label>
                                <Link to={`/institutional-holdings/funds/${fund.slug}`} className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#333333] px-4 py-3 text-xs font-bold text-white">Full manager profile <ExternalLink className="h-3.5 w-3.5" /></Link>
                              </div>
                            </div>
                            <div className="mt-5 overflow-x-auto rounded-xl border border-[#dddddd] bg-white">
                              <table className="w-full min-w-[1060px] text-left">
                                <thead className="bg-[#333333] text-[9px] font-extrabold uppercase tracking-[.13em] text-[#cccccc]"><tr><th className="px-4 py-3">Security</th><th className="px-4 py-3">Class</th><th className="px-4 py-3 text-right">Shares</th><th className="px-4 py-3 text-right">Market value</th><th className="px-4 py-3 text-right">Portfolio</th><th className="px-4 py-3 text-right">Previous</th><th className="px-4 py-3 text-right">Rank</th><th className="px-4 py-3 text-right">Share change</th><th className="px-4 py-3 text-right">Change %</th><th className="px-4 py-3">Signal</th></tr></thead>
                                <tbody>{pageRows.map((row, index) => { const change = changes.get(row.cusip); return <tr key={`${row.id || row.cusip}-${index}`} className="border-t border-[#eeeeee] text-xs hover:bg-[#ffffff]"><td className="px-4 py-3"><Link to={`/institutional-holdings/stocks/${row.ticker || row.cusip}`} className="font-bold text-[#555555] hover:underline">{row.ticker || row.cusip}</Link><span className="block max-w-[220px] truncate text-[10px] text-[#888888]">{row.issuer_name}</span></td><td className="px-4 py-3 text-[#777777]">{row.title_of_class || 'Security'}{row.put_call ? ` / ${row.put_call}` : ''}</td><td className="px-4 py-3 text-right font-medium">{number(row.shares)}</td><td className="px-4 py-3 text-right font-bold">{money(row.value_usd)}</td><td className="px-4 py-3 text-right font-bold">{percent(row.portfolio_weight)}</td><td className="px-4 py-3 text-right text-[#777777]">{change ? percent(change.previous_weight) : '--'}</td><td className="px-4 py-3 text-right font-bold">{(holdingPage - 1) * PAGE_SIZE + index + 1}</td><td className={`px-4 py-3 text-right font-bold ${Number(change?.share_change || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>{change ? number(change.share_change) : '--'}</td><td className="px-4 py-3 text-right">{change?.share_change_pct == null ? '--' : percent(change.share_change_pct)}</td><td className="px-4 py-3"><ChangeBadge change={change} /></td></tr>; })}</tbody>
                              </table>
                              {!pageRows.length ? <div className="flex items-center justify-center gap-2 py-12 text-sm text-[#777777]"><FileClock className="h-4 w-4" /> No holdings match this filter.</div> : null}
                            </div>
                            <div className="mt-4 flex flex-col gap-3 text-xs text-[#777777] sm:flex-row sm:items-center sm:justify-between"><span>Rows {(holdingPage - 1) * PAGE_SIZE + (pageRows.length ? 1 : 0)}–{Math.min(holdingPage * PAGE_SIZE, filtered.length)} of {filtered.length}</span><div className="flex items-center gap-2"><button disabled={holdingPage <= 1} onClick={() => setHoldingPage((page) => Math.max(1, page - 1))} className="rounded-lg border border-[#cccccc] bg-white px-3 py-2 font-bold disabled:opacity-40">Previous</button><span className="px-2 font-bold">{holdingPage} / {pageCount}</span><button disabled={holdingPage >= pageCount} onClick={() => setHoldingPage((page) => Math.min(pageCount, page + 1))} className="rounded-lg border border-[#cccccc] bg-white px-3 py-2 font-bold disabled:opacity-40">Next</button></div></div>
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
      {!funds.length ? <p className="p-10 text-center text-sm text-[#777777]">No institutional managers match this search.</p> : null}
    </div>
  );
}
