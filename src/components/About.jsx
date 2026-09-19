import { Link } from 'react-router-dom';
import { Target, Users, Award, TrendingUp, ArrowRight, Mail } from 'lucide-react';
import PageShell from '@/components/Layout/PageShell';
import { Button } from '@/components/ui/button';

const pillars = [
  {
    icon: Target,
    title: 'Independent Research',
    description:
      'Original analysis on Indian and global markets — free from sell-side conflicts and promotional bias.',
  },
  {
    icon: Users,
    title: 'Built for Professionals',
    description:
      'Institutional-quality depth written for investors, analysts, and decision-makers who need clarity fast.',
  },
  {
    icon: Award,
    title: 'Analytical Rigor',
    description:
      'Every report is structured for action: thesis, evidence, risks, and implications — not noise.',
  },
  {
    icon: TrendingUp,
    title: 'Markets + Macro + Private Capital',
    description:
      'Coverage spanning equities, macroeconomics, private markets, M&A, and business strategy.',
  },
];

const coverage = [
  'Pre-market, mid-day & close updates',
  'Equity research & sector deep-dives',
  'Company earnings & corporate actions',
  'RBI policy, inflation & GDP analysis',
  'Live market overview & indices',
];

export default function About() {
  return (
    <PageShell
      theme="light"
      eyebrow="About AGI"
      title="Independent Research for Serious Investors"
      description="Agarwal Global Investments delivers actionable research on finance, economics, and Indian markets — built for professionals who demand clarity."
      metaTitle="About | Agarwal Global Investments"
    >
      <div className="aspect-[21/9] rounded-xl overflow-hidden border border-slate-200 mb-12 shadow-sm">
        <img
          src="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80"
          alt="Financial markets analysis"
          className="w-full h-full object-cover"
        />
      </div>

      <div className="mb-14 space-y-4">
        <p className="text-slate-700 text-lg leading-relaxed">
          Agarwal Global Investments (AGI) is an independent research platform focused on Indian capital
          markets. We publish daily market updates, company research, and institutional-grade analysis
          — designed to help investors make better-informed decisions.
        </p>
        <p className="text-slate-600 leading-relaxed">
          Content is organized into clear sections: pre-market briefings, mid-day updates, market close
          summaries, research notes, and company updates — so you always know where to find what you need.
        </p>
      </div>

      <h2 className="text-xl font-semibold text-slate-900 mb-6">What we cover</h2>
      <ul className="grid sm:grid-cols-2 gap-3 mb-14">
        {coverage.map((item) => (
          <li
            key={item}
            className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-blue-700 shrink-0" />
            {item}
          </li>
        ))}
      </ul>

      <div className="grid sm:grid-cols-2 gap-5 mb-14">
        {pillars.map(({ icon: Icon, title, description }) => (
          <div key={title} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <Icon className="text-blue-700 mb-4" size={26} />
            <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Work with us</h2>
          <p className="text-slate-600 mt-2 text-sm max-w-lg">
            Media inquiries, research partnerships, and institutional subscriptions.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 shrink-0">
          <Button asChild className="bg-blue-700 hover:bg-blue-800">
            <Link to="/contact">
              <Mail className="mr-2 h-4 w-4" />
              Contact us
            </Link>
          </Button>
          <Button asChild variant="outline" className="border-slate-300 text-slate-700">
            <Link to="/research">
              Browse research
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </PageShell>
  );
}
