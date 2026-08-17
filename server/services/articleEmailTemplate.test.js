import assert from 'node:assert/strict';
import test from 'node:test';
import { buildArticleEmail, excerptFromHtml } from '../lib/articleEmailTemplate.js';

test('buildArticleEmail renders editorial HTML and a plain-text fallback', () => {
  const email = buildArticleEmail({
    title: 'Markets Reprice the Rate Path',
    summary: 'Bond yields moved sharply as investors reassessed the policy outlook.',
    slug: 'markets-reprice-rate-path',
    email: 'reader@example.com',
    section: 'Macro',
    publishedAt: '2026-08-17T10:00:00Z',
    letter: {
      name: 'AGI Macro',
      tagline: 'Understanding the forces shaping global markets.',
    },
  });

  assert.equal(email.subject, 'AGI Macro | Markets Reprice the Rate Path');
  assert.match(email.html, /The takeaway/i);
  assert.match(email.html, /Read the full analysis/i);
  assert.match(email.html, /17 AUG 2026/);
  assert.match(email.html, /This communication is for informational purposes only/);
  assert.match(email.text, /THE TAKEAWAY/);
  assert.match(email.text, /https:\/\/agarwalglobalinvestments\.com\/article\/markets-reprice-rate-path/);
  assert.match(email.unsubscribeUrl, /reader%40example\.com/);
});

test('buildArticleEmail escapes subscriber-controlled and article content', () => {
  const email = buildArticleEmail({
    title: '<script>alert("x")</script>',
    summary: 'A & B',
    slug: 'safe-slug',
    email: 'reader+agi@example.com',
    letter: { name: 'AGI Markets', tagline: 'Markets & intelligence.' },
  });

  assert.doesNotMatch(email.html, /<script>/);
  assert.match(email.html, /&lt;script&gt;/);
  assert.match(email.html, /A &amp; B/);
  assert.match(email.unsubscribeUrl, /reader%2Bagi%40example\.com/);
});

test('excerptFromHtml strips scripts, styles and markup', () => {
  const excerpt = excerptFromHtml(
    '<style>.x{color:red}</style><p>Market <strong>brief</strong> &amp; outlook.</p><script>bad()</script>'
  );
  assert.equal(excerpt, 'Market brief & outlook.');
});
