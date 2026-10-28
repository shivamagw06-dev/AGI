import { useState } from 'react';
import PageShell, { LegalSection } from '@/components/Layout/PageShell';

export default function PrivacyPolicy() {
  const [optout,setOptout]=useState(()=>{try{return localStorage.getItem('agi_analytics_optout')==='1';}catch{return false;}});
  return (
    <PageShell
      theme="light"
      eyebrow="Legal"
      title="Privacy Policy"
      description="How Agarwal Global Investments collects, uses, and protects your information."
      metaTitle="Privacy Policy | Agarwal Global Investments"
    >
      <p className="text-sm text-slate-500 mb-10">Last updated: 27 October 2026</p>

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

      <LegalSection title="AGI Plus payment records">
        <p>For paid membership, we store your account ID, email, submitted transaction reference, fixed payment amount, submission and review times, review notes and membership dates. Authorized administrators also record the verified bank reference and approval decision to reconcile payments and prevent a credit being reused. Your payment history is available to you and authorized administrators. Our backend and database providers process these records to operate the service.</p>
        <p>Payments are authorised in your own UPI app. AGI does not request or store your UPI PIN, OTP, bank password or payment mandate. The checkout QR is generated locally in your browser. Payment records are retained as needed for membership support, reconciliation and applicable recordkeeping obligations.</p>
      </LegalSection>

      <LegalSection title="Finance Tools applications">
        <p>When you apply to list a finance tool, we store your account email, company name, website, description, category, proposed budget and application status. These applications are private to you and authorized AGI administrators, who use them to review your listing and respond to your application. Submitting an application does not authorize a payment or publish your contact details.</p>
      </LegalSection>

      <LegalSection title="Website analytics preferences">
        <p>Our first-party traffic measurement uses a random browser identifier stored on your device for up to 90 days. It records public page paths, referring domains, device categories and sign-up or download actions. It does not store your IP address, email, URL query strings or private portfolio identifiers. Browser Do Not Track and Global Privacy Control signals disable this tracking.</p>
        <button onClick={()=>{const next=!optout;try{localStorage.setItem('agi_analytics_optout',next?'1':'0');if(next){localStorage.removeItem('agi_site_visitor_v1');localStorage.removeItem('agi_site_session_v1');}setOptout(next);}catch{}}} className="border px-4 py-2 mt-3" aria-pressed={optout}>{optout?'Anonymous website analytics disabled — enable':'Disable anonymous website analytics'}</button>
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
