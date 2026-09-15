import { Link } from 'react-router-dom';

export default function PopularInvestorQuestions({ questions = [], loading = false }) {
  const rows = (questions || []).slice(0, 8);

  return (
    <section className="pb-8 border-b border-[#dddddd]" aria-labelledby="popular-investor-questions">
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 id="popular-investor-questions" className="text-lg font-bold text-[#111111]">
            Popular Investor Questions
          </h2>
          <p className="text-xs text-[#767676] mt-1">
            Dynamically shaped by today&apos;s regime, research desk, themes and macro events
          </p>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 bg-[#eee] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {rows.map((row) => {
            const q = row.question || row.label || row;
            const reason = row.reason;
            return (
              <Link
                key={q}
                to={`/ask?q=${encodeURIComponent(q)}`}
                className="border border-[#dddddd] px-4 py-3 hover:border-[#111111] group"
              >
                <p className="text-sm font-bold text-[#111111] group-hover:text-[#ff6600] leading-snug">
                  {q}
                </p>
                {reason && <p className="text-[11px] text-[#767676] mt-1">{reason}</p>}
              </Link>
            );
          })}
          {rows.length === 0 && (
            <p className="text-sm text-[#767676]">Questions will appear as the desk publishes research.</p>
          )}
        </div>
      )}
    </section>
  );
}
