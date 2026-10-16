/**
 * One-click Research Distribution Engine.
 * Website article (CMS) → Newsletter → LinkedIn → X → Telegram → WhatsApp (ready) → Analytics → Archive
 * Does NOT duplicate article storage — expects CMS publish already done or article payload provided.
 */

import { generateChannelContent, maybeEnrichChannels } from './channels.js';
import { sendBulk } from './emailProvider.js';
import { buildNewsletterHtml, buildPlainText } from './templates.js';
import { markEmailSent, segmentSubscribers } from './subscribers.js';
import { recordEvent } from './analytics.js';
import { newId, store, supabaseUpsert } from './store.js';

function siteOrigin() {
  return (process.env.SITE_ORIGIN || process.env.BASE_URL || 'https://agarwalglobalinvestments.com').replace(/\/$/, '');
}

/**
 * Publish distribution for an already-saved CMS article.
 */
export async function publishArticleWorkflow(article = {}, { segment = 'all', dryRun } = {}) {
  const channels = await maybeEnrichChannels(generateChannelContent(article), article);
  const job = {
    id: newId('job_'),
    article_id: article.id || article.articleId || null,
    article_slug: article.slug || null,
    title: article.title || 'Untitled',
    status: 'running',
    channels: {
      website: { status: 'published', url: channels.article_url },
      newsletter: { status: 'pending' },
      linkedin: { status: 'generated' },
      twitter: { status: 'generated' },
      telegram: { status: 'generated' },
      whatsapp: { status: 'future_ready' },
      analytics: { status: 'pending' },
      archive: { status: 'pending' },
      section: channels.section,
    },
    channel_content: channels,
    newsletter_sent: 0,
    newsletter_failed: 0,
    segment,
    analytics: { opens: 0, clicks: 0 },
    error: null,
    created_at: new Date().toISOString(),
    completed_at: null,
  };

  const jobs = store.listJobs();
  jobs.unshift(job);
  store.saveJobs(jobs.slice(0, 500));

  const recipients = segmentSubscribers(segment);
  const html = buildNewsletterHtml({
    headline: article.title,
    coverImage: article.coverUrl || article.cover_url,
    oneMinuteSummary: channels.one_minute_summary,
    keyCharts: channels.key_charts,
    articleUrl: channels.article_url,
    relatedResearch: channels.related_research,
    siteName: 'AGI',
    siteUrl: siteOrigin(),
    logoUrl: process.env.NEWSLETTER_LOGO_URL,
    unsubscribeUrl: `${siteOrigin()}/unsubscribe`,
    privacyUrl: `${siteOrigin()}/privacy`,
    preheader: channels.one_minute_summary,
  });

  const messages = recipients.map((s) => ({
    to: s.email,
    subject: channels.seo_title || article.title,
    html: html.split(`${siteOrigin()}/unsubscribe`).join(
      `${siteOrigin()}/unsubscribe?token=${encodeURIComponent(s.unsubscribe_token || '')}&email=${encodeURIComponent(s.email)}`,
    ),
    text: buildPlainText({
      headline: article.title,
      oneMinuteSummary: channels.newsletter_summary,
      articleUrl: channels.article_url,
    }),
    tags: [{ name: 'campaign', value: 'research_distribution' }],
    _subscriber_id: s.id,
  }));

  const forceDry = dryRun || process.env.NEWSLETTER_DRY_RUN === '1' || !process.env.RESEND_API_KEY;
  let sent = 0;
  let failed = 0;

  if (messages.length === 0) {
    job.channels.newsletter = { status: 'skipped', reason: 'No active subscribers in segment' };
  } else if (forceDry) {
    for (const m of messages) {
      recordEvent({
        job_id: job.id,
        subscriber_id: m._subscriber_id,
        email: m.to,
        event_type: 'sent',
        meta: { dryRun: true },
      });
      sent += 1;
    }
    job.channels.newsletter = { status: 'dry_run', attempted: messages.length, sent };
  } else {
    const results = await sendBulk(
      messages.map(({ _subscriber_id, ...m }) => m),
      { concurrency: 4 },
    );
    results.forEach((r, idx) => {
      const m = messages[idx];
      if (r.ok) {
        sent += 1;
        recordEvent({
          job_id: job.id,
          subscriber_id: m._subscriber_id,
          email: m.to,
          event_type: 'sent',
          meta: { provider: r.provider, id: r.id },
        });
      } else {
        failed += 1;
        recordEvent({
          job_id: job.id,
          subscriber_id: m._subscriber_id,
          email: m.to,
          event_type: 'bounce',
          meta: { error: r.error },
        });
      }
    });
    job.channels.newsletter = { status: failed ? 'partial' : 'sent', attempted: messages.length, sent, failed };
  }

  markEmailSent(messages.slice(0, sent).map((m) => m.to));
  job.newsletter_sent = sent;
  job.newsletter_failed = failed;

  const campaign = {
    id: newId('cmp_'),
    name: article.title,
    subject: channels.seo_title || article.title,
    segment,
    status: forceDry ? 'dry_run' : failed ? 'partial' : 'sent',
    article_id: job.article_id,
    article_slug: job.article_slug,
    html_preview: html.slice(0, 4000),
    stats: { sent, failed, recipients: recipients.length },
    scheduled_at: null,
    sent_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
  };
  const campaigns = store.listCampaigns();
  campaigns.unshift(campaign);
  store.saveCampaigns(campaigns.slice(0, 300));

  job.channels.analytics = { status: 'recorded' };
  job.channels.archive = { status: 'stored', job_id: job.id, campaign_id: campaign.id };
  job.status = 'completed';
  job.completed_at = new Date().toISOString();

  const allJobs = store.listJobs();
  const idx = allJobs.findIndex((j) => j.id === job.id);
  if (idx >= 0) allJobs[idx] = job;
  else allJobs.unshift(job);
  store.saveJobs(allJobs);

  await supabaseUpsert('publish_jobs', [
    {
      id: job.id,
      article_id: job.article_id,
      article_slug: job.article_slug,
      title: job.title,
      status: job.status,
      channels: job.channels,
      channel_content: job.channel_content,
      newsletter_sent: job.newsletter_sent,
      newsletter_failed: job.newsletter_failed,
      segment: job.segment,
      analytics: job.analytics,
      completed_at: job.completed_at,
    },
  ]);
  await supabaseUpsert('newsletter_campaigns', [campaign]);

  return {
    ok: true,
    job,
    campaign,
    distribution: {
      website: job.channels.website,
      newsletter: job.channels.newsletter,
      linkedin: { status: 'generated', content: channels.linkedin_post },
      twitter: { status: 'generated', thread: channels.twitter_thread },
      telegram: { status: 'generated', content: channels.telegram_summary },
      whatsapp: { status: 'future_ready', content: channels.whatsapp_channel },
      seo: {
        title: channels.seo_title,
        description: channels.seo_meta_description,
        social_preview: channels.social_preview,
      },
      analytics: job.channels.analytics,
      archive: job.channels.archive,
    },
  };
}

export function previewNewsletter(article = {}) {
  const channels = generateChannelContent(article);
  const html = buildNewsletterHtml({
    headline: article.title || 'Preview',
    coverImage: article.coverUrl || article.cover_url,
    oneMinuteSummary: channels.one_minute_summary,
    keyCharts: channels.key_charts,
    articleUrl: channels.article_url,
    relatedResearch: channels.related_research,
    siteUrl: siteOrigin(),
    unsubscribeUrl: `${siteOrigin()}/unsubscribe`,
    privacyUrl: `${siteOrigin()}/privacy`,
    preheader: channels.one_minute_summary,
  });
  return { html, channels };
}

export function listPublishJobs(limit = 50) {
  return store.listJobs().slice(0, limit);
}

export function listCampaigns(limit = 50) {
  return store.listCampaigns().slice(0, limit);
}
