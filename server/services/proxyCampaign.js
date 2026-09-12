/**
 * Who a manager campaigned against, and when.
 *
 * Of the fifty tracked managers, forty-four file nothing with the SEC but
 * position tables and stake declarations. The exception is the proxy contest:
 * a manager soliciting against a board has to file what it sends to
 * shareholders, so Pershing Square's 162 campaign filings and Third Point's
 * 115 are public, indexed by CIK, and fetchable on a schedule. It is the only
 * manager-authored writing in EDGAR.
 *
 * This reads none of that writing. The documents are the managers' own words
 * and their own copyright, and reproducing them is not ours to do. What is
 * ours is the record of the campaign itself - who filed against whom, from
 * when to when, and how hard - which is a fact about public filings and not a
 * copy of anything. A link goes with every row so a reader who wants the
 * argument can read it at the source, where it belongs.
 *
 * The subject is in the filing header rather than the document. EDGAR stamps
 * every solicitation with a SUBJECT COMPANY block naming the target and a
 * FILED BY block naming the filer, which is how a campaign is attributed
 * without opening anything.
 */

/**
 * Forms a manager files when soliciting against a board.
 *
 * The N and C suffixes mark non-management and contested solicitations. DFAN
 * is additional material from a non-management soliciting party, which is the
 * bulk of any campaign. PX14A6G is the exempt solicitation - a holder urging
 * others how to vote without running a full proxy, which is the cheap version
 * of the same act and was missed on the first pass.
 */
export const PROXY_CONTEST_FORMS = new Set([
  'DFAN14A', 'DEFN14A', 'PREN14A', 'DEFC14A', 'PREC14A', 'PRRN14A', 'DFRN14A',
  'PX14A6G', 'PX14A6N',
]);

export function isProxyContestForm(formType) {
  return PROXY_CONTEST_FORMS.has(String(formType || '').trim().toUpperCase().replace(/\/A$/, ''));
}

const SECTION = /^(SUBJECT COMPANY|FILED BY|FILER|REPORTING-OWNER|ISSUER):/gm;

function field(block, label) {
  const match = new RegExp(`^\\s*${label}:\\s*(.+?)\\s*$`, 'm').exec(block || '');
  return match ? match[1].trim() : null;
}

/**
 * The parties to one filing, from its EDGAR header.
 *
 * Sections are delimited by their own labels at the start of a line, so a
 * block runs to the next label or to the end. Reading the first
 * COMPANY CONFORMED NAME inside a block rather than the first in the file is
 * the whole trick: both parties carry that field, and a naive search returns
 * whichever appears first, which for a solicitation is the target rather than
 * the manager.
 */
export function parseFilingHeader(text) {
  const source = String(text || '');
  const submissionType = field(source, 'CONFORMED SUBMISSION TYPE');
  const filedAt = field(source, 'FILED AS OF DATE');
  const accession = field(source, 'ACCESSION NUMBER');

  const marks = [...source.matchAll(SECTION)].map((match) => ({ label: match[1], at: match.index }));
  const party = (label) => {
    const index = marks.findIndex((mark) => mark.label === label);
    if (index < 0) return null;
    const block = source.slice(marks[index].at, marks[index + 1]?.at ?? source.length);
    const name = field(block, 'COMPANY CONFORMED NAME');
    const cik = field(block, 'CENTRAL INDEX KEY');
    if (!name && !cik) return null;
    return { name, cik: cik ? cik.padStart(10, '0') : null };
  };

  return {
    accession,
    submissionType,
    // EDGAR writes dates as YYYYMMDD in the header.
    filedAt: /^\d{8}$/.test(filedAt || '')
      ? `${filedAt.slice(0, 4)}-${filedAt.slice(4, 6)}-${filedAt.slice(6, 8)}`
      : null,
    subject: party('SUBJECT COMPANY'),
    // A solicitation names the activist under FILED BY. A filing with only a
    // FILER block is the registrant speaking for itself, which is a different
    // document and not a campaign.
    filedBy: party('FILED BY') || null,
  };
}

/**
 * Filings grouped into campaigns.
 *
 * A campaign is one manager against one company. Its shape is the interesting
 * part: Pershing Square filed ten documents against Automatic Data Processing
 * in six days, which is a different thing from one exempt solicitation sent
 * once. Intensity is filings per campaign and duration is first to last, and
 * both come from the dates alone.
 */
export function campaignsFrom(filings = []) {
  const byTarget = new Map();
  // Coerced rather than defaulted: a default parameter covers undefined and
  // not null, and a caller reading a table that does not exist yet passes
  // null. The page it feeds should render an empty list, not fail.
  for (const filing of filings || []) {
    const managerId = filing?.manager_id;
    const subjectCik = filing?.subject_cik;
    if (!managerId || !subjectCik) continue;
    const key = `${managerId}|${subjectCik}`;
    if (!byTarget.has(key)) {
      byTarget.set(key, {
        manager_id: managerId,
        subject_cik: subjectCik,
        subject_name: filing.subject_name || null,
        filings: 0,
        forms: new Set(),
        first_filed: filing.filed_at || null,
        last_filed: filing.filed_at || null,
        // The newest filing's own page, so a reader lands on the latest word
        // in the campaign rather than its opening shot.
        source_url: filing.source_url || null,
      });
    }
    const campaign = byTarget.get(key);
    campaign.filings += 1;
    if (filing.form_type) campaign.forms.add(filing.form_type);
    if (filing.filed_at) {
      if (!campaign.first_filed || filing.filed_at < campaign.first_filed) campaign.first_filed = filing.filed_at;
      if (!campaign.last_filed || filing.filed_at > campaign.last_filed) {
        campaign.last_filed = filing.filed_at;
        if (filing.source_url) campaign.source_url = filing.source_url;
      }
    }
  }
  return [...byTarget.values()]
    .map((campaign) => ({ ...campaign, forms: [...campaign.forms].sort() }))
    .sort((a, b) => b.filings - a.filings
      || String(b.last_filed).localeCompare(String(a.last_filed))
      || String(a.subject_name).localeCompare(String(b.subject_name)));
}

/**
 * Whether this filing is the manager campaigning, or being campaigned against.
 *
 * EDGAR's submissions list for a CIK includes every filing that names it, as
 * the filer or as the subject. For an operating company that is mostly the
 * latter: Berkshire's twenty-three PX14A6G filings are shareholders soliciting
 * against Berkshire, and the first run recorded all of them as Berkshire
 * campaigning against itself. Alphabet and NVIDIA did the same.
 *
 * The header settles it. A solicitation names the activist under FILED BY and
 * the target under SUBJECT COMPANY, so a manager is campaigning only when its
 * own CIK is the one that filed. Anything else is a campaign against it, which
 * is worth knowing and is not the same fact.
 */
export function campaignDirection(header, managerCik) {
  const mine = String(managerCik || '').replace(/\D/g, '').padStart(10, '0');
  if (!mine || mine === '0000000000') return 'unknown';
  const filedBy = header?.filedBy?.cik || null;
  const subject = header?.subject?.cik || null;
  if (filedBy && filedBy === mine) return subject && subject !== mine ? 'by_manager' : 'unknown';
  if (subject && subject === mine) return 'against_manager';
  return 'unknown';
}

/**
 * A contested fight, or a proposal put to a vote.
 *
 * Both arrive as the same family of forms and the difference is not a matter
 * of degree. A contested solicitation runs its own proxy card - DEFC14A,
 * PRRN14A, DEFN14A and their relatives - and Pershing Square filed 110 of
 * them against Automatic Data Processing in fourteen weeks. An exempt
 * solicitation under PX14A6G is a holder urging a vote on someone else's
 * card, and Norges Bank filed one each at Wells Fargo, CME and Staples on a
 * single day in April 2012.
 *
 * Calling both "board campaigns" overstates the second and flattens the
 * first, which is the same mistake as calling a thousand-name book focused.
 * The forms say which it was, so nothing has to be inferred from the count.
 */
const CONTESTED = new Set([
  'DFAN14A', 'DEFN14A', 'PREN14A', 'DEFC14A', 'PREC14A', 'PRRN14A', 'DFRN14A',
]);

export function campaignKind(forms = []) {
  const used = (forms || []).map((form) => String(form || '').toUpperCase().replace(/\/A$/, ''));
  if (used.some((form) => CONTESTED.has(form))) return 'contest';
  if (used.length) return 'proposal';
  return null;
}

/** What to call a manager's set of campaigns, given the forms in them. */
export function campaignHeading(campaigns = []) {
  const kinds = new Set((campaigns || []).map((row) => campaignKind(row?.forms)).filter(Boolean));
  if (!kinds.size) return null;
  if (kinds.has('contest')) return kinds.size > 1 ? 'Board campaigns and proposals' : 'Board campaigns';
  return 'Shareholder proposals';
}
