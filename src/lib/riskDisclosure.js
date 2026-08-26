/**
 * Risk disclosure configuration.
 *
 * The text below is a starting point written by an engineer, not a lawyer, and
 * it has not been reviewed by anyone qualified under Indian securities law. It
 * should be approved by a SEBI-registered compliance professional before it is
 * relied on, and this file is deliberately separate from the component so the
 * wording can be replaced without touching any code.
 *
 * A disclaimer also does not substitute for registration. SEBI's Research
 * Analysts Regulations 2014 govern publishing research and recommendations on
 * securities, and the Investment Advisers Regulations 2013 govern personalised
 * advice. If either applies to what AGI publishes, the registration is the
 * control that matters and this notice is secondary to it.
 */

/**
 * Bump when the wording changes materially.
 *
 * Acknowledgements are stored against this version, so raising it asks every
 * user to read and accept again. That is the point: an acknowledgement of text
 * somebody never saw is worth nothing if it is ever examined.
 */
export const DISCLOSURE_VERSION = '2026-08-2';

export const STORAGE_KEY = 'agi_risk_disclosure_ack';

/**
 * Registration status, confirmed by the business owner: none held.
 *
 * Stated as a fact rather than left unset. "Regulatory status not configured"
 * reads as an unfinished site, and a visitor cannot tell an absent claim from
 * an unanswered one - so the notice says plainly that AGI is not registered.
 *
 * Set this if that ever changes, including the registration number, and raise
 * DISCLOSURE_VERSION so everyone is asked to read the new position.
 */
export const SEBI_REGISTRATION = Object.freeze({ registered: false });

export const DISCLOSURE = Object.freeze({
  title: 'You are entering the Founders Intelligence Portal',
  intro:
    'Agarwal Global Investments (AGI) publishes market research, data and analysis for '
    + 'information and education. Please read the following in full before you continue.',
  sections: [
    {
      heading: 'AGI is not registered with SEBI',
      body:
        'Agarwal Global Investments is not registered with the Securities and Exchange '
        + 'Board of India as a Research Analyst or as an Investment Adviser. AGI does not '
        + 'provide personalised investment advice, portfolio management services, or '
        + 'trade execution. Content and analytical tools on this platform are intended '
        + 'for informational, educational and research purposes only.',
    },
    {
      heading: 'This is information, not advice',
      body:
        'Everything on this website — research notes, market data, screens, scores, '
        + 'signals, live broadcasts and AI-generated commentary — is provided for '
        + 'informational and educational purposes only. It is not investment advice, '
        + 'not a recommendation, and not an offer or solicitation to buy or sell any '
        + 'security or financial product. Nothing here is tailored to your financial '
        + 'situation, objectives or risk tolerance.',
    },
    {
      heading: 'No buy or sell recommendation',
      body:
        'AGI does not tell you what to buy or sell. Where content describes a company, '
        + 'sector or instrument as cheap, expensive, leading, lagging, or as carrying a '
        + 'signal, those are descriptions of data and are not instructions to trade. '
        + 'Any decision you take is your own.',
    },
    {
      heading: 'Markets carry risk, including total loss',
      body:
        'Investing in securities is subject to market risk. Prices can fall as well as '
        + 'rise, and you may lose part or all of the money you invest. Leveraged and '
        + 'derivative instruments can result in losses exceeding the amount invested.',
    },
    {
      heading: 'Past performance is not indicative of future results',
      body:
        'Historical data, backtests, model outputs and prior analysis do not predict or '
        + 'guarantee future outcomes. Any performance shown is historical and may not be '
        + 'repeated.',
    },
    {
      heading: 'Accuracy is not guaranteed',
      body:
        'Data is sourced from exchanges, regulators, market data vendors and public '
        + 'filings and may be delayed, incomplete, revised or wrong. Parts of this site '
        + 'are generated automatically and may contain errors. AGI does not warrant the '
        + 'accuracy, completeness or timeliness of any information and accepts no '
        + 'liability for any loss arising from reliance on it. Verify anything material '
        + 'against primary sources — exchange filings, offer documents and regulatory '
        + 'disclosures — before acting.',
    },
    {
      heading: 'Third-party content',
      body:
        'This site displays third-party broadcasts and data through their official '
        + 'embedded players and feeds. That content belongs to its publishers, is not '
        + 'produced or endorsed by AGI, and AGI does not control it. Displaying it does '
        + 'not imply any partnership or affiliation.',
    },
    {
      heading: 'No advisory relationship',
      body:
        'Using this website does not create an advisory, fiduciary or client '
        + 'relationship between you and AGI. AGI is not acting as your investment '
        + 'adviser, broker, or portfolio manager, and does not accept discretionary '
        + 'mandates through this site.',
    },
    {
      heading: 'Conflicts of interest',
      body:
        'AGI, its personnel and its associates may hold positions in securities '
        + 'discussed on this site, and those positions may change without notice. '
        + 'Content should be read with that possibility in mind.',
    },
    {
      heading: 'Take your own advice',
      body:
        'Consider your own financial situation and objectives, and consult a '
        + 'SEBI-registered investment adviser and a tax professional, before making any '
        + 'investment decision.',
    },
  ],
  // Replaced by the real status at render time; see SEBI_REGISTRATION above.
  registrationHeading: 'Regulatory status',
  jurisdiction:
    'This website is intended for users in India and is governed by Indian law. '
    + 'Nothing here is directed at any person in a jurisdiction where publishing or '
    + 'accessing it would be contrary to local law.',
  acknowledgement:
    'I have read and understood the above. I understand this website provides '
    + 'information only, does not constitute investment advice or a recommendation to '
    + 'buy or sell, and that I am responsible for my own investment decisions.',
});

/**
 * A stable fingerprint of the exact text a user was shown.
 *
 * The version alone records that somebody clicked a button on "2026-08-2". The
 * hash records which words were on the screen when they did, which is the part
 * that matters if the acknowledgement is ever examined and the file has been
 * edited since.
 *
 * FNV-1a: not cryptographic, and does not need to be. It is a change detector,
 * and using it avoids pulling a hashing dependency into the bundle for a
 * notice that renders once.
 */
export function disclosureHash() {
  const text = [
    DISCLOSURE.title,
    DISCLOSURE.intro,
    ...DISCLOSURE.sections.flatMap((section) => [section.heading, section.body]),
    DISCLOSURE.acknowledgement,
    SEBI_REGISTRATION?.registered ? `registered:${SEBI_REGISTRATION.number || ''}` : 'registered:false',
  ].join('\u0000');

  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, '0');
}
