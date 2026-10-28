// supabase/functions/bright-service/index.ts
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") || "";
const FROM_EMAIL =
  Deno.env.get("NEWSLETTER_FROM_EMAIL") ||
  "AGI Updates <updates@agarwalglobalinvestments.com>";
const SITE_ORIGIN = Deno.env.get("SITE_ORIGIN") || "https://agarwalglobalinvestments.com";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  try {
    let email: string | null = null;

    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const body = await req.json().catch(() => ({}));
      email = (body?.email ?? null) as string | null;
    }
    if (!email) {
      const url = new URL(req.url);
      email = url.searchParams.get("email");
    }
    if (!email) return json({ error: "email required" }, 400);
    if (!RESEND_API_KEY) return json({ error: "RESEND_API_KEY missing" }, 503);

    const unsub = `${SITE_ORIGIN}/unsubscribe?email=${encodeURIComponent(email)}`;
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: email,
        subject: "Welcome to AGI Updates",
        html: `<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
          <h2>Welcome to AGI Updates</h2>
          <p>Thanks for subscribing. You'll get an email when we publish new research and market updates.</p>
          <p><a href="${SITE_ORIGIN}">Visit Agarwal Global Investments →</a></p>
          <p style="color:#6b7280;font-size:12px"><a href="${unsub}">Unsubscribe</a></p>
        </div>`,
      }),
    });

    if (!r.ok) {
      const t = await r.text();
      console.error("Resend error:", t);
      return json({ error: "email provider failed" }, 502);
    }

    return json({ ok: true, message: `Hello ${email}!` });
  } catch (e) {
    console.error(e);
    return json({ error: "internal error" }, 500);
  }
});
