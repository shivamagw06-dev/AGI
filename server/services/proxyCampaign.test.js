import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { isProxyContestForm, parseFilingHeader, campaignsFrom, campaignDirection } from './proxyCampaign.js';

/**
 * The fixture is a real EDGAR header, fetched from the filing it describes.
 *
 *   server/tests/fixtures/edgar/pershing-adp.dfan14a-header.txt
 *     Pershing Square Capital Management against Automatic Data Processing,
 *     accession 0001193125-17-334499, filed 2017-11-06 - the ADP proxy fight.
 *     https://www.sec.gov/Archives/edgar/data/8670/000119312517334499
 *
 * Hand-written SGML would have agreed with any parser. The real header is what
 * shows that both parties carry a COMPANY CONFORMED NAME field, which is the
 * one thing a naive implementation gets wrong.
 */
const FIXTURE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', 'tests', 'fixtures', 'edgar',
    'pershing-adp.dfan14a-header.txt'),
  'utf8',
);

describe('the parties to a solicitation', () => {
  test('the target and the manager are read from their own blocks', () => {
    const parsed = parseFilingHeader(FIXTURE);
    assert.equal(parsed.submissionType, 'DFAN14A');
    assert.equal(parsed.filedAt, '2017-11-06');
    assert.equal(parsed.accession, '0001193125-17-334499');
    assert.deepEqual(parsed.subject,
      { name: 'AUTOMATIC DATA PROCESSING INC', cik: '0000008670' });
    assert.deepEqual(parsed.filedBy,
      { name: 'Pershing Square Capital Management, L.P.', cik: '0001336528' });
  });

  test('the first name in the file is the target, not the manager', () => {
    // The trap, and the reason the fixture is a real document. Both parties
    // carry COMPANY CONFORMED NAME, and SUBJECT COMPANY comes first - so a
    // parser that searches the whole header attributes every campaign to the
    // company being campaigned against.
    const naive = /COMPANY CONFORMED NAME:\s*(.+)/.exec(FIXTURE)[1].trim();
    assert.equal(naive, 'AUTOMATIC DATA PROCESSING INC');
    assert.notEqual(parseFilingHeader(FIXTURE).filedBy.name, naive);
  });

  test('a filing with no FILED BY block is not a campaign', () => {
    // A registrant speaking for itself files under FILER alone. Reading that
    // as a manager campaigning against someone would invent a fight.
    const registrant = FIXTURE
      .replace('SUBJECT COMPANY:', 'FILER:')
      .replace(/FILED BY:[\s\S]*$/, '');
    const parsed = parseFilingHeader(registrant);
    assert.equal(parsed.filedBy, null);
    assert.equal(parsed.subject, null);
  });

  test('nothing in is not a filing', () => {
    for (const empty of ['', null, undefined]) {
      const parsed = parseFilingHeader(empty);
      assert.equal(parsed.subject, null);
      assert.equal(parsed.filedBy, null);
      assert.equal(parsed.filedAt, null);
    }
  });
});

describe('which forms are a campaign', () => {
  test('solicitations against a board, including the cheap kind', () => {
    for (const form of ['DFAN14A', 'DEFN14A', 'PREN14A', 'DEFC14A', 'PRRN14A']) {
      assert.equal(isProxyContestForm(form), true, form);
    }
    // An exempt solicitation is a holder urging others how to vote without
    // running a full proxy - the same act, done cheaply, and missed on the
    // first pass through the form types.
    assert.equal(isProxyContestForm('PX14A6G'), true);
    assert.equal(isProxyContestForm('DFAN14A/A'), true);
  });

  test('management proxies and holdings are not campaigns', () => {
    // DEF 14A without the N or C is the board's own proxy. Counting it would
    // turn every company's annual meeting into an activist campaign.
    for (const form of ['DEF 14A', 'DEFA14A', '13F-HR', 'SC 13D', '']) {
      assert.equal(isProxyContestForm(form), false, form);
    }
  });
});

describe('filings grouped into campaigns', () => {
  const filings = [
    { manager_id: 'm1', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'DFAN14A', filed_at: '2017-11-06' },
    { manager_id: 'm1', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'DFAN14A', filed_at: '2017-11-01' },
    { manager_id: 'm1', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'PRRN14A', filed_at: '2017-10-25' },
    { manager_id: 'm1', subject_cik: '0000320193', subject_name: 'APPLE INC', form_type: 'PX14A6G', filed_at: '2021-02-01' },
    { manager_id: 'm2', subject_cik: '0000008670', subject_name: 'AUTOMATIC DATA PROCESSING INC', form_type: 'DFAN14A', filed_at: '2017-11-02' },
  ];

  test('a campaign is one manager against one company', () => {
    const campaigns = campaignsFrom(filings);
    assert.equal(campaigns.length, 3);
    const [biggest] = campaigns;
    assert.equal(biggest.manager_id, 'm1');
    assert.equal(biggest.subject_cik, '0000008670');
    assert.equal(biggest.filings, 3);
    // Ten documents in six days is a different thing from one exempt
    // solicitation sent once, and the dates are what say so.
    assert.equal(biggest.first_filed, '2017-10-25');
    assert.equal(biggest.last_filed, '2017-11-06');
    assert.deepEqual(biggest.forms, ['DFAN14A', 'PRRN14A']);
  });

  test('two managers against the same company are two campaigns', () => {
    // They are not co-ordinated and must not be merged; each manager's record
    // is its own.
    const adp = campaignsFrom(filings).filter((row) => row.subject_cik === '0000008670');
    assert.deepEqual(adp.map((row) => row.manager_id).sort(), ['m1', 'm2']);
  });

  test('a filing missing either party is dropped rather than half-attributed', () => {
    assert.deepEqual(campaignsFrom([{ manager_id: 'm1', filed_at: '2020-01-01' }]), []);
    assert.deepEqual(campaignsFrom([{ subject_cik: '0000008670' }]), []);
    assert.deepEqual(campaignsFrom([]), []);
    assert.deepEqual(campaignsFrom(), []);
  });
});

describe('who is campaigning against whom', () => {
  const header = parseFilingHeader(FIXTURE);

  test('the manager is campaigning when it is the one that filed', () => {
    assert.equal(campaignDirection(header, '0001336528'), 'by_manager');
    // Unpadded is the same CIK.
    assert.equal(campaignDirection(header, '1336528'), 'by_manager');
  });

  test('a filing naming the manager as the target is not its campaign', () => {
    // The bug the first run produced. EDGAR's submissions list for a CIK
    // includes every filing that names it, filer or subject, and for an
    // operating company that is mostly the latter - Berkshire's twenty-three
    // PX14A6G filings are shareholders soliciting against Berkshire. All
    // twenty-three were recorded as Berkshire campaigning against itself,
    // and Alphabet and NVIDIA did the same.
    assert.equal(campaignDirection(header, '0000008670'), 'against_manager');
  });

  test('a manager on neither side is on neither side', () => {
    assert.equal(campaignDirection(header, '0000320193'), 'unknown');
    assert.equal(campaignDirection(header, null), 'unknown');
    assert.equal(campaignDirection(null, '0001336528'), 'unknown');
  });

  test('a filer campaigning against itself is refused rather than recorded', () => {
    // Not a campaign in any useful sense, and the shape a self-referential
    // row would take. Better to drop it than to publish a manager fighting
    // its own board.
    const self = { filedBy: { cik: '0001336528' }, subject: { cik: '0001336528' } };
    assert.equal(campaignDirection(self, '0001336528'), 'unknown');
  });
});
