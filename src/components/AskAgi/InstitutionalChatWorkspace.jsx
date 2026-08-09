import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell,
  Bookmark,
  Building2,
  CandlestickChart,
  Globe2,
  Home,
  Layers3,
  LineChart,
  MessageSquarePlus,
  Newspaper,
  Search,
  Settings,
  Sparkles,
  User,
  Briefcase,
  Eye,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';
import { mapChatAnswer } from '@/components/AskAgi/adapters/mapChatAnswer';
import { getRecentSearches } from '@/lib/searchHistory';
import { submitLaunchFeedback } from '@/lib/intelligenceApi';
import '@/components/AskAgi/institutionalChat.css';

const NAV = [
  { label: 'Home', path: '/', icon: Home },
  { label: 'Research', path: '/sections/research-notes', icon: Newspaper },
  { label: 'Companies', path: '/company-updates', icon: Building2 },
  { label: 'Markets', path: '/market-intelligence', icon: CandlestickChart },
  { label: 'Sectors', path: '/sectors/banks', icon: Layers3 },
  { label: 'Macro', path: '/macro-intelligence', icon: Globe2 },
  { label: 'IPO', path: '/ipo-intelligence', icon: LineChart },
  { label: 'Portfolio', path: '/portfolio', icon: Briefcase },
  { label: 'Watchlist', path: '/workspace', icon: Eye },
  { label: 'Intelligence Hub', path: '/admin/mission-control', icon: Sparkles },
  { label: 'Saved Research', path: '/workspace', icon: Bookmark },
  { label: 'Settings', path: '/account/security', icon: Settings },
];

const STARTERS = [
  'Should I buy Eternal?',
  'RBI outlook',
  'Compare HDFC vs ICICI',
  'Market outlook tomorrow',
];

function viewClass(tone) {
  if (tone === 'pos') return 'ac-view-pos';
  if (tone === 'neg') return 'ac-view-neg';
  return 'ac-view-neu';
}

function deepText(answer, chipId) {
  const d = answer?.deep || {};
  switch (chipId) {
    case 'company':
      return d.thesis || answer?.thesisCards?.find((c) => c.id === 'business')?.body;
    case 'research':
      return [d.thesis, ...(d.why || [])].filter(Boolean).join('\n\n');
    case 'financial':
      return d.financialNarrative;
    case 'sector':
      return d.sectorNarrative;
    case 'market':
      return d.marketNarrative;
    case 'macro':
      return d.macroNarrative;
    case 'historical':
      return (d.whatChanged || []).join(' · ') || 'Historical context refreshes with the research desk.';
    case 'forecast':
      return ['Bull: ' + (d.bull || [])[0], 'Base: ' + (d.base || [])[0], 'Bear: ' + (d.bear || [])[0]]
        .filter((x) => !x.endsWith('undefined'))
        .join('\n');
    default:
      return '';
  }
}

function ResearchStatus({ status, workflow, objective }) {
  if (!status?.items?.length) return null;
  return (
    <section className="ac-block ac-journey">
      <h2>{status.display || 'Research Status'}</h2>
      {objective && (
        <p className="ac-intent-note" style={{ fontSize: '0.82rem', color: '#5b6570', marginTop: 0 }}>
          Objective: {objective}
          {workflow?.name ? ` · Workflow: ${workflow.name}` : ''}
        </p>
      )}
      <ul className="ac-journey-steps">
        {status.items.map((item) => (
          <li
            key={item.label}
            className={
              item.status === 'complete' ? 'done' : item.status === 'needs_review' ? 'review' : item.current ? 'current' : ''
            }
          >
            <span>{item.symbol || (item.status === 'complete' ? '✓' : item.status === 'needs_review' ? '⚠' : '□')}</span>{' '}
            {item.note || item.label}
          </li>
        ))}
      </ul>
      {status.needs_further_investigation && (
        <p className="ac-confidence-why" style={{ marginTop: '0.55rem' }}>
          Needs Further Investigation — additional evidence required before research can firm up.
        </p>
      )}
    </section>
  );
}

function NextBestResearch({ nbrq, onAsk }) {
  if (!nbrq?.question) return null;
  return (
    <section className="ac-block ac-nbrq">
      <h2>Next Best Research Question</h2>
      <button type="button" className="ac-nbrq-btn" onClick={() => onAsk(nbrq.question)}>
        {nbrq.question}
      </button>
      {nbrq.reason && <p className="ac-confidence-why">{nbrq.reason}</p>}
    </section>
  );
}

function ResearchProgressFallback({ journey, playbook }) {
  if (!journey?.steps?.length) return null;
  return (
    <section className="ac-block ac-journey">
      <h2>Research Progress</h2>
      {playbook?.name && (
        <p className="ac-intent-note" style={{ fontSize: '0.82rem', color: '#5b6570', marginTop: 0 }}>
          Playbook: {playbook.name}
        </p>
      )}
      <ul className="ac-journey-steps">
        {journey.steps.map((step) => (
          <li key={step.label} className={step.completed ? 'done' : step.current ? 'current' : ''}>
            <span>{step.completed ? '✓' : '□'}</span> {step.label}
          </li>
        ))}
      </ul>
    </section>
  );
}

function AnswerTurn({ answer, onAsk }) {
  const [openChip, setOpenChip] = useState(null);
  const [feedback, setFeedback] = useState({ reaction: '', status: 'idle' });
  if (!answer) return null;
  const presentation = answer.presentation || {};
  const isBrief = presentation.depth === 'brief';
  const sourcesOnly = presentation.style === 'sources';
  const tableMode = presentation.style === 'table';
  const feedbackTags = [
    ['wrong_entity', 'Wrong company'],
    ['stale_data', 'Stale data'],
    ['missing_evidence', 'Missing evidence'],
    ['unclear_reasoning', 'Unclear reasoning'],
    ['too_long', 'Too long'],
    ['forecast_issue', 'Forecast issue'],
  ];
  const sendFeedback = async (reaction, tags = []) => {
    if (feedback.status === 'sending') return;
    setFeedback({ reaction, status: 'sending' });
    try {
      // Privacy-minimal V1: never transmit the question, answer, entity, or conversation ID.
      await submitLaunchFeedback({ screen: 'ask_agi', reaction, tags });
      setFeedback({ reaction, status: 'sent' });
    } catch {
      setFeedback({ reaction, status: 'error' });
    }
  };

  if (answer.clarification?.required) {
    return (
      <div className="ac-msg ac-msg-agi">
        <div className="ac-label">AGI · Clarification</div>
        <section className="ac-block ac-clarification">
          <p className="ac-kicker">One detail needed</p>
          <h2>{answer.clarification.question}</h2>
          {(answer.clarification.options || []).length > 0 && (
            <div className="ac-clarification-options">
              {answer.clarification.options.map((option) => (
                <button key={option.label} type="button" onClick={() => onAsk(option.prompt)}>
                  {option.label}
                </button>
              ))}
            </div>
          )}
          <p className="ac-confidence-why">
            AGI has not run the research pipeline yet, so no company, horizon, or comparison has been guessed.
          </p>
        </section>
      </div>
    );
  }

  if (sourcesOnly) {
    return (
      <div className="ac-msg ac-msg-agi">
        <div className="ac-label">AGI · Sources</div>
        <section className="ac-block ac-source-only">
          <h2>Evidence and provenance</h2>
          {(answer.provenance || []).length ? (
            <ol className="ac-source-list">
              {answer.provenance.map((item, index) => (
                <li key={`${item.title}-${index}`}>
                  {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : <strong>{item.title}</strong>}
                  <span>{item.source}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="ac-confidence-why">No attributable source records were returned for this turn.</p>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="ac-msg ac-msg-agi">
      <div className="ac-label">AGI</div>

      {!isBrief && <ResearchStatus
        status={answer.researchStatus}
        workflow={answer.workflow}
        objective={answer.decisionObjective}
      />}
      {!isBrief && !answer.researchStatus?.items?.length && (
        <ResearchProgressFallback journey={answer.researchJourney} playbook={answer.playbook} />
      )}

      {!isBrief && <NextBestResearch nbrq={answer.nextBestResearchQuestion} onAsk={onAsk} />}

      {/* 1. Direct Answer */}
      <div className="ac-direct">
        <p className="ac-kicker">Direct Answer</p>
        {answer.realIntent && (
          <p className="ac-intent-note" style={{ fontSize: '0.82rem', color: '#5b6570', marginBottom: '0.55rem' }}>
            Research focus: {answer.realIntent}
          </p>
        )}
        <p className="ac-direct-text">{answer.directAnswer}</p>
        <div className="ac-meta-row">
          <div>
            <span>Investment Horizon</span>
            <strong>{answer.horizon}</strong>
          </div>
          <div>
            <span>Confidence</span>
            <strong>{answer.confidence == null ? '—' : `${answer.confidence}%`}</strong>
          </div>
          <div>
            <span>Institutional View</span>
            <strong className={viewClass(answer.stanceTone)}>{answer.institutionalView}</strong>
          </div>
        </div>
        {answer.confidenceExplanation && (
          <p className="ac-confidence-why">{answer.confidenceExplanation}</p>
        )}
        {answer.deep?.degraded && (
          <div className="ac-degraded">
            Research desk is warming — this answer uses live institutional context while the full engine recovers.
          </div>
        )}
      </div>

      {tableMode && answer.thesisCards?.length > 0 && (
        <section className="ac-block">
          <h2>Research summary table</h2>
          <div className="ac-answer-table-wrap">
            <table className="ac-answer-table">
              <thead><tr><th>Dimension</th><th>Assessment</th><th>Evidence</th></tr></thead>
              <tbody>
                {answer.thesisCards.map((card) => (
                  <tr key={card.id}><td>{card.title}</td><td>{card.impact}</td><td>{card.body}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 2. Evidence / rationale */}
      {!tableMode && answer.whyAgib?.length > 0 && (
        <section className="ac-block">
          <h2>{answer.answerFormat?.evidenceTitle || 'Why AGI thinks this'}</h2>
          <ul className="ac-why-list">
            {answer.whyAgib.slice(0, isBrief ? 3 : undefined).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* 3. Company / financial thesis — not meaningful for factual comparisons. */}
      {!isBrief && !tableMode && answer.answerFormat?.thesis !== false && <section className="ac-block">
        <h2>{answer.answerFormat?.key === 'financials' ? 'Financial performance' : answer.answerFormat?.key === 'valuation' ? 'Valuation framework' : 'Investment Thesis'}</h2>
        <div className="ac-thesis">
          {answer.thesisCards.map((card) => (
            <details key={card.id} className="ac-thesis-card">
              <summary>
                <span>{card.title}</span>
                <span className={`ac-impact ${card.tone}`}>{card.impact}</span>
              </summary>
              <p>{card.body}</p>
            </details>
          ))}
        </div>
      </section>}

      {/* 4. Bull vs Bear Case */}
      {!isBrief && answer.answerFormat?.scenarios !== false && answer.confidence != null && !answer.evidenceUnavailable && (answer.moreBullish?.length || answer.moreBearish?.length) ? (
        <section className="ac-block">
          <h2>{answer.answerFormat?.key === 'catalysts' ? 'Upside and downside catalysts' : 'Bull vs Bear Case'}</h2>
          <div className="ac-change">
            <div className="ac-change-col bull">
              <h3>Bull Case</h3>
              <p className="ac-case-lead">Why someone would buy</p>
              <ul>
                {answer.moreBullish.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="ac-change-col bear">
              <h3>Bear Case</h3>
              <p className="ac-case-lead">Why someone would avoid it</p>
              <ul>
                {answer.moreBearish.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      {/* 5. Research Conclusion */}
      {!isBrief && answer.researchConclusion && (
        <section className="ac-block ac-research-conclusion">
          <h2>Research Conclusion</h2>
          <p>{answer.researchConclusion.summary || answer.bottomLine}</p>
          {answer.researchConclusion.key_uncertainties?.length > 0 && (
            <>
              <h3 style={{ fontSize: '0.88rem', marginTop: '0.75rem' }}>Key Uncertainties</h3>
              <ul className="ac-why-list">
                {answer.researchConclusion.key_uncertainties.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          )}
          <p className="ac-confidence-why" style={{ marginTop: '0.65rem' }}>
            The final investment decision remains yours — AGI provides institutional research context, not instructions.
          </p>
        </section>
      )}

      {/* 6. Questions Before You Decide */}
      {!isBrief && answer.questionsBeforeYouDecide?.length > 0 && (
        <section className="ac-block">
          <h2>Questions Before You Decide</h2>
          <ul className="ac-why-list">
            {answer.questionsBeforeYouDecide.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {/* 7. Bottom Line */}
      {answer.bottomLine && (
        <section className="ac-block ac-bottom-line">
          <h2>{answer.answerFormat?.bottomLine || 'Bottom Line'}</h2>
          <p>{answer.bottomLine}</p>
        </section>
      )}

      {/* 8. Supporting Intelligence */}
      <section className="ac-block">
        <h2>Supporting Intelligence</h2>
        <div className="ac-chips">
          {answer.intelligenceChips.map((chip) => (
            <button
              key={chip.id}
              type="button"
              className={openChip === chip.id ? 'active' : ''}
              onClick={() => setOpenChip((prev) => (prev === chip.id ? null : chip.id))}
            >
              {chip.label}
            </button>
          ))}
        </div>
        {openChip && (
          <div className="ac-chip-panel">
            {deepText(answer, openChip) || 'Detailed evidence for this layer will appear as coverage completes.'}
          </div>
        )}
      </section>

      {/* 9. Suggested Follow-up Questions */}
      <section className="ac-block">
        <h2>Suggested Follow-up Questions</h2>
        <div className="ac-follows">
          {answer.followUps.map((q) => (
            <button key={q} type="button" onClick={() => onAsk(q)}>
              {q}
            </button>
          ))}
        </div>
      </section>

      <section className="ac-answer-feedback" aria-label="Rate this AGI answer">
        {feedback.status === 'sent' ? (
          <p>Feedback recorded for AGI quality review.</p>
        ) : (
          <>
            <span>Was this research answer useful?</span>
            <button type="button" onClick={() => sendFeedback('helpful')} aria-label="Helpful answer">
              <ThumbsUp size={15} /> Yes
            </button>
            <button
              type="button"
              onClick={() => setFeedback({ reaction: 'not_helpful', status: 'choosing' })}
              aria-label="Answer needs improvement"
            >
              <ThumbsDown size={15} /> Needs improvement
            </button>
          </>
        )}
        {feedback.status === 'choosing' && (
          <div className="ac-feedback-tags">
            <span>What went wrong?</span>
            {feedbackTags.map(([tag, label]) => (
              <button type="button" key={tag} onClick={() => sendFeedback('not_helpful', [tag])}>
                {label}
              </button>
            ))}
          </div>
        )}
        {feedback.status === 'error' && <p>Feedback could not be saved. Please try again.</p>}
      </section>
    </div>
  );
}

export default function InstitutionalChatWorkspace({
  pack,
  loading,
  error,
  question,
  onAsk,
  onSave,
  onNewChat,
  conversationTurns = [],
  savedFlash,
  embedded = false,
  basePath = '/ask',
}) {
  const navigate = useNavigate();
  const answer = useMemo(() => (pack ? mapChatAnswer(pack) : null), [pack]);
  const [draft, setDraft] = useState('');
  const [topQ, setTopQ] = useState('');
  const [recents, setRecents] = useState([]);
  const threadRef = useRef(null);
  const inputRef = useRef(null);
  const askHome = basePath || '/ask';
  const priorTurns = useMemo(() => {
    const turns = Array.isArray(conversationTurns) ? conversationTurns : [];
    const last = turns[turns.length - 1];
    return last && String(last.question || '').trim() === String(question || '').trim()
      ? turns.slice(0, -1)
      : turns;
  }, [conversationTurns, question]);

  useEffect(() => {
    setRecents(getRecentSearches(8));
  }, [question, pack]);

  useEffect(() => {
    if (threadRef.current && (answer || loading)) {
      threadRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [answer, loading, question]);

  const submit = (value) => {
    const q = String(value || draft || topQ).trim();
    if (!q) return;
    setDraft('');
    setTopQ('');
    onAsk(q);
  };

  const newChat = () => {
    onNewChat?.();
    navigate(askHome);
    setDraft('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    inputRef.current?.focus();
  };

  return (
    <div className={`agib-chat${embedded ? ' agib-chat-embedded' : ''}`}>
      {!embedded && (
      <aside className="ac-sidebar" aria-label="AGI navigation">
        <Link to="/" className="ac-brand">
          <span className="ac-brand-mark">AGI</span>
          <span className="ac-brand-text">
            AGI
            <span className="ac-brand-sub">Institutional Research</span>
          </span>
        </Link>

        <button type="button" className="ac-new-chat" onClick={newChat}>
          <MessageSquarePlus size={16} style={{ display: 'inline', marginRight: 8, verticalAlign: -3 }} />
          New Chat
        </button>

        <nav className="ac-nav">
          <button type="button" className="active" onClick={() => navigate(askHome)}>
            <Sparkles size={16} />
            <span>Ask AGI</span>
          </button>
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.label} to={item.path}>
                <Icon size={16} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          <div className="ac-nav-label">Recent Chats</div>
          <div className="ac-recent">
            {recents.length ? (
              recents.map((q) => (
                <button key={q} type="button" onClick={() => onAsk(q)} title={q}>
                  {q}
                </button>
              ))
            ) : (
              <button type="button" disabled style={{ opacity: 0.45 }}>
                No recent chats yet
              </button>
            )}
          </div>
        </nav>

        <div className="ac-side-foot">
          <button type="button" className="ac-upgrade" onClick={() => navigate('/#newsletter')}>
            Upgrade Plan
          </button>
          <div className="ac-user">
            <span className="ac-avatar">
              <User size={14} />
            </span>
            Institutional desk
          </div>
        </div>
      </aside>
      )}

      <div className="ac-main">
        <header className="ac-topbar">
          <form
            className="ac-top-search"
            onSubmit={(e) => {
              e.preventDefault();
              submit(topQ);
            }}
          >
            <Search size={16} color="#6b7280" />
            <input
              value={topQ}
              onChange={(e) => setTopQ(e.target.value)}
              placeholder="Ask AGI anything..."
              aria-label="Ask AGI"
            />
          </form>
          <div className="ac-top-actions">
            {embedded && (
              <button type="button" className="ac-icon-btn" aria-label="New chat" onClick={newChat} title="New chat">
                <MessageSquarePlus size={17} />
              </button>
            )}
            <button type="button" className="ac-icon-btn" aria-label="Notifications" onClick={() => navigate(embedded ? '/agi/alerts' : '/workspace')}>
              <Bell size={17} />
            </button>
            <button type="button" className="ac-icon-btn" aria-label="Save research" onClick={onSave} title="Save">
              <Bookmark size={17} />
            </button>
            <button type="button" className="ac-icon-btn" aria-label="Workspace" onClick={() => navigate(embedded ? '/agi' : '/workspace')}>
              <Briefcase size={17} />
            </button>
          </div>
        </header>

        <div className="ac-workspace">
          <div className="ac-thread">
            {!question && !loading && (
              <div className="ac-empty">
                <h1>What would you like to analyse?</h1>
                <p>
                  Ask AGI in plain English. Receive a concise institutional answer first — then open deeper thesis,
                  evidence and intelligence layers on demand.
                </p>
                <div className="ac-starters">
                  {STARTERS.map((q) => (
                    <button key={q} type="button" onClick={() => onAsk(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {priorTurns.map((turn) => (
              <div className="ac-prior-turn" key={turn.id}>
                <div className="ac-msg ac-msg-user">
                  <div className="ac-bubble-user">{turn.question}</div>
                </div>
                <div className="ac-msg ac-msg-agi ac-msg-prior">
                  <div className="ac-label">AGI</div>
                  <div className="ac-direct">
                    <p className="ac-direct-text">{turn.summary || 'Research response recorded.'}</p>
                    <div className="ac-turn-meta">
                      {turn.stance ? <span>{turn.stance}</span> : null}
                      {turn.confidence != null ? <span>Confidence {turn.confidence}%</span> : null}
                      {(turn.entities || []).map((entity) => <span key={entity}>{entity}</span>)}
                      {turn.focus ? <span>{turn.focus.replaceAll('_', ' ')}</span> : null}
                      {turn.horizon ? <span>{turn.horizon}</span> : null}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {priorTurns.length > 0 && <div className="ac-thread-divider">Current turn</div>}

            {question && (
              <div className="ac-msg ac-msg-user">
                <div className="ac-bubble-user">{question}</div>
              </div>
            )}

            {loading && (
              <div className="ac-msg ac-msg-agi">
                <div className="ac-label">AGI</div>
                <div className="ac-loading" aria-live="polite">
                  <div className="ac-skel" />
                  <div className="ac-skel" style={{ height: '7rem' }} />
                  <div className="ac-skel" style={{ height: '3rem' }} />
                </div>
              </div>
            )}

            {error && !loading && (
              <div className="ac-msg ac-msg-agi">
                <div className="ac-label">AGI</div>
                <div className="ac-direct">
                  <p className="ac-direct-text">
                    The research desk is momentarily unavailable. Please retry — AGI will resume institutional analysis
                    as soon as the engine is warm.
                  </p>
                </div>
              </div>
            )}

            {!loading && answer && <AnswerTurn answer={answer} onAsk={onAsk} />}

            {savedFlash && (
              <p style={{ color: '#0f6b4c', fontSize: '0.82rem', fontWeight: 650 }}>Saved to your research workspace.</p>
            )}

            <div ref={threadRef} />
          </div>

          <aside className="ac-rail" aria-label="Conviction rail">
            <div className="ac-rail-card">
              <h3>Company</h3>
              <p className="ac-rail-company">{answer?.company || answer?.ticker || 'AGI Desk'}</p>
              <p className="ac-rail-ticker">{answer?.ticker || 'Ask a company or market question'}</p>

              <div style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#6b7280' }}>
                Current View
              </div>
              <div style={{ fontSize: '1.05rem', fontWeight: 750, marginTop: 4 }} className={viewClass(answer?.stanceTone)}>
                {answer?.institutionalView || '—'}
              </div>

              <div style={{ marginTop: '0.9rem', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#6b7280' }}>
                Confidence
              </div>
              <div style={{ fontSize: '1.1rem', fontWeight: 750 }}>
                {answer?.confidence == null ? '—' : `${answer.confidence}%`}
              </div>
              <div className="ac-gauge" aria-hidden>
                <i style={{ width: `${Math.min(100, answer?.confidence || 0)}%` }} />
              </div>

              <div className="ac-score-grid">
                <div>
                  <span>Investment Horizon</span>
                  <strong>{answer?.horizon || '—'}</strong>
                </div>
                <div>
                  <span>Business Quality</span>
                  <strong>{answer?.scores?.business || '—'}</strong>
                </div>
                <div>
                  <span>Financial Quality</span>
                  <strong>{answer?.scores?.financial || '—'}</strong>
                </div>
                <div>
                  <span>Growth Score</span>
                  <strong>{answer?.scores?.growth || '—'}</strong>
                </div>
                <div>
                  <span>Valuation Score</span>
                  <strong>{answer?.scores?.valuation || '—'}</strong>
                </div>
                <div>
                  <span>Risk</span>
                  <strong>{answer?.scores?.risk || '—'}</strong>
                </div>
                <div>
                  <span>Overall Conviction</span>
                  <strong>{answer?.scores?.conviction || '—'}</strong>
                </div>
              </div>
            </div>

            <div className="ac-rail-card">
              <h3>Latest Research Refresh</h3>
              <p style={{ margin: 0, fontSize: '0.84rem', color: '#3a4450' }}>
                {answer?.lastUpdated || answer?.freshness || 'Live AGI intelligence cycle'}
              </p>
            </div>

            <div className="ac-rail-card">
              <h3>Recent Research</h3>
              <ul className="ac-rail-list">
                {(answer?.recentResearch || ['Internal AGI', 'Exchange Filing']).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </aside>
        </div>

        <div className="ac-composer-wrap">
          <form
            className="ac-composer"
            onSubmit={(e) => {
              e.preventDefault();
              submit(draft);
            }}
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  submit(draft);
                }
              }}
              placeholder="Ask AGI anything about markets, companies, macro or your portfolio..."
              aria-label="Message AGI"
            />
            <button type="submit" disabled={!draft.trim() || loading}>
              Ask
            </button>
          </form>
          <p className="ac-composer-note">
            AGI provides institutional research context — not personalised investment advice.
          </p>
        </div>
      </div>
    </div>
  );
}
