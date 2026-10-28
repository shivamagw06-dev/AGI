/**
 * IAX — Institutional Answer Experience workspace.
 * Preserves AGI editorial visual language. No engine names.
 */
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, Copy, Download, Link2, Share2 } from 'lucide-react';
import { getFavouriteCompanies, toggleFavouriteCompany } from '@/lib/searchHistory';

function Block({ id, title, children, className = '' }) {
  return (
    <section id={id} className={`border border-[#dddddd] p-5 bg-white scroll-mt-24 ${className}`}>
      <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
      <div className="mt-3 text-sm text-[#333333] leading-relaxed">{children}</div>
    </section>
  );
}

function List({ items, empty = 'None listed yet.' }) {
  const rows = (items || []).filter(Boolean);
  if (!rows.length) return <p className="text-xs text-[#929292]">{empty}</p>;
  return (
    <ul className="space-y-2">
      {rows.map((item, idx) => (
        <li key={item.id || item.title || item || idx} className="border-b border-[#eeeeee] pb-2 last:border-0">
          {typeof item === 'string' ? <span>• {item}</span> : (
            <>
              <p className="font-bold text-[#111]">{item.title || item.id}</p>
              {(item.summary || item.snippet) && (
                <p className="text-xs text-[#767676] mt-1">{item.summary || item.snippet}</p>
              )}
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

function fmtConfidence(value) {
  if (value == null) return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  return n <= 1 ? `${Math.round(n * 100)}%` : `${Math.round(n)}%`;
}

function asPlainText(value, fallback = '') {
  if (value == null) return fallback;
  if (typeof value === 'object') {
    const nested = value.thesis || value.summary || value.snippet || value.title || value.stance;
    return asPlainText(nested, fallback);
  }
  const text = String(value).replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
  if (!text || text.startsWith('{') || text.includes("'document_id'") || text.includes('"document_id"')) {
    return fallback;
  }
  if (/^doc_[a-z0-9]+$/i.test(text)) return fallback;
  return text;
}

function asStance(value) {
  if (value && typeof value === 'object') {
    const thesis = asPlainText(value.thesis || value.summary, '');
    const blob = thesis.toLowerCase();
    if (/(weak growth|slower deal|macro challenge|pressure|muted|headwind|demand weakness)/.test(blob)) {
      return 'Bearish';
    }
    if (/(upgrade|overweight|acceleration|strong demand|reacceleration)/.test(blob)) {
      return 'Bullish';
    }
    return 'Neutral';
  }
  const raw = asPlainText(value, '');
  if (!raw) return 'Neutral';
  const s = raw.toLowerCase();
  // Do not treat field names like "bull_case" as Bullish.
  if (s.includes('bull_case') || s.includes('bear_case') || s.includes('document_id')) {
    return asStance({ thesis: raw });
  }
  if (/\bbearish\b|\bunderweight\b|\bdowngrade\b|\bsell\b/.test(s)) return 'Bearish';
  if (/\bbullish\b|\boverweight\b|\bupgrade\b|\bbuy\b/.test(s)) return 'Bullish';
  if (s === 'bear') return 'Bearish';
  if (s === 'bull') return 'Bullish';
  return 'Neutral';
}

function stanceTone(stance = '') {
  const s = String(stance).toLowerCase();
  if (s.includes('bull')) return 'bg-[#e8f5e9] text-[#1b5e20] border-[#a5d6a7]';
  if (s.includes('bear')) return 'bg-[#ffebee] text-[#b71c1c] border-[#ef9a9a]';
  return 'bg-[#fff8e1] text-[#f57f17] border-[#ffe082]';
}

function evidenceHref(item) {
  if (item?.href) return item.href;
  const type = String(item?.type || '').toLowerCase();
  const id = item?.id;
  if (id && (type.includes('article') || type.includes('agi') || type.includes('research'))) {
    return `/article/${encodeURIComponent(id)}`;
  }
  const ticker = (item?.tickers || [])[0];
  if (ticker) return `/research/stocks/${encodeURIComponent(ticker)}`;
  return null;
}

function EvidenceCard({ item }) {
  const href = evidenceHref(item);
  const body = (
    <>
      <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[#767676]">
        <span>{item.type || 'research'}</span>
        <span>·</span>
        <span>{item.source || 'institutional'}</span>
        {item.date && (
          <>
            <span>·</span>
            <span>{String(item.date).slice(0, 10)}</span>
          </>
        )}
        {item.reliability && (
          <>
            <span>·</span>
            <span>Reliability {item.reliability}</span>
          </>
        )}
      </div>
      <p className="mt-2 text-sm font-bold text-[#111]">
        {asPlainText(item.title, asPlainText(item.summary, 'Research note'))}
      </p>
      {asPlainText(item.summary, '') &&
        asPlainText(item.summary, '') !== asPlainText(item.title, '') && (
        <p className="mt-1 text-xs text-[#555] leading-relaxed">{asPlainText(item.summary, '')}</p>
      )}
      {item.confidence != null && (
        <p className="mt-2 text-[11px] text-[#767676]">Confidence {fmtConfidence(item.confidence)}</p>
      )}
      {(item.tickers || [])
        .filter((t) => typeof t === 'string' && !/^(SERVICES|GLOBAL|UPDATE|OUTLOOK|EARNINGS|CONTINUES|AMP|HIS|IMPLICATIONS|RESEARCH|INDIA|INDIAN|MARKET|SECTOR|GROWTH)$/i.test(t))
        .slice(0, 3)
        .map((t) => (
        <span key={t} className="inline-block mt-2 mr-2 text-[11px] font-bold text-[#111]">
          {t}
        </span>
      ))}
    </>
  );

  if (href?.startsWith('http')) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className="block border border-[#eeeeee] p-3 hover:border-[#111]">
        {body}
      </a>
    );
  }
  if (href) {
    return (
      <Link to={href} className="block border border-[#eeeeee] p-3 hover:border-[#111]">
        {body}
      </Link>
    );
  }
  return <article className="border border-[#eeeeee] p-3">{body}</article>;
}

function Toc({ items }) {
  return (
    <nav aria-label="Answer sections" className="hidden lg:block sticky top-24 border border-[#dddddd] p-4 bg-white">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">On this page</p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.id}>
            <a href={`#${item.id}`} className="text-xs text-[#333] hover:text-[#ff6600]">
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export default function InstitutionalAnswer({ pack, onFollowUp, onContinue, onSave }) {
  const [copied, setCopied] = useState(false);
  const [favs, setFavs] = useState(() => getFavouriteCompanies());

  const house = pack?.house_view_card || {};
  const stance = asStance(house.stance || pack?.answer?.house_view_label || 'Neutral');
  const ticker = pack?.entities?.ticker;
  const changed = pack?.whats_changed || {};
  const thesis = pack?.current_thesis || {};
  const research = pack?.research_panel || {};
  const kg = pack?.knowledge_graph?.buckets || {};
  const ideas = pack?.related_ideas || {};
  const portfolio = pack?.portfolio_context || {};
  const charts = pack?.charts || [];
  const mi = pack?.market_intelligence || [];
  const executiveSummary = asPlainText(
    pack?.executive_summary || pack?.answer?.summary,
    'Institutional evidence pack. Not investment advice.'
  );
  const whyItems = (pack?.why || [])
    .map((w) => asPlainText(w, ''))
    .filter(Boolean);
  const thesisSummary = asPlainText(thesis.summary || pack?.investment_thesis, '');
  const briefing = pack?.institutional_briefing || {};
  const sectorIntel = pack?.sector_intelligence || {};
  const irpMeta = pack?.irp || {};
  const outlook = asPlainText(pack?.current_outlook || briefing.current_outlook, '');
  const keyDrivers = pack?.key_drivers || briefing.key_drivers || [];
  const macroDrivers = pack?.macro_drivers || briefing.macro_drivers || [];
  const sectorDrivers = pack?.sector_drivers || briefing.sector_drivers || [];
  const companyLeaders = pack?.company_leaders || briefing.company_leaders || [];
  const valuationPerspective = asPlainText(
    pack?.valuation_perspective || briefing.valuation_perspective || thesis.valuation,
    ''
  );
  const historicalComparison = asPlainText(
    pack?.historical_comparison || briefing.historical_comparison,
    ''
  );

  const toc = useMemo(
    () => [
      { id: 'iax-summary', label: 'Executive Summary' },
      { id: 'iax-house', label: 'House View' },
      { id: 'iax-outlook', label: 'Outlook & Drivers' },
      { id: 'iax-changed', label: "What's Changed" },
      { id: 'iax-thesis', label: 'Current Thesis' },
      { id: 'iax-sector', label: 'Sector Intelligence' },
      { id: 'iax-evidence', label: 'Evidence' },
      { id: 'iax-research', label: 'Research' },
      { id: 'iax-timeline', label: 'Timeline' },
      { id: 'iax-charts', label: 'Charts' },
      { id: 'iax-graph', label: 'Knowledge Graph' },
      { id: 'iax-market', label: 'Market Intelligence' },
      { id: 'iax-related', label: 'Related Ideas' },
      { id: 'iax-followups', label: 'Follow-ups' },
    ],
    []
  );

  if (!pack) return null;

  const shareUrl = typeof window !== 'undefined' ? window.location.href : '';

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  const briefingText = () =>
    [
      `Ask AGI — Institutional Answer`,
      `Question: ${pack.question}`,
      `House view: ${stance}`,
      `Confidence: ${fmtConfidence(pack.confidence)}`,
      `Market regime: ${pack.market_regime || '—'}`,
      `Last updated: ${pack.last_updated || '—'}`,
      '',
      executiveSummary || '',
      '',
      `Thesis: ${thesisSummary || ''}`,
      '',
      'Why:',
      ...whyItems.map((w) => `- ${w}`),
      '',
      "What's changed:",
      ...((changed.items || []).map((i) => `- ${i.label}: ${i.detail}`)),
      '',
      'Follow-ups:',
      ...(pack.follow_up_questions || []).map((q) => `- ${q}`),
      '',
      'Not investment advice. Agarwal Global Investments.',
    ].join('\n');

  const exportText = () => {
    const blob = new Blob([briefingText()], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agi-answer-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPdf = () => {
    // Browser print-to-PDF keeps institutional layout without new dependencies.
    window.print();
  };

  return (
    <div className="lg:grid lg:grid-cols-12 lg:gap-6">
      <div className="lg:col-span-3 order-2 lg:order-1 mb-6 lg:mb-0">
        <Toc items={toc} />
      </div>

      <div className="lg:col-span-9 order-1 lg:order-2 space-y-4">
        {/* Export / share bar */}
        <div className="flex flex-wrap gap-2 border border-[#dddddd] p-3 bg-[#fafafa]">
          <button type="button" onClick={copyLink} className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]">
            <Link2 className="w-3.5 h-3.5" /> {copied ? 'Copied' : 'Copy link'}
          </button>
          <button type="button" onClick={exportText} className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]">
            <Download className="w-3.5 h-3.5" /> Export
          </button>
          <button type="button" onClick={exportPdf} className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]">
            <Download className="w-3.5 h-3.5" /> Export PDF
          </button>
          <button
            type="button"
            onClick={() => {
              if (navigator.share) navigator.share({ title: pack.question, url: shareUrl }).catch(() => {});
              else copyLink();
            }}
            className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]"
          >
            <Share2 className="w-3.5 h-3.5" /> Share research
          </button>
          {ticker && (
            <button
              type="button"
              onClick={() => setFavs(toggleFavouriteCompany(ticker))}
              className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]"
            >
              <Bookmark className="w-3.5 h-3.5" />
              {favs.includes(ticker) ? 'Saved company' : 'Bookmark company'}
            </button>
          )}
          <button
            type="button"
            onClick={() => onSave?.(pack)}
            className="inline-flex items-center gap-1.5 text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:border-[#111]"
          >
            <Copy className="w-3.5 h-3.5" /> Save answer
          </button>
        </div>

        <header className="border border-[#dddddd] border-l-4 border-l-[#ff6600] bg-[#fafafa] p-5">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#ff6600]">Question</p>
          <h1 className="mt-2 text-2xl md:text-3xl font-bold text-[#111111] leading-tight">{pack.question}</h1>
          {pack.intent && (
            <p className="mt-2 text-xs text-[#767676]">
              Intent: {String(pack.intent).replace(/_/g, ' ')}
              {irpMeta.domain ? ` · Domain: ${String(irpMeta.domain).replace(/_/g, ' ')}` : ''}
              {pack.workspace?.programme ? ` · ${pack.workspace.programme}` : ''}
            </p>
          )}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div className="border border-[#eee] bg-white p-2">
              <p className="text-[#767676] uppercase font-bold">AGI view</p>
              <p className="font-bold text-[#111] mt-1">{stance}</p>
            </div>
            <div className="border border-[#eee] bg-white p-2">
              <p className="text-[#767676] uppercase font-bold">Why</p>
              <p className="font-bold text-[#111] mt-1 line-clamp-2">{whyItems[0] || outlook || 'See evidence'}</p>
            </div>
            <div className="border border-[#eee] bg-white p-2">
              <p className="text-[#767676] uppercase font-bold">Evidence</p>
              <p className="font-bold text-[#111] mt-1">{(pack.supporting_evidence || []).length} items</p>
            </div>
            <div className="border border-[#eee] bg-white p-2">
              <p className="text-[#767676] uppercase font-bold">Explore next</p>
              <p className="font-bold text-[#111] mt-1">{(pack.follow_up_questions || []).length} follow-ups</p>
            </div>
          </div>
        </header>

        <Block id="iax-summary" title="Executive Summary">
          <p className="text-base text-[#222]">{executiveSummary}</p>
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Current stance</p>
              <p className={`mt-1 inline-flex border px-2 py-0.5 text-xs font-bold ${stanceTone(stance)}`}>{stance}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Market regime</p>
              <p className="mt-1 text-sm font-bold text-[#111]">{pack.market_regime || '—'}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Last updated</p>
              <p className="mt-1 text-sm font-bold text-[#111]">{pack.last_updated || '—'}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Freshness</p>
              <p className="mt-1 text-sm font-bold text-[#111] capitalize">{pack.freshness_indicator || '—'}</p>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-[#929292]">Institutional briefing — not a buy/sell instruction.</p>
        </Block>

        <Block id="iax-house" title="Current House View">
          <div className="grid grid-cols-3 gap-2 mb-4">
            {['Bullish', 'Neutral', 'Bearish'].map((s) => (
              <div
                key={s}
                className={`border p-3 text-center text-sm font-bold ${
                  stance === s ? stanceTone(s) : 'border-[#eee] text-[#999]'
                }`}
              >
                {s}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Confidence</p>
              <p className="mt-1 text-lg font-bold">{fmtConfidence(house.confidence ?? pack.confidence)}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Horizon</p>
              <p className="mt-1 text-sm font-bold capitalize">{house.investment_horizon || '—'}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Conviction</p>
              <p className="mt-1 text-sm font-bold capitalize">{house.conviction || '—'}</p>
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Change</p>
              <p className="mt-1 text-xs font-bold line-clamp-3">
                {house.change_since_last_update || changed.summary || 'Stable'}
              </p>
            </div>
          </div>
        </Block>

        <Block id="iax-outlook" title="Current Outlook & Key Drivers">
          {outlook ? <p className="mb-3">{outlook}</p> : null}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Key drivers</p>
              <List items={keyDrivers} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Macro drivers</p>
              <List items={macroDrivers} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Sector drivers</p>
              <List items={sectorDrivers} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Valuation perspective</p>
              <p className="mt-2 text-sm">{valuationPerspective || '—'}</p>
              {historicalComparison ? (
                <p className="mt-2 text-xs text-[#767676]">{historicalComparison}</p>
              ) : null}
            </div>
          </div>
          {companyLeaders.length > 0 && (
            <div className="mt-3 border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Company leaders</p>
              <List items={companyLeaders} />
            </div>
          )}
        </Block>

        <Block id="iax-changed" title="What's Changed">
          <p className="text-sm text-[#333] mb-3">{changed.summary}</p>
          <ul className="space-y-2">
            {(changed.items || []).map((item, idx) => (
              <li key={idx} className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#ff6600]">{item.label}</p>
                <p className="text-sm mt-1">{item.detail}</p>
              </li>
            ))}
          </ul>
          {(changed.buckets?.new_risks || []).length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-bold uppercase text-[#767676]">New risks</p>
              <List items={changed.buckets.new_risks} />
            </div>
          )}
          {(changed.buckets?.new_catalysts || []).length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">New catalysts</p>
              <List items={changed.buckets.new_catalysts} />
            </div>
          )}
        </Block>

        <Block id="iax-thesis" title="Current Thesis">
          {thesisSummary ? <p className="mb-4">{thesisSummary}</p> : null}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#087443]">Bull case</p>
              <List items={thesis.bull_case || pack.bull_case} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#b42318]">Bear case</p>
              <List items={thesis.bear_case || pack.bear_case} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#966a00]">Neutral case</p>
              <List items={thesis.neutral_case} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Time horizon</p>
              <p className="mt-2 font-bold capitalize">{thesis.time_horizon || house.investment_horizon || '—'}</p>
              {thesis.valuation && <p className="mt-2 text-xs">{String(thesis.valuation)}</p>}
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Catalysts</p>
              <List items={thesis.catalysts || pack.key_catalysts} />
            </div>
            <div className="border border-[#eee] p-3">
              <p className="text-[10px] font-bold uppercase text-[#767676]">Risks</p>
              <List items={thesis.risks || pack.key_risks} />
            </div>
          </div>
        </Block>

        {(sectorIntel.sector_overview || sectorIntel.top_companies?.length) ? (
          <Block id="iax-sector" title="Sector Intelligence">
            {sectorIntel.sector_overview ? (
              <p className="mb-3 font-bold text-[#111]">{sectorIntel.sector_overview}</p>
            ) : null}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">Top companies</p>
                <List
                  items={(sectorIntel.top_companies || []).map((c) =>
                    typeof c === 'string' ? c : `${c.ticker || ''} — ${c.name || ''}`.trim()
                  )}
                />
              </div>
              <div className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">Demand / competitive notes</p>
                <List items={sectorIntel.demand_drivers || sectorIntel.competitive_landscape || []} />
              </div>
              <div className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">Countries / themes</p>
                <List
                  items={[
                    ...((sectorIntel.countries || []).map((c) => `Country: ${c}`)),
                    ...((sectorIntel.themes || []).map((t) => `Theme: ${t}`)),
                    ...((sectorIntel.currencies || []).map((c) => `FX: ${c}`)),
                  ]}
                />
              </div>
              <div className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">AGI sector view</p>
                <p className="mt-2 text-sm font-bold">{sectorIntel.current_agi_view || stance}</p>
                <p className="mt-2 text-xs text-[#555]">{asPlainText(sectorIntel.outlook, outlook)}</p>
              </div>
            </div>
          </Block>
        ) : null}

        <div id="iax-evidence" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Block title="Supporting Evidence">
            <div className="space-y-2">
              {(pack.supporting_evidence || []).map((item, idx) => (
                <EvidenceCard key={item.id || idx} item={item} />
              ))}
              {(pack.supporting_evidence || []).length === 0 && (
                <p className="text-xs text-[#929292]">Supporting evidence will appear as knowledge is retrieved.</p>
              )}
            </div>
          </Block>
          <Block title="Conflicting Evidence">
            <div className="space-y-2">
              {(pack.conflicting_evidence || []).map((item, idx) => (
                <EvidenceCard key={item.id || idx} item={item} />
              ))}
              {(pack.conflicting_evidence || []).length === 0 && (
                <p className="text-xs text-[#929292]">No material conflicts retrieved.</p>
              )}
            </div>
          </Block>
        </div>

        <Block id="iax-research" title="Research Panel">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              ['Latest AGI Research', research.latest_agi_research],
              ['Most Relevant Research', research.most_relevant_research],
              ['Historical Research', research.historical_research],
              ['Latest Broker Research', research.latest_broker_research],
              ['Latest Filings', research.latest_filings],
              ['Latest Earnings', research.latest_earnings],
            ].map(([label, items]) => (
              <div key={label} className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676] mb-2">{label}</p>
                <List items={items} />
              </div>
            ))}
          </div>
        </Block>

        <Block id="iax-timeline" title="Knowledge Timeline">
          <ol className="space-y-3">
            {(pack.knowledge_timeline || []).slice(0, 16).map((ev, idx) => (
              <li key={idx} className="border-l-2 border-[#ff6600] pl-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">
                  {ev.as_of ? String(ev.as_of).slice(0, 10) : 'Undated'} · {ev.type || 'event'}
                </p>
                <p className="text-sm font-bold text-[#111] mt-0.5">{ev.title}</p>
                {ev.summary && <p className="text-xs text-[#555] mt-1">{ev.summary}</p>}
              </li>
            ))}
            {(pack.knowledge_timeline || []).length === 0 && (
              <p className="text-xs text-[#929292]">Timeline populates as knowledge is ingested.</p>
            )}
          </ol>
        </Block>

        <Block id="iax-charts" title="Charts">
          {(charts || []).length === 0 ? (
            <p className="text-xs text-[#929292]">
              Charts appear when research and prediction timelines are available for this question.
            </p>
          ) : (
            <div className="space-y-3">
              {charts.map((chart) => (
                <div key={chart.id} className="border border-[#eee] p-3">
                  <p className="text-sm font-bold text-[#111]">{chart.title}</p>
                  <p className="text-[11px] text-[#767676] mt-1">{chart.answers}</p>
                  <ul className="mt-3 space-y-1">
                    {(chart.points || []).slice(0, 8).map((p, idx) => (
                      <li key={idx} className="text-xs border-b border-[#f3f3f3] py-1 flex justify-between gap-3">
                        <span className="text-[#767676]">{p.as_of ? String(p.as_of).slice(0, 10) : '—'}</span>
                        <span className="font-bold text-[#111] text-right">{p.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Block>

        <Block id="iax-graph" title="Knowledge Graph">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(kg).map(([key, vals]) => (
              <div key={key} className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676] mb-2">{key.replace(/_/g, ' ')}</p>
                <div className="flex flex-wrap gap-1">
                  {(vals || []).slice(0, 6).map((v) => (
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
                  {(vals || []).length === 0 && <span className="text-[11px] text-[#929292]">—</span>}
                </div>
              </div>
            ))}
          </div>
        </Block>

        <Block id="iax-market" title="Market Intelligence">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {mi.map((row) => (
              <div key={row.dimension} className="border border-[#eee] p-3">
                <p className="text-[10px] font-bold uppercase text-[#767676]">{row.dimension}</p>
                <p className="mt-1 text-sm font-bold text-[#111]">{row.status}</p>
                <p className="mt-1 text-xs text-[#555]">{row.explanation}</p>
                {row.confidence != null && (
                  <p className="mt-1 text-[11px] text-[#767676]">Confidence {fmtConfidence(row.confidence)}</p>
                )}
              </div>
            ))}
            {mi.length === 0 && <p className="text-xs text-[#929292]">Intelligence summaries load with company context.</p>}
          </div>
        </Block>

        {(pack.predictions || []).length > 0 && (
          <Block title="Predictions">
            <List
              items={(pack.predictions || []).map((p) => ({
                title: `${p.ticker || ticker || 'Prediction'} · ${String(p.predicted_at || p.as_of || '').slice(0, 10)}`,
                summary: p.thesis || p.horizon || '',
              }))}
            />
          </Block>
        )}

        <Block id="iax-related" title="Related Ideas">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] font-bold uppercase text-[#767676] mb-2">Similar thesis</p>
              <div className="flex flex-wrap gap-2">
                {(ideas.similar_thesis || pack.related_companies || []).map((t) => (
                  <Link key={t} to={`/research/stocks/${encodeURIComponent(t)}`} className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                    {t}
                  </Link>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase text-[#767676] mb-2">Same sector / macro</p>
              <div className="flex flex-wrap gap-2">
                {(ideas.same_sector || pack.related_sectors || []).map((t) => (
                  <Link key={t} to={`/sectors/${encodeURIComponent(t)}`} className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                    {t}
                  </Link>
                ))}
                {(ideas.same_macro_exposure || pack.related_themes || []).map((t) => (
                  <Link key={t} to={`/themes/${encodeURIComponent(t)}`} className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]">
                    {t}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </Block>

        {portfolio && (portfolio.current_exposure != null || Object.keys(portfolio.sector_allocation || {}).length > 0) && (
          <Block title="Portfolio Context">
            <p className="text-xs text-[#767676] mb-2">{portfolio.note}</p>
            <p className="text-sm">
              Current exposure: <span className="font-bold">{portfolio.current_exposure ?? '—'}</span>
            </p>
            {(portfolio.theme_allocation || []).length > 0 && (
              <p className="text-xs mt-2">Themes: {(portfolio.theme_allocation || []).join(', ')}</p>
            )}
          </Block>
        )}

        <Block id="iax-followups" title="Suggested Follow-up Questions">
          <div className="flex flex-wrap gap-2">
            {(pack.follow_up_questions || []).map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => onFollowUp?.(q)}
                className="text-[11px] border border-[#ddd] px-3 py-1.5 hover:border-[#111] hover:text-[#ff6600] text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </Block>

      </div>
    </div>
  );
}
