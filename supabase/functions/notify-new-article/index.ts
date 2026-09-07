// supabase/functions/notify-new-article/index.ts
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") || "";
const SITE_ORIGIN = Deno.env.get("SITE_ORIGIN") || "https://agarwalglobalinvestments.com";
const FROM_EMAIL =
  Deno.env.get("NEWSLETTER_FROM_EMAIL") ||
  "AGI Updates <updates@agarwalglobalinvestments.com>";

type Payload = { title: string; slug: string; summary?: string };

Deno.serve(async (req) => {
  try {
    const auth = req.headers.get("authorization") || "";
    const cronSecret = req.headers.get("x-cron-secret");
    const allowed =
      auth.startsWith("Bearer ") ||
      (cronSecret && cronSecret === Deno.env.get("CRON_SECRET"));

    if (!allowed) return new Response("Unauthorized", { status: 401 });
    if (!RESEND_API_KEY) return new Response("RESEND_API_KEY missing", { status: 503 });

    const { title, slug, summary } = (await req.json()) as Payload;
    if (!title || !slug) return new Response("Missing title/slug", { status: 400 });

    const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
    const serviceKey =
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ||
      Deno.env.get("SUPABASE_ANON_KEY") ||
      "";
    if (!supabaseUrl || !serviceKey) {
      return new Response("Supabase credentials missing", { status: 503 });
    }

    const r = await fetch(`${supabaseUrl}/rest/v1/subscribers?select=email&is_active=eq.true`, {
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
      },
    });
    if (!r.ok) return new Response("Failed to fetch subscribers", { status: 500 });
    const list = (await r.json()) as { email: string }[];

    if (!Array.isArray(list) || list.length === 0) {
      return new Response("No subscribers", { status: 200 });
    }

    const url = `${SITE_ORIGIN}/article/${encodeURIComponent(slug)}`;
    const subject = `New from AGI: ${title}`;

    for (let i = 0; i < list.length; i += 50) {
      const chunk = list.slice(i, i + 50);
      const items = chunk.map((row) => {
        const email = row.email;
        const unsub = `${SITE_ORIGIN}/unsubscribe?email=${encodeURIComponent(email)}`;
        return {
          from: FROM_EMAIL,
          to: [email],
          subject,
          html: `
            <div style="font-family:system-ui,Segoe UI,Roboto,Arial">
              <h2>${title}</h2>
              ${summary ? `<p>${summary}</p>` : ""}
              <p><a href="${url}">Read it on Agarwal Global Investments →</a></p>
              <hr/>
              <p style="color:#6b7280;font-size:12px">
                You received this because you subscribed at ${SITE_ORIGIN}.
                <a href="${unsub}">Unsubscribe</a>.
              </p>
            </div>
          `,
        };
      });

      const send = await fetch("https://api.resend.com/emails/batch", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(items),
      });
      if (!send.ok) {
        const txt = await send.text();
        console.error("Resend error:", txt);
        return new Response("Email provider failed", { status: 502 });
      }
    }

    return new Response("ok", { status: 200 });
  } catch (e) {
    console.error(e);
    return new Response("Failed", { status: 500 });
  }
});
