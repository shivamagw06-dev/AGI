import test, { describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  identityTokens, heldIssuerVocabulary, heldIssuerIn, heldIssuersIn,
  claimsByHolding, claimsByStep, managerMentions,
} from './publicationSaid.js';

/** Names as a 13F files them, which is not how a letter writes them. */
const HELD = ['KRAFT HEINZ CO', 'OCCIDENTAL PETROLEUM CORP', 'MITSUBISHI CORPORATION',
  'APPLE INC', 'COCA COLA CO', 'BANK OF AMERICA CORP', 'AMERICAN EXPRESS CO'];
const VOCAB = heldIssuerVocabulary(HELD, { exclude: ['Berkshire Hathaway Inc'] });

describe('the words that identify a holding', () => {
  test('corporate suffixes and short words carry no identity', () => {
    assert.deepEqual(identityTokens('KRAFT HEINZ CO'), ['kraft', 'heinz']);
    assert.deepEqual(identityTokens('APPLE INC'), ['apple']);
    // "&" and "Co" leave nothing distinguishing but the family name.
    assert.deepEqual(identityTokens('MITSUI & CO LTD'), ['mitsui']);
  });

  test('the manager is not one of its own holdings', () => {
    // Otherwise every sentence in a Berkshire report is filed against a
    // position in Berkshire.
    const vocab = heldIssuerVocabulary(['BERKSHIRE HATHAWAY INC CL B', 'KRAFT HEINZ CO'],
      { exclude: ['Berkshire Hathaway Inc'] });
    assert.deepEqual(vocab.map((entry) => entry.issuer), ['KRAFT HEINZ CO']);
  });

  test('one company filed under two spellings is one entry', () => {
    const vocab = heldIssuerVocabulary(['KRAFT HEINZ CO', 'KRAFT HEINZ COMPANY']);
    assert.equal(vocab.length, 1);
    assert.equal(vocab[0].issuer, 'KRAFT HEINZ CO');
  });
});

describe('matching a holding in a sentence', () => {
  test('every identifying word present is the strong match', () => {
    assert.deepEqual(heldIssuerIn('Our investment in Kraft Heinz has been disappointing.', VOCAB),
      { issuer: 'KRAFT HEINZ CO', match: 'name' });
  });

  test('a lead word alone is a weaker match, not a refusal', () => {
    // Requiring every word lost Occidental entirely: the registrant name is
    // "OCCIDENTAL PETROLEUM CORP" and the filer writes "our investment in
    // Occidental", which is 27 sentences of real commentary.
    assert.deepEqual(
      heldIssuerIn('OxyChem is a business we encountered through our investment in Occidental.', VOCAB),
      { issuer: 'OCCIDENTAL PETROLEUM CORP', match: 'word' },
    );
  });

  test('a one-word name in a list of unrelated companies is flagged, not trusted', () => {
    // The hardest case in the report, and the reason nothing here is
    // auto-approved. Mitsubishi Corporation is a holding; this sentence is
    // about IMC's competitors in cutting tools and has nothing to do with the
    // trading house. Only world knowledge separates them.
    const found = heldIssuerIn('Other manufacturing companies such as Kyocera, Mitsubishi, '
      + 'Sumitomo, Ceratizit and OSG play a role in the cutting tools market.', VOCAB);
    assert.equal(found.issuer, 'MITSUBISHI CORPORATION');
    assert.equal(found.match, 'word', 'a single word must not read as a confident match');
  });

  test('a generic lead word matches nothing on its own', () => {
    // "Bank of America" is found wherever the filer writes it in full. What
    // this prevents is every sentence containing "bank" being filed there.
    assert.equal(heldIssuerIn('We deposited the proceeds in a bank account.', VOCAB), null);
    assert.deepEqual(heldIssuerIn('Bank of America Corporation was among them.', VOCAB),
      { issuer: 'BANK OF AMERICA CORP', match: 'name' });
  });

  test('a generic lead word matches nothing even when long enough', () => {
    // The stoplist only ever gates a LEAD word, and "bank" is four characters
    // so the length rule catches it first - which left the stoplist untested
    // and surviving mutation. "American Express" leads on "american", eight
    // characters and generic, so this is the case that exercises it: the word
    // appears constantly in an American company's report.
    assert.equal(heldIssuerIn('Our businesses serve American consumers in every state.', VOCAB),
      null);
    // Written in full, it is still found.
    assert.deepEqual(heldIssuerIn('American Express Company remains a large holding.', VOCAB),
      { issuer: 'AMERICAN EXPRESS CO', match: 'name' });
  });

  test('a sentence naming four holdings is about all four', () => {
    // Returning one best match filed this under whichever scored highest and
    // hid it from the other three.
    const found = heldIssuersIn('The five largest holdings at each date were American Express '
      + 'Company, Apple Inc., Bank of America Corporation and The Coca-Cola Company.', VOCAB);
    const issuers = found.map((entry) => entry.issuer).sort();
    assert.deepEqual(issuers, ['AMERICAN EXPRESS CO', 'APPLE INC', 'BANK OF AMERICA CORP',
      'COCA COLA CO']);
  });

  test('nothing held, nothing matched', () => {
    assert.deepEqual(heldIssuersIn('A sentence about nobody in particular.', VOCAB), []);
    assert.deepEqual(heldIssuersIn('', VOCAB), []);
    assert.deepEqual(heldIssuersIn('Kraft Heinz', []), []);
  });
});

describe('grouping what the fund said', () => {
  const claim = (slot, text) => ({ slot, source_excerpt: text, basis: 'stated' });
  const CLAIMS = [
    claim('why', 'Our investment in Kraft Heinz has been disappointing.'),
    claim('how_much', 'We recorded an impairment charge of $5.0 billion on Kraft Heinz.'),
    claim('what_happened', 'Berkshire acquired Occidental’s chemicals business for $9.5 billion.'),
    claim('what_happened', 'A large portion of our portfolio is concentrated in a small number of '
      + 'American companies such as Apple, American Express and Coca-Cola.'),
    claim('risks', 'A sentence naming no holding at all.'),
  ];

  test('positions are ordered by how much the filer said about them', () => {
    // The number of things a filer writes about a position is itself the
    // signal about which positions it is thinking about.
    const groups = claimsByHolding(CLAIMS, VOCAB);
    assert.equal(groups[0].issuer, 'KRAFT HEINZ CO');
    assert.equal(groups[0].commentary, 2);
  });

  test('a list of names is not commentary on each name in it', () => {
    const groups = claimsByHolding(CLAIMS, VOCAB);
    const apple = groups.find((group) => group.issuer === 'APPLE INC');
    assert.equal(apple.claims.length, 1);
    assert.equal(apple.claims[0].enumeration, true);
    // So it contributes nothing to how much the filer is said to have
    // discussed the position - which is what orders the list.
    assert.equal(apple.commentary, 0);
  });

  test('a claim naming no holding appears under no holding', () => {
    const groups = claimsByHolding(CLAIMS, VOCAB);
    const texts = groups.flatMap((group) => group.claims.map((item) => item.source_excerpt));
    assert.ok(!texts.includes('A sentence naming no holding at all.'));
  });

  test('steps come back in the order the chain asks them', () => {
    const order = ['what_happened', 'why', 'how_much', 'risks'];
    assert.deepEqual(claimsByStep(CLAIMS, order).map((group) => group.slot),
      ['what_happened', 'why', 'how_much', 'risks']);
  });

  test('a step with nothing in it is not a group', () => {
    // An empty heading implies the document was checked and said nothing.
    // Berkshire did not decline to discuss Apple; it disclosed Apple in a
    // table.
    const slots = claimsByStep(CLAIMS, ['what_happened', 'how', 'why', 'how_much', 'risks'])
      .map((group) => group.slot);
    assert.ok(!slots.includes('how'));
  });

  test('nothing in, nothing out', () => {
    assert.deepEqual(claimsByHolding(null, VOCAB), []);
    assert.deepEqual(claimsByStep(null, ['why']), []);
  });
});

describe('does this document belong to this manager', () => {
  const BERKSHIRE = 'BERKSHIRE HATHAWAY INC. At year-end, our insurance float stood at '
    + '$176 billion. Berkshire acquired BNSF in 2010.';
  const NORGES = 'Government Pension Fund Global Annual report 2025. The fund returned 15.1 '
    + 'percent in 2025. Norges Bank Investment Management manages the fund.';

  test('a filer names itself', () => {
    const found = managerMentions(BERKSHIRE, 'Berkshire Hathaway Inc');
    assert.equal(found.checked, true);
    assert.equal(found.token, 'berkshire');
    assert.ok(found.mentions >= 2);
  });

  test('the wrong document names it never', () => {
    // Norges Bank's annual report was pasted into a command that said
    // --manager berkshire-hathaway, and 177 of Norges Bank's sentences were
    // stored as things Berkshire said. Nothing connected the manager on the
    // command line to the document on stdin.
    assert.equal(managerMentions(NORGES, 'Berkshire Hathaway Inc').mentions, 0);
    assert.equal(managerMentions(BERKSHIRE, 'Norges Bank Investment Management').mentions, 0);
  });

  test('the distinctive word is chosen, not the first', () => {
    // "Norges Bank Investment Management" happens to lead on its distinctive
    // word, so it does not test this at all - the first draft used it and the
    // mutation survived. "National Pension Service" is the case that bites:
    // it leads on "national", which appears in any number of documents having
    // nothing to do with the manager.
    assert.equal(managerMentions(NORGES, 'Norges Bank Investment Management').token, 'norges');
    const nps = managerMentions('The national economy grew strongly in 2025.',
      'National Pension Service');
    assert.equal(nps.token, 'pension', 'picked a word every report uses');
    assert.equal(nps.mentions, 0);
    assert.equal(managerMentions('The National Pension Service raised its allocation.',
      'National Pension Service').mentions, 1);
  });

  test('a whole word, not a fragment', () => {
    // "Berk" or "shire" appearing inside another word is not a mention.
    assert.equal(managerMentions('The Berkshires are a mountain range.', 'Berkshire Hathaway').mentions, 0);
  });

  test('no manager name means nothing was checked', () => {
    // Distinct from zero mentions: the caller must not refuse a document
    // because a manager record has no usable name.
    const found = managerMentions(BERKSHIRE, '');
    assert.equal(found.checked, false);
    assert.equal(found.mentions, 0);
    assert.equal(managerMentions('', 'Berkshire Hathaway').mentions, 0);
  });
});
