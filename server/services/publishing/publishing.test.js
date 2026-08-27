/**
 * Publishing & Newsletter platform tests (node:test).
 * Run: node --test server/services/publishing/publishing.test.js
 */

import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  commitCsvImport,
  generateChannelContent,
  getAnalytics,
  listSubscribers,
  previewCsvImport,
  previewNewsletter,
  publishArticleWorkflow,
  resetStoreForTests,
  segmentSubscribers,
  subscribe,
  unsubscribe,
  updatePreferences,
  validEmail,
} from './index.js';

beforeEach(() => {
  resetStoreForTests();
  process.env.NEWSLETTER_DRY_RUN = '1';
});

test('email validation', () => {
  assert.equal(validEmail('a@b.com'), true);
  assert.equal(validEmail('bad'), false);
  assert.equal(validEmail(''), false);
});

test('subscribe dedupe and unsubscribe', async () => {
  const a = await subscribe({ email: 'One@Example.com', source: 'website_signup' });
  assert.equal(a.mode, 'created');
  const b = await subscribe({ email: 'one@example.com', source: 'api' });
  assert.equal(b.mode, 'exists');
  const listed = listSubscribers({ email: 'one@example.com' });
  assert.equal(listed.total, 1);

  const un = await unsubscribe({ email: 'one@example.com' });
  assert.equal(un.ok, true);
  const active = segmentSubscribers('all');
  assert.equal(active.length, 0);
});

test('csv import preview and commit', async () => {
  const csv = `email,first_name,last_name,tags
good@agi.test,Good,User,macro
bad-email,X,Y,
good@agi.test,Dup,User,x
also@agi.test,Also,User,forecast`;
  const preview = previewCsvImport(csv, { source: 'LinkedIn Campaign July 2026' });
  assert.equal(preview.imported, 2);
  assert.ok(preview.duplicates >= 1);
  assert.ok(preview.errors + preview.skipped >= 1);

  const committed = await commitCsvImport(csv, { source: 'LinkedIn Campaign July 2026' });
  assert.equal(committed.committed, true);
  assert.equal(committed.imported, 2);
  assert.equal(listSubscribers().total, 2);
});

test('preference updates and segmentation', async () => {
  await subscribe({
    email: 'macro@agi.test',
    preferences: { macro_research: true, company_research: false },
    tags: ['linkedin'],
    source: 'linkedin_campaign',
  });
  await subscribe({
    email: 'stock@agi.test',
    preferences: { macro_research: false, company_research: true },
  });
  await updatePreferences({
    email: 'macro@agi.test',
    preferences: { investment_office_brief: true },
  });
  assert.equal(segmentSubscribers('macro').length, 1);
  assert.equal(segmentSubscribers('stock_research').length, 1);
  assert.equal(segmentSubscribers('linkedin').length, 1);
  assert.equal(segmentSubscribers('tag:linkedin').length, 1);
});

test('channel content generation does not invent buy/sell', () => {
  const pack = generateChannelContent({
    title: 'Oil & Banks Research',
    body: '<p>Oil rose. Banks face NIM pressure. Evidence remains mixed.</p>',
    slug: 'oil-banks',
    section: 'Macro Research',
  });
  const blob = `${pack.linkedin_post} ${pack.telegram_summary} ${pack.newsletter_summary}`.toLowerCase();
  assert.equal(blob.includes('buy '), false);
  assert.equal(blob.includes('sell '), false);
  assert.ok(pack.twitter_thread.length >= 2);
  assert.ok(pack.seo_title);
  assert.ok(pack.whatsapp_channel);
});

test('publishing workflow + analytics', async () => {
  await subscribe({ email: 'reader@agi.test', source: 'website_signup' });
  const result = await publishArticleWorkflow(
    {
      id: 'art_1',
      title: 'RBI Watch',
      slug: 'rbi-watch',
      body: '<p>Liquidity conditions tightened. Watch the policy corridor.</p><p>Credit growth remains healthy.</p>',
      section: 'Macro Research',
    },
    { dryRun: true },
  );
  assert.equal(result.ok, true);
  assert.equal(result.job.status, 'completed');
  assert.ok(result.distribution.newsletter);
  assert.ok(result.distribution.linkedin.content);
  assert.ok(result.distribution.telegram.content);
  assert.equal(result.distribution.whatsapp.status, 'future_ready');

  const analytics = getAnalytics();
  assert.ok(analytics.subscribers.active >= 1);
  assert.ok(analytics.email.sent >= 1);
  assert.ok(analytics.publish_jobs.length >= 1);
});

test('newsletter preview html', () => {
  const preview = previewNewsletter({
    title: 'Preview Note',
    body: 'Summary sentence one. Summary sentence two.',
    slug: 'preview-note',
  });
  assert.match(preview.html, /One Minute Summary/);
  assert.match(preview.html, /Unsubscribe/);
  assert.match(preview.html, /Read Full Report/);
});
