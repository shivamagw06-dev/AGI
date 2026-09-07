import { Link } from 'react-router-dom';
import { Calendar, Mail, Video } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import { Button } from '@/components/ui/button';

const upcoming = [
  {
    title: 'India Macro Outlook — H2 2026',
    type: 'Webinar',
    date: 'Coming soon',
    description: 'RBI policy, inflation trajectory, and implications for Indian equities.',
  },
  {
    title: 'Private Markets Roundtable',
    type: 'Virtual event',
    date: 'Coming soon',
    description: 'PE deal flow, venture funding trends, and exit activity in India.',
  },
];

export default function Events() {
  return (
    <PageShell
      eyebrow="Events"
      title="Events & Webinars"
      description="Live briefings, macro roundtables, and research sessions for institutional readers."
      metaTitle="Events & Webinars | Agarwal Global Investments"
      backTo="/"
    >
      <div className="grid md:grid-cols-2 gap-6 mb-14">
        {upcoming.map((event) => (
          <article
            key={event.title}
            className="rounded-2xl border border-white/10 bg-white/5 p-6"
          >
            <div className="flex items-center gap-2 text-blue-400 text-xs font-semibold uppercase tracking-wide">
              {event.type === 'Webinar' ? <Video size={14} /> : <Calendar size={14} />}
              {event.type}
            </div>
            <h2 className="mt-3 text-lg font-semibold text-white">{event.title}</h2>
            <p className="text-sm text-slate-500 mt-1">{event.date}</p>
            <p className="mt-3 text-slate-400 text-sm leading-relaxed">{event.description}</p>
          </article>
        ))}
      </div>

      <div className="rounded-2xl border border-blue-500/30 bg-blue-600/10 p-8 text-center">
        <Mail className="mx-auto text-blue-400 mb-4" size={28} />
        <h2 className="text-xl font-semibold text-white">Get notified when we go live</h2>
        <p className="text-slate-400 mt-2 max-w-md mx-auto text-sm">
          Subscribe to research updates and we&apos;ll email you when new webinars and briefings are announced.
        </p>
        <Button asChild className="mt-6 bg-blue-600 hover:bg-blue-700">
          <Link to="/#newsletter">Subscribe to updates</Link>
        </Button>
        <p className="mt-4 text-xs text-slate-500">
          For partnership or speaking inquiries,{' '}
          <Link to="/contact" className="text-blue-400 hover:underline">
            contact us
          </Link>
          .
        </p>
      </div>
    </PageShell>
  );
}
