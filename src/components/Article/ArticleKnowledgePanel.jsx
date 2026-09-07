/**
 * Research note → Intelligence Hub.
 * AGIB v4.0 — every article is a gateway into the institutional knowledge graph.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import DiscoveryRail from '@/components/Product/DiscoveryRail';
import { getUiArticle, getUiCopilot } from '@/lib/uiApi';
import { pushReading } from '@/lib/searchHistory';
import { trackProductEvent } from '@/lib/productAnalytics';

function fmtConf(value) {
  if (value == null) return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  return n <= 1 ? `${Math.round(n * 100)}%` : `${Math.round(n)}%`;
}

function LinkChips({ items, fallbackPath }) {
  if (!items?.length) return <p className="text-xs text-[#929292]">No linked items yet.</p>;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {items.map((item) => {
        const key = item.id || item.label;
        const href = item.href || `${fallbackPath}/${encodeURIComponent(item.id || item.label)}`;
        return (
          <Link
            key={key}
            to={href}
            className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
          >
            {item.label || item.id}
            {item.role ? <span className="ml-1 font-normal text-[#929292]">· {item.role}</span> : null}
          </Link>
        );
      })}
    </div>
  );
}

function HubSection({ title, children }) {
  return (
    <section className="mt-4 border border-[#dddddd] p-4">
      <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function IntelligenceHubView({ hub }) {
  if (!hub || !hub.id) return null;
  const forecast = hub.forecast || {};
  const scenarios = forecast.scenarios || [];
  const dist = forecast.probability_distribution || {};

  return (
    <div className="mt-8">
      <h2 className="text-lg font-bold text-[#111111]">Intelligence Hub</h2>
      <p className="text-xs text-[#767676] mt-1">
        This research note is an Intelligence Object — navigate companies, sectors, macro, markets,
        analogues and forecasts without searching again.
      </p>

      <HubSection title="Executive Summary">
        <ul className="space-y-2">
          {(hub.executive_summary || []).map((line) => (
            <li key={line} className="text-sm text-[#333]">• {line}</li>
          ))}
        </ul>
        {hub.investment_thesis && (
          <p className="mt-3 text-sm text-[#111] border-t border-[#eee] pt-3">{hub.investment_thesis}</p>
        )}
      </HubSection>

      <HubSection title="Why It Matters">
        <ul className="space-y-2">
          {(hub.why_it_matters || []).map((line) => (
            <li key={line} className="text-sm text-[#333]">• {line}</li>
          ))}
        </ul>
      </HubSection>

      <HubSection title="Affected Companies">
        <LinkChips items={hub.companies} fallbackPath="/research/stocks" />
      </HubSection>

      <HubSection title="Affected Sectors">
        <LinkChips items={hub.sectors} fallbackPath="/sectors" />
      </HubSection>

      <HubSection title="Market Impact">
        <LinkChips items={hub.markets} fallbackPath="/markets" />
        {(hub.markets || [])[0]?.meta?.market_regime && (
          <p className="mt-2 text-xs text-[#767676]">
            Regime: {hub.markets[0].meta.market_regime}
            {hub.markets[0].meta.breadth ? ` · Breadth: ${typeof hub.markets[0].meta.breadth === 'string' ? hub.markets[0].meta.breadth : 'linked'}` : ''}
          </p>
        )}
      </HubSection>

      <HubSection title="Macro Impact">
        <LinkChips items={hub.macro_topics} fallbackPath="/macro" />
      </HubSection>

      {(hub.ipo_links || []).length > 0 && (
        <HubSection title="IPO Links">
          <LinkChips items={hub.ipo_links} fallbackPath="/ipo" />
        </HubSection>
      )}

      {(hub.global_topics || []).length > 0 && (
        <HubSection title="Global Links">
          <LinkChips items={hub.global_topics} fallbackPath="/global" />
        </HubSection>
      )}

      <HubSection title="Historical Context">
        <LinkChips items={hub.historical_context} fallbackPath="/history" />
      </HubSection>

      <HubSection title="Key Relationships">
        <ul className="space-y-2">
          {(hub.relationships || []).slice(0, 6).map((r) => (
            <li key={`${r.source}-${r.target}-${r.relationship}`} className="text-xs text-[#333] border-b border-[#eee] pb-1">
              <span className="font-bold">{r.source}</span>
              {' → '}
              <span className="font-bold">{r.target}</span>
              {' · '}
              {r.relationship}
              <span className="text-[#929292]"> · {r.strength} · {r.confidence_pct}%</span>
            </li>
          ))}
        </ul>
      </HubSection>

      <HubSection title="Historical Analogues">
        <ul className="space-y-2">
          {(hub.historical_analogues || []).slice(0, 5).map((a) => (
            <li key={a.matched_period} className="text-xs text-[#333] border-b border-[#eee] pb-1">
              <span className="font-bold">{a.matched_period}</span>
              {a.label ? ` — ${a.label}` : ''}
              <span className="text-[#929292]"> · {Math.round(a.similarity_score)}% similar</span>
              {a.historical_outcome ? <div className="mt-1 text-[#555]">{a.historical_outcome}</div> : null}
            </li>
          ))}
        </ul>
      </HubSection>

      <HubSection title="Bull / Base / Bear Outlook">
        <p className="text-xs text-[#767676] mb-2">
          Distribution: Bull {dist.Bull ?? '—'}% · Base {dist.Base ?? '—'}% · Bear {dist.Bear ?? '—'}%
          {' · '}Horizon {forecast.horizon || '6 Months'}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {scenarios.map((s) => (
            <div key={s.scenario} className="border border-[#eee] p-3">
              <p className="text-sm font-bold text-[#111]">
                {s.scenario} · {s.probability_pct}%
              </p>
              <p className="text-[11px] text-[#767676]">Confidence {s.confidence_pct}%</p>
              <ul className="mt-2 space-y-1">
                {(s.narrative || []).slice(0, 3).map((n) => (
                  <li key={n} className="text-[11px] text-[#333]">• {n}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </HubSection>

      <HubSection title="Supporting Evidence">
        <ul className="space-y-2">
          {(hub.supporting_evidence || []).map((e) => (
            <li key={`${e.kind}-${e.summary}`} className="text-xs text-[#333] border-b border-[#eee] pb-1">
              <span className="font-bold uppercase text-[#767676]">{e.kind}</span>
              {' — '}
              {e.summary}
            </li>
          ))}
        </ul>
      </HubSection>

      {(hub.related_research || []).length > 0 && (
        <HubSection title="Related Research Notes">
          <LinkChips items={hub.related_research} fallbackPath="/research/hub" />
        </HubSection>
      )}
    </div>
  );
}

export default function ArticleKnowledgePanel({ researchId, ticker, title }) {
  const [pack, setPack] = useState(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        if (researchId) {
          const data = await getUiArticle(researchId, ticker || undefined);
          if (active) setPack(data);
          trackProductEvent('research_read', { researchId, title });
          pushReading({
            id: researchId,
            title: title || researchId,
            href: `/article/${encodeURIComponent(researchId)}`,
          });
          return;
        }
        const ctx = await getUiCopilot({
          page: 'research',
          question: title || 'Related institutional context',
          ticker: ticker || undefined,
        });
        if (active) {
          setPack({
            related_companies: ctx.context?.house_view?.ticker
              ? [ctx.context.house_view.ticker]
              : ticker
                ? [ticker]
                : [],
            related_themes: [],
            latest_updates: ctx.context?.latest_news || [],
            latest_news: ctx.context?.latest_news || [],
            previous_agi_articles: [],
            research_timeline: [],
            house_view: ctx.context?.house_view,
            confidence: ctx.context?.house_view?.confidence,
            supporting_evidence: [],
            whats_changed_since_publication: [],
            thesis_still_holds: null,
            thesis_status: {},
            prediction_status: [],
            discovery: {},
            follow_up_questions: [],
            intelligence_hub: {},
          });
        }
        if (title) {
          trackProductEvent('research_read', { title });
          pushReading({
            id: title,
            title,
            href: typeof window !== 'undefined' ? window.location.pathname : '/research',
          });
        }
      } catch {
        if (active) setPack(null);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [researchId, ticker, title]);

  if (!pack) return null;

  const houseLabel =
    pack.house_view?.current_view ||
    pack.house_view?.stance ||
    pack.house_view?.label;
  const holds = pack.thesis_still_holds;
  const changed = pack.whats_changed_since_publication || pack.thesis_status?.whats_changed_since_publication || [];
  const hub = pack.intelligence_hub || {};

  return (
    <aside className="mt-10 border-t border-[#dddddd] pt-8">
      <h2 className="text-lg font-bold text-[#111111]">Institutional Context</h2>
      <p className="text-xs text-[#767676] mt-1">
        Living research — know whether the original thesis still holds.
      </p>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div className="border border-[#dddddd] p-3">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Current House View</p>
          <p className="mt-1 text-sm font-bold text-[#111]">{houseLabel || 'Under review'}</p>
        </div>
        <div className="border border-[#dddddd] p-3">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Confidence</p>
          <p className="mt-1 text-sm font-bold text-[#111]">
            {fmtConf(pack.confidence ?? hub.confidence?.overall_pct)}
          </p>
        </div>
        <div className="border border-[#dddddd] p-3">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Thesis status</p>
          <p className="mt-1 text-sm font-bold text-[#111]">
            {holds == null ? 'Under review' : holds ? 'Still holds' : 'Evolved'}
          </p>
        </div>
        <div className="border border-[#dddddd] p-3">
          <Link
            to={`/ask?q=${encodeURIComponent(title ? `Summarise: ${title}` : "Summarise today's research")}`}
            className="text-xs font-bold text-[#111] hover:text-[#ff6600]"
          >
            Ask AGI about this article →
          </Link>
        </div>
      </div>

      {changed.length > 0 && (
        <section className="mt-4 border border-[#dddddd] p-4">
          <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676]">What changed since publication</h3>
          <ul className="mt-3 space-y-2">
            {changed.map((item) => (
              <li key={item} className="text-sm text-[#333]">• {item}</li>
            ))}
          </ul>
          {pack.thesis_status?.summary && (
            <p className="mt-2 text-xs text-[#767676]">{pack.thesis_status.summary}</p>
          )}
        </section>
      )}

      <IntelligenceHubView hub={hub} />

      <div className="mt-4 flex flex-wrap gap-2">
        {(pack.related_companies || []).map((t) => (
          <Link
            key={t}
            to={`/research/stocks/${encodeURIComponent(t)}`}
            className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
          >
            {t}
          </Link>
        ))}
        {(pack.related_themes || []).map((t) => (
          <Link
            key={t}
            to={`/themes/${encodeURIComponent(t)}`}
            className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
          >
            Theme: {t}
          </Link>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          ['Related AGI Research', pack.previous_agi_articles],
          ['Latest News', pack.latest_news || pack.latest_updates],
          ['Knowledge Timeline', pack.research_timeline],
          ['Supporting Evidence', pack.supporting_evidence],
          ['Prediction Status', pack.prediction_status],
        ].map(([label, items]) => (
          <section key={label} className="border border-[#dddddd] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{label}</h3>
            <ul className="mt-3 space-y-2">
              {(items || []).slice(0, 5).map((item, idx) => (
                <li key={item.id || item.title || idx} className="text-xs text-[#333] border-b border-[#eee] pb-1">
                  {item.title || item.thesis || item.id || String(item)}
                </li>
              ))}
              {(items || []).length === 0 && (
                <li className="text-xs text-[#929292]">No linked items yet.</li>
              )}
            </ul>
          </section>
        ))}
      </div>

      {(pack.follow_up_questions || []).length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {(pack.follow_up_questions || []).map((q) => (
            <Link
              key={q}
              to={`/ask?q=${encodeURIComponent(q)}`}
              className="text-[11px] border border-[#ddd] px-2.5 py-1.5 hover:border-[#111] hover:text-[#ff6600]"
            >
              {q}
            </Link>
          ))}
        </div>
      )}

      <div className="mt-4">
        <DiscoveryRail discovery={pack.discovery} />
      </div>
    </aside>
  );
}
