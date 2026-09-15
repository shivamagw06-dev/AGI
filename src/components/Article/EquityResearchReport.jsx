import React from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import './equityResearchReport.css';

const STANCE_LABELS = { bullish: 'Bullish', neutral: 'Neutral', bearish: 'Bearish' };

function formatReportDate(value, fallback) {
  if (!value) return fallback;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return fallback;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

function parseKeyData(value) {
  return String(value || '').split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const separator = line.indexOf(':');
    return separator === -1
      ? { label: line, value: '' }
      : { label: line.slice(0, separator).trim(), value: line.slice(separator + 1).trim() };
  });
}

function PriceCell({ label, value, currency, strong = false }) {
  if (!value) return null;
  return (
    <div className={`equity-report__price-cell${strong ? ' equity-report__price-cell--strong' : ''}`}>
      <span>{label}</span>
      <b>{currency && label !== 'Implied move' ? `${currency} ` : ''}{value}</b>
    </div>
  );
}

export default function EquityResearchReport({ article, author, html, niceDate, minutes, shareMeta, isoPubDate, isOwner }) {
  const meta = article.equity_research || {};
  const stance = STANCE_LABELS[meta.stance] ? meta.stance : 'neutral';
  const keyData = parseKeyData(meta.key_data);
  const analystName = meta.analyst_name || author?.full_name || author?.display_name || 'AGI Research';
  const publishedLabel = formatReportDate(meta.report_date, niceDate);
  const canonical = shareMeta?.url || `https://agarwalglobalinvestments.com/article/${article.slug}`;

  return (
    <div className="equity-report-page">
      <Helmet>
        <title>{article.title} • AGI Equity Research</title>
        <meta name="description" content={shareMeta?.description || article.excerpt || article.title} />
        <link rel="canonical" href={canonical} />
        <meta property="og:type" content="article" />
        <meta property="og:url" content={canonical} />
        <meta property="og:title" content={`${article.title} | AGI Equity Research`} />
        <meta property="og:description" content={shareMeta?.description || article.excerpt || article.title} />
        {shareMeta?.image && <meta property="og:image" content={shareMeta.image} />}
        {isoPubDate && <meta property="article:published_time" content={isoPubDate} />}
      </Helmet>

      <main className="equity-report-page__main">
        <section className="equity-report" aria-label={`${meta.company_name || article.title} equity research`}>
          <div className="equity-report__utility">
            <Link to="/research">Back to research</Link>
            <div>{isOwner && <Link to={`/admin/articles/edit/${encodeURIComponent(article.slug)}`}>Edit report</Link>}<span>Informational research</span></div>
          </div>

          <header className="equity-report__masthead">
            <Link to="/" className="equity-report__brand" aria-label="Agarwal Global Investments home">
              <img src="/agi-logo.png" alt="" />
              <span><b>Agarwal Global</b><em>Investments</em></span>
            </Link>
            <div className="equity-report__edition"><strong>{meta.report_label || 'Equity Research'}</strong><span>{publishedLabel}</span></div>
          </header>

          <div className="equity-report__headline">
            <p className="equity-report__company">{meta.company_name || 'Company research'}{meta.ticker && <span> ({meta.ticker}{meta.exchange ? ` · ${meta.exchange}` : ''})</span>}</p>
            <h1>{article.title}</h1>
          </div>

          <div className="equity-report__facts">
            {meta.ticker && <div className="equity-report__ticker">{meta.ticker}</div>}
            <PriceCell label="Fair value" value={meta.fair_value} currency={meta.currency} strong />
            <PriceCell label="Reference price" value={meta.current_price} currency={meta.currency} />
            <PriceCell label="Implied move" value={meta.potential_pct} />
            <div className={`equity-report__stance equity-report__stance--${stance}`}><i aria-hidden="true" /><span><small>Thesis stance</small><strong>{STANCE_LABELS[stance]}</strong></span></div>
          </div>

          <div className="equity-report__grid">
            <div className="equity-report__analysis">
              {article.excerpt && <div className="equity-report__summary"><span>Investment view</span><p>{article.excerpt}</p></div>}
              {article.cover_url && <figure className="equity-report__cover"><img src={article.cover_url} alt="" /></figure>}
              <article className="equity-report__body article-prose" dangerouslySetInnerHTML={{ __html: html }} />
            </div>

            <aside className="equity-report__sidebar">
              <section className="equity-report__analyst"><p>Prepared by</p><strong>{analystName}</strong>{meta.analyst_title && <span>{meta.analyst_title}</span>}{meta.analyst_contact && <a href={`mailto:${meta.analyst_contact}`}>{meta.analyst_contact}</a>}<small>Agarwal Global Investments</small></section>
              {keyData.length > 0 && <section className="equity-report__key-data"><h2><span>Key data</span></h2><dl>{keyData.map((row, index) => <div key={`${row.label}-${index}`}><dt>{row.label}</dt>{row.value && <dd>{row.value}</dd>}</div>)}</dl></section>}
              <section className="equity-report__document-data"><span>{minutes} min read</span><span>{article.section || 'Equity Research'}</span>{Array.isArray(article.tags) && article.tags.filter((tag) => tag !== 'equity-research').slice(0, 5).map((tag) => <span key={tag}>#{tag}</span>)}</section>
            </aside>
          </div>

          <footer className="equity-report__disclaimer"><strong>Research disclosure</strong><p>The Bullish, Neutral or Bearish stance reflects the author&apos;s thesis and is not a buy, hold or sell recommendation. This material is for information and research purposes only and does not constitute investment advice, an offer or a solicitation.</p></footer>
        </section>
      </main>
    </div>
  );
}
