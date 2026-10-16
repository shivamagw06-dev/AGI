export function StorySection({ kicker, chapter, title, children, className = '' }) {
  return (
    <section className={`scroll-mt-28 ${className}`}>
      {(kicker || chapter) && (
        <div className="mb-2 flex items-baseline gap-3">
          {chapter && <span className="beta-chapter">{chapter}</span>}
          {kicker && <p className="beta-kicker">{kicker}</p>}
        </div>
      )}
      {title && <h2 className="beta-h2">{title}</h2>}
      <div className={title || kicker || chapter ? 'mt-6' : ''}>{children}</div>
    </section>
  );
}

export function EmptyState({ title = 'Nothing to show yet', detail }) {
  return (
    <div className="border-t border-[var(--beta-border)] py-6">
      <p className="text-sm font-semibold text-[var(--beta-ink)]">{title}</p>
      {detail && <p className="beta-caption mt-2 max-w-lg">{detail}</p>}
    </div>
  );
}

export function InsightCard({ title, body, meta, children, lede = false }) {
  return (
    <article className="border-t border-[var(--beta-border)] pt-6">
      {meta && <p className="beta-caption mb-2">{meta}</p>}
      {title && <h3 className="beta-h3">{title}</h3>}
      {body && <p className={`${lede ? 'beta-lede' : 'beta-body'} ${title ? 'mt-4' : ''}`}>{body}</p>}
      {children}
    </article>
  );
}

export function MetricStoryCard({ label, from, to, change, why = [], meaning, watchNext }) {
  return (
    <article className="border-t border-[var(--beta-border)] pt-8">
      <p className="beta-kicker">{label}</p>
      <div className="mt-5 flex flex-wrap items-end gap-3">
        {from != null && (
          <p className="font-[family-name:var(--beta-serif)] text-2xl text-[var(--beta-muted)] line-through decoration-[var(--beta-border-strong)]">
            {from}
          </p>
        )}
        {from != null && to != null && <span className="pb-1 text-[var(--beta-caption)]">→</span>}
        {to != null && <p className="beta-metric-hero">{to}</p>}
        {change && (
          <span
            className={`beta-chip mb-2 ${
              String(change).startsWith('-') || String(change).includes('↓') ? 'beta-chip-neg' : 'beta-chip-pos'
            }`}
          >
            {change}
          </span>
        )}
      </div>
      {why.length > 0 && (
        <div className="mt-8 max-w-xl">
          <p className="text-[12px] font-bold uppercase tracking-[0.14em] text-[var(--beta-navy)]">Why?</p>
          <ul className="mt-3 space-y-2 beta-body">
            {why.map((line) => (
              <li key={line} className="flex gap-2">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[var(--beta-navy)]" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {meaning && (
        <p className="beta-lede mt-8 max-w-2xl border-l-2 border-[var(--beta-navy)] pl-4">
          <span className="beta-kicker mr-2">Meaning</span>
          {meaning}
        </p>
      )}
      {watchNext && (
        <p className="mt-5 text-sm text-[var(--beta-muted)]">
          <span className="font-semibold text-[var(--beta-ink-soft)]">Watch next — </span>
          {watchNext}
        </p>
      )}
    </article>
  );
}

export function CompanyCard({ symbol, name, stance, confidence, why = [], onOpen }) {
  return (
    <article className="beta-panel flex h-full flex-col transition-transform duration-200 hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--beta-serif)] text-xl font-semibold text-[var(--beta-navy)]">{symbol}</p>
          {name && <p className="beta-caption mt-1">{name}</p>}
        </div>
        {stance && <span className="beta-chip">{stance}</span>}
      </div>
      {confidence != null && <p className="beta-caption mt-4">Confidence {confidence}%</p>}
      {why.length > 0 && (
        <ul className="mt-4 flex-1 space-y-2 text-sm leading-relaxed text-[var(--beta-ink-soft)]">
          {why.slice(0, 3).map((line) => (
            <li key={line}>• {line}</li>
          ))}
        </ul>
      )}
      {onOpen && (
        <button type="button" className="beta-btn-ghost beta-btn mt-6 self-start px-0" onClick={onOpen}>
          Open story →
        </button>
      )}
    </article>
  );
}

export function EvidenceCard({ claim, source }) {
  return (
    <article className="border-t border-[var(--beta-border)] py-4">
      <p className="text-sm leading-relaxed text-[var(--beta-ink)]">{claim}</p>
      {source && <p className="beta-caption mt-2">{source}</p>}
    </article>
  );
}

export function RiskCard({ title, items = [], level = 'stated' }) {
  const tone = level === 'high' ? 'beta-chip-neg' : level === 'low' ? 'beta-chip-pos' : 'beta-chip-warn';
  return (
    <article className="beta-panel">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--beta-ink)]">{title}</h3>
        <span className={`beta-chip ${tone}`}>{level}</span>
      </div>
      <ul className="mt-3 space-y-2 text-sm text-[var(--beta-ink-soft)]">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </article>
  );
}

export function TimelineCard({ items = [] }) {
  if (!items.length) return null;
  return (
    <ol className="relative space-y-8 border-l border-[var(--beta-border-strong)] pl-6">
      {items.map((item, idx) => (
        <li key={`${item.label}-${idx}`} className="relative">
          <span className="absolute -left-[1.55rem] top-1.5 h-2.5 w-2.5 rounded-full bg-[var(--beta-navy)] ring-4 ring-[var(--beta-bg)]" />
          <p className="beta-chapter">{item.label}</p>
          <p className="beta-body mt-2 text-[1.02rem]">{item.detail}</p>
        </li>
      ))}
    </ol>
  );
}

export function ForecastCard({ label, probability, detail }) {
  return (
    <article className="beta-panel">
      <div className="flex items-end justify-between gap-3">
        <p className="text-sm font-semibold text-[var(--beta-ink)]">{label}</p>
        {probability != null && (
          <p className="font-[family-name:var(--beta-serif)] text-3xl font-semibold text-[var(--beta-navy)]">{probability}%</p>
        )}
      </div>
      {probability != null && (
        <div className="mt-4 h-1 overflow-hidden rounded-full bg-[#e5e7eb]">
          <div
            className="h-full rounded-full bg-[var(--beta-navy)] transition-all duration-700"
            style={{ width: `${Math.min(100, Math.max(0, Number(probability) || 0))}%` }}
          />
        </div>
      )}
      {detail && <p className="beta-caption mt-4 leading-relaxed">{detail}</p>}
    </article>
  );
}

export function OpportunityCard({ title, detail }) {
  return (
    <article className="border-t border-[var(--beta-border)] py-5">
      <p className="font-[family-name:var(--beta-serif)] text-lg font-semibold text-[var(--beta-ink)]">{title}</p>
      {detail && <p className="beta-caption mt-2">{detail}</p>}
    </article>
  );
}
