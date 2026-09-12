import PageShell, { LegalSection } from '@/components/Layout/PageShell';

export default function PrivacyPolicy() {
  return (
    <PageShell
      theme="light"
      eyebrow="Legal"
      title="Privacy Policy"
      description="How Agarwal Global Investments collects, uses, and protects your information."
      metaTitle="Privacy Policy | Agarwal Global Investments"
    >
      <p className="text-sm text-slate-500 mb-10">Last updated: July 2026</p>

      <LegalSection theme="light" title="Overview">
        <p>
          Agarwal Global Investments (&quot;AGI&quot;, &quot;we&quot;, &quot;us&quot;) respects your privacy.
          This policy explains what data we collect when you use agarwalglobalinvestments.com and related services,
          and how we use it.
        </p>
      </LegalSection>

      <LegalSection title="Information we collect">
        <p>
          We may collect your email address when you subscribe to research updates, contact us, or create an account.
          We also collect standard usage data (pages visited, browser type, approximate location) through analytics
          to improve the platform.
        </p>
      </LegalSection>

      <LegalSection title="How we use your information">
        <ul className="list-disc pl-5 space-y-2">
          <li>Deliver research newsletters and product updates you opt into</li>
          <li>Respond to inquiries submitted via our contact form</li>
          <li>Maintain account security and platform functionality</li>
          <li>Improve content, navigation, and user experience</li>
        </ul>
      </LegalSection>

      <LegalSection title="Third-party services">
        <p>
          We use trusted providers including Supabase (hosting and database), Render (API proxy),
          IndianAPI (market news feeds), Trendlyne and TradingView (market widgets), and email delivery services.
          These providers process data according to their own privacy policies.
        </p>
      </LegalSection>

      <LegalSection title="Data retention & security">
        <p>
          We retain subscriber and contact data only as long as needed to provide our services or comply with law.
          We apply reasonable technical and organizational measures to protect your information,
          though no online service can guarantee absolute security.
        </p>
      </LegalSection>

      <LegalSection title="Your rights">
        <p>
          You may request access, correction, or deletion of your personal data by emailing{' '}
          <a href="mailto:shivam@agarwalglobalinvestments.com" className="text-blue-400 hover:underline">
            shivam@agarwalglobalinvestments.com
          </a>
          . You may unsubscribe from marketing emails at any time using the link in any newsletter.
        </p>
      </LegalSection>

      <LegalSection title="Contact">
        <p>
          Questions about this policy? Email{' '}
          <a href="mailto:shivam@agarwalglobalinvestments.com" className="text-blue-400 hover:underline">
            shivam@agarwalglobalinvestments.com
          </a>
          .
        </p>
      </LegalSection>
    </PageShell>
  );
}
