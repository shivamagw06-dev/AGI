const TRUNCATED_END_RE = /(?:\u2026|\.\.\.)\s*$/;

function canonicalSentence(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9%₹$]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Remove repeated synthesis fragments without changing supported claims. */
export function dedupeAnswerText(value = '') {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  const sentences = text.match(/[^.!?]+(?:[.!?]+|$)/g) || [text];
  const seen = new Set();
  const kept = [];
  for (const raw of sentences) {
    const sentence = raw.trim();
    const key = canonicalSentence(sentence);
    if (!key || seen.has(key)) continue;
    if ([...seen].some((prior) =>
      Math.min(prior.length, key.length) >= 48 && (prior.startsWith(key) || key.startsWith(prior)))) {
      continue;
    }
    // A clipped fragment is not acceptable evidence and should never be surfaced.
    if (TRUNCATED_END_RE.test(sentence) && key.split(' ').length < 8) continue;
    seen.add(key);
    kept.push(sentence);
  }
  return kept.join(' ').trim();
}

export function normalizeProvenance(items = [], limit = 12) {
  const out = [];
  const seen = new Set();
  for (const item of Array.isArray(items) ? items : []) {
    const row = typeof item === 'string'
      ? { title: item, source: 'AGI research' }
      : {
          title: item?.title || item?.name || item?.text || item?.source || 'Research evidence',
          source: item?.source || item?.publisher || item?.provider || 'AGI research',
          url: item?.url || item?.href || '',
          date: item?.publication_date || item?.published_at || item?.as_of || item?.date || '',
          evidenceType: item?.evidence_type || item?.type || item?.classification || '',
        };
    const key = `${row.title}|${row.url}|${row.date}`.toLowerCase();
    if (!row.title || seen.has(key)) continue;
    seen.add(key);
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}

export function calibrateDisplayedConfidence(value, qualityGates = {}) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  let cap = 100;
  if (qualityGates.full_company_analysis) {
    if (qualityGates.financials_supported === false) cap = Math.min(cap, 65);
    if (qualityGates.valuation_supported === false) cap = Math.min(cap, 65);
    if (qualityGates.financials_supported === false && qualityGates.valuation_supported === false) {
      cap = 50;
    }
  }
  if (qualityGates.conglomerate_framework_validated === false) cap = Math.min(cap, 50);
  return Math.max(0, Math.min(parsed, cap));
}

export function scenarioCopy(formatKey = 'company') {
  if (formatKey === 'sector') {
    return {
      title: 'Market Scenarios',
      positive: 'Constructive scenario',
      negative: 'Risk scenario',
      positiveLead: 'What could improve the outlook',
      negativeLead: 'What could weaken the outlook',
    };
  }
  if (formatKey === 'trading') {
    return {
      title: 'Market Setup',
      positive: 'Positive confirmation',
      negative: 'Invalidation risk',
      positiveLead: 'What would confirm the setup',
      negativeLead: 'What would invalidate it',
    };
  }
  return {
    title: 'Bull vs Bear Case',
    positive: 'Bull Case',
    negative: 'Bear Case',
    positiveLead: 'Evidence that could strengthen the thesis',
    negativeLead: 'Evidence that could weaken the thesis',
  };
}
