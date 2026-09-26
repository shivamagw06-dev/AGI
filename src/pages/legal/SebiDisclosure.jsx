import PageShell, { LegalSection } from '@/components/Layout/PageShell';

export default function SebiDisclosure() {
  return (
    <PageShell
      theme="light"
      eyebrow="Regulatory"
      title="SEBI Disclosure"
      description="Regulatory disclosures for Agarwal Global Investments research platform."
      metaTitle="SEBI Disclosure | Agarwal Global Investments"
    >
      <p className="text-sm text-slate-500 mb-10">Last updated: July 2026</p>

      <LegalSection theme="light" title="Nature of service">
        <p>
          Agarwal Global Investments publishes independent research and market commentary for
          informational and educational purposes. We are not registered as a Research Analyst
          under SEBI (Research Analyst) Regulations, 2014 unless explicitly stated otherwise on
          specific licensed content.
        </p>
      </LegalSection>

      <LegalSection theme="light" title="No investment advice">
        <p>
          Content on this website — including research notes, market updates, and opinions — does
          not constitute investment advice, a recommendation, or an offer to buy or sell any
          security. Readers should consult a SEBI-registered investment adviser before making
          investment decisions.
        </p>
      </LegalSection>

      <LegalSection theme="light" title="Conflicts of interest">
        <p>
          Authors and contributors may hold positions in securities discussed in published research.
          Where applicable, conflicts will be disclosed within the relevant article. AGI does not
          engage in investment banking or brokerage activities through this platform.
        </p>
      </LegalSection>

      <LegalSection theme="light" title="Accuracy of information">
        <p>
          While we strive for accuracy, market data and third-party feeds may be delayed or contain
          errors. AGI does not guarantee the completeness or timeliness of any information
          published.
        </p>
      </LegalSection>

      <LegalSection theme="light" title="Contact">
        <p>
          For regulatory or compliance inquiries, email{' '}
          <a href="mailto:shivam@agarwalglobalinvestments.com" className="text-blue-700 hover:underline">
            shivam@agarwalglobalinvestments.com
          </a>
          .
        </p>
      </LegalSection>
    </PageShell>
  );
}
