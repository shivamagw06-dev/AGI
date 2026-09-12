import assert from 'node:assert/strict';
import test from 'node:test';
import { fetchLatestPublishedArticle } from './sendLatestArticleEmail.js';

test('fetchLatestPublishedArticle queries published articles by published_at desc', async () => {
  const calls = [];
  const admin = {
    from(table) {
      calls.push(table);
      const chain = {
        select(columns) {
          calls.push(['select', columns]);
          return chain;
        },
        eq(column, value) {
          calls.push(['eq', column, value]);
          return chain;
        },
        order(column, opts) {
          calls.push(['order', column, opts]);
          return chain;
        },
        limit(n) {
          calls.push(['limit', n]);
          return chain;
        },
        async maybeSingle() {
          return {
            data: {
              id: '1',
              title: 'Test Brief',
              slug: 'test-brief',
              excerpt: 'Hello',
              section: 'Indian Market',
              content: '<p>Hello</p>',
              published_at: '2026-08-16T10:00:00Z',
            },
            error: null,
          };
        },
      };
      return chain;
    },
  };

  const article = await fetchLatestPublishedArticle(admin);
  assert.equal(article.slug, 'test-brief');
  assert.match(String(calls.find((row) => Array.isArray(row) && row[0] === 'select')?.[1] || ''), /cover_url/);
  assert.equal(calls[0], 'articles');
  assert.deepEqual(calls.find((row) => Array.isArray(row) && row[0] === 'eq'), ['eq', 'status', 'published']);
  assert.deepEqual(
    calls.find((row) => Array.isArray(row) && row[0] === 'order'),
    ['order', 'published_at', { ascending: false }]
  );
});
