import { Link } from 'react-router-dom';

/**
 * Always-on discovery — never leave the user at a dead end.
 * Preserves AGI editorial borders/type.
 */
export default function DiscoveryRail({
  discovery = {},
  onAsk,
  title = 'Explore next',
  className = '',
}) {
  const companies = discovery.related_companies || [];
  const themes = discovery.related_themes || [];
  const sectors = discovery.related_sectors || [];
  const research = discovery.related_research || [];
  const questions = discovery.related_questions || discovery.popular_questions || [];

  if (
    !companies.length &&
    !themes.length &&
    !sectors.length &&
    !research.length &&
    !questions.length
  ) {
    return (
      <section className={`border border-[#dddddd] p-5 ${className}`}>
        <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/ask" className="text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
            Ask AGI
          </Link>
          <Link to="/predictions" className="text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
            Prediction Centre
          </Link>
          <Link to="/workspace" className="text-[11px] font-bold border border-[#ddd] px-2.5 py-1.5 hover:text-[#ff6600]">
            Personal Workspace
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className={`border border-[#dddddd] p-5 ${className}`}>
      <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
      <p className="mt-1 text-xs text-[#929292]">Related research, companies, themes and questions.</p>

      {companies.length > 0 && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Related companies</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {companies.map((t) => (
              <Link
                key={t}
                to={`/research/stocks/${encodeURIComponent(t)}`}
                className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
              >
                {t}
              </Link>
            ))}
          </div>
        </div>
      )}

      {themes.length > 0 && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Related themes</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {themes.map((t) => (
              <Link
                key={t}
                to={`/themes/${encodeURIComponent(t)}`}
                className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
              >
                {t}
              </Link>
            ))}
          </div>
        </div>
      )}

      {sectors.length > 0 && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Related sectors</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {sectors.map((s) => (
              <Link
                key={s}
                to={`/sectors/${encodeURIComponent(s)}`}
                className="text-[11px] font-bold border border-[#ddd] px-2 py-1 hover:text-[#ff6600]"
              >
                {s}
              </Link>
            ))}
          </div>
        </div>
      )}

      {research.length > 0 && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Related research</p>
          <ul className="mt-2 space-y-2">
            {research.slice(0, 5).map((r, idx) => (
              <li key={r.id || r.title || idx} className="text-sm border-b border-[#eee] pb-2">
                {r.id ? (
                  <Link to={`/article/${encodeURIComponent(r.id)}`} className="font-bold text-[#111] hover:text-[#ff6600]">
                    {r.title || r.id}
                  </Link>
                ) : (
                  <span className="font-bold text-[#111]">{r.title || String(r)}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {questions.length > 0 && (
        <div className="mt-4">
          <p className="text-[10px] font-bold uppercase text-[#767676]">Related questions</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {questions.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => onAsk?.(q)}
                className="text-[11px] border border-[#ddd] px-2.5 py-1.5 text-left hover:border-[#111] hover:text-[#ff6600]"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
