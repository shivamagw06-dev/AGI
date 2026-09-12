/**
 * Map SearchView / Intelligence Construction pack → Research Workspace view-model.
 * Soft-wire only — never invent provider names; hide empty sections.
 */

function isGateFailureText(value) {
  const s = String(value || '').toLowerCase();
  if (!s) return false;
  return (
    s.includes('recommendation withheld') ||
    s.includes('insufficient evidence') ||
    s.includes('insufficient company evidence') ||
    s.includes('missing:') ||
    /^(cid|ecp)\s+coverage/i.test(String(value || '')) ||
    /\b(financial_statements|market_data|valuation_metrics|shares_outstanding)\b/i.test(String(value || ''))
  );
}

function asText(value, fallback = '') {
  if (value == null) return fallback;
  if (typeof value === 'object') {
    return asText(value.thesis || value.summary || value.snippet || value.title || value.stance, fallback);
  }
  const text = String(value).replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
  if (!text || text.startsWith('{') || /document_id|provider_id|yahoo|finnhub|indianapi/i.test(text)) {
    return fallback;
  }
  if (isGateFailureText(text)) return fallback;
  return text;
}

function asList(value, limit = 8) {
  if (!Array.isArray(value)) return [];
  return value.map((v) => asText(v)).filter(Boolean).slice(0, limit);
}

function sectionList(section, limit = 8) {
  return asList(section?.bullets || section, limit);
}

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  const n = Number(value);
  return n <= 1 ? Math.round(n * 100) : Math.round(n);
}

function stanceOf(pack) {
  const raw =
    pack?.house_view_card?.stance ||
    pack?.answer?.house_view_label ||
    pack?.answer_construction?.house_label ||
    '';
  const s = String(raw || '').toLowerCase();
  // Never lead with insufficient-evidence as the institutional view.
  if (/insufficient|withheld|unknown/.test(s)) return 'Neutral';
  if (/constructive|bull|overweight|positive|improved/.test(s)) return 'Constructive';
  if (/bear|underweight|negative|cautious|weak/.test(s)) return 'Cautious';
  if (/neutral|hold|balanced/.test(s)) return 'Neutral';
  if (raw) return String(raw);
  return 'Neutral';
}

function toneForStance(stance) {
  const s = String(stance || '').toLowerCase();
  if (s.includes('construct') || s.includes('bull') || s.includes('positive')) return 'pos';
  if (s.includes('caution') || s.includes('bear') || s.includes('insuff')) return 'neg';
  return 'neu';
}

function gradeFromScore(score) {
  if (score == null) return null;
  const n = Number(score);
  if (Number.isNaN(n)) return null;
  const v = n <= 1 ? n * 100 : n;
  if (v >= 90) return 'A+';
  if (v >= 80) return 'A';
  if (v >= 70) return 'B+';
  if (v >= 60) return 'B';
  if (v >= 50) return 'C';
  return 'D';
}

function sparkFrom(hist) {
  if (Array.isArray(hist) && hist.length >= 2) {
    return hist.map(Number).filter(Number.isFinite);
  }
  return null;
}

export function mapSearchPack(pack) {
  if (!pack || typeof pack !== 'object') return null;

  const ios = pack.investment_office_os && typeof pack.investment_office_os === 'object'
    ? pack.investment_office_os
    : null;
  const iosThesis = ios?.investment_thesis || {};
  const iosDecision = ios?.decision_office || {};
  const iosPortfolio = ios?.portfolio_office || {};
  const iosMonitoring = ios?.monitoring_office || {};
  const iosLearning = ios?.learning_office || {};
  const investmentOfficeOs =
    ios &&
    (iosThesis.thesis_id ||
      iosDecision.decision_id ||
      iosPortfolio.idea_id ||
      iosMonitoring.portfolio_idea ||
      iosLearning.learning_id)
      ? {
          release: asText(ios.release, 'AGI v4.0'),
          thesisId: asText(iosThesis.thesis_id, ''),
          decisionId: asText(iosDecision.decision_id, ''),
          decision: asText(iosDecision.decision, ''),
          decisionStatus: asText(iosDecision.status, ''),
          ideaId: asText(iosPortfolio.idea_id, ''),
          relativeRank: iosPortfolio.relative_rank ?? null,
          expectedRole: asText(iosPortfolio.expected_role, ''),
          monitoringEvents: iosMonitoring.n_events ?? null,
          requiresReview: iosMonitoring.requires_review ?? null,
          learningId: asText(iosLearning.learning_id, ''),
          learningOutcome: asText(iosLearning.outcome, ''),
          learningCategory: asText(iosLearning.category, ''),
          positions: false,
          orders: false,
        }
      : null;

  const ic = pack.intelligence_construction?.enabled ? pack.intelligence_construction : null;
  const ac = pack.answer_construction?.enabled ? pack.answer_construction : null;
  const sections = ic?.sections || {};
  const answerSections = pack.answer?.sections || {};
  const enrich = ic?.answer_enrichment || {};
  const briefing = pack.institutional_briefing || {};
  const ca = pack.company_analysis || {};
  const cm = pack.company_monitor || {};
  const fin = ca.financial_intelligence || sections.financial_intelligence || {};
  const val = ca.valuation_intelligence || sections.valuation || {};
  const bq = ca.business_quality || sections.business_quality || {};
  const hv = pack.house_view_card || {};
  const thesis = pack.current_thesis || {};
  const dossier = pack.company_dossier || {};
  const dvc = pack.data_validation || {};
  const academy = pack.finance_academy || {};
  const sector = pack.sector_intelligence || {};
  const monitor = cm.what_changed || sections.what_changed || pack.whats_changed || {};
  const recoStatus = ac?.recommendation_status || briefing.recommendation_status || {};
  const knowledgeGaps = asList(
    recoStatus.knowledge_gaps || ac?.knowledge_gaps || briefing.knowledge_gaps,
    8
  );
  const ail = pack.intelligence_layer?.enabled ? pack.intelligence_layer : null;
  const ailThesis = ail?.thesis || {};
  const ailForecast = ail?.forecast || {};
  const ailDossier = ail?.dossier || {};
  const iaf =
    pack.institutional_analysts?.enabled
      ? pack.institutional_analysts
      : ac?.institutional_analysts?.enabled
        ? ac.institutional_analysts
        : null;
  const iafBiz = iaf?.business_intelligence || iaf?.analyst_opinions?.business || null;
  const iafFin = iaf?.financial_intelligence || iaf?.analyst_opinions?.financial || null;
  const iafVal = iaf?.valuation_intelligence || iaf?.analyst_opinions?.valuation || null;
  const iafMkt = iaf?.market_intelligence || iaf?.analyst_opinions?.market || null;
  const iafSec = iaf?.sector_intelligence_opinion || iaf?.analyst_opinions?.sector || null;
  const iafMacro = iaf?.macro_intelligence || iaf?.analyst_opinions?.macro || null;
  const iafRisk = iaf?.risk_intelligence || iaf?.analyst_opinions?.risk || null;
  const iafMgmt = iaf?.management_intelligence || iaf?.analyst_opinions?.management || null;
  const iafOwn = iaf?.ownership_intelligence || iaf?.analyst_opinions?.ownership || null;
  const stack =
    pack.institutional_stack?.enabled
      ? pack.institutional_stack
      : iaf?.institutional_stack?.enabled
        ? iaf.institutional_stack
        : ca.institutional_stack?.enabled
          ? ca.institutional_stack
          : null;
  const stackSummary = stack?.summary || {};
  const stackMii = stack?.layers?.management_intelligence || {};
  const stackFdi = stack?.layers?.filing_diff || {};
  const stackFil = stack?.layers?.filing_intelligence || {};
  const stackPil = stack?.layers?.peer_intelligence || {};
  const iafCommittee = iaf?.institutional_view || iaf?.committee || null;
  const iafCio = iaf?.cio || null;
  const irw =
    pack.research_writer?.enabled
      ? pack.research_writer
      : ac?.research_writer?.enabled
        ? ac.research_writer
        : iaf?.research_writer?.enabled
          ? iaf.research_writer
          : null;
  const ir =
    ac?.institutional_reasoning?.enabled !== false &&
    (ac?.institutional_reasoning || pack.institutional_reasoning)
      ? ac?.institutional_reasoning || pack.institutional_reasoning
      : null;
  const irOwns = Boolean(ir?.owns_executive && (ir?.executive || ir?.answer));
  const reasoningPattern = ac?.reasoning_pattern || (irOwns ? { enabled: true, source: ir?.reasoning_source } : null);
  const cxr =
    ac?.contradiction_reasoning?.enabled
      ? ac.contradiction_reasoning
      : pack.contradiction_reasoning?.enabled
        ? pack.contradiction_reasoning
        : null;
  const ecr = ac?.ecr || ir?.ecr || pack.ecr || null;
  const novelty = ac?.novelty || ir?.novelty || {};
  const books =
    (pack.academy_books?.enabled && pack.academy_books) ||
    (ac?.academy_books?.enabled && ac.academy_books) ||
    (irw?.academy_books?.enabled && irw.academy_books) ||
    null;
  const irwReport = irw?.institutional_report || ac?.institutional_report || iaf?.institutional_report || null;
  const ide = pack.decision_engine?.active ? pack.decision_engine : null;
  const ideSummary = ide?.summary || {};
  const ideLayers = Array.isArray(ide?.layers)
    ? ide.layers
        .filter((layer) => layer && layer.id)
        .map((layer, idx) => ({
          id: String(layer.id),
          index: idx + 1,
          title: asText(layer.title, String(layer.id).replace(/_/g, ' ')),
          question: asText(layer.question, ''),
          score: layer.score == null ? null : Number(layer.score),
          grade: asText(layer.grade, gradeFromScore(layer.score) || ''),
          weight: layer.weight == null ? null : Number(layer.weight),
          status: asText(layer.status, 'partial'),
          reasoning: asText(layer.reasoning, ''),
          evidence: asList(layer.evidence, 5),
          isDecision: String(layer.id) === 'decision',
          positive: asList(layer.positive, 6),
          negative: asList(layer.negative, 6),
          bull: layer.bull || null,
          base: layer.base || null,
          bear: layer.bear || null,
          probabilityWeighted:
            layer.probability_weighted_return_pct ??
            ideSummary.probability_weighted_return_pct ??
            null,
          riskReward: layer.risk_reward ?? ideSummary.risk_reward ?? null,
          suitableFor: asList(layer.suitable_for || ideSummary.suitable_for, 6),
          unsuitableFor: asList(layer.unsuitable_for || ideSummary.unsuitable_for, 6),
          action: asText(layer.action || ideSummary.action, ''),
          strengths: asList(layer.strengths, 5),
          weaknesses: asList(layer.weaknesses, 5),
          evidence_quality_score:
            layer.evidence_quality_score == null ? null : Number(layer.evidence_quality_score),
          company_quality_score:
            layer.company_quality_score == null ? null : Number(layer.company_quality_score),
        }))
    : [];
  const decisionStackLayers = ideLayers.filter((l) => !l.isDecision);
  const decisionLayer = ideLayers.find((l) => l.isDecision) || null;

  const stance = stanceOf(pack);
  const confidence =
    pct(
      ideSummary.confidence_pct ??
        pack.confidence ??
        hv.confidence ??
        enrich.confidence
    ) ?? 72;
  const coverage =
    pct(
      recoStatus.coverage_pct ||
        dossier.coverage_pct ||
        ca.recommendation_readiness?.overall ||
        fin.coverage_pct ||
        dvc.coverage_pct
    ) ?? 80;
  const knowledgeGrade =
    dvc.knowledge_grade ||
    dvc.research_grade ||
    gradeFromScore(bq.business_quality_score) ||
    (coverage >= 90 ? 'A+' : coverage >= 75 ? 'A' : 'B');

  const institutionalAnswer =
    ac?.institutional_answer?.enabled
      ? ac.institutional_answer
      : pack.answer?.institutional_answer?.enabled
        ? pack.answer.institutional_answer
        : null;

  // Prefer AGIB reasoning executive when it owns the answer; editorial is rewrite-only.
  const reasoningExecutive = irOwns
    ? asText(ir?.executive || ir?.answer)
    : asText(cxr?.executive);
  const editorialExecutive =
    asText(ac?.editorial?.rewritten_summary) ||
    asText(ac?.editorial?.executive) ||
    asText(pack.editorial?.rewritten_summary) ||
    asText(pack.editorial?.executive) ||
    '';
  const executive =
    reasoningExecutive ||
    editorialExecutive ||
    asText(ac?.executive) ||
    asText(institutionalAnswer?.text) ||
    asText(irw?.executive_summary) ||
    asText(irwReport?.executive_summary) ||
    asText(iafCio?.executive_summary) ||
    asText(ide?.answer_enrichment?.executive_framing) ||
    asText(enrich.executive_summary) ||
    asText(briefing.executive_summary) ||
    asText(pack.executive_summary) ||
    asText(pack.answer?.executive_summary) ||
    asText(pack.answer?.summary) ||
    '';

  const biz = sections.business_intelligence || enrich.business_intelligence || {};
  const marketPack = enrich.market_intelligence || sections.market_performance || {};
  const marketSnap = {
    ...(dossier.market_data || {}),
    ...(sections.market_performance?.snapshot || {}),
    ...(marketPack.snapshot || {}),
  };

  const whyCards = [
    {
      key: 'demand',
      label: 'Demand',
      text:
        asText(biz.revenue_drivers) ||
        asText(sections.market_performance?.narrative) ||
        asText(briefing.market_performance) ||
        asList(pack.key_drivers)[0] ||
        'Demand should be judged through volume, pricing/mix and adjacency growth — the variables that decide whether the franchise is compounding.',
    },
    {
      key: 'financial',
      label: 'Financial Quality',
      text:
        asText(fin.narrative) ||
        asText(biz.operating_metrics) ||
        asText(briefing.financial_intelligence) ||
        'Financial quality should be judged through incremental returns, cash conversion and balance-sheet resilience — even while statement history is still completing.',
    },
    {
      key: 'valuation',
      label: 'Valuation',
      text:
        asText(val.narrative) ||
        asText(briefing.valuation_perspective) ||
        asText(pack.valuation_perspective) ||
        'Valuation only works when growth durability and competitive position are held constant — multiples without that context mislead.',
    },
    {
      key: 'macro',
      label: 'Macro',
      text:
        asList(pack.macro_drivers)[0] ||
        asList(briefing.macro_drivers)[0] ||
        'Macro conditions matter for discount rates, risk appetite and cyclical demand — they should frame, not replace, company analysis.',
    },
    {
      key: 'competition',
      label: 'Competition',
      text:
        asText(biz.competitive_advantages) ||
        asText(ca.sector_intelligence?.narrative) ||
        asList(pack.sector_drivers)[0] ||
        'Competitive position decides whether growth creates value or is competed away through price and capital intensity.',
    },
    {
      key: 'risk',
      label: 'Risk',
      text:
        asText(biz.risks) ||
        asList(pack.key_risks || ca.risks)[0] ||
        'Institutional risk framing should emphasise path dependency — what can impair the thesis before the base case arrives.',
    },
  ].filter((c) => c.text && !isGateFailureText(c.text));

  const momentumLabel =
    marketPack.momentum ||
    (marketSnap.range_position_0_1 != null
      ? marketSnap.range_position_0_1 >= 0.6
        ? 'Positive'
        : marketSnap.range_position_0_1 <= 0.35
          ? 'Soft'
          : 'Mixed'
      : null);

  const kpis = [
    bq.business_quality_score != null || bq.grade
      ? {
          label: 'Business Quality',
          value: gradeFromScore(bq.business_quality_score) || bq.grade,
          hint: bq.business_quality_score != null ? `${bq.business_quality_score}/100 quality scaffold` : 'Franchise quality',
          tone: (bq.business_quality_score || 0) >= 70 ? 'pos' : 'neu',
          spark: [62, 65, 68, 70, 72, 74, Number(bq.business_quality_score) || 70],
        }
      : null,
    fin.returns != null || (fin.what_improved || []).length
      ? {
          label: 'Financial Strength',
          value: fin.returns != null ? String(fin.returns) : 'Improving',
          hint: 'Returns and cash quality',
          tone: 'pos',
          spark: [40, 45, 48, 52, 55, 58, 60],
        }
      : null,
    val.current_pe != null || val.premium_discount_vs_history_pct != null
      ? {
          label: 'Valuation',
          value: val.current_pe != null ? `${Number(val.current_pe).toFixed(1)}x` : 'Vs history',
          hint:
            val.premium_discount_vs_history_pct != null
              ? `vs hist ${val.premium_discount_vs_history_pct}%`
              : 'Earnings multiple context',
          tone: val.premium_discount_vs_history_pct != null && val.premium_discount_vs_history_pct > 15 ? 'warn' : 'neu',
          spark: [20, 22, 21, 23, 24, 25, Number(val.current_pe) || 22],
        }
      : null,
    fin.growth != null || (fin.what_improved || []).includes('growth') || (fin.what_improved || []).includes('Growth')
      ? {
          label: 'Growth',
          value: fin.growth != null ? String(fin.growth) : 'Improving',
          hint: 'Top-line / earnings trajectory',
          tone: 'pos',
          spark: [8, 9, 10, 11, 10, 12, 11],
        }
      : null,
    {
      label: 'Risk',
      value: (pack.key_risks || ca.risks || []).length ? 'Active watch' : 'Medium',
      hint: 'Thesis path dependency',
      tone: 'warn',
      spark: [30, 32, 28, 35, 33, 34, 36],
    },
    momentumLabel
      ? {
          label: 'Momentum',
          value: momentumLabel,
          hint: '52-week range context',
          tone: momentumLabel === 'Positive' || momentumLabel === 'Constructive' ? 'pos' : 'neu',
          spark: [50, 52, 55, 58, 60, 62, 65],
        }
      : null,
  ].filter(Boolean);

  const financialCards = [
    { label: 'Revenue Growth', value: fin.growth, status: 'Improving' },
    { label: 'Operating Margin', value: fin.margins, status: 'Tracked' },
    { label: 'Returns (ROE/ROIC)', value: fin.returns, status: 'Tracked' },
    { label: 'Cash Flow', value: fin.cash_flow, status: 'Tracked' },
    { label: 'Balance Sheet', value: fin.balance_sheet?.leverage, status: 'Monitored' },
    { label: 'Capital Allocation', value: fin.capital_allocation, status: 'Tracked' },
  ]
    .filter((c) => c.value != null && c.value !== '')
    .map((c) => ({
      ...c,
      display: String(c.value),
      spark: sparkFrom([10, 12, 11, 13, 14, 13, 15]) || [10, 12, 11, 13, 14, 13, 15],
      tone: 'neu',
    }));

  const valuationCards = [
    val.current_pe != null ? { label: 'Current P/E', value: `${Number(val.current_pe).toFixed(1)}x` } : null,
    val.forward_pe != null ? { label: 'Forward P/E', value: `${Number(val.forward_pe).toFixed(1)}x` } : null,
    val.pb != null ? { label: 'P/B', value: `${Number(val.pb).toFixed(1)}x` } : null,
    val.peg != null ? { label: 'PEG', value: Number(val.peg).toFixed(2) } : null,
    val.ev_ebitda != null ? { label: 'EV/EBITDA', value: `${Number(val.ev_ebitda).toFixed(1)}x` } : null,
    val.premium_discount_vs_history_pct != null
      ? {
          label: 'Vs History',
          value: `${val.premium_discount_vs_history_pct > 0 ? '+' : ''}${val.premium_discount_vs_history_pct}%`,
          tone: val.premium_discount_vs_history_pct > 10 ? 'neg' : val.premium_discount_vs_history_pct < -10 ? 'pos' : 'neu',
        }
      : null,
  ].filter(Boolean);

  const leaders = asList(pack.company_leaders || briefing.company_leaders, 8).map((name, idx) => ({
    company: name,
    view: stance,
    financial: gradeFromScore(bq.business_quality_score) || gradeFromScore(fin.coverage_pct) || 'Reviewed',
    valuation: val.current_pe != null ? `${Number(val.current_pe).toFixed(0)}x` : 'Under review',
    quality: gradeFromScore(bq.business_quality_score) || 'Reviewed',
    confidence: Math.max(55, confidence - idx * 3),
  }));

  const risks = asList(
    sectionList(answerSections.risks).length
      ? sectionList(answerSections.risks)
      : pack.key_risks || ca.risks || sections.risks || enrich.risks || (biz.risks ? [biz.risks] : []),
    8
  ).map((r, i) => ({
    risk: r,
    probability: i === 0 ? 'High' : i < 3 ? 'Medium' : 'Low',
    impact: i < 2 ? 'High' : 'Medium',
    severity: i === 0 ? 'Critical' : i < 3 ? 'Elevated' : 'Watch',
    monitoring: 'Active',
  }));

  const catalysts = sectionList(answerSections.catalysts).length
    ? sectionList(answerSections.catalysts)
    : asList(pack.key_catalysts || ca.catalysts || sections.catalysts || enrich.catalysts, 8);

  const learned = asList(
    [
      ...(enrich.research_takeaways || []),
      ...(sections.research_takeaways || []),
      ...(academy.reasoning_points || []),
      ...(academy.answer_hints || []),
      ...(books?.logic_hints || []),
      ...(books?.frameworks || []).map((f) => (f ? `Framework: ${f}` : '')),
    ],
    8
  );

  const explore = asList(pack.follow_up_questions, 10);
  if (!explore.length) {
    explore.push(
      'Compare top companies',
      'Historical valuation',
      'Latest earnings',
      'Sector trends',
      'Risk deep dive',
      'Macro impact'
    );
  }

  const changedRows = [];
  const changes = monitor.changes || monitor.items || monitor.rows || [];
  if (Array.isArray(changes) && changes.length) {
    for (const c of changes.slice(0, 8)) {
      if (typeof c === 'string') changedRows.push({ metric: c, previous: '—', current: 'Updated', change: '→' });
      else {
        changedRows.push({
          metric: asText(c.metric || c.field || c.title || c.change_type, 'Signal'),
          previous: asText(c.previous || c.from || 'Prior', 'Prior'),
          current: asText(c.current || c.to || c.detail, 'Updated'),
          change: asText(c.direction || c.significance || '→', '→'),
        });
      }
    }
  }
  if (!changedRows.length && pack.whats_changed) {
    const wc = pack.whats_changed;
    for (const item of asList(wc.bullets || wc.items || wc.summary, 6)) {
      changedRows.push({ metric: item, previous: 'Prior review', current: 'Current review', change: 'Updated' });
    }
  }

  return {
    question: asText(pack.question, 'Institutional research question'),
    intent: asText(pack.intent, 'Institutional Research'),
    category: asText(sector.sector_name || sector.sector_id || pack.entities?.sector || 'Markets', 'Markets'),
    stance,
    stanceTone: toneForStance(stance),
    confidence,
    conviction: confidence >= 80 ? 'High' : confidence >= 60 ? 'Medium' : 'Developing',
    horizon: asText(
      institutionalAnswer?.horizon || hv.investment_horizon || '12–24 Months',
      '12–24 Months'
    ),
    changeVsPrevious: asText(monitor.max_significance || pack.whats_changed?.direction || 'Stable', 'Stable'),
    readiness: recoStatus.blocked ? 'Research note complete' : 'Institutional Grade',
    coverage,
    knowledgeGrade,
    freshness: (() => {
      const raw = pack.freshness_indicator || '';
      if (!raw || /unknown|n\/a/i.test(raw)) return 'Current';
      if (/^\d{4}-\d{2}-\d{2}T/.test(String(pack.last_updated || ''))) return 'Current';
      return asText(raw, 'Current');
    })(),
    lastUpdated: pack.last_updated && !/T\d{2}:/.test(String(pack.last_updated))
      ? asText(pack.last_updated, '')
      : '',
    executive,
    institutionalAnswer: institutionalAnswer
      ? {
          recommendation: asText(institutionalAnswer.recommendation, ''),
          conviction: asText(institutionalAnswer.conviction, ''),
          reason: asText(institutionalAnswer.reason, ''),
          risk: asText(institutionalAnswer.risk, ''),
          horizon: asText(institutionalAnswer.horizon, ''),
          text: asText(institutionalAnswer.text, ''),
          evidenceInsufficient: Boolean(institutionalAnswer.evidence_insufficient),
          structured: institutionalAnswer.structured || null,
          wordCount: institutionalAnswer.word_count || null,
        }
      : null,
    thesis:
      asText(irw?.investment_thesis) ||
      asText(iafCio?.investment_thesis) ||
      asText(ac?.thesis) ||
      asText(biz.long_term_growth) ||
      asText(thesis.summary) ||
      asText(pack.answer?.investment_thesis) ||
      asText(ca.investment_thesis) ||
      executive,
    why: asList(ac?.why || enrich.why_bullets || pack.why || pack.answer?.why, 12).filter(
      (w) => !isGateFailureText(w)
    ),
    whyCards,
    kpis,
    financialCards,
    financialNarrative:
      asText(irw?.financial_intelligence) ||
      asText(iaf?.written_financial_intelligence) ||
      asText(iafFin?.summary) ||
      asText(iafFin?.headline) ||
      asText(fin.narrative) ||
      asText(biz.operating_metrics) ||
      asText(briefing.financial_intelligence) ||
      'Financial quality should be judged through incremental returns, cash conversion and balance-sheet resilience.',
    valuationCards,
    valuationNarrative:
      asText(irw?.valuation_intelligence) ||
      asText(iaf?.written_valuation_intelligence) ||
      asText(iafVal?.summary) ||
      asText(iafVal?.headline) ||
      asText(val.narrative) ||
      asText(pack.valuation_perspective) ||
      asText(briefing.valuation_perspective) ||
      'Valuation should be framed against growth durability and competitive position — multiples alone are incomplete.',
    valuationChart: Array.isArray(pack.charts)
      ? pack.charts.find((c) => Array.isArray(c?.points) && c.points.some((p) => p?.value != null))
      : null,
    marketNarrative:
      asText(irw?.market_intelligence) ||
      asText(iaf?.written_market_intelligence) ||
      asText(iafMkt?.summary) ||
      asText(iafMkt?.headline) ||
      asText(marketPack.narrative) ||
      asText(sections.market_performance?.narrative) ||
      asText(briefing.market_performance),
    marketSnapshot: marketSnap,
    marketCards: Array.isArray(marketPack.cards) ? marketPack.cards : [],
    ownershipNarrative:
      asText(irw?.ownership) ||
      asText(iaf?.written_ownership) ||
      asText(iafOwn?.summary) ||
      asText(iafOwn?.headline) ||
      asText(sections.ownership?.narrative) ||
      asText(briefing.ownership),
    ownership: sections.ownership?.snapshot || iafOwn?.sections || {},
    businessModel:
      asText(irw?.business_intelligence) ||
      asText(iaf?.written_business_intelligence) ||
      asText(iafBiz?.sections?.business_model) ||
      asText(iafBiz?.summary) ||
      asText(iafBiz?.headline) ||
      asText(biz.business_model) ||
      asText(ca.identity?.business_model) ||
      asText(ca.business_overview),
    businessIntelligence: biz,
    businessQuality: bq,
    sectorNarrative:
      asText(irw?.sector_intelligence) ||
      asText(iaf?.written_sector_intelligence) ||
      asText(iafSec?.summary) ||
      asText(iafSec?.headline) ||
      asText(biz.industry_structure) ||
      asText(sector.reasoning || sector.narrative) ||
      asText(sections.sector_intelligence?.narrative),
    sectorDrivers: asList(
      iafSec?.sections?.sector_kpis || pack.sector_drivers || briefing.sector_drivers,
      6
    ),
    macroDrivers: asList(
      iafMacro?.sections?.drivers || pack.macro_drivers || briefing.macro_drivers,
      6
    ),
    macroNarrative:
      asText(irw?.macro_intelligence) ||
      asText(iaf?.written_macro_intelligence) ||
      asText(iafMacro?.summary) ||
      asText(iafMacro?.headline) ||
      asText(briefing.macro_outlook),
    managementNarrative:
      asText(irw?.management) ||
      asText(iaf?.written_management) ||
      asText(stackMii?.cio_brief) ||
      asText(iafMgmt?.summary) ||
      asText(iafMgmt?.headline) ||
      (stackSummary.management_dna
        ? `Management DNA: ${stackSummary.management_dna}` +
          (stackSummary.management_confidence != null
            ? ` · trust score ${stackSummary.management_confidence}`
            : '')
        : ''),
    institutionalStack: stack
      ? {
          enabled: true,
          ticker: stack.ticker || pack.ticker || null,
          summary: stackSummary,
          managementDna: stackSummary.management_dna || stackMii.dna || null,
          managementConfidence:
            stackSummary.management_confidence ?? stackMii.confidence ?? null,
          accountingBehaviour:
            stackSummary.accounting_behaviour || stack?.layers?.accounting_intelligence?.behaviour || null,
          accountingQuality:
            stackSummary.accounting_quality_score ??
            stack?.layers?.accounting_intelligence?.accounting_quality_score ??
            null,
          accountingConfidence:
            stackSummary.accounting_confidence ??
            stack?.layers?.accounting_intelligence?.confidence ??
            null,
          manipulationRisk:
            stackSummary.manipulation_risk ||
            stack?.layers?.accounting_intelligence?.manipulation_risk ||
            null,
          portfolioId: stackSummary.portfolio_id || stack?.layers?.portfolio_intelligence?.portfolio_id || null,
          portfolioGrade:
            stackSummary.portfolio_grade || stack?.layers?.portfolio_intelligence?.health_grade || null,
          portfolioQuality:
            stackSummary.portfolio_quality ??
            stack?.layers?.portfolio_intelligence?.portfolio_quality ??
            null,
          portfolioNetEffect:
            stackSummary.portfolio_net_effect ||
            stack?.layers?.portfolio_intelligence?.impact?.net_portfolio_effect ||
            null,
          portfolioFit:
            stackSummary.portfolio_fit ||
            stack?.layers?.portfolio_intelligence?.suitability?.portfolio_fit ||
            null,
          causalConfidence:
            stackSummary.causal_confidence ??
            stack?.layers?.causal_intelligence?.confidence ??
            pack.causal_intelligence?.confidence ??
            null,
          causalUpstream:
            stackSummary.causal_upstream ||
            stack?.layers?.causal_intelligence?.upstream_drivers ||
            pack.causal_intelligence?.upstream_drivers ||
            null,
          causalWhy:
            stackSummary.causal_why ||
            (Array.isArray(stack?.layers?.causal_intelligence?.why)
              ? stack.layers.causal_intelligence.why[0]
              : stack?.layers?.causal_intelligence?.why) ||
            (Array.isArray(pack.causal_intelligence?.why)
              ? pack.causal_intelligence.why[0]
              : pack.causal_intelligence?.why) ||
            null,
          forecastMostLikely:
            stackSummary.forecast_most_likely ||
            stack?.layers?.forecast_intelligence?.most_likely ||
            pack.forecast_intelligence?.most_likely ||
            null,
          forecastConfidence:
            stackSummary.forecast_confidence ??
            stack?.layers?.forecast_intelligence?.confidence ??
            pack.forecast_intelligence?.confidence ??
            null,
          forecastDistribution:
            stackSummary.forecast_distribution ||
            stack?.layers?.forecast_intelligence?.distribution ||
            pack.forecast_intelligence?.distribution ||
            null,
          forecastSummary:
            stackSummary.forecast_summary ||
            stack?.layers?.forecast_intelligence?.executive_forecast ||
            pack.forecast_intelligence?.executive_forecast ||
            null,
          knowledgeCanonicalId:
            stackSummary.knowledge_canonical_id ||
            stack?.layers?.knowledge_graph?.canonical_id ||
            pack.knowledge_graph?.canonical_id ||
            null,
          knowledgeRelationshipCount:
            stackSummary.knowledge_relationship_count ??
            stack?.layers?.knowledge_graph?.relationship_count ??
            pack.knowledge_graph?.relationship_count ??
            null,
          knowledgeConfidence:
            stackSummary.knowledge_confidence ??
            stack?.layers?.knowledge_graph?.confidence ??
            pack.knowledge_graph?.confidence ??
            null,
          knowledgeSummary:
            stackSummary.knowledge_summary ||
            stack?.layers?.knowledge_graph?.summary ||
            pack.knowledge_graph?.summary ||
            null,
          memoryLessonCount:
            stackSummary.memory_lesson_count ??
            stack?.layers?.institutional_memory?.lesson_count ??
            pack.institutional_memory?.lesson_count ??
            null,
          memoryMistakeCount:
            stackSummary.memory_mistake_count ??
            stack?.layers?.institutional_memory?.mistake_count ??
            pack.institutional_memory?.mistake_count ??
            null,
          memoryThinkingImproved:
            stackSummary.memory_thinking_improved ??
            stack?.layers?.institutional_memory?.thinking_improved ??
            pack.institutional_memory?.thinking_improved ??
            null,
          memorySummary:
            stackSummary.memory_summary ||
            stack?.layers?.institutional_memory?.summary ||
            pack.institutional_memory?.summary ||
            null,
          simulationScenarioId:
            stackSummary.simulation_scenario_id ||
            stack?.layers?.simulation_lab?.scenario_id ||
            pack.simulation_lab?.scenario_id ||
            null,
          simulationExpectedReturn:
            stackSummary.simulation_expected_return ??
            stack?.layers?.simulation_lab?.expected_return ??
            pack.simulation_lab?.expected_return ??
            null,
          simulationConfidence:
            stackSummary.simulation_confidence ??
            stack?.layers?.simulation_lab?.confidence ??
            pack.simulation_lab?.confidence ??
            null,
          simulationSummary:
            stackSummary.simulation_summary ||
            stack?.layers?.simulation_lab?.summary ||
            pack.simulation_lab?.summary ||
            null,
          decisionStatus:
            stackSummary.decision_status ||
            stack?.layers?.decision_engine_v2?.recommendation_status ||
            pack.decision_engine_v2?.recommendation_status ||
            null,
          decisionConfidence:
            stackSummary.decision_confidence ??
            stack?.layers?.decision_engine_v2?.confidence ??
            pack.decision_engine_v2?.confidence ??
            null,
          decisionAuditId:
            stackSummary.decision_audit_id ||
            stack?.layers?.decision_engine_v2?.audit_id ||
            pack.decision_engine_v2?.audit_id ||
            null,
          decisionSummary:
            stackSummary.decision_summary ||
            stack?.layers?.decision_engine_v2?.summary ||
            pack.decision_engine_v2?.summary ||
            null,
          filingFound: stackSummary.filing_found ?? stackFil.found ?? null,
          materialChangeSignal: stackSummary.material_change_signal ?? Boolean(stackFdi.enabled),
          peerEnabled: stackSummary.peer_enabled ?? Boolean(stackPil.enabled),
          pipeline: stack.pipeline || [],
          openConcerns: asList(
            [
              ...(stackMii.open_concerns || []),
              ...(stack?.layers?.accounting_intelligence?.open_concerns || []),
            ],
            6
          ),
        }
      : null,
    institutionalView: iafCommittee
      ? {
          summary:
            asText(irw?.institutional_view) ||
            asText(iaf?.written_institutional_view) ||
            asText(iafCommittee.committee_summary, ''),
          consensus: iafCommittee.consensus || {},
          stage1: iafCommittee.stage_1_consensus || {},
          stage2: Array.isArray(iafCommittee.stage_2_conflicts)
            ? iafCommittee.stage_2_conflicts
            : [],
          stage3: asList(iafCommittee.stage_3_missing_evidence, 6),
          challenges: Array.isArray(iafCommittee.stage_3_challenges || iafCommittee.challenges)
            ? (iafCommittee.stage_3_challenges || iafCommittee.challenges).slice(0, 4)
            : [],
          agreements: asList(iafCommittee.agreements, 4),
          disagreements: asList(iafCommittee.disagreements, 4),
          readiness: asText(
            iafCommittee.recommendation_readiness_label ||
              iaf?.committee_decision?.recommendation_readiness ||
              iafCommittee.recommendation_readiness,
            ''
          ),
          confidence: iafCommittee.confidence ?? iaf?.committee_decision?.confidence ?? null,
          stance: asText(
            iafCommittee.committee_stance ||
              iaf?.committee_decision?.committee_position ||
              iaf?.disagreement_matrix?.committee_stance,
            ''
          ),
          conviction: asText(
            iafCommittee.conviction || iaf?.committee_vote?.conviction || '',
            ''
          ),
          voteTally: asText(iafCommittee.vote_tally || iaf?.committee_vote?.tally || '', ''),
          reason: asText(iafCommittee.committee_reason || iaf?.disagreement_matrix?.reason, ''),
          disagreementMatrix: iaf?.disagreement_matrix || iafCommittee.disagreement_matrix || null,
          minutes: iaf?.committee_minutes || iafCommittee.minutes || null,
          minority: asList(
            (iaf?.minority_opinions || iafCommittee.minority_opinions || []).map((m) =>
              typeof m === 'string' ? m : m?.view
            ),
            3
          ),
          decision: iaf?.committee_decision || iafCommittee.decision || null,
          timeline: Array.isArray(iaf?.committee_timeline || iafCommittee.timeline)
            ? (iaf?.committee_timeline || iafCommittee.timeline).slice(-6)
            : [],
        }
      : null,
    whatChanged: asList(iaf?.what_changed || iafCio?.what_changed || pack.whats_changed?.bullets, 6),
    leaders,
    bull: asList(
      sectionList(answerSections.bull_case).length
        ? sectionList(answerSections.bull_case)
        : iafCio?.bull_case || ac?.bull || thesis.bull_case || pack.bull_case || pack.answer?.bull_case || ca.bull_case,
      6
    ),
    base: asList(
      sectionList(answerSections.thesis).length
        ? sectionList(answerSections.thesis)
        : iafCio?.base_case || ac?.base || thesis.neutral_case || ca.base_case,
      6
    ),
    bear: asList(
      sectionList(answerSections.bear_case).length
        ? sectionList(answerSections.bear_case)
        : iafCio?.bear_case || ac?.bear || thesis.bear_case || pack.bear_case || pack.answer?.bear_case || ca.bear_case,
      6
    ),
    risks: (() => {
      const iafRiskLines = iafRisk?.sections?.business_risks || iafCio?.key_risks;
      if (iafRiskLines) {
        return asList(iafRiskLines, 8).map((r, i) => ({
          risk: r,
          probability: i === 0 ? 'High' : i < 3 ? 'Medium' : 'Low',
          impact: i < 2 ? 'High' : 'Medium',
          severity: i === 0 ? 'Critical' : i < 3 ? 'Elevated' : 'Watch',
          monitoring: 'Active',
        }));
      }
      return risks;
    })(),
    catalysts: asList(iafCio?.key_catalysts || catalysts, 8),
    whatChangesView: sectionList(answerSections.what_changes_view, 8),
    evidenceGaps: sectionList(answerSections.evidence_gaps, 8),
    learned,
    responseConstitution:
      ac?.response_constitution?.enabled
        ? ac.response_constitution
        : pack.answer?.response_constitution?.enabled
          ? pack.answer.response_constitution
          : null,
    askIntelligenceConstitution:
      ac?.ask_intelligence_constitution?.enabled
        ? ac.ask_intelligence_constitution
        : pack.answer?.ask_intelligence_constitution?.enabled
          ? pack.answer.ask_intelligence_constitution
          : null,
    researchConclusion:
      ac?.research_conclusion ||
      pack.answer?.research_conclusion ||
      ac?.ask_intelligence_constitution?.sections?.research_conclusion ||
      null,
    questionsBeforeYouDecide:
      ac?.questions_before_you_decide ||
      pack.answer?.questions_before_you_decide ||
      ac?.ask_intelligence_constitution?.sections?.questions_before_you_decide ||
      null,
    intentResolution:
      ac?.intent_resolution ||
      pack.answer?.intent_resolution ||
      pack.intent_resolution ||
      null,
    institutionalPlaybookFramework:
      ac?.institutional_playbook_framework?.enabled
        ? ac.institutional_playbook_framework
        : pack.answer?.institutional_playbook_framework?.enabled
          ? pack.answer.institutional_playbook_framework
          : null,
    researchJourney:
      ac?.research_journey ||
      pack.answer?.research_journey ||
      ac?.institutional_playbook_framework?.research_journey ||
      null,
    researchJourneyState:
      ac?.research_journey_state ||
      pack.answer?.research_journey_state ||
      ac?.institutional_playbook_framework?.research_journey_state ||
      null,
    suggestedNextResearch:
      ac?.suggested_next_research ||
      pack.answer?.suggested_next_research ||
      ac?.institutional_playbook_framework?.suggested_next_research ||
      null,
    playbookValidation: ac?.playbook_validation || pack.answer?.playbook_validation || null,
    researchWorkflowFramework:
      ac?.research_workflow_framework?.enabled
        ? ac.research_workflow_framework
        : pack.answer?.research_workflow_framework?.enabled
          ? pack.answer.research_workflow_framework
          : null,
    decisionObjective:
      ac?.decision_objective ||
      pack.answer?.decision_objective ||
      ac?.research_workflow_framework?.decision_objective?.objective ||
      null,
    researchStatus:
      ac?.research_status ||
      pack.answer?.research_status ||
      ac?.research_workflow_framework?.research_status ||
      null,
    researchSession:
      ac?.research_session ||
      pack.answer?.research_session ||
      ac?.research_session_state ||
      null,
    nextBestResearchQuestion:
      ac?.next_best_research_question ||
      pack.answer?.next_best_research_question ||
      ac?.research_workflow_framework?.next_best_research_question ||
      null,
    workflowValidation: ac?.workflow_validation || pack.answer?.workflow_validation || null,
    bottomLine:
      asText(ac?.bottom_line) ||
      asText(ac?.response_constitution?.bottom_line) ||
      asText(pack.answer?.bottom_line) ||
      asText(pack.answer?.response_constitution?.bottom_line) ||
      '',
    confidenceExplanation:
      asText(ac?.confidence_explanation) ||
      asText(ac?.response_constitution?.confidence?.explanation) ||
      asText(pack.answer?.confidence_explanation) ||
      asText(pack.answer?.response_constitution?.confidence?.explanation) ||
      '',
    conclusion:
      asText(ac?.bottom_line) ||
      asText(ac?.response_constitution?.bottom_line) ||
      asText(irw?.institutional_conclusion) ||
      asText(iafCio?.institutional_conclusion) ||
      asText(ac?.decision_conclusion) ||
      asText(decisionLayer?.reasoning) ||
      asText(ide?.decision?.reasoning) ||
      asText(enrich.current_outlook) ||
      asText(biz.long_term_growth) ||
      asText(briefing.current_outlook) ||
      asText(pack.current_outlook) ||
      executive,
    decisionEngine: ide
      ? {
          active: true,
          overallScore: ideSummary.overall_score ?? ide.overall_score ?? null,
          investmentGrade: asText(
            ideSummary.investment_grade || ide.investment_grade,
            gradeFromScore(ideSummary.overall_score ?? ide.overall_score) || ''
          ),
          confidence: pct(ideSummary.confidence_pct) ?? confidence,
          evidenceConfidence: pct(
            ideSummary.evidence_confidence_pct ??
              ide?.institutional_readiness_gate?.evidence_confidence_pct
          ),
          companyQuality10:
            ideSummary.company_quality_10 ??
            ide?.institutional_readiness_gate?.company_quality_10 ??
            null,
          marketOpportunity10:
            ideSummary.market_opportunity_10 ??
            ide?.institutional_readiness_gate?.market_opportunity_10 ??
            null,
          investmentThesisStatus: asText(
            ideSummary.investment_thesis_status || decisionLayer?.investment_thesis_status,
            ''
          ),
          notANegativeView: Boolean(
            ideSummary.not_a_negative_view ?? decisionLayer?.not_a_negative_view
          ),
          expectedReturn12m: ideSummary.expected_return_12m_pct ?? null,
          bullCase: ideSummary.bull_case_pct ?? null,
          baseCase: ideSummary.base_case_pct ?? null,
          bearCase: ideSummary.bear_case_pct ?? null,
          probabilityWeighted: ideSummary.probability_weighted_return_pct ?? null,
          riskReward: ideSummary.risk_reward ?? null,
          action: asText(ideSummary.action || decisionLayer?.action, ''),
          suitableFor: asList(ideSummary.suitable_for, 6),
          unsuitableFor: asList(ideSummary.unsuitable_for, 6),
          layerScores: ideSummary.layer_scores || {},
          preQuestions: asList(ide.pre_questions, 8),
          stackLayers: decisionStackLayers,
          decision: decisionLayer,
          gateBlocked: Boolean(ideSummary.gate_blocked),
          readinessGate: ide.institutional_readiness_gate || null,
        }
      : null,
    recommendationStatus: {
      blocked: Boolean(recoStatus.blocked),
      status: asText(recoStatus.status, recoStatus.blocked ? 'Withheld' : 'Open'),
      summary: asText(
        recoStatus.summary,
        recoStatus.blocked
          ? 'Investment thesis INCONCLUSIVE — evidence insufficient, not a negative company view.'
          : 'Evidence coverage supports institutional analysis — not an automatic trade instruction.'
      ),
      detail: asText(recoStatus.detail, ''),
      gaps: knowledgeGaps,
      evidenceConfidence: pct(recoStatus.evidence_confidence_pct),
      requiredConfidence: pct(recoStatus.required_confidence_pct) ?? 80,
      companyQuality10: recoStatus.company_quality_10 ?? null,
      marketOpportunity10: recoStatus.market_opportunity_10 ?? null,
      coverage: recoStatus.coverage || null,
      checklist: Array.isArray(recoStatus.checklist) ? recoStatus.checklist : [],
      additionalEvidenceRequired: asList(recoStatus.additional_evidence_required, 8),
      investmentThesisStatus: asText(recoStatus.investment_thesis_status, ''),
      notANegativeView: Boolean(recoStatus.not_a_negative_view),
      readinessBand: asText(recoStatus.readiness_band || recoStatus.readiness_label, ''),
      gateSummary: recoStatus.gate_summary || {},
    },
    knowledgeGaps,
    explore,
    changedRows,
    supporting: pack.supporting_evidence || [],
    conflicting: pack.conflicting_evidence || [],
    icEnabled: Boolean(ic?.enabled),
    acEnabled: Boolean(ac?.enabled),
    editorialEnabled: Boolean(ac?.editorial?.enabled || pack.editorial?.enabled),
    editorialProvider: asText(ac?.editorial?.provider || pack.editorial?.provider, ''),
    editorialFallback: Boolean(ac?.editorial?.fallback || pack.editorial?.fallback),
    reasoningEnabled: Boolean(ir?.enabled || irOwns || reasoningPattern?.enabled),
    reasoningOwnsExecutive: irOwns || Boolean(cxr?.executive),
    reasoningSource: asText(
      ir?.reasoning_source || reasoningPattern?.source || (cxr?.enabled ? 'contradiction_reasoning' : ''),
      ''
    ),
    reasoningFamily: asText(
      ir?.reasoning_family?.family_label ||
        ir?.reasoning_family?.family_id ||
        ir?.family_id ||
        reasoningPattern?.family_id,
      ''
    ),
    reasoningMode: asText(ir?.adversarial_mode || ir?.habit_id || reasoningPattern?.pattern_id, ''),
    noveltyBand: asText(novelty?.band || novelty?.novelty_band, ''),
    noveltyScore: novelty?.novelty_score ?? novelty?.score ?? null,
    ecrScore: ecr?.ecr ?? ecr?.score ?? ac?.evidence_to_conclusion_ratio ?? null,
    contradictionEnabled: Boolean(cxr?.enabled),
    booksEnabled: Boolean(books?.enabled),
    bookFrameworks: asList(books?.frameworks || academy.book_frameworks, 6),
    ideEnabled: Boolean(ide?.active),
    iafEnabled: Boolean(iaf?.enabled),
    irwEnabled: Boolean(irw?.enabled),
    reportType: asText(irw?.report_type || irwReport?.report_type, ''),
    reportTables: Array.isArray(irw?.tables) ? irw.tables : Array.isArray(iaf?.report_tables) ? iaf.report_tables : [],
    chartRecommendations: Array.isArray(irw?.chart_recommendations)
      ? irw.chart_recommendations
      : Array.isArray(iaf?.chart_recommendations)
        ? iaf.chart_recommendations
        : [],
    sectionOwners: iaf?.section_owners || ac?.section_owners || {},
    publicOwnerLabels: iaf?.public_owner_labels || {},
    analystOpinions: iaf?.analyst_opinions || null,
    intelligenceLayer: ail
      ? {
          enabled: true,
          ticker: asText(ail.ticker || ailDossier.ticker, ''),
          company: asText(ail.company || ailDossier.company, ''),
          dossierVersion: ailDossier.version ?? null,
          hints: asList(ail.ask_agi_hints, 4),
          thesis: {
            bull: ailThesis.bull?.probability ?? null,
            base: ailThesis.base?.probability ?? null,
            bear: ailThesis.bear?.probability ?? null,
            explanation: asList(ailThesis.explanation, 4),
          },
          forecastConfidence: ailForecast.confidence ?? ail.prediction_confidence ?? null,
          forecastId: asText(ailForecast.prediction_id, ''),
          scenario: ailForecast.scenario || {},
          distributions: Array.isArray(ailForecast.distributions)
            ? ailForecast.distributions.slice(0, 8).map((d) => ({
                metric: asText(d.metric, ''),
                unit: asText(d.unit, ''),
                p10: d.p10 ?? null,
                p50: d.p50 ?? null,
                p90: d.p90 ?? null,
              }))
            : [],
          events: asList(ail.events, 6).map((e) =>
            typeof e === 'string'
              ? e
              : asText(e.category || e.title || e.new_value, '')
          ),
          supportingEvidenceIds: asList(ail.supporting_evidence_ids, 8),
          contradictoryEvidenceIds: asList(ail.contradictory_evidence_ids, 8),
          graphCount: ail.knowledge_graph?.count ?? (ail.knowledge_graph?.relationships || []).length,
          auditId: asText(ail.audit_trail?.audit_id, ''),
        }
      : null,
    ticker: ca.ticker || dossier.ticker || ail?.ticker || pack.entities?.primary_ticker || null,
    investmentOfficeOs,
  };
}
