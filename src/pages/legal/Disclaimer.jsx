import PageShell, { LegalSection } from '@/components/Layout/PageShell';

export default function Disclaimer() {
  return (
    <PageShell
      theme="light"
      eyebrow="Legal"
      title="Investment Disclaimer"
      description="Important information about the nature of content published on this platform."
      metaTitle="Disclaimer | Agarwal Global Investments"
    >
      <p className="text-sm text-slate-500 mb-10">Last updated: July 2026</p>

      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 mb-10 text-amber-900 text-sm leading-relaxed">
        Agarwal Global Investments is a research and insights platform. Nothing on this website
        constitutes investment advice, a recommendation, or a solicitation to buy or sell any security.
      </div>

      <LegalSection title="Not investment advice">
        <p>
          All articles, notes, market commentary, data widgets, and opinions published on this site
          are for general informational and educational purposes only. They do not account for your
          individual financial situation, objectives, or risk tolerance.
        </p>
      </LegalSection>

      <LegalSection title="No fiduciary relationship">
        <p>
          Your use of this website does not create a client, advisory, or fiduciary relationship
          between you and Agarwal Global Investments. Consult a qualified financial adviser before
          making investment decisions.
        </p>
      </LegalSection>

      <LegalSection title="Market data & accuracy">
        <p>
          Live quotes, news, heatmaps, and third-party widgets may be delayed, incomplete, or inaccurate.
          We do not warrant the timeliness, accuracy, or completeness of any market data displayed.
          Past performance is not indicative of future results.
        </p>
      </LegalSection>

      <LegalSection title="Forward-looking statements">
        <p>
          Research may contain forward-looking statements involving risks and uncertainties.
          Actual outcomes may differ materially. AGI undertakes no obligation to update such statements.
        </p>
      </LegalSection>

      <LegalSection title="External links">
        <p>
          Links to third-party websites are provided for convenience. AGI does not endorse and is not
          responsible for the content or policies of external sites.
        </p>
      </LegalSection>

      <LegalSection title="Contact">
        <p>
          Questions? Email{' '}
          <a href="mailto:shivam@agarwalglobalinvestments.com" className="text-blue-400 hover:underline">
            shivam@agarwalglobalinvestments.com
          </a>
          .
        </p>
      </LegalSection>
    </PageShell>
  );
}
