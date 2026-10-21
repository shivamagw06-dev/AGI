import PageShell, { LegalSection } from '@/components/Layout/PageShell';

export default function TermsOfService() {
  return (
    <PageShell
      theme="light"
      eyebrow="Legal"
      title="Terms of Service"
      description="Terms governing use of the Agarwal Global Investments research platform."
      metaTitle="Terms of Service | Agarwal Global Investments"
    >
      <p className="text-sm text-slate-500 mb-10">Last updated: July 2026</p>

      <LegalSection title="Acceptance of terms">
        <p>
          By accessing agarwalglobalinvestments.com you agree to these Terms of Service.
          If you do not agree, please do not use the site.
        </p>
      </LegalSection>

      <LegalSection title="Research platform">
        <p>
          AGI provides independent research, commentary, market data widgets, and educational content
          for informational purposes. Access to certain features may require registration.
          We may modify, suspend, or discontinue any part of the service at any time.
        </p>
      </LegalSection>

      <LegalSection title="Accounts & acceptable use">
        <p>You agree not to:</p>
        <ul className="list-disc pl-5 space-y-2 mt-2">
          <li>Misuse the platform or attempt unauthorized access to systems or data</li>
          <li>Scrape, redistribute, or resell our research without written permission</li>
          <li>Upload unlawful, misleading, or infringing content</li>
          <li>Interfere with other users&apos; access to the service</li>
        </ul>
      </LegalSection>

      <LegalSection title="Intellectual property">
        <p>
          All research articles, branding, design, and original content on this site are owned by
          Agarwal Global Investments or its licensors unless otherwise stated.
          You may share links to published articles; reproduction requires prior consent.
        </p>
      </LegalSection>

      <LegalSection title="Third-party content">
        <p>
          Market data, news feeds, and widgets may be provided by third parties (e.g. IndianAPI, Trendlyne, TradingView).
          Their terms and accuracy disclaimers apply to that content. AGI does not guarantee third-party data.
        </p>
      </LegalSection>

      <LegalSection title="Limitation of liability">
        <p>
          To the fullest extent permitted by law, AGI is not liable for any direct, indirect, incidental,
          or consequential damages arising from your use of the site or reliance on any content published herein.
        </p>
      </LegalSection>

      <LegalSection title="Governing law">
        <p>
          These terms are governed by the laws of India. Disputes shall be subject to the exclusive jurisdiction
          of courts in New Delhi, India, unless otherwise required by applicable law.
        </p>
      </LegalSection>

      <LegalSection title="Contact">
        <p>
          For questions about these terms, contact{' '}
          <a href="mailto:shivam@agarwalglobalinvestments.com" className="text-blue-400 hover:underline">
            shivam@agarwalglobalinvestments.com
          </a>
          .
        </p>
      </LegalSection>
    </PageShell>
  );
}
