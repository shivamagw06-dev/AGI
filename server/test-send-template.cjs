/**
 * server/test-send-template.js
 * Send a single test email using your SendGrid template and server/.env
 * Edit the `TO_EMAIL` below to your inbox before running.
 */

require('dotenv').config({ path: './server/.env' });
const sgMail = require('@sendgrid/mail');

const TO_EMAIL = 'shivam.agw06@gmail.com'; // <<-- replace with your email

if (!process.env.SENDGRID_API_KEY) {
  console.error('Missing SENDGRID_API_KEY in server/.env');
  process.exit(1);
}
if (!process.env.SENDGRID_TEMPLATE_ID) {
  console.error('Missing SENDGRID_TEMPLATE_ID in server/.env');
  process.exit(1);
}
if (!process.env.FROM_EMAIL) {
  console.error('Missing FROM_EMAIL in server/.env');
  process.exit(1);
}

sgMail.setApiKey(process.env.SENDGRID_API_KEY);

(async () => {
  try {
    const msg = {
      to: TO_EMAIL,
      from: process.env.FROM_EMAIL,
      templateId: process.env.SENDGRID_TEMPLATE_ID,
      dynamicTemplateData: {
        title: 'Test — AGI Article Notification',
        excerpt: 'This is a short test excerpt to confirm template rendering and deliverability.',
        articleUrl: process.env.BASE_URL ? `${process.env.BASE_URL}/article/test` : 'https://agarwalglobalinvestments.com/article/test',
        coverUrl: process.env.BASE_URL ? `${process.env.BASE_URL}/assets/covers/opec.jpg` : 'https://agarwalglobalinvestments.com/assets/covers/opec.jpg',
        author: 'Shivam Agarwal',
        publishedAt: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        readTime: '3 min',
        section: 'Live Articles',
        siteUrl: process.env.BASE_URL || 'https://agarwalglobalinvestments.com',
        siteName: 'Agarwal Global Investments',
        preheader: 'Test preheader: deliverability and layout check.',
        year: new Date().getFullYear(),
        unsubscribe: (process.env.BASE_URL ? process.env.BASE_URL.replace(/\/$/, '') : 'https://agarwalglobalinvestments.com') + '/unsubscribe?email=' + encodeURIComponent(TO_EMAIL),
        unsubscribe_preferences: (process.env.BASE_URL ? process.env.BASE_URL.replace(/\/$/, '') : 'https://agarwalglobalinvestments.com') + '/unsubscribe-preferences?email=' + encodeURIComponent(TO_EMAIL)
      }
    };

    const result = await sgMail.send(msg);
    console.log('✅ Test email request sent to SendGrid (check inbox). SendGrid response status:', result[0]?.statusCode || 'unknown');
  } catch (err) {
    console.error('❌ Send failed. Full error:');
    // show helpful error info from SendGrid
    if (err.response && err.response.body) {
      console.error(JSON.stringify(err.response.body, null, 2));
    } else {
      console.error(err);
    }
    process.exit(1);
  }
})();
