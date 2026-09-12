import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';

export default function AskAgiFooter({ placeholder = 'Still have questions? Ask AGI…' }) {
  const [q, setQ] = useState('');
  const navigate = useNavigate();

  const submit = (e) => {
    e?.preventDefault?.();
    const query = q.trim();
    if (!query) {
      navigate('/beta/copilot');
      return;
    }
    navigate(`/beta/copilot?q=${encodeURIComponent(query)}`);
  };

  return (
    <section className="mt-16 border-t border-[var(--beta-border)] pt-10">
      <p className="beta-kicker">Ask AGI</p>
      <h2 className="beta-h3 mt-2">Still have questions?</h2>
      <p className="beta-caption mt-2 max-w-xl">
        One more question can turn a report into a decision. Copilot routes to existing desks — it never invents analysis.
      </p>
      <form onSubmit={submit} className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex-1">
          <span className="sr-only">Ask AGI</span>
          <input
            className="beta-input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={placeholder}
          />
        </label>
        <button type="submit" className="beta-btn shrink-0">
          Ask
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </form>
    </section>
  );
}
