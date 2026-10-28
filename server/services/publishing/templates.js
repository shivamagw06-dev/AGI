/**
 * Institutional research newsletter HTML template — minimal, mobile responsive.
 */

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function buildNewsletterHtml({
  headline,
  coverImage,
  oneMinuteSummary,
  keyCharts = [],
  articleUrl,
  relatedResearch = [],
  siteName = 'AGI',
  siteUrl = 'https://agarwalglobalinvestments.com',
  logoUrl,
  unsubscribeUrl,
  privacyUrl,
  preheader,
}) {
  const charts = (keyCharts || [])
    .slice(0, 3)
    .map(
      (c) => `
      <tr><td style="padding:8px 0;font-size:14px;color:#334155;border-bottom:1px solid #e2e8f0;">
        <strong>${escapeHtml(c.title || c.label || 'Chart')}</strong>
        ${c.caption ? `<div style="color:#64748b;margin-top:4px">${escapeHtml(c.caption)}</div>` : ''}
      </td></tr>`,
    )
    .join('');

  const related = (relatedResearch || [])
    .slice(0, 4)
    .map(
      (r) => `
      <tr><td style="padding:6px 0;font-size:14px">
        <a href="${escapeHtml(r.url || siteUrl)}" style="color:#0a1e38;text-decoration:none">${escapeHtml(r.title || 'Related')}</a>
      </td></tr>`,
    )
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>${escapeHtml(headline)}</title>
  <!--[if !mso]><!--><style>
    @media (max-width:620px){ .agi-wrap{ width:100% !important; } .agi-pad{ padding:20px !important; } }
  </style><!--<![endif]-->
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Georgia,'Source Serif 4',serif;color:#0c1222">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0">${escapeHtml(preheader || oneMinuteSummary || '')}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f1f5f9;padding:24px 12px">
    <tr><td align="center">
      <table class="agi-wrap" role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:600px;max-width:600px;background:#ffffff;border:1px solid #e2e8f0">
        <tr><td class="agi-pad" style="padding:28px 32px 12px;border-bottom:1px solid #e2e8f0">
          ${logoUrl ? `<img src="${escapeHtml(logoUrl)}" alt="${escapeHtml(siteName)}" height="28" style="display:block;border:0" />` : `<div style="font-size:22px;font-weight:700;letter-spacing:-0.03em;color:#0a1e38">${escapeHtml(siteName)}</div>`}
          <div style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#64748b;margin-top:8px">Research Distribution</div>
        </td></tr>
        ${coverImage ? `<tr><td><img src="${escapeHtml(coverImage)}" alt="" width="600" style="display:block;width:100%;max-width:600px;height:auto;border:0" /></td></tr>` : ''}
        <tr><td class="agi-pad" style="padding:28px 32px">
          <h1 style="margin:0 0 16px;font-size:28px;line-height:1.2;font-weight:600;color:#0c1222">${escapeHtml(headline)}</h1>
          <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#0a1e38;font-weight:700">One Minute Summary</p>
          <p style="margin:0 0 24px;font-size:16px;line-height:1.55;color:#334155">${escapeHtml(oneMinuteSummary)}</p>
          ${charts ? `<p style="margin:0 0 8px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#0a1e38;font-weight:700">Key Charts</p><table width="100%" cellspacing="0" cellpadding="0">${charts}</table>` : ''}
          <table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px 0 8px"><tr>
            <td style="background:#0a1e38;border-radius:8px">
              <a href="${escapeHtml(articleUrl)}" style="display:inline-block;padding:12px 22px;color:#ffffff;text-decoration:none;font-family:system-ui,-apple-system,sans-serif;font-size:14px;font-weight:600">Read Full Report →</a>
            </td>
          </tr></table>
          ${related ? `<p style="margin:28px 0 8px;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#0a1e38;font-weight:700">Related Research</p><table width="100%" cellspacing="0" cellpadding="0">${related}</table>` : ''}
        </td></tr>
        <tr><td class="agi-pad" style="padding:20px 32px;background:#0a1e38;color:#cbd5e1;font-family:system-ui,-apple-system,sans-serif;font-size:12px;line-height:1.5">
          <div style="color:#ffffff;font-weight:600;margin-bottom:8px">${escapeHtml(siteName)}</div>
          Institutional research updates. Not investment advice.
          <div style="margin-top:12px">
            <a href="${escapeHtml(unsubscribeUrl || `${siteUrl}/unsubscribe`)}" style="color:#94a3b8">Unsubscribe</a>
            &nbsp;·&nbsp;
            <a href="${escapeHtml(privacyUrl || `${siteUrl}/privacy`)}" style="color:#94a3b8">Privacy</a>
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

export function buildPlainText({ headline, oneMinuteSummary, articleUrl }) {
  return `${headline}\n\n${oneMinuteSummary}\n\nRead: ${articleUrl}\n`;
}
