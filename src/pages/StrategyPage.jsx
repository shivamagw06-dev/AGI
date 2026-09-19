import React from 'react';
import { STRATEGIES } from '@/components/strategy/strategies';
import { FOCUS } from '@/components/strategy/strategyUi';

/**
 * Strategies: AGI's sector and thematic strategies, one table each. Each
 * strategy links to the monitor behind it, where the evidence, filed figures
 * and estimates live.
 */
export default function StrategyPage() {
  React.useEffect(() => {
    document.title = 'Strategies | AGI';
    // A hash link to one strategy scrolls to it once the page has rendered.
    const id = window.location.hash.replace('#', '');
    if (id) requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: 'start' }));
  }, []);
  return (
    <div className="min-h-screen bg-white text-[#0f1720]">
      <div className="mx-auto w-full max-w-[1480px] px-4 pb-20 pt-10 sm:px-8">
        <header className="border-b border-[#e5e8ec] pb-8">
          <p className="text-[12px] font-semibold uppercase tracking-[0.2em] text-[#d9701f]">AGI Strategies</p>
          <h1 className="mt-2 text-[34px] font-semibold leading-[1.1] tracking-tight sm:text-[44px]">Strategies</h1>
          <p className="mt-3 max-w-[70ch] text-[17px] leading-relaxed text-[#4b5563]">
            Sector and thematic strategies, each with the companies in it and the case for them. Every strategy sits on a monitor that holds the evidence, filed figures and estimates behind each name.
          </p>
          {STRATEGIES.length > 1 ? (
            <nav aria-label="Strategies" className="mt-5 flex flex-wrap gap-2">
              {STRATEGIES.map((s) => (
                <a key={s.id} href={`#${s.id}`} className={`rounded-full border border-[#e5e8ec] px-3.5 py-1.5 text-[14px] text-[#34404f] hover:border-[#c7ccd3] ${FOCUS}`}>{s.title}</a>
              ))}
            </nav>
          ) : null}
        </header>

        {STRATEGIES.map(({ id, title, sector, summary, monitor, Component }) => (
          <section key={id} id={id} aria-labelledby={`${id}-h`} className="scroll-mt-24 border-b border-[#e5e8ec] py-10 last:border-b-0">
            <p className="text-[13px] font-medium text-[#6b7480]">{sector}</p>
            <h2 id={`${id}-h`} className="mt-1 text-[28px] font-semibold tracking-tight sm:text-[32px]">{title}</h2>
            <p className="mt-2 max-w-[80ch] text-[16px] leading-relaxed text-[#34404f]">{summary}</p>
            <div className="mt-6">
              <Component monitor={monitor} />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
