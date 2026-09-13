import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import { publicationMatch } from './publicationImportService.js';

// Berkshire's 2025 annual report, as it actually stood: one publication, 758
// rows, 199 of them decided by a person.
const STORED = [
  { id: 'a', title: '2025 Annual Report', digest: 'abc123', pasted_at: '2026-09-12T12:26:12Z', rows: 758, decisions: 199 },
  { id: 'b', title: 'Q2 2026 Earnings Release', digest: 'def456', pasted_at: '2026-07-14T09:00:00Z', rows: 30, decisions: 0 },
];

describe('whether a pasted document is already stored', () => {
  test('the same text is the same publication', () => {
    const match = publicationMatch(STORED, { digest: 'abc123', title: '2025 Annual Report' });
    assert.equal(match.kind, 'same_text');
    assert.equal(match.publication.id, 'a');
  });

  test('the same text is recognised even under a different title', () => {
    // The title is typed by a person and the text is not. A re-paste under a
    // renamed title still updates the publication it hashes to, so saying
    // "new" here would be a lie.
    const match = publicationMatch(STORED, { digest: 'abc123', title: 'Annual Report 2025' });
    assert.equal(match.kind, 'same_text');
    assert.equal(match.publication.id, 'a');
  });

  test('the same title with different text is the case that cost 199 decisions', () => {
    const match = publicationMatch(STORED, { digest: 'CHANGED', title: '2025 Annual Report' });
    assert.equal(match.kind, 'same_title');
    assert.equal(match.publication.id, 'a');
    assert.equal(match.publication.decisions, 199);
  });

  test('a title is compared the way a person types it', () => {
    for (const typed of ['2025 annual report', '  2025 Annual Report  ', '2025 ANNUAL REPORT']) {
      assert.equal(publicationMatch(STORED, { digest: 'CHANGED', title: typed }).kind,
        'same_title', typed);
    }
  });

  test('a document unlike anything stored is new', () => {
    const match = publicationMatch(STORED, { digest: 'CHANGED', title: '2026 Annual Report' });
    assert.equal(match.kind, 'new');
    assert.equal(match.publication, null);
  });

  test('a manager with nothing stored gets no false warning', () => {
    for (const empty of [[], null, undefined]) {
      assert.equal(publicationMatch(empty, { digest: 'abc123', title: 'Anything' }).kind, 'new');
    }
  });

  test('an empty title never matches by title', () => {
    // Every stored title would otherwise compare equal to '' after trimming
    // and the panel would warn about an unrelated publication.
    for (const blank of ['', '   ', null, undefined]) {
      assert.equal(publicationMatch(STORED, { digest: 'CHANGED', title: blank }).kind, 'new', String(blank));
    }
  });

  test('matching on text wins over matching on title', () => {
    // A manager republishing the same text under a name already used by a
    // different document: the text is the identity the database keys on.
    const stored = [
      { id: 'title-twin', title: 'Letter', digest: 'zzz', rows: 5, decisions: 5 },
      { id: 'text-twin', title: 'Something Else', digest: 'abc123', rows: 9, decisions: 0 },
    ];
    const match = publicationMatch(stored, { digest: 'abc123', title: 'Letter' });
    assert.equal(match.kind, 'same_text');
    assert.equal(match.publication.id, 'text-twin');
  });
});
