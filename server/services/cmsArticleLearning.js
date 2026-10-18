import { persistResearchKnowledge } from './researchKnowledgeRegistry.js';

/**
 * CMS Article Learning — read uploaded articles into KIP/KF/KC (soft-wire).
 * Architecture v1.0.1 LOCKED — additive only; never redesign engines.
 */

function stripHtml(html = '') {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const KNOWN_TICKERS = new Set([
  'ICICIBANK',
  'HDFCBANK',
  'RELIANCE',
  'TCS',
  'INFY',
  'SBIN',
  'AXISBANK',
  'KOTAKBANK',
  'BHARTIARTL',
  'LT',
  'ITC',
  'WIPRO',
  'MARUTI',
  'TATAMOTORS',
  'HINDUNILVR',
  'HCLTECH',
  'AAPL',
  'MSFT',
  'GOOGL',
  'AMZN',
  'NVDA',
]);

function normalizedCompanyName(value = '') {
  return String(value).toUpperCase().replace(/\b(LIMITED|LTD|INDIA|THE)\b/g, ' ').replace(/[^A-Z0-9]/g, '');
}

function extractTickers(parts, universe = []) {
  const text = parts.filter(Boolean).join(' ').toUpperCase();
  const matches = text.match(/\b[A-Z]{2,12}\b/g) || [];
  const known = new Set([...KNOWN_TICKERS, ...universe.map((row) => row.symbol)]);
  const found = matches.filter((t) => known.has(t) || t.endsWith('BANK'));
  const compactText = normalizedCompanyName(text);
  for (const row of universe) {
    const company = normalizedCompanyName(row.company_name);
    if (company.length >= 5 && compactText.includes(company)) found.push(row.symbol);
  }
  return [...new Set(found)].slice(0, 12);
}

async function loadCompanyUniverse(engineFetch) {
  try {
    const result = await engineFetch('/v1/warehouse/tab/company_master?limit=10000', {
      timeoutMs: 30_000,
    });
    if (!result.ok) return [];
    return (result.data?.rows || [])
      .map((row) => ({
        symbol: String(row.symbol || row.nse_symbol || row.company_id || '').toUpperCase().trim(),
        company_name: row.company_name || row.legal_name || '',
      }))
      .filter((row) => /^[A-Z0-9]{2,12}$/.test(row.symbol));
  } catch {
    // Article ingestion must remain available if the warehouse is temporarily busy.
    return [];
  }
}

function learningDateIST(d = new Date()) {
  // Asia/Kolkata calendar date — knowledge updates run every day
  return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });
}

function learnedOnISTDate(iso, dateStr) {
  if (!iso || !dateStr) return false;
  return learningDateIST(new Date(iso)) === dateStr;
}

async function createAdmin() {
  const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
  return createSupabaseAdmin();
}

/** Stamp CMS article after a successful (or queued) KIP ingest from the Node gateway. */
export async function markArticleIntelligenceIngest({
  articleId,
  documentId = null,
  status = 'learned',
  error = null,
} = {}) {
  if (!articleId) return { ok: false, skipped: true, reason: 'articleId required' };
  const admin = await createAdmin();
  if (!admin) {
    return {
      ok: false,
      skipped: true,
      reason: 'Supabase admin credentials unavailable on API',
    };
  }

  const learnedAt = status === 'learned' ? new Date().toISOString() : null;
  const patch = {
    learn_status: status,
    last_learn_error: error ? String(error).slice(0, 500) : null,
  };
  if (documentId) {
    patch.intelligence_document_id = documentId;
    patch.intelligence_ingested_at = learnedAt || new Date().toISOString();
  }
  if (learnedAt) {
    patch.last_learned_at = learnedAt;
  }

  const { error: updateError } = await admin.from('articles').update(patch).eq('id', articleId);
  if (updateError) return { ok: false, error: updateError.message || String(updateError) };

  if (status === 'learned' && documentId) {
    try {
      const { data: row } = await admin
        .from('articles')
        .select('title,slug,status')
        .eq('id', articleId)
        .maybeSingle();
      await admin.from('cms_article_learn_events').insert({
        article_id: articleId,
        learned_at: learnedAt,
        learning_date: learningDateIST(),
        document_id: documentId,
        status: 'learned',
        title: row?.title || null,
        slug: row?.slug || null,
        destination: row?.status === 'published' ? 'website' : 'intelligence',
        error: null,
      });
    } catch {
      /* events table optional */
    }
  }

  return { ok: true, article_id: articleId, document_id: documentId, status };
}

/**
 * @param {object} opts
 * @param {(path:string, init?:object)=>Promise<{status:number,data:any}>} opts.engineFetch
 */
export async function learnCmsArticles({
  engineFetch,
  limit = 50,
  onlyUnlearned = false,
  sinceDate = null,
  mode = null,
  compound = true,
} = {}) {
  const admin = await createAdmin();
  if (!admin) {
    return {
      ok: false,
      skipped: true,
      reason: 'Supabase admin credentials unavailable on API (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY).',
    };
  }

  const learningDate = learningDateIST();
  const dailyMode = mode === 'daily' || Boolean(sinceDate === 'today');
  const effectiveOnlyUnlearned = onlyUnlearned && !dailyMode;

  // Publishing is reversible. Tombstone previously learned drafts before
  // ingesting active articles so Ask AGI cannot quote unpublished research.
  const { data: unpublished } = await admin
    .from('articles')
    .select('id,title,intelligence_document_id,status')
    .eq('status', 'draft')
    .not('intelligence_document_id', 'is', null)
    .limit(200);
  let retired = 0;
  for (const article of unpublished || []) {
    try {
      const result = await engineFetch(
        `/v1/kip/article/${encodeURIComponent(article.id)}/retire`,
        { method: 'POST', body: {}, timeoutMs: 30_000 }
      );
      if (!result.ok) continue;
      retired += result.data?.retired ? 1 : 0;
      await admin
        .from('articles')
        .update({
          intelligence_document_id: null,
          intelligence_ingested_at: null,
          learn_status: 'unpublished',
          last_learn_error: null,
        })
        .eq('id', article.id);
    } catch {
      // Leave metadata intact so the next scheduler pass retries safely.
    }
  }

  let query = admin
    .from('articles')
    .select(
      'id,title,slug,section,tags,status,content,content_md,excerpt,published_at,created_at,intelligence_document_id,intelligence_ingested_at,last_learned_at,learn_status,learn_count'
    )
    .in('status', ['published', 'intelligence'])
    .order('published_at', { ascending: false, nullsFirst: false })
    .limit(Math.min(Math.max(Number(limit) || 50, 1), 200));

  if (effectiveOnlyUnlearned) {
    query = query.is('last_learned_at', null);
  }

  const { data: articles, error } = await query;
  if (error) {
    return { ok: false, error: error.message || String(error) };
  }

  let rows = Array.isArray(articles) ? articles : [];
  const companyUniverse = await loadCompanyUniverse(engineFetch);
  if (dailyMode) {
    // Daily knowledge update: skip articles already learned on today's IST date
    rows = rows.filter((a) => !learnedOnISTDate(a.last_learned_at, learningDate));
  } else if (sinceDate && sinceDate !== 'today') {
    const cutoff = String(sinceDate).slice(0, 10);
    rows = rows.filter((a) => !a.last_learned_at || String(a.last_learned_at).slice(0, 10) < cutoff);
  }
  const results = [];
  let learned = 0;
  let failed = 0;
  let skipped = 0;

  for (const article of rows) {
    const title = String(article.title || '').trim();
    const content = stripHtml(article.content_md || article.content || article.excerpt || '');
    if (!title || content.length < 40) {
      skipped += 1;
      results.push({
        article_id: article.id,
        title,
        status: 'skipped',
        error: 'Insufficient content',
      });
      await admin
        .from('articles')
        .update({ learn_status: 'skipped', last_learn_error: 'Insufficient content' })
        .eq('id', article.id);
      continue;
    }

    const destination = article.status === 'published' ? 'website' : 'intelligence';
    const payload = {
      title,
      content,
      author: 'AGI Research Desk',
      source: 'agi',
      document_type: destination === 'website' ? 'agi_research' : 'agi_note',
      language: 'en',
      tickers: extractTickers(
        [title, ...(article.tags || []), content.slice(0, 1200)],
        companyUniverse
      ),
      themes: Array.isArray(article.tags) ? article.tags.slice(0, 8) : [],
      sectors: [],
      article_id: article.id || article.slug,
      research_type: article.section || '',
      metadata: {
        cms_status: article.status,
        slug: article.slug || null,
        section: article.section || null,
        destination,
        learning_date: learningDate,
        cms_bulk_learn: true,
      },
    };

    try {
      const result = await engineFetch('/v1/kip/ingest/agi', { method: 'POST', body: payload });
      if (result.status >= 400) {
        throw new Error(result.data?.error || result.data?.detail || `Ingest failed (${result.status})`);
      }
      const documentId =
        result.data?.document_id ||
        result.data?.id ||
        result.data?.document?.id ||
        article.intelligence_document_id ||
        null;
      if (!documentId) {
        throw new Error('Ingest returned no document_id');
      }

      // Do NOT mark learned until the document is retrievable (closes metadata/data split).
      const verified = await engineFetch(`/v1/kip/verify/${encodeURIComponent(documentId)}`);
      if (!verified.ok || verified.data?.retrievable === false) {
        const detail =
          verified.data?.error ||
          verified.data?.detail?.error ||
          verified.data?.detail ||
          `Document not retrievable (${verified.status})`;
        throw new Error(`Knowledge validation failed: ${detail}`);
      }

      const knowledgeRegistry = await persistResearchKnowledge({
        job: {
          article_id: article.id,
          document_id: documentId,
          content_hash: String(result.data?.metadata?.content_hash || article.id),
          slug: article.slug || null,
          embedding_version: result.data?.metadata?.embedding_version || 'kip-default',
          quality: result.data?.knowledge?.quality ?? 0.7,
          payload,
        },
        ingestResult: result.data,
        verified: true,
      });

      const learnedAt = new Date().toISOString();
      const nextCount = Number(article.learn_count || 0) + 1;

      await admin
        .from('articles')
        .update({
          intelligence_document_id: documentId,
          intelligence_ingested_at: learnedAt,
          last_learned_at: learnedAt,
          learn_status: 'learned',
          last_learn_error: null,
          learn_count: nextCount,
        })
        .eq('id', article.id);

      await admin.from('cms_article_learn_events').insert({
        article_id: article.id,
        learned_at: learnedAt,
        learning_date: learningDate,
        document_id: documentId,
        status: 'learned',
        title,
        slug: article.slug || null,
        destination,
      });

      learned += 1;
      results.push({
        article_id: article.id,
        title,
        slug: article.slug,
        status: 'learned',
        document_id: documentId,
        learned_at: learnedAt,
        learning_date: learningDate,
        learn_count: nextCount,
        verified: true,
        knowledge_registry: knowledgeRegistry,
      });
    } catch (err) {
      failed += 1;
      const message = err?.message || String(err);
      await admin
        .from('articles')
        .update({ learn_status: 'failed', last_learn_error: message.slice(0, 500) })
        .eq('id', article.id);
      await admin.from('cms_article_learn_events').insert({
        article_id: article.id,
        learning_date: learningDate,
        status: 'failed',
        title,
        slug: article.slug || null,
        destination,
        error: message.slice(0, 500),
      });
      results.push({
        article_id: article.id,
        title,
        status: 'failed',
        error: message,
      });
    }
  }

  let compoundResult = null;
  if (compound && learned > 0) {
    try {
      const populated = await engineFetch('/v1/kc/populate?rebuild_kip=false', {
        method: 'POST',
        body: {},
      });
      compoundResult = {
        ok: populated.status < 400,
        status: populated.status,
        summary: populated.data?.metrics || populated.data?.message || null,
      };
    } catch (err) {
      compoundResult = { ok: false, error: err?.message || String(err) };
    }
  }

  // Soft-wire Research Intelligence Hub — learned articles become Intelligence Objects.
  let researchHubResult = null;
  if (learned > 0) {
    const hubBuilds = [];
    for (const row of results.filter((r) => r.status === 'learned').slice(0, 25)) {
      try {
        const article = rows.find((a) => a.id === row.article_id) || {};
        const hub = await engineFetch('/v1/research/hub/build', {
          method: 'POST',
          body: {
            note_id: String(row.article_id),
            headline: row.title || article.title || String(row.article_id),
            body: String(article.content || article.body || article.markdown || ''),
            publication_date: article.published_at || article.publication_date || null,
            persist: true,
            importance_score: 70,
          },
        });
        hubBuilds.push({
          article_id: row.article_id,
          ok: hub.status < 400,
          hub_id: hub.data?.id || row.article_id,
          status: hub.status,
        });
      } catch (err) {
        hubBuilds.push({
          article_id: row.article_id,
          ok: false,
          error: err?.message || String(err),
        });
      }
    }
    researchHubResult = {
      attempted: hubBuilds.length,
      ok: hubBuilds.filter((h) => h.ok).length,
      failed: hubBuilds.filter((h) => !h.ok).length,
      builds: hubBuilds,
    };
  }

  return {
    ok: true,
    learning_date: learningDate,
    timezone: 'Asia/Kolkata',
    mode: dailyMode ? 'daily' : effectiveOnlyUnlearned ? 'unlearned' : 'bulk',
    scanned: rows.length,
    learned,
    failed,
    skipped,
    retired,
    compound: compoundResult,
    research_hub: researchHubResult,
    results,
    architecture_status: 'v1.0.1 LOCKED',
    note: 'Soft-wire CMS → KIP → KF/KC → RIH. Every learned article becomes an Intelligence Hub.',
  };
}

export async function cmsLearningStatus({ days = 14 } = {}) {
  const admin = await createAdmin();
  if (!admin) {
    return {
      ok: false,
      skipped: true,
      reason: 'Supabase admin credentials unavailable on API.',
    };
  }

  const dayCount = Math.min(Math.max(Number(days) || 14, 1), 90);
  const since = new Date(Date.now() - dayCount * 86400000).toISOString();

  const [{ data: events, error: eventsError }, { data: pending, error: pendingError }, { count, error: countError }] =
    await Promise.all([
      admin
        .from('cms_article_learn_events')
        .select('id,article_id,learned_at,learning_date,document_id,status,title,slug,error')
        .gte('learned_at', since)
        .order('learned_at', { ascending: false })
        .limit(200),
      admin
        .from('articles')
        .select('id,title,slug,status,last_learned_at,learn_status,published_at')
        .in('status', ['published', 'intelligence'])
        .is('last_learned_at', null)
        .limit(100),
      admin
        .from('articles')
        .select('id', { count: 'exact', head: true })
        .in('status', ['published', 'intelligence']),
    ]);

  if (eventsError || pendingError || countError) {
    return {
      ok: false,
      error: eventsError?.message || pendingError?.message || countError?.message,
    };
  }

  const byDate = {};
  for (const ev of events || []) {
    const d = ev.learning_date || String(ev.learned_at || '').slice(0, 10);
    if (!d) continue;
    if (!byDate[d]) byDate[d] = { learning_date: d, learned: 0, failed: 0, titles: [] };
    if (ev.status === 'learned') byDate[d].learned += 1;
    if (ev.status === 'failed') byDate[d].failed += 1;
    if (ev.title && byDate[d].titles.length < 8) byDate[d].titles.push(ev.title);
  }

  const calendar = Object.values(byDate).sort((a, b) => String(b.learning_date).localeCompare(String(a.learning_date)));

  return {
    ok: true,
    today: learningDateIST(),
    timezone: 'Asia/Kolkata',
    articles_total: count || 0,
    pending_unlearned: pending || [],
    pending_count: (pending || []).length,
    recent_events: events || [],
    learning_calendar: calendar,
    scheduler: getCmsLearningSchedulerStatus(),
    architecture_status: 'v1.0.1 LOCKED',
  };
}

export function cmsLearningConfigured() {
  // Sync check — credentials only (client constructed async elsewhere)
  const url = (process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').trim();
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  return Boolean(url && key);
}

/**
 * Founder-facing digest: what intelligence learned over the last N days.
 * Soft-wire only — CMS learn events + optional KC corpus digest.
 */
export async function buildRecentLearningSummary({ engineFetch = null, days = 5 } = {}) {
  const dayCount = Math.min(Math.max(Number(days) || 5, 1), 30);
  const status = await cmsLearningStatus({ days: dayCount });
  const today = learningDateIST();

  let corpus = null;
  if (typeof engineFetch === 'function') {
    try {
      const kc = await engineFetch('/v1/kc/learning');
      if (kc?.ok && kc.data) {
        corpus = {
          as_of: kc.data.as_of || null,
          learned_today: kc.data.learned_today || [],
          what_changed: kc.data.what_changed || [],
          companies_changed: kc.data.companies_changed || [],
          sectors_changed: kc.data.sectors_changed || [],
          themes_changed: kc.data.themes_changed || [],
          documents_processed: kc.data.documents_processed ?? null,
        };
      }
    } catch {
      corpus = null;
    }
  }

  if (!status?.ok) {
    return {
      ok: Boolean(corpus),
      days: dayCount,
      timezone: 'Asia/Kolkata',
      today,
      summary:
        corpus?.learned_today?.length
          ? `Corpus digest available for ${corpus.as_of || today}; CMS learning calendar unavailable (${status?.reason || status?.error || 'unknown'}).`
          : `Learning summary unavailable (${status?.reason || status?.error || 'unknown'}).`,
      articles_learned: 0,
      unique_articles: 0,
      failed: 0,
      highlights: [],
      by_day: [],
      latest_learning_date: null,
      corpus,
      architecture_status: 'v1.0.1 LOCKED',
    };
  }

  const events = Array.isArray(status.recent_events) ? status.recent_events : [];
  const learnedEvents = events.filter((e) => e.status === 'learned');
  const failedEvents = events.filter((e) => e.status === 'failed');
  const uniqueIds = new Set(learnedEvents.map((e) => e.article_id).filter(Boolean));
  const uniqueTitles = [];
  const seenTitle = new Set();
  for (const ev of learnedEvents) {
    const t = String(ev.title || '').trim();
    if (!t || seenTitle.has(t)) continue;
    seenTitle.add(t);
    uniqueTitles.push(t);
  }

  const byDayMap = {};
  for (const ev of events) {
    const d = ev.learning_date || String(ev.learned_at || '').slice(0, 10);
    if (!d) continue;
    if (!byDayMap[d]) {
      byDayMap[d] = {
        learning_date: d,
        learned_events: 0,
        failed: 0,
        article_ids: new Set(),
        titles: [],
      };
    }
    if (ev.status === 'learned') {
      byDayMap[d].learned_events += 1;
      if (ev.article_id) byDayMap[d].article_ids.add(ev.article_id);
      const t = String(ev.title || '').trim();
      if (t && byDayMap[d].titles.length < 6 && !byDayMap[d].titles.includes(t)) {
        byDayMap[d].titles.push(t);
      }
    }
    if (ev.status === 'failed') byDayMap[d].failed += 1;
  }

  const by_day = Object.values(byDayMap)
    .map((d) => ({
      learning_date: d.learning_date,
      articles_learned: d.article_ids.size || d.learned_events,
      learned_events: d.learned_events,
      failed: d.failed,
      titles: d.titles,
    }))
    .sort((a, b) => String(b.learning_date).localeCompare(String(a.learning_date)))
    .slice(0, dayCount);

  const uniqueCount = uniqueIds.size || uniqueTitles.length;
  const latest = by_day[0]?.learning_date || null;
  const dayBits = by_day
    .filter((d) => d.articles_learned > 0)
    .slice(0, 5)
    .map((d) => `${d.learning_date}: ${d.articles_learned} article${d.articles_learned === 1 ? '' : 's'}`);

  let summary;
  if (uniqueCount === 0) {
    summary = `No CMS articles were learned in the last ${dayCount} days.`;
  } else {
    summary = `Over the last ${dayCount} days, intelligence learned ${uniqueCount} CMS article${
      uniqueCount === 1 ? '' : 's'
    }${latest ? ` (latest ${latest})` : ''}.`;
    if (dayBits.length) summary += ` Daily: ${dayBits.join(' · ')}.`;
  }

  const corpusBits = (corpus?.learned_today || []).slice(0, 3);
  if (corpusBits.length) {
    summary += ` Corpus also notes: ${corpusBits.join('; ')}`;
  }

  return {
    ok: true,
    days: dayCount,
    timezone: 'Asia/Kolkata',
    today,
    from_window_days: dayCount,
    articles_total: status.articles_total || 0,
    pending_count: status.pending_count || 0,
    articles_learned: uniqueCount,
    unique_articles: uniqueCount,
    learn_events: learnedEvents.length,
    failed: failedEvents.length,
    highlights: uniqueTitles.slice(0, 12),
    by_day,
    latest_learning_date: latest,
    summary,
    corpus,
    architecture_status: 'v1.0.1 LOCKED',
  };
}

let cmsLearnScheduler = null;
let cmsLearnLastRun = null;
let cmsLearnLastDate = null;

export function getCmsLearningSchedulerStatus() {
  return {
    enabled: Boolean(cmsLearnScheduler),
    last_run: cmsLearnLastRun,
    last_learning_date: cmsLearnLastDate,
    interval_ms: Number(process.env.CMS_ARTICLE_LEARN_INTERVAL_MS || 60 * 60 * 1000),
  };
}

/**
 * Soft daily learner — once per IST calendar day, read CMS articles into KIP/KF/KC.
 * Disable with CMS_ARTICLE_LEARN_DAILY=false.
 */
export function startCmsArticleLearningScheduler(engineFetch) {
  if (cmsLearnScheduler) return;
  if ((process.env.CMS_ARTICLE_LEARN_DAILY || 'true').toLowerCase() === 'false') return;
  if (!cmsLearningConfigured()) {
    console.info('[cms-learn] scheduler idle — Supabase admin credentials missing');
    return;
  }
  if (typeof engineFetch !== 'function') {
    console.warn('[cms-learn] scheduler skipped — engineFetch required');
    return;
  }

  const intervalMs = Number(process.env.CMS_ARTICLE_LEARN_INTERVAL_MS || 60 * 60 * 1000);
  const tick = async () => {
    const today = learningDateIST();
    if (cmsLearnLastDate === today && cmsLearnLastRun?.ok) return;
    try {
      const result = await learnCmsArticles({
        engineFetch,
        mode: 'daily',
        limit: Number(process.env.CMS_ARTICLE_LEARN_LIMIT || 50),
        compound: true,
      });
      cmsLearnLastRun = {
        at: new Date().toISOString(),
        ok: Boolean(result?.ok),
        learning_date: result?.learning_date || today,
        learned: result?.learned ?? 0,
        failed: result?.failed ?? 0,
        skipped: result?.skipped ?? 0,
        reason: result?.reason || result?.error || null,
      };
      if (result?.ok) cmsLearnLastDate = result.learning_date || today;
      console.info(
        '[cms-learn] daily run',
        cmsLearnLastRun.learning_date,
        `learned=${cmsLearnLastRun.learned}`,
        `failed=${cmsLearnLastRun.failed}`
      );
    } catch (err) {
      cmsLearnLastRun = {
        at: new Date().toISOString(),
        ok: false,
        error: err?.message || String(err),
      };
      console.warn('[cms-learn] scheduled run failed:', err?.message || err);
    }
  };

  setTimeout(() => {
    tick().catch(() => {});
  }, 45_000);
  cmsLearnScheduler = setInterval(() => {
    tick().catch(() => {});
  }, intervalMs);
  cmsLearnScheduler.unref?.();
  console.info(`[cms-learn] daily scheduler active every ${Math.round(intervalMs / 60000)}m (IST dates)`);
}
