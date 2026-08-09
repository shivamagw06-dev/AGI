/**
 * Project mapSearchPack → chat-first AGIB answer model.
 * Stack: Response Constitution → Ask Intelligence Constitution → Playbook Framework → Workflow Framework.
 */

import { mapSearchPack } from './mapSearchPack';
import {
  enrichJourneyMap,
  getResearchJourneyState,
  mergeResearchJourneyState,
} from '@/lib/researchJourney';
import { getResearchSession, mergeResearchSession } from '@/lib/researchSession';
import { answerFormatFor } from '@/components/AskAgi/answerFormat';
import {
  calibrateDisplayedConfidence,
  dedupeAnswerText,
  normalizeProvenance,
  scenarioCopy,
} from '@/components/AskAgi/answerQuality';

function asList(v, n = 8) {
  if (!Array.isArray(v)) return [];
  return v
    .map((x) => (typeof x === 'string' ? x : x?.text || x?.title || x?.label || x?.risk || ''))
    .filter(Boolean)
    .slice(0, n);
}

function impactFromLabel(label = '', text = '') {
  const blob = `${label} ${text}`.toLowerCase();
  if (/risk|bear|weak|pressure|concern|negative|impair|cautious/.test(blob)) return 'Watch';
  if (/neutral|mixed|watch|monitor|balanced/.test(blob)) return 'Balanced';
  if (/positive|bull|strong|growth|quality|catalyst|expand|constructive/.test(blob)) return 'Supportive';
  return 'Balanced';
}

function institutionalViewLabel(stance = '', recommendation = '') {
  const s = `${stance} ${recommendation}`.toLowerCase();
  if (/buy|overweight|constructive|bullish|accumulate/.test(s)) return 'Constructive';
  if (/sell|underweight|cautious|bearish|avoid|reduce/.test(s)) return 'Cautious';
  if (/monitor|hold|neutral|selective|watch|withheld|insufficient/.test(s)) return 'Monitoring';
  return stance || 'Monitoring';
}

function scoreTone(impact) {
  if (impact === 'Supportive' || impact === 'Positive') return 'pos';
  if (impact === 'Watch' || impact === 'Medium' || impact === 'Negative') return 'neg';
  return 'neu';
}

function explainConfidenceFallback(confidence, view) {
  const pct = Number(confidence);
  if (!Number.isFinite(pct)) {
    return 'AGIB confidence is still forming because coverage and valuation evidence are incomplete for a firmer view.';
  }
  if (pct >= 80) {
    return `AGIB has high confidence (${pct}%) because the business picture is relatively clear and the main risks are identifiable.`;
  }
  if (pct >= 60) {
    return `AGIB has moderate confidence (${pct}%) because the business fundamentals are readable, but future earnings and valuation still leave room for surprise.`;
  }
  if (pct >= 40) {
    return `AGIB has limited confidence (${pct}%) because some important evidence is still thin or conflicting — current view: ${view}.`;
  }
  return `AGIB has low confidence (${pct}%) because validated coverage is insufficient for a firm institutional view.`;
}

/**
 * @param {object|null} pack raw /api/ui/search pack
 */
export function mapChatAnswer(pack) {
  const vm = mapSearchPack(pack || {});
  if (!vm) return null;

  // The presentation layer must never turn an empty evidence pack into a
  // confident-looking research answer.  Keep the answer visibly incomplete
  // until the engine has supplied at least one attributable evidence item.
  const evidenceRows = [
    ...(Array.isArray(vm.supporting) ? vm.supporting : []),
    ...(Array.isArray(pack?.supporting_evidence) ? pack.supporting_evidence : []),
    ...(Array.isArray(pack?.evidence_used) ? pack.evidence_used : []),
    ...(Array.isArray(pack?.evidence) ? pack.evidence : []),
  ];
  const hasVerifiedEvidence = evidenceRows.some((item) => {
    if (typeof item === 'string') return Boolean(item.trim());
    return Boolean(item?.source || item?.title || item?.url || item?.id);
  });
  const conversationExecution = pack?.conversation_context?.research_execution
    || pack?.ask_orchestration?.conversation?.research_execution;
  const conversationalOnly = pack?.intent === 'conversation'
    || conversationExecution === 'SKIP'
    || conversationExecution === 'REUSE_PREVIOUS';
  const evidenceUnavailable =
    !conversationalOnly && (!hasVerifiedEvidence ||
    Boolean(
      pack?.degraded ||
        pack?.mode === 'node_desk_fallback' ||
        pack?.ask_orchestration?.fallback ||
        pack?.ask_orchestration?.fallback_used
    ));
  const answerFormat = answerFormatFor(vm.question || pack?.question, vm.intent || pack?.intent);
  const unavailableText =
    'Evidence unavailable: AGI could not retrieve verified company research for this answer. Retry when the research desk is available.';
  const evidenceBacked = (value, fallback) =>
    evidenceUnavailable ? unavailableText : (value || fallback);
  const qualityGates = pack?.answer?.quality_gates || {};
  const financialsUnsupported = qualityGates.financials_supported === false;
  const valuationUnsupported = qualityGates.valuation_supported === false;
  const conversation = pack?.conversation_context || pack?.ask_orchestration?.conversation || {};
  const provenance = normalizeProvenance([
    ...(Array.isArray(pack?.evidence_used) ? pack.evidence_used : []),
    ...(Array.isArray(pack?.supporting_research) ? pack.supporting_research : []),
    ...(Array.isArray(pack?.supporting_evidence) ? pack.supporting_evidence : []),
  ]);

  const rc = vm.responseConstitution || pack?.answer_construction?.response_constitution || null;
  const aic =
    vm.askIntelligenceConstitution ||
    pack?.answer_construction?.ask_intelligence_constitution ||
    pack?.answer?.ask_intelligence_constitution ||
    null;
  const aicSections = aic?.sections || {};
  const investmentContext = aicSections.investment_context || aic?.intent || null;
  const ipf =
    vm.institutionalPlaybookFramework ||
    pack?.answer_construction?.institutional_playbook_framework ||
    pack?.answer?.institutional_playbook_framework ||
    null;
  const playbook = ipf?.playbook || null;
  const ticker = vm.ticker;
  const playbookKey = playbook?.playbook_key || 'investment_assessment';

  let journeyState = vm.researchJourneyState || ipf?.research_journey_state || null;
  if (journeyState) {
    journeyState = mergeResearchJourneyState(ticker, playbookKey, journeyState);
  } else {
    journeyState = getResearchJourneyState(ticker, playbookKey);
  }
  const journeyRaw = vm.researchJourney || ipf?.research_journey || null;
  const researchJourney = enrichJourneyMap(journeyRaw, journeyState) || journeyRaw;

  const rwf =
    vm.researchWorkflowFramework ||
    pack?.answer_construction?.research_workflow_framework ||
    pack?.answer?.research_workflow_framework ||
    null;
  const workflowKey = rwf?.workflow?.workflow_key || 'investment_opportunity_evaluation';
  let researchSession = vm.researchSession || rwf?.research_session || null;
  if (researchSession) {
    researchSession = mergeResearchSession(ticker, workflowKey, researchSession);
  } else {
    researchSession = getResearchSession(ticker, workflowKey);
  }
  const researchStatus = vm.researchStatus || rwf?.research_status || null;
  const decisionObjective = vm.decisionObjective || rwf?.decision_objective?.objective || null;
  const nextBestResearchQuestion =
    vm.nextBestResearchQuestion || rwf?.next_best_research_question || null;

  const view = institutionalViewLabel(
    vm.stance || vm.institutionalView?.stance || '',
    vm.institutionalAnswer?.recommendation || vm.decisionEngine?.action || ''
  );

  const thesisSrc = rc?.investment_thesis || {};
  const thesisCards = [
    {
      id: 'business',
      title: 'Business',
      body: evidenceBacked(
        thesisSrc.business ||
        asList([vm.businessQuality, vm.businessModel, vm.whyCards?.find((c) => c.key === 'demand')?.text])[0] ||
          vm.why?.[0],
        'What the company does, why customers choose it, and whether that advantage can last.'
      ),
      impact: impactFromLabel('business', thesisSrc.business || vm.businessQuality || ''),
    },
    {
      id: 'growth',
      title: 'Growth',
      body: evidenceBacked(
        thesisSrc.growth ||
        asList([vm.whyCards?.find((c) => c.key === 'demand')?.text, vm.sectorNarrative, vm.macroNarrative])[0] ||
          null,
        'Where future growth could come from — and what could slow it down.'
      ),
      impact: impactFromLabel('growth', thesisSrc.growth || vm.sectorNarrative || ''),
    },
    {
      id: 'financial',
      title: 'Financial Quality',
      body: evidenceBacked(
        thesisSrc.financial_quality ||
        asList([vm.financialNarrative, vm.whyCards?.find((c) => c.key === 'financial')?.text])[0] ||
          null,
        'Whether the company is making real cash and whether its balance sheet can handle stress.'
      ),
      impact: financialsUnsupported
        ? 'Unavailable'
        : impactFromLabel('financial', thesisSrc.financial_quality || vm.financialNarrative || ''),
    },
    {
      id: 'valuation',
      title: 'Valuation',
      body: evidenceBacked(
        thesisSrc.valuation ||
        asList([vm.valuationNarrative, vm.whyCards?.find((c) => c.key === 'valuation')?.text])[0] ||
          null,
        'Whether the share price already assumes strong future results — and compared with what.'
      ),
      impact: valuationUnsupported
        ? 'Unavailable'
        : impactFromLabel('valuation', thesisSrc.valuation || vm.valuationNarrative || 'neutral'),
    },
    {
      id: 'risk',
      title: 'Risks',
      body: evidenceBacked(
        thesisSrc.risks ||
        asList([vm.risks?.[0]?.risk, vm.whyCards?.find((c) => c.key === 'risk')?.text])[0] ||
          null,
        'What could make this investment go wrong — and why those risks matter.'
      ),
      impact: 'Watch',
    },
    {
      id: 'catalysts',
      title: 'Catalysts',
      body: evidenceBacked(
        thesisSrc.catalysts ||
        asList(vm.catalysts)[0] ||
          asList(vm.bull)[0],
        'Upcoming events that could raise or reduce AGIB’s conviction — explained in plain English.'
      ),
      impact: 'Supportive',
    },
  ].map((c) =>
    evidenceUnavailable
      ? { ...c, impact: 'Unavailable', tone: 'neu' }
      : { ...c, tone: scoreTone(c.impact) }
  );

  const moreBullish = evidenceUnavailable
    ? []
    : asList(
      [
        ...(rc?.bull_vs_bear?.bull_case || []),
        ...(vm.bull || []),
        ...(vm.catalysts || []),
      ],
      6
    );

  const moreBearish = evidenceUnavailable
    ? []
    : asList(
      [
        ...(rc?.bull_vs_bear?.bear_case || []),
        ...(vm.bear || []),
        ...(vm.risks || []).map((r) => (typeof r === 'string' ? r : r.risk)),
      ],
      6
    );

  const intelligenceChips = [
    { id: 'company', label: 'Company Intelligence', section: 'business' },
    { id: 'research', label: 'Research Intelligence', section: 'thesis' },
    { id: 'financial', label: 'Financial Intelligence', section: 'financial' },
    { id: 'sector', label: 'Sector Intelligence', section: 'sector' },
    { id: 'market', label: 'Market Intelligence', section: 'market' },
    { id: 'macro', label: 'Macro Intelligence', section: 'macro' },
    { id: 'historical', label: 'Historical Intelligence', section: 'changed' },
    { id: 'forecast', label: 'Forecast Intelligence', section: 'scenarios' },
  ];

  const scores = evidenceUnavailable ? {
    business: null,
    financial: null,
    growth: null,
    valuation: null,
    risk: null,
    conviction: null,
  } : {
    business: vm.kpis?.find((k) => /business|quality/i.test(k.label))?.value || null,
    financial: vm.kpis?.find((k) => /financial|cash|roe/i.test(k.label))?.value || null,
    growth: vm.kpis?.find((k) => /growth|momentum/i.test(k.label))?.value || null,
    valuation: vm.kpis?.find((k) => /valuation|multiple/i.test(k.label))?.value || null,
    risk: vm.risks?.[0]?.severity || vm.risks?.[0]?.impact || 'Watch',
    conviction: vm.conviction || view,
  };

  const directAnswer = dedupeAnswerText(evidenceUnavailable
    ? unavailableText
    : (
      aicSections.executive_summary ||
      rc?.direct_answer ||
      vm.institutionalAnswer?.text ||
      vm.executive ||
      vm.conclusion ||
      unavailableText
    ));

  const researchConclusion =
    vm.researchConclusion ||
    pack?.answer?.research_conclusion ||
    aicSections.research_conclusion ||
    null;

  const questionsBeforeYouDecide = asList(
    vm.questionsBeforeYouDecide ||
      pack?.answer?.questions_before_you_decide ||
      aicSections.questions_before_you_decide ||
      researchConclusion?.key_questions_remaining,
    8
  );

  const institutionalThinkingFramework = aic?.institutional_thinking_framework || null;

  const followUps = asList(
    [
      nextBestResearchQuestion?.question,
      ...(vm.suggestedNextResearch || []),
      ...questionsBeforeYouDecide,
      ...(rc?.suggested_follow_ups || []),
      ...(vm.explore || []),
      researchStatus?.next_activity ? `Continue: ${researchStatus.next_activity}` : null,
      researchJourney?.next_step ? `Continue: ${researchJourney.next_step}` : null,
      `Why ${view}?`,
      vm.ticker ? `Compare ${vm.ticker} with peers` : 'Show peer comparison',
      'Explain the valuation in plain English',
      'Show financials',
      'Latest earnings',
      'What changed?',
      'Bull vs Bear case',
      'Show risks',
    ],
    10
  );

  const recentResearch = evidenceUnavailable
    ? []
    : asList(
      [
        ...(vm.supporting || []).map((s) => s.title || s.source || s),
        'Internal AGIB',
        'Exchange Filing',
      ],
      4
    );

  const whyAgib = evidenceUnavailable
    ? [unavailableText]
    : asList(rc?.why_agib_thinks_this?.length ? rc.why_agib_thinks_this : vm.why, 5);

  const bottomLine = dedupeAnswerText(evidenceUnavailable
    ? unavailableText
    : (rc?.bottom_line || vm.bottomLine || vm.conclusion || directAnswer));

  const confidence = evidenceUnavailable
    ? null
    : calibrateDisplayedConfidence(vm.confidence ?? rc?.confidence?.score ?? null, qualityGates);
  const confidenceExplanation =
    evidenceUnavailable
      ? unavailableText
      : (rc?.confidence?.explanation ||
        vm.confidenceExplanation ||
        explainConfidenceFallback(confidence, view));

  return {
    question: vm.question,
    ticker: vm.ticker,
    company: vm.intelligenceLayer?.company || vm.ticker || rc?.company || null,
    intent: vm.intent,
    category: vm.category,
    directAnswer,
    whyAgib,
    bottomLine,
    horizon: vm.horizon || vm.institutionalAnswer?.horizon || '12–24 Months',
    confidence,
    confidenceExplanation,
    institutionalView: evidenceUnavailable ? 'Evidence unavailable' : view,
    stanceTone: evidenceUnavailable ? 'neu' : (vm.stanceTone || (view === 'Constructive' ? 'pos' : view === 'Cautious' ? 'neg' : 'neu')),
    thesisCards,
    moreBullish,
    moreBearish,
    intelligenceChips,
    scores,
    followUps,
    recentResearch,
    freshness: vm.freshness,
    lastUpdated: vm.lastUpdated,
    evidenceUnavailable,
    conversationalOnly,
    answerFormat,
    presentation: {
      depth: conversation.answer_depth || 'standard',
      style: conversation.output_style || 'standard',
      audience: conversation.audience || 'analyst',
    },
    clarification: conversation.clarification || null,
    provenance,
    scenarioCopy: scenarioCopy(answerFormat.key),
    dataQuality: {
      financialsSupported: !financialsUnsupported,
      valuationSupported: !valuationUnsupported,
      conglomerateFrameworkValidated: qualityGates.conglomerate_framework_validated !== false,
      incomplete: financialsUnsupported || valuationUnsupported || qualityGates.conglomerate_framework_validated === false,
    },
    constitutionVersion: aic?.version || ipf?.version || rc?.version || '1.0',
    investmentContext,
    researchConclusion,
    questionsBeforeYouDecide,
    institutionalThinkingFramework,
    methodologyIntent: investmentContext?.primary_intent || aic?.intent?.primary_intent || null,
    realIntent: investmentContext?.real_intent || aic?.intent?.real_intent || decisionObjective || null,
    playbook,
    researchJourney,
    researchJourneyState: journeyState,
    researchStatus,
    researchSession,
    decisionObjective,
    nextBestResearchQuestion,
    workflow: rwf?.workflow || null,
    suggestedNextResearch: asList(vm.suggestedNextResearch || [], 6),
    deep: {
      thesis: vm.thesis,
      why: whyAgib,
      financialNarrative: vm.financialNarrative,
      valuationNarrative: vm.valuationNarrative,
      sectorNarrative: vm.sectorNarrative,
      macroNarrative: vm.macroNarrative,
      marketNarrative: vm.marketNarrative,
      bull: moreBullish,
      base: vm.base,
      bear: moreBearish,
      risks: vm.risks,
      catalysts: vm.catalysts,
      conclusion: bottomLine,
      whatChanged: vm.whatChanged,
      recommendationStatus: vm.recommendationStatus,
      readinessGate: vm.decisionEngine?.readinessGate || null,
      companyQuality10: vm.decisionEngine?.companyQuality10 ?? vm.recommendationStatus?.companyQuality10,
      marketOpportunity10:
        vm.decisionEngine?.marketOpportunity10 ?? vm.recommendationStatus?.marketOpportunity10,
      evidenceConfidence:
        vm.decisionEngine?.evidenceConfidence ?? vm.recommendationStatus?.evidenceConfidence,
      investmentThesisStatus:
        vm.decisionEngine?.investmentThesisStatus ||
        vm.recommendationStatus?.investmentThesisStatus ||
        '',
      askSlim: pack?.degradation?.ask_slim,
      degraded: Boolean(pack?.degraded || pack?.mode === 'node_desk_fallback'),
    },
  };
}
