import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { getUiWorkflow } from '@/lib/uiApi';

export default function ResearchWorkflowDesk() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    getUiWorkflow()
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  const data = state.data;

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>Research Workflow | AGI</title>
      </Helmet>
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">
        <Link to="/research" className="text-xs font-bold text-[#111] hover:text-[#ff6600]">← Research</Link>
        <p className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Research Desk</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111111]">Research Workflow</h1>
        <p className="mt-2 text-sm text-[#767676]">
          Idea → Draft → Review → Compliance → Approval → Published → Knowledge Ingested → Prediction Tracking
        </p>

        {state.loading ? (
          <div className="mt-8 h-40 bg-[#eee] animate-pulse" />
        ) : state.error ? (
          <p className="mt-8 text-sm text-[#767676]">Workflow intelligence unavailable.</p>
        ) : (
          <>
            <div className="mt-8 flex flex-wrap gap-2">
              {(data?.stages || []).map((s) => (
                <span key={s.id} className="text-[11px] font-bold border border-[#ddd] px-3 py-1.5 text-[#111]">
                  {s.label}
                </span>
              ))}
            </div>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              <section className="border border-[#dddddd] p-5">
                <h2 className="text-xs font-bold uppercase text-[#767676]">Draft Queue</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {(data?.draft_queue || []).map((id) => (
                    <li key={id} className="border-b border-[#eee] pb-1">{typeof id === 'string' ? id : id.title || id.research_id}</li>
                  ))}
                  {(data?.draft_queue || []).length === 0 && <li className="text-[#767676]">Empty</li>}
                </ul>
              </section>
              <section className="border border-[#dddddd] p-5">
                <h2 className="text-xs font-bold uppercase text-[#767676]">Review Queue</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  {(data?.review_queue || []).map((id) => (
                    <li key={id} className="border-b border-[#eee] pb-1">{typeof id === 'string' ? id : id.title || id.research_id}</li>
                  ))}
                  {(data?.review_queue || []).length === 0 && <li className="text-[#767676]">Empty</li>}
                </ul>
              </section>
              <section className="border border-[#dddddd] p-5 md:col-span-2">
                <h2 className="text-xs font-bold uppercase text-[#767676]">Pipeline</h2>
                <ul className="mt-3 space-y-3">
                  {(data?.pipeline || []).slice(0, 20).map((row) => (
                    <li key={row.research_id} className="border border-[#eee] p-3">
                      <p className="text-sm font-bold text-[#111]">{row.title}</p>
                      <p className="text-[11px] text-[#767676] mt-1">
                        {(row.tickers || []).join(', ')} · {row.status}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(row.stages || []).map((s) => (
                          <span
                            key={s.id}
                            className={`text-[10px] px-2 py-0.5 border ${
                              s.current
                                ? 'bg-[#111] text-white border-[#111]'
                                : s.state === 'done'
                                  ? 'border-[#111] text-[#111]'
                                  : 'border-[#ddd] text-[#999]'
                            }`}
                          >
                            {s.label}
                          </span>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
