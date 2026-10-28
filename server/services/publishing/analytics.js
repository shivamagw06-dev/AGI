/**
 * Newsletter / publishing analytics — from events + jobs + subscribers.
 */

import { store } from './store.js';

export function getAnalytics() {
  const subscribers = store.listSubscribers();
  const events = store.listEvents();
  const jobs = store.listJobs();
  const imports = store.listImports();
  const campaigns = store.listCampaigns();

  const active = subscribers.filter((s) => s.status === 'active' && s.is_active !== false);
  const unsubscribed = subscribers.filter((s) => s.status === 'unsubscribed' || s.is_active === false);

  const sent = events.filter((e) => e.event_type === 'sent').length;
  const opens = events.filter((e) => e.event_type === 'open').length;
  const clicks = events.filter((e) => e.event_type === 'click').length;
  const bounces = events.filter((e) => e.event_type === 'bounce').length;
  const unsubEvents = events.filter((e) => e.event_type === 'unsubscribe').length;

  const bySource = {};
  for (const s of subscribers) {
    const key = s.source || 'unknown';
    bySource[key] = (bySource[key] || 0) + 1;
  }

  const topicCounts = {};
  for (const job of jobs) {
    const section = job.channels?.section || job.channel_content?.section || 'Research';
    topicCounts[section] = (topicCounts[section] || 0) + 1;
  }

  const mostRead = [...jobs]
    .map((j) => ({
      title: j.title,
      slug: j.article_slug,
      sent: j.newsletter_sent || 0,
      opens: (j.analytics?.opens || 0),
      clicks: (j.analytics?.clicks || 0),
    }))
    .sort((a, b) => b.opens + b.clicks - (a.opens + a.clicks))
    .slice(0, 10);

  const growth = subscribers
    .slice()
    .sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)))
    .reduce((acc, s) => {
      const day = String(s.created_at || '').slice(0, 10) || 'unknown';
      const last = acc[acc.length - 1];
      const total = (last?.total || 0) + 1;
      if (last && last.day === day) last.total = total;
      else acc.push({ day, total });
      return acc;
    }, []);

  return {
    subscribers: {
      total: subscribers.length,
      active: active.length,
      unsubscribed: unsubscribed.length,
      by_source: bySource,
    },
    growth,
    email: {
      sent,
      open_rate: sent ? Number(((opens / sent) * 100).toFixed(2)) : 0,
      click_rate: sent ? Number(((clicks / sent) * 100).toFixed(2)) : 0,
      bounce_rate: sent ? Number(((bounces / sent) * 100).toFixed(2)) : 0,
      unsubscribes: unsubEvents,
      opens,
      clicks,
      bounces,
    },
    most_read_articles: mostRead,
    traffic_source: bySource,
    campaign_performance: campaigns.slice(0, 20).map((c) => ({
      id: c.id,
      name: c.name,
      status: c.status,
      segment: c.segment,
      stats: c.stats || {},
      sent_at: c.sent_at,
    })),
    top_performing_topics: Object.entries(topicCounts)
      .map(([topic, count]) => ({ topic, count }))
      .sort((a, b) => b.count - a.count),
    imports: imports.slice(0, 10),
    publish_jobs: jobs.slice(0, 20),
  };
}

export function recordEvent({ job_id, subscriber_id, email, event_type, meta = {} }) {
  const events = store.listEvents();
  const row = {
    id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
    job_id: job_id || null,
    subscriber_id: subscriber_id || null,
    email: email || null,
    event_type,
    meta,
    created_at: new Date().toISOString(),
  };
  events.push(row);
  store.saveEvents(events.slice(-5000));

  if (job_id && (event_type === 'open' || event_type === 'click')) {
    const jobs = store.listJobs();
    const job = jobs.find((j) => j.id === job_id);
    if (job) {
      job.analytics = job.analytics || {};
      if (event_type === 'open') job.analytics.opens = (job.analytics.opens || 0) + 1;
      if (event_type === 'click') job.analytics.clicks = (job.analytics.clicks || 0) + 1;
      store.saveJobs(jobs);
    }
  }
  return row;
}
