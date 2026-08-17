const DEFAULT_SITE_URL = 'https://agarwalglobalinvestments.com';

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function siteUrl() {
  return (process.env.PUBLIC_SITE_URL || process.env.BASE_URL || DEFAULT_SITE_URL).replace(/\/$/, '');
}

function formatEditionDate(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  })
    .format(date)
    .toUpperCase();
}

export function excerptFromHtml(html = '', maxChars = 280) {
  const text = String(html)
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<\/?[^>]+(>|$)/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/\s+/g, ' ')
    .trim();
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars).trim()}…`;
}

export function buildArticleEmail({
  title,
  summary = '',
  slug,
  email,
  letter,
  section = '',
  publishedAt = null,
  unsubscribeToken = null,
  coverUrl = '',
  author = '',
  readTime = '',
} = {}) {
  const site = siteUrl();
  const articleUrl = `${site}/article/${encodeURIComponent(String(slug || '').trim())}`;
  const unsubscribeUrl = unsubscribeToken
    ? `${site}/unsubscribe?token=${encodeURIComponent(String(unsubscribeToken).trim())}`
    : `${site}/unsubscribe?email=${encodeURIComponent(String(email || '').trim())}`;
  const logoUrl = `${site}/agi-logo-email.png`;
  const letterName = letter?.name || 'AGI Markets';
  const tagline = letter?.tagline || 'Independent market intelligence for serious investors.';
  const safeTitle = String(title || '').trim();
  const safeSummary = String(summary || '').trim();
  const sectionLabel = String(section || 'Research & Intelligence').trim();
  const editionDate = formatEditionDate(publishedAt);
  const desk = author && !String(author).includes('@') ? String(author).trim() : 'AGI Research Desk';
  const readingLabel = String(readTime || '3 min read').trim();
  const safeCoverUrl = String(coverUrl || '').trim();
  const preheader = excerptFromHtml(
    safeSummary || `Read the latest ${letterName} research from Agarwal Global Investments.`,
    145
  );

  const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>${escapeHtml(safeTitle)}</title>
  <style>
    body, table, td, a { -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }
    table, td { mso-table-lspace:0pt; mso-table-rspace:0pt; }
    table { border-collapse:collapse !important; }
    img { border:0; height:auto; line-height:100%; outline:none; text-decoration:none; }
    @media only screen and (max-width:640px) {
      .email-shell { width:100% !important; }
      .pad-x { padding-left:24px !important; padding-right:24px !important; }
      .headline { font-size:31px !important; line-height:1.08 !important; }
      .desktop-meta { display:none !important; }
    }
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f2f2;color:#101820;font-family:Arial,Helvetica,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;mso-hide:all;">
    ${escapeHtml(preheader)}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f1f2f2;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table role="presentation" class="email-shell" width="640" cellspacing="0" cellpadding="0" border="0" style="width:640px;max-width:640px;background:#ffffff;border-top:5px solid #c5a028;">
          <tr>
            <td class="pad-x" style="padding:25px 34px 22px;border-bottom:1px solid #d7dadd;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td valign="middle">
                    <a href="${escapeHtml(site)}" style="text-decoration:none;color:#101820;">
                      <img src="${escapeHtml(logoUrl)}" width="74" alt="Agarwal Global Investments" style="display:block;width:74px;max-width:74px;">
                    </a>
                  </td>
                  <td class="desktop-meta" align="right" valign="middle" style="font-size:10px;line-height:1.5;letter-spacing:1.4px;text-transform:uppercase;color:#626a72;">
                    Independent Research<br>
                    Markets · Macro · Intelligence
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:13px 34px;background:#101820;color:#ffffff;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#d9bb55;">
                    ${escapeHtml(letterName)}
                  </td>
                  <td align="right" style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#c9ced3;">
                    ${escapeHtml(editionDate)}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          ${safeCoverUrl ? `<tr><td><img src="${escapeHtml(safeCoverUrl)}" width="640" alt="" style="display:block;width:100%;max-width:640px;height:auto;border:0;"></td></tr>` : ''}
          <tr>
            <td class="pad-x" style="padding:42px 34px 16px;">
              <p style="margin:0 0 14px;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#8a6c08;">
                ${escapeHtml(sectionLabel)}
              </p>
              <h1 class="headline" style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:40px;line-height:1.08;font-weight:700;letter-spacing:-0.5px;color:#101820;">
                ${escapeHtml(safeTitle)}
              </h1>
              <p style="margin:17px 0 0;font-size:13px;line-height:1.5;color:#697178;">
                ${escapeHtml(tagline)}
              </p>
              <p style="margin:14px 0 0;padding-top:13px;border-top:1px solid #d7dadd;font-size:10px;line-height:1.5;letter-spacing:1px;text-transform:uppercase;color:#697178;">
                ${escapeHtml(desk)}&nbsp;&nbsp;·&nbsp;&nbsp;${escapeHtml(editionDate)}&nbsp;&nbsp;·&nbsp;&nbsp;${escapeHtml(readingLabel)}
              </p>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:18px 34px 8px;">
              <div style="border-left:4px solid #c5a028;padding:4px 0 4px 20px;">
                <p style="margin:0 0 8px;font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#8a6c08;">
                  The takeaway
                </p>
                <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:19px;line-height:1.55;color:#2d353c;">
                  ${escapeHtml(safeSummary || 'Read the full analysis from Agarwal Global Investments.')}
                </p>
              </div>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:28px 34px 42px;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td bgcolor="#101820" style="background:#101820;">
                    <a href="${escapeHtml(articleUrl)}" style="display:inline-block;padding:14px 22px;font-size:12px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;text-decoration:none;color:#ffffff;">
                      Read the full analysis&nbsp;&nbsp;→
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:16px 0 0;font-size:11px;line-height:1.5;color:#7a8289;">
                Or <a href="${escapeHtml(articleUrl)}" style="color:#3b4d5d;text-decoration:underline;">view this article in your browser</a>.
              </p>
            </td>
          </tr>
          <tr>
            <td class="pad-x" style="padding:24px 34px;background:#f7f7f5;border-top:1px solid #d7dadd;">
              <p style="margin:0 0 9px;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#101820;">
                Agarwal Global Investments
              </p>
              <p style="margin:0 0 12px;font-size:11px;line-height:1.55;color:#697178;">
                Independent research and market intelligence. This communication is for informational purposes only and is not investment advice.
              </p>
              <p style="margin:0;font-size:11px;line-height:1.55;color:#697178;">
                You received this email because you subscribed to ${escapeHtml(letterName)}.
                <a href="${escapeHtml(unsubscribeUrl)}" style="color:#3b4d5d;text-decoration:underline;">Unsubscribe</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  const text = `${letterName.toUpperCase()} | ${editionDate}
${sectionLabel.toUpperCase()}

${safeTitle}

THE TAKEAWAY
${safeSummary || 'Read the full analysis from Agarwal Global Investments.'}

Read the full analysis:
${articleUrl}

—
Agarwal Global Investments
Independent research and market intelligence.
This communication is for informational purposes only and is not investment advice.

Unsubscribe: ${unsubscribeUrl}`;

  return {
    subject: `${letterName} | ${safeTitle}`,
    html,
    text,
    articleUrl,
    unsubscribeUrl,
  };
}
