/**
 * AGI Pre-Market Morning Investment Committee Note
 * One AI research note + structured global context. No NSE/BSE raw quotes.
 */

import { getPreMarketContext } from './preMarketContextService.js';
import { getMarketBriefing } from './marketBriefingService.js';
import {
  getCachedDataset,
  saveDataset,
  isFresh,
  MACRO_REFRESH_MS,
} from './macroRepository.js';

const CACHE_MS = MACRO_REFRESH_MS.pre_market_briefing;
let memory = null;
let inflight = null;
let scheduler = null;

function avgTone(markets = []) {
  const score = markets.reduce((sum, item) => {
    if (item.tone === 'Bullish') return sum + 1;
    if (item.tone === 'Bearish') return sum - 1;
    return sum;
  }, 0);
  if (score >= 2) return 'Mildly Positive';
  if (score <= -2) return 'Mildly Negative';
  return 'Selective / Mixed';
}

function buildOvernightDevelopments(context) {
  return (context.globalMarkets || [])
    .filter((item) => !item.unavailable)
    .slice(0, 6)
    .map((item) => ({
      market: item.label,
      move: item.changeLabel,
      tone: item.tone,
      why: item.note || `${item.label} overnight tone is ${String(item.tone).toLowerCase()}.`,
    }));
}

function buildOvernightNews(context) {
  return (context.headlines || []).slice(0, 6).map((item) => {
    const title = item.title || 'Market development';
    const isEarnings = /earn|profit|beats|misses|results/i.test(title);
    const isPolicy = /rbi|fed|ecb|policy|rate/i.test(title);
    const isOil = /oil|crude|opec/i.test(title);
    return {
      headline: title,
      whyItMatters: isEarnings
        ? 'Earnings surprises can reset sector leadership and risk appetite into the India open.'
        : isPolicy
          ? 'Policy communication can reprice rate expectations and financial conditions.'
          : isOil
            ? 'Energy moves transmit into inflation, deficits and fuel-sensitive sectors.'
            : 'This overnight item may influence opening positioning if it changes the global risk narrative.',
      affectedSectors: isEarnings
        ? ['IT', 'Technology']
        : isPolicy
          ? ['Banks', 'NBFCs', 'Rate-sensitive']
          : isOil
            ? ['Energy', 'Airlines', 'Auto']
            : ['Broad market'],
      importance: isEarnings || isPolicy || isOil ? 'HIGH' : 'MEDIUM',
      source: item.source || 'IndianAPI',
      url: item.url || null,
    };
  });
}

function buildDriversTransmission(context) {
  return (context.drivers || []).map((driver) => ({
    id: driver.id,
    label: driver.label,
    move: driver.changeLabel,
    tone: driver.tone,
    indiaTone: driver.indiaTone,
    sectors: String(driver.indiaImpact || '')
      .split(/[·,]/)
      .map((part) => part.trim())
      .filter(Boolean),
    transmission: driver.transmission || [],
  }));
}

function buildScenarios(baseTone) {
  if (/positive/i.test(baseTone)) {
    return {
      base: { probability: 65, label: 'Mildly Positive', detail: 'Selective institutional buying into leaders rather than broad risk-on.' },
      bull: { probability: 20, label: 'Broad-based rally', detail: 'US risk appetite strengthens further and domestic cues confirm breadth.' },
      bear: { probability: 15, label: 'Risk-off open', detail: 'Overnight gains reverse or a domestic catalyst reprices rate/oil risk.' },
    };
  }
  if (/negative/i.test(baseTone)) {
    return {
      base: { probability: 60, label: 'Soft / Cautious open', detail: 'Defensive positioning until volatility and global cues stabilize.' },
      bull: { probability: 15, label: 'Relief bounce', detail: 'Overnight pressure fades and domestic buyers defend key sectors.' },
      bear: { probability: 25, label: 'Risk-off extension', detail: 'Global weakness deepens and India opens with broad selling pressure.' },
    };
  }
  return {
    base: { probability: 55, label: 'Selective open', detail: 'Stock and sector dispersion dominates; indices may look calm while leadership rotates.' },
    bull: { probability: 25, label: 'Risk-on confirmation', detail: 'Global futures stay firm and domestic breadth improves.' },
    bear: { probability: 20, label: 'Fade into weakness', detail: 'A negative domestic catalyst or oil/yield shock flips the open.' },
  };
}

function buildMorningNote(context, marketBriefing) {
  const baseTone = avgTone(context.globalMarkets);
  const preNote = marketBriefing?.intelligence?.sessionNotes?.preMarket || {};
  const sectors = marketBriefing?.intelligence?.sectorImpact || [];
  const winners = sectors.filter((s) => /positive|bull/i.test(s.direction)).slice(0, 4);
  const risks = sectors.filter((s) => /negative|bear/i.test(s.direction)).slice(0, 4);
  const us = (context.globalMarkets || []).filter((m) => /S&P|NASDAQ|Dow/i.test(m.label));
  const oil = (context.drivers || []).find((d) => d.id === 'oil');
  const treasury = (context.drivers || []).find((d) => d.id === 'treasury');

  const executiveThesis = [
    `AGI’s Morning Investment Committee classifies the pre-open backdrop as ${baseTone.toLowerCase()} because overnight global risk appetite is ${us.filter((m) => m.tone === 'Bullish').length >= 2 ? 'constructive across US proxies' : us.filter((m) => m.tone === 'Bearish').length >= 2 ? 'softer across US proxies' : 'mixed across US proxies'}.`,
    oil ? `Crude-linked conditions are ${String(oil.tone).toLowerCase()}, which ${/bullish/i.test(oil.tone) ? 'raises fuel and inflation sensitivity for Airlines, Paint and Auto' : /bearish/i.test(oil.tone) ? 'eases near-term cost pressure for fuel-sensitive sectors' : 'keeps energy transmission neutral into the open'}.` : '',
    treasury ? `US duration/yield cues are ${String(treasury.tone).toLowerCase()}, so rate-sensitive India sectors (Banks, NBFCs) should be read through global financial conditions rather than domestic tape alone.` : '',
    winners.length
      ? `Into the India open, AGI’s base case favours selective strength in ${winners.map((s) => s.name).join(', ')} rather than a blanket risk-on stance.`
      : 'Into the India open, AGI prefers selective institutional positioning over broad beta.',
    'Domestic catalysts (policy communication, PMI/earnings, and any overnight corporate radar items) remain the key invalidation risks for the morning base case.',
  ].filter(Boolean).join(' ');

  const questions = [
    'Will Banks continue recent relative strength into the open?',
    'Can IT outperform if NASDAQ proxies remain firm overnight?',
    'Will oil stay contained enough to keep Airlines and Auto from opening weak?',
    'Can Capital Goods extend leadership if global cyclicals hold?',
    'Will today’s economic calendar surprise change rate expectations?',
    'How will RBI tone influence duration and NBFC positioning?',
  ];

  return {
    title: 'AGI Morning Investment Committee Note',
    subtitle: 'One-page pre-market research brief for institutions',
    generatedForSession: 'Pre-Market',
    outlook: baseTone,
    confidence: Math.max(48, Math.min(78, 52 + (context.sourcesUsed?.length || 0) * 4)),
    executiveThesis,
    overnightDevelopments: buildOvernightDevelopments(context),
    whatMattersToday: [
      'Whether US overnight risk appetite holds into Asia and India.',
      'Whether oil and dollar transmission stays supportive for India margins.',
      'Whether domestic catalysts (policy / PMI / earnings) confirm or invalidate the global cue.',
    ],
    sectorOutlook: {
      winners: winners.map((s) => ({ name: s.name, why: s.explanation || 'Relative leadership in the AGI market model.' })),
      risks: risks.map((s) => ({ name: s.name, why: s.explanation || 'Relative weakness in the AGI market model.' })),
    },
    risks: (preNote.watch || []).slice(0, 4).concat([
      'A sudden reversal in US proxies after Indian cash open.',
      'An oil or Middle East shock that reprices inflation risk.',
    ]).slice(0, 5),
    catalysts: (context.economicCalendar || []).slice(0, 4).map((item) => `${item.country}: ${item.event}`),
    questions,
    scenarios: buildScenarios(baseTone),
    threeThingsToWatch: [
      'US proxy direction into the India open',
      'Oil / USDINR transmission into fuel-sensitive sectors',
      'Domestic calendar and corporate radar surprises',
    ],
    evidence: [
      ...us.map((m) => `${m.label} ${m.changeLabel} (${m.source})`),
      ...(context.drivers || []).slice(0, 4).map((d) => `${d.label} ${d.changeLabel}`),
    ],
    mintStyleNote: preNote,
  };
}

function buildWorkspace(context, morningNote, marketBriefing) {
  return {
    globalMarkets: context.globalMarkets,
    drivers: buildDriversTransmission(context),
    heatMap: context.heatMap,
    overnightNews: buildOvernightNews(context),
    economicCalendar: context.economicCalendar,
    earningsCalendar: context.earningsCalendar,
    sectorWatch: (marketBriefing?.intelligence?.sectorImpact || []).slice(0, 8).map((s) => ({
      name: s.name,
      direction: s.direction,
      why: s.explanation,
    })),
    researchSidebar: [
      { label: "Today's Note", href: '#morning-note' },
      { label: 'Weekly Strategy', href: '/research' },
      { label: 'Oil Research', href: '/macro-intelligence' },
      { label: 'Fed Watch', href: '/macro-intelligence' },
      { label: 'RBI Preview', href: '/macro-intelligence' },
      { label: 'Sector Outlook', href: '/market-intelligence' },
    ],
    scenarios: morningNote.scenarios,
    questions: morningNote.questions,
  };
}

async function enrichWithLlm(briefing) {
  const note = briefing.morningNote;
  try {
    const { completeJson } = await import('./llmClient.js');
    const generated = await completeJson({
      system:
        'You are AGI’s Chief Investment Strategist writing a Pre-Market Morning Investment Committee Note for India-focused institutions. Return JSON with: executiveThesis (180-280 words), outlook, baseCase, bullCase, bearCase, threeThingsToWatch (string array), questions (string array). Never invent exact live prices. You may discuss directional global moves already provided. Never give buy/sell recommendations. Every important claim must answer “because what?”. Ban vague phrases like “markets may remain positive”.',
      user: {
        outlook: note.outlook,
        evidence: note.evidence,
        globalMarkets: briefing.workspace.globalMarkets,
        drivers: briefing.workspace.drivers,
        heatMap: briefing.workspace.heatMap,
        scenarios: note.scenarios,
      },
      temperature: 0.25,
    });
    if (!generated) return briefing;
    return {
      ...briefing,
      aiGenerated: true,
      morningNote: {
        ...note,
        executiveThesis: typeof generated.executiveThesis === 'string' ? generated.executiveThesis : note.executiveThesis,
        outlook: typeof generated.outlook === 'string' ? generated.outlook : note.outlook,
        threeThingsToWatch: Array.isArray(generated.threeThingsToWatch) ? generated.threeThingsToWatch.slice(0, 3) : note.threeThingsToWatch,
        questions: Array.isArray(generated.questions) ? generated.questions.slice(0, 6) : note.questions,
        scenarios: {
          base: {
            ...note.scenarios.base,
            detail: typeof generated.baseCase === 'string' ? generated.baseCase : note.scenarios.base.detail,
          },
          bull: {
            ...note.scenarios.bull,
            detail: typeof generated.bullCase === 'string' ? generated.bullCase : note.scenarios.bull.detail,
          },
          bear: {
            ...note.scenarios.bear,
            detail: typeof generated.bearCase === 'string' ? generated.bearCase : note.scenarios.bear.detail,
          },
        },
      },
    };
  } catch (error) {
    console.warn('[pre-market] AI narrative fallback:', error.message);
    return briefing;
  }
}

function assembleBriefing(context, marketBriefing) {
  const morningNote = buildMorningNote(context, marketBriefing);
  return {
    updatedAt: new Date().toISOString(),
    refreshesAt: new Date(Date.now() + CACHE_MS).toISOString(),
    aiGenerated: false,
    stale: Boolean(context.stale),
    morningNote,
    workspace: buildWorkspace(context, morningNote, marketBriefing),
    sourcesUsed: context.sourcesUsed,
    datasetStatus: context.datasetStatus,
    compliance: context.compliance,
    disclaimer: 'AGI Pre-Market Intelligence is institutional research for information only. Global figures come from licensed/redistribution-friendly market-data APIs (ETF/crypto proxies). AGI does not display raw NSE/BSE real-time quotes here. This is not investment advice.',
  };
}

export async function getPreMarketBriefing({ force = false } = {}) {
  if (!force && memory?.workspace && isFresh({ expiresAt: memory.refreshesAt })) {
    return { ...memory, fromCache: true };
  }
  if (inflight) return inflight;

  inflight = (async () => {
    const persisted = force ? null : await getCachedDataset('pre_market_briefing');
    if (persisted?.payload?.workspace && isFresh(persisted)) {
      memory = {
        ...persisted.payload,
        fromCache: true,
        repositoryServedFrom: 'agi-repository',
      };
      return memory;
    }

    const staleFallback = memory?.workspace
      ? memory
      : persisted?.payload?.workspace
        ? { ...persisted.payload, stale: true, fromCache: true }
        : null;

    try {
      const [context, marketBriefing] = await Promise.all([
        getPreMarketContext({ force }),
        getMarketBriefing().catch(() => null),
      ]);
      const briefing = await enrichWithLlm(assembleBriefing(context, marketBriefing));
      const saved = await saveDataset('pre_market_briefing', briefing, {
        source: 'agi-premarket-engine',
        ttlMs: CACHE_MS,
        refreshPolicy: '30m morning window',
        meta: { aiGenerated: Boolean(briefing.aiGenerated) },
      });
      memory = {
        ...briefing,
        fromCache: false,
        refreshesAt: saved.expiresAt,
      };
      return memory;
    } catch (error) {
      if (staleFallback) {
        console.warn('[pre-market] rebuild failed; serving stale cache:', error.message);
        memory = { ...staleFallback, stale: true, fromCache: true, upstreamError: error.message };
        return memory;
      }
      throw error;
    }
  })().finally(() => {
    inflight = null;
  });

  return inflight;
}

export function startPreMarketBriefingScheduler() {
  if (scheduler) return;
  const refresh = () => {
    getPreMarketBriefing().catch((error) => console.warn('[pre-market] scheduled refresh failed:', error.message));
  };
  refresh();
  scheduler = setInterval(refresh, CACHE_MS);
  scheduler.unref?.();
}
