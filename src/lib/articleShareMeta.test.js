import assert from 'node:assert/strict';
import test from 'node:test';
import {
  absoluteShareImageUrl,
  buildArticleShareMeta,
  injectShareMetaIntoHtml,
  sanitizeArticleSlug,
} from './articleShareMeta.js';

test('sanitizeArticleSlug accepts published slugs and rejects junk', () => {
  assert.equal(
    sanitizeArticleSlug('indias-banking-cycle-is-turning-private-banks-could-lead-the-next-leg-of-growth'),
    'indias-banking-cycle-is-turning-private-banks-could-lead-the-next-leg-of-growth'
  );
  assert.equal(sanitizeArticleSlug('../etc/passwd'), '');
  assert.equal(sanitizeArticleSlug('%E0%A4%A'), '');
  assert.equal(sanitizeArticleSlug(''), '');
});

test('absoluteShareImageUrl forces a public https image LinkedIn can fetch', () => {
  assert.equal(
    absoluteShareImageUrl('https://cdn.example.com/cover.jpg'),
    'https://cdn.example.com/cover.jpg'
  );
  assert.equal(
    absoluteShareImageUrl('http://cdn.example.com/cover.jpg'),
    'https://cdn.example.com/cover.jpg'
  );
  assert.equal(
    absoluteShareImageUrl('/covers/bank.png', 'https://agarwalglobalinvestments.com'),
    'https://agarwalglobalinvestments.com/covers/bank.png'
  );
  assert.equal(
    absoluteShareImageUrl('', 'https://agarwalglobalinvestments.com'),
    'https://agarwalglobalinvestments.com/agi-og-cover.png'
  );
});

test('buildArticleShareMeta uses the article cover, title and canonical URL', () => {
  const meta = buildArticleShareMeta(
    {
      title: 'India’s banking cycle is turning',
      slug: 'indias-banking-cycle-is-turning-private-banks-could-lead-the-next-leg-of-growth',
      excerpt: 'Private banks could lead the next leg of growth.',
      cover_url: 'https://zrvdtpxfmuijhionbaxr.supabase.co/storage/v1/object/public/covers/bank.jpg',
      published_at: '2026-08-26T04:00:00Z',
    },
    { site: 'https://agarwalglobalinvestments.com' }
  );
  assert.equal(meta.type, 'article');
  assert.equal(meta.author, 'AGI Research');
  assert.equal(meta.title, 'India’s banking cycle is turning');
  assert.match(meta.url, /\/article\/indias-banking-cycle-is-turning/);
  assert.match(meta.image, /covers\/bank\.jpg$/);
});

test('buildArticleShareMeta uses the first inline image when cover_url is missing', () => {
  const meta = buildArticleShareMeta(
    {
      title: 'Private banks could lead',
      slug: 'private-banks-could-lead',
      excerpt: 'The cycle is turning.',
      content: '<p>Hi</p><img src="http://cdn.example.com/hero.png">',
    },
    { site: 'https://agarwalglobalinvestments.com' }
  );
  assert.equal(meta.image, 'https://cdn.example.com/hero.png');
});

test('injectShareMetaIntoHtml puts crawler-visible OG tags in the SPA shell', () => {
  const html = `<!doctype html><html><head>
    <title>AGI — Agarwal Global Investments</title>
  </head><body><div id="root"></div></body></html>`;
  const injected = injectShareMetaIntoHtml(
    html,
    buildArticleShareMeta(
      {
        title: 'Private banks could lead',
        slug: 'private-banks-could-lead',
        excerpt: 'The cycle is turning.',
        content: '<p>Hi</p><img src="https://cdn.example.com/hero.png">',
      },
      { site: 'https://agarwalglobalinvestments.com' }
    )
  );
  assert.match(injected, /<title>Private banks could lead • AGI<\/title>/);
  assert.match(injected, /property="og:image" content="https:\/\/cdn\.example\.com\/hero\.png"/);
  assert.match(injected, /property="og:title" content="Private banks could lead"/);
  assert.doesNotMatch(injected, /AGI — Agarwal Global Investments/);
});
