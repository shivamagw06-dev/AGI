import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  TOP_FIRMS,
  SECTORS,
  TRANSACTIONS,
  FUNDS,
  RESEARCH_FEED,
  TEAM_SAMPLE,
} from '../../data/peIntelligenceSeed.js';
import { slugify } from './entityTypes.js';
import { bulkUpsertEntities, listEntities } from './entityStore.js';
import { bulkAddRelationships } from './relationshipStore.js';
import { bulkAddTimelineEvents } from './timelineService.js';
import { generateEntitySummary } from './aiSummaryService.js';
import { isBootstrapped, writeEntities } from './store.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KKR_PORTFOLIO_PATH = path.join(__dirname, '../../data/kkr_portfolio.json');

function loadKkrPortfolio() {
  try {
    return JSON.parse(fs.readFileSync(KKR_PORTFOLIO_PATH, 'utf8'));
  } catch {
    return [];
  }
}

function firmSlugToName(slug) {
  return TOP_FIRMS.find((f) => f.slug === slug)?.name || slug;
}

export async function bootstrapIntelligencePlatform({ force = false } = {}) {
  if (isBootstrapped() && !force) {
    return { bootstrapped: true, skipped: true, stats: listEntities({ limit: 1 }) };
  }

  const entityRows = [];
  const slugToId = new Map();
  const relRows = [];
  const timelineRows = [];

  const register = (row) => {
    entityRows.push(row);
    slugToId.set(row.slug, row.id);
    return row.id;
  };

  // PE Firms
  TOP_FIRMS.forEach((firm) => {
    const id = register({
      id: `firm-${firm.slug}`,
      slug: firm.slug,
      entity_type: 'pe_firm',
      name: firm.name,
      description: firm.strategy,
      tags: [...(firm.industries || []), ...(firm.geoFocus || []), 'Private Markets'],
      metadata: {
        hq: firm.hq,
        aum: firm.aum,
        founded: firm.founded,
        offices: firm.offices,
        portfolioCount: firm.portfolioCount,
        fundCount: firm.fundCount,
        exitCount: firm.exitCount,
        geoFocus: firm.geoFocus,
        industries: firm.industries,
        website: firm.website,
        logo: firm.logo,
      },
      source_refs: [{ type: 'pe_seed', id: firm.slug }],
    });
    timelineRows.push({
      entity_id: id,
      event_type: 'founded',
      title: `Founded ${firm.founded}`,
      description: `${firm.name} established in ${firm.hq}.`,
      occurred_at: `${firm.founded}-01-01T00:00:00.000Z`,
      source_type: 'pe_seed',
      source_id: firm.slug,
    });
  });

  // Industries
  SECTORS.forEach((sector) => {
    register({
      id: `industry-${slugify(sector)}`,
      slug: slugify(sector),
      entity_type: 'industry',
      name: sector,
      description: `${sector} sector coverage across global private markets.`,
      tags: ['Industry', sector],
      metadata: { sector },
    });
  });

  // Funds
  FUNDS.forEach((fund) => {
    const gpSlug = slugify(fund.gp);
    const firm = TOP_FIRMS.find((f) => f.name === fund.gp || f.slug === gpSlug);
    const firmSlug = firm?.slug || gpSlug;
    const id = register({
      id: fund.id,
      slug: slugify(fund.name),
      entity_type: 'fund',
      name: fund.name,
      description: `${fund.strategy} · ${fund.geography}`,
      tags: [fund.strategy, fund.geography, fund.status],
      metadata: {
        vintage: fund.vintage,
        fundSize: fund.fundSize,
        strategy: fund.strategy,
        status: fund.status,
        gp: fund.gp,
        geography: fund.geography,
      },
    });
    const firmId = slugToId.get(firmSlug);
    if (firmId) {
      relRows.push({
        from_entity_id: firmId,
        to_entity_id: id,
        relation_type: 'MANAGES',
      });
    }
    timelineRows.push({
      entity_id: id,
      event_type: 'fund',
      title: `${fund.name} (${fund.vintage})`,
      description: `${fund.fundSize} · ${fund.status}`,
      occurred_at: `${fund.vintage}-06-01T00:00:00.000Z`,
      source_type: 'pe_seed',
      source_id: fund.id,
    });
    if (firmId) {
      timelineRows.push({
        entity_id: firmId,
        event_type: 'fund',
        title: fund.name,
        description: `${fund.fundSize} flagship fund`,
        occurred_at: `${fund.vintage}-06-01T00:00:00.000Z`,
        source_type: 'fund',
        source_id: fund.id,
      });
    }
  });

  // Transactions + target companies
  TRANSACTIONS.forEach((tx) => {
    const buyerSlug = slugify(tx.buyer);
    const targetSlug = slugify(tx.target);
    let targetId = slugToId.get(targetSlug);
    if (!targetId) {
      targetId = register({
        id: `co-${targetSlug}`,
        slug: targetSlug,
        entity_type: 'company',
        name: tx.target,
        description: `${tx.industry} · ${tx.country}`,
        tags: [tx.industry, tx.country],
        metadata: { industry: tx.industry, country: tx.country },
      });
    }
    const txId = register({
      id: tx.id,
      slug: tx.id,
      entity_type: 'transaction',
      name: `${tx.buyer} / ${tx.target}`,
      description: `${tx.dealValue} · ${tx.status}`,
      tags: [tx.industry, tx.status, tx.country],
      metadata: {
        buyer: tx.buyer,
        seller: tx.seller,
        target: tx.target,
        dealValue: tx.dealValue,
        enterpriseValue: tx.enterpriseValue,
        equityValue: tx.equityValue,
        industry: tx.industry,
        country: tx.country,
        status: tx.status,
        date: tx.date,
      },
    });
    const buyerId = slugToId.get(buyerSlug) || slugToId.get(TOP_FIRMS.find((f) => f.name === tx.buyer)?.slug);
    if (buyerId) {
      relRows.push({ from_entity_id: buyerId, to_entity_id: targetId, relation_type: 'INVESTED_IN' });
      relRows.push({ from_entity_id: buyerId, to_entity_id: txId, relation_type: 'SPONSORED_BY' });
    }
    timelineRows.push({
      entity_id: txId,
      event_type: 'transaction',
      title: tx.status,
      description: `${tx.dealValue} — ${tx.buyer} / ${tx.target}`,
      occurred_at: `${tx.date}T12:00:00.000Z`,
      source_type: 'transaction',
      source_id: tx.id,
    });
    if (buyerId) {
      timelineRows.push({
        entity_id: buyerId,
        event_type: 'transaction',
        title: `${tx.status}: ${tx.target}`,
        description: tx.dealValue,
        occurred_at: `${tx.date}T12:00:00.000Z`,
        source_type: 'transaction',
        source_id: tx.id,
      });
    }
  });

  // KKR portfolio companies (sample)
  const kkrId = slugToId.get('kkr');
  loadKkrPortfolio().slice(0, 60).forEach((row, i) => {
    const slug = slugify(row.company);
    if (slugToId.has(slug)) return;
    const id = register({
      id: `pc-${slug}`,
      slug,
      entity_type: 'portfolio_company',
      name: row.company,
      description: `${row.industry || '—'} · ${row.region || '—'}`,
      tags: [row.industry, row.region, row.asset_class, row.status].filter(Boolean),
      metadata: {
        industry: row.industry,
        country: (row.hq || '').split(',').pop()?.trim() || row.region,
        region: row.region,
        investmentYear: row.investment_year,
        exitYear: row.exit_year,
        status: row.status,
        assetClass: row.asset_class,
        website: row.company_website,
        logo: row.logo,
      },
    });
    if (kkrId) {
      relRows.push({ from_entity_id: kkrId, to_entity_id: id, relation_type: 'INVESTED_IN' });
    }
    if (row.investment_year && row.investment_year !== '—') {
      timelineRows.push({
        entity_id: id,
        event_type: 'investment',
        title: `Investment (${row.investment_year})`,
        description: kkrId ? `Backed by KKR` : '',
        occurred_at: `${row.investment_year}-01-01T00:00:00.000Z`,
        source_type: 'portfolio',
        source_id: slug,
      });
      if (kkrId) {
        timelineRows.push({
          entity_id: kkrId,
          event_type: 'investment',
          title: `Invested in ${row.company}`,
          description: row.industry,
          occurred_at: `${row.investment_year}-01-01T00:00:00.000Z`,
          source_type: 'portfolio',
          source_id: slug,
        });
      }
    }
    if (row.exit_year) {
      timelineRows.push({
        entity_id: id,
        event_type: 'exit',
        title: `Exit (${row.exit_year})`,
        occurred_at: `${row.exit_year}-06-01T00:00:00.000Z`,
        source_type: 'portfolio',
        source_id: slug,
      });
    }
    if (i % 17 === 0) {
      /* avoid timeline bloat — already covered above */
    }
  });

  // People
  TEAM_SAMPLE.forEach((person, i) => {
    const slug = slugify(person.name);
    const id = register({
      id: `person-${slug}`,
      slug,
      entity_type: 'person',
      name: person.name,
      description: person.bio,
      tags: person.sectors || [],
      metadata: {
        title: person.title,
        office: person.office,
        prior: person.prior,
        education: person.education,
      },
    });
    if (kkrId) {
      relRows.push({ from_entity_id: id, to_entity_id: kkrId, relation_type: 'WORKS_AT' });
    }
    timelineRows.push({
      entity_id: id,
      event_type: 'appointment',
      title: person.title,
      description: person.office,
      occurred_at: `2010-01-${String(i + 1).padStart(2, '0')}T00:00:00.000Z`,
      source_type: 'team',
      source_id: slug,
    });
  });

  // News / research feed
  RESEARCH_FEED.forEach((item) => {
    const slug = slugify(item.headline).slice(0, 80);
    const id = register({
      id: item.id,
      slug,
      entity_type: 'news',
      name: item.headline,
      description: item.summary,
      tags: [item.category, item.sector, item.geography],
      metadata: {
        category: item.category,
        dealType: item.dealType,
        firmSlug: item.firmSlug,
        firmName: item.firmName,
        company: item.company,
        sector: item.sector,
        geography: item.geography,
        source: item.source,
        timestamp: item.timestamp,
      },
    });
    const firmId = slugToId.get(item.firmSlug);
    if (firmId) {
      relRows.push({ from_entity_id: id, to_entity_id: firmId, relation_type: 'MENTIONS' });
      timelineRows.push({
        entity_id: firmId,
        event_type: 'news',
        title: item.headline,
        description: item.summary?.slice(0, 120),
        occurred_at: item.timestamp,
        source_type: 'news',
        source_id: item.id,
      });
    }
  });

  // Comparable firms (COMPETES_WITH among top GPs)
  const firmSlugs = TOP_FIRMS.map((f) => f.slug);
  firmSlugs.forEach((slug, i) => {
    const firmId = slugToId.get(slug);
    if (!firmId) return;
    const peerSlug = firmSlugs[(i + 1) % firmSlugs.length];
    const peerId = slugToId.get(peerSlug);
    if (peerId && peerId !== firmId) {
      relRows.push({ from_entity_id: firmId, to_entity_id: peerId, relation_type: 'COMPETES_WITH' });
    }
  });

  bulkUpsertEntities(entityRows);
  bulkAddRelationships(relRows);
  bulkAddTimelineEvents(timelineRows);
  writeEntities(listEntities({ limit: 10000 }).entities, { bootstrapped: true });

  // Generate summaries for top firms (deterministic + optional LLM)
  const firmIds = TOP_FIRMS.map((f) => slugToId.get(f.slug)).filter(Boolean);
  for (const id of firmIds.slice(0, 5)) {
    await generateEntitySummary(id, { force: true });
  }

  const stats = listEntities({ limit: 10000 });
  return {
    bootstrapped: true,
    skipped: false,
    entityCount: stats.total,
    relationshipCount: relRows.length,
    timelineCount: timelineRows.length,
  };
}

export function ensurePlatformBootstrapped() {
  if (!isBootstrapped()) {
    return bootstrapIntelligencePlatform();
  }
  return Promise.resolve({ bootstrapped: true, skipped: true });
}
