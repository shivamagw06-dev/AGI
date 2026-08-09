import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import InstitutionalChatWorkspace from '@/components/AskAgi/InstitutionalChatWorkspace';
import { postUiSearch, resetAskConversation } from '@/lib/uiApi';
import { universalAsk } from '@/lib/intelligenceApi';
import { pushSearch, saveAnswer, saveSearch } from '@/lib/searchHistory';
import { trackProductEvent } from '@/lib/productAnalytics';
import { ASK_PROMPTS } from './helpers';

/**
 * Ask AGI — product homepage experience inside the AGI shell.
 * Context-aware: ticker / portfolio from query params supply institutional scope.
 */
export default function AskAgiProductPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const question = (params.get('q') || '').trim();
  const ticker = (params.get('ticker') || '').trim().toUpperCase();
  const context = (params.get('context') || '').trim().toLowerCase();
  const portfolio = (params.get('portfolio') || '').trim();
  const [state, setState] = useState({ loading: false, pack: null, error: null, orchestrated: null });
  const [draft, setDraft] = useState('');
  const [savedFlash, setSavedFlash] = useState(false);

  const contextLabel = useMemo(() => {
    if (ticker) return `Company context: ${ticker}`;
    if (context === 'portfolio' || portfolio) return `Portfolio context: ${portfolio || 'desk'}`;
    return '';
  }, [ticker, context, portfolio]);

  const scopedQuestion = useMemo(() => {
    if (!question) return '';
    if (ticker && !question.toUpperCase().includes(ticker)) {
      return `${question} (company: ${ticker})`;
    }
    if ((context === 'portfolio' || portfolio) && !/portfolio|holding/i.test(question)) {
      return `${question} (portfolio context)`;
    }
    return question;
  }, [question, ticker, context, portfolio]);

  useEffect(() => {
    if (!question) {
      setState({ loading: false, pack: null, error: null, orchestrated: null });
      return;
    }
    let active = true;
    setState({ loading: true, pack: null, error: null, orchestrated: null });
    pushSearch(scopedQuestion);
    trackProductEvent('question_asked', {
      question: scopedQuestion,
      surface: 'agi_product',
      ticker: ticker || undefined,
      context: context || undefined,
    });
    const uagBody = {
      question: scopedQuestion,
      portfolio_id: portfolio || 'agi-core-equity',
      entities: ticker ? [ticker] : undefined,
    };
    Promise.all([
      postUiSearch(scopedQuestion).catch((error) => ({ __error: error })),
      universalAsk(uagBody).catch(() => null),
    ]).then(([packOrErr, uag]) => {
      if (!active) return;
      if (packOrErr?.__error) {
        setState({
          loading: false,
          pack: null,
          error: packOrErr.__error,
          orchestrated: uag && uag.ok !== false ? uag : null,
        });
        return;
      }
      setState({
        loading: false,
        pack: packOrErr,
        error: null,
        orchestrated: uag && uag.ok !== false ? uag : null,
      });
      trackProductEvent('search_success', { question: scopedQuestion, surface: 'agi_product' });
    });
    return () => {
      active = false;
    };
  }, [question, scopedQuestion, ticker, context, portfolio]);

  const buildAskHref = (q) => {
    const next = String(q || '').trim();
    const qs = new URLSearchParams();
    qs.set('q', next);
    if (ticker) qs.set('ticker', ticker);
    if (context) qs.set('context', context);
    if (portfolio) qs.set('portfolio', portfolio);
    return `/agi/ask?${qs.toString()}`;
  };

  const onAsk = (q) => {
    const next = String(q || '').trim();
    if (!next) return;
    trackProductEvent('follow_up_question', { question: next, surface: 'agi_product' });
    navigate(buildAskHref(next));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onSaveAnswer = () => {
    if (!state.pack) {
      if (question) saveSearch(question);
      return;
    }
    saveAnswer({
      question: state.pack.question || question,
      stance: state.pack.house_view_card?.stance || state.pack.answer?.house_view_label || '',
      summary: state.pack.executive_summary || '',
      href: buildAskHref(state.pack.question || question),
    });
    saveSearch(state.pack.question || question);
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1600);
  };

  const contextualPrompts = ticker
    ? [
        'What changed?',
        'Why is confidence moderate?',
        'Show supporting evidence.',
        'Show contradictory evidence.',
        'What would change your conclusion?',
        'Summarise management execution.',
        'Explain margins.',
      ]
    : context === 'portfolio' || portfolio
      ? ['Which holding concerns you most?', 'Where is research coverage weakest?', 'Summarise portfolio quality.']
      : ASK_PROMPTS;

  if (!question) {
    return (
      <div className="agi-ask-hero">
        <h1 className="agi-greeting">Ask AGI</h1>
        <p className="agi-lede">
          Bloomberg command meets institutional chat — confidence, evidence, timeline, and drill-down in every
          answer.
        </p>
        {contextLabel ? (
          <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
            {contextLabel}
            {ticker ? (
              <>
                {' · '}
                <Link to={`/agi/companies/${ticker}`}>Open workspace</Link>
              </>
            ) : null}
          </p>
        ) : null}
        <form
          className="agi-ask-input-wrap"
          onSubmit={(e) => {
            e.preventDefault();
            onAsk(draft);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              ticker
                ? `Ask about ${ticker} — no ticker needed`
                : context === 'portfolio'
                  ? 'Ask about this portfolio…'
                  : 'Ask about a company, market, or idea…'
            }
            aria-label="Ask AGI"
            autoFocus
          />
          <button type="submit" className="agi-btn agi-btn-primary">
            Ask
          </button>
        </form>
        <div className="agi-prompts">
          {contextualPrompts.map((p) => (
            <button key={p} type="button" onClick={() => onAsk(p)}>
              {p}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const orch = state.orchestrated?.response || null;

  return (
    <div style={{ margin: '0 -0.5rem' }}>
      {contextLabel ? (
        <p className="agi-list-meta" style={{ margin: '0 0 0.5rem 0.25rem' }}>
          {contextLabel}
        </p>
      ) : null}

      {orch ? (
        <section className="agi-section" style={{ margin: '0 0.25rem 1rem' }}>
          <div className="agi-section-head">
            <h2>Orchestrated answer</h2>
            <span className="agi-list-meta">
              UAG-01 · {orch.intent} · conf {orch.confidence}
            </span>
          </div>
          <p style={{ marginBottom: '0.75rem' }}>{orch.direct_answer}</p>
          <p className="agi-list-meta" style={{ marginBottom: '0.5rem' }}>
            {(orch.evidence_lineage || []).join(' → ')}
          </p>
          <ul className="agi-list">
            {(orch.why || []).slice(0, 5).map((line) => (
              <li key={line}>
                <div className="agi-list-meta">{line}</div>
              </li>
            ))}
          </ul>
          <p className="agi-list-meta" style={{ marginTop: '0.5rem' }}>
            Objects: {(orch.objects_consulted || []).join(', ') || '—'} · does not generate
            recommendations
          </p>
          {state.orchestrated?.workspace?.href ? (
            <p style={{ marginTop: '0.85rem' }}>
              <Link className="agi-chip ok" to={state.orchestrated.workspace.href}>
                Open Research Workspace
                {state.orchestrated.workspace.focus
                  ? ` · ${state.orchestrated.workspace.focus}`
                  : ''}
              </Link>
              <span className="agi-list-meta" style={{ marginLeft: '0.5rem' }}>
                {(state.orchestrated.workspace.lineage_hint || []).join(' → ') ||
                  'Decision → Timeline → Evidence'}
              </span>
            </p>
          ) : ticker ? (
            <p style={{ marginTop: '0.85rem' }}>
              <Link className="agi-chip ok" to={`/agi/companies/${ticker}?tab=timeline&rw=1`}>
                Open Research Workspace · timeline
              </Link>
            </p>
          ) : null}
        </section>
      ) : null}

      <InstitutionalChatWorkspace
        pack={state.pack}
        loading={Boolean(question && state.loading)}
        error={state.error}
        question={question}
        onAsk={onAsk}
        onSave={onSaveAnswer}
        onNewChat={resetAskConversation}
        savedFlash={savedFlash}
        embedded
        basePath="/agi/ask"
      />
    </div>
  );
}
