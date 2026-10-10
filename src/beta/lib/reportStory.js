/** Map an InstitutionalReport (or run) into story blocks — never invents metrics. */

export function estimateReadTime(report) {
  if (!report) return 3;
  const text = [
    report.executive_summary,
    report.company_view,
    report.financial_view,
    report.market_view,
    report.macro_view,
    report.sector_view,
    report.valuation_view,
    report.technical_view,
    ...(report.key_findings || []),
  ]
    .filter(Boolean)
    .join(' ');
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(3, Math.min(12, Math.ceil(words / 180)));
}

export function stanceTone(stance) {
  const t = String(stance || '').toLowerCase();
  if (t.includes('constructive') || t.includes('bull')) return 'pos';
  if (t.includes('cautious') || t.includes('bear')) return 'neg';
  return 'warn';
}

export function buildStoryFromReport(report, { symbols = [] } = {}) {
  if (!report) return null;
  const confidence = report.confidence?.score ?? null;
  return {
    title: report.title,
    symbols,
    stance: report.recommendation || report.confidence?.rationale?.slice(0, 24) || 'Neutral',
    confidence,
    summary: report.executive_summary,
    thesis: report.investment_thesis || null,
    takeaways: report.key_findings || [],
    business: report.company_view || report.sector_view || null,
    financial: report.financial_view || report.earnings_view || report.valuation_view || null,
    growth: (report.catalysts || []).slice(0, 6),
    forecast:
      report.base_case || report.bull_case || report.bear_case
        ? {
            bull: report.bull_case,
            base: report.base_case,
            bear: report.bear_case,
          }
        : null,
    risks: report.risks || [],
    timeline: [
      ...(report.action_items || []).map((item, i) => ({ label: `Action ${i + 1}`, detail: item })),
      ...(report.catalysts || []).slice(0, 3).map((item, i) => ({ label: `Catalyst ${i + 1}`, detail: item })),
    ],
    evidence: (report.supporting_evidence || []).map((ev) => ({
      claim: ev.claim,
      source_id: ev.source_id,
      source_type: ev.source_type,
    })),
    macro: report.macro_view || null,
    market: report.market_view || null,
    readTime: estimateReadTime(report),
  };
}

export function whyFromText(text, limit = 3) {
  if (!text) return [];
  return String(text)
    .split(/[\n•]+|(?<=\.)\s+(?=[A-Z])/)
    .map((s) => s.trim())
    .filter((s) => s.length > 18)
    .slice(0, limit);
}
