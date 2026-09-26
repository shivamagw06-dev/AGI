import { useState } from 'react';
import { previewNewsletter } from '@/lib/publishingApi';
import { Button } from '@/components/ui/button';

export default function NewsletterTemplates() {
  const [title, setTitle] = useState('India Banks: Credit Cycle Watch');
  const [body, setBody] = useState(
    'Deposit franchises remain resilient. NIM pressure is moderating. Asset quality is stable outside unsecured pockets. Watch RBI liquidity and loan growth prints next.',
  );
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');

  async function run() {
    setError('');
    try {
      const data = await previewNewsletter({
        title,
        body,
        slug: 'india-banks-credit-cycle-watch',
        excerpt: body.slice(0, 180),
        section: 'Macro Research',
      });
      setPreview(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Email Templates & Channel Packs</h1>
        <p className="text-sm text-slate-500 mt-1">Institutional newsletter preview + LinkedIn / X / Telegram packs.</p>
      </div>

      <input className="w-full border rounded-lg px-3 py-2" value={title} onChange={(e) => setTitle(e.target.value)} />
      <textarea className="w-full min-h-[120px] border rounded-lg px-3 py-2 text-sm" value={body} onChange={(e) => setBody(e.target.value)} />
      <Button className="bg-blue-700 hover:bg-blue-800" onClick={run}>Generate preview</Button>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {preview && (
        <div className="space-y-6">
          <div className="bg-white border rounded-xl overflow-hidden">
            <div className="px-4 py-2 border-b text-xs uppercase tracking-wide text-slate-500">Newsletter preview</div>
            <iframe title="newsletter-preview" className="w-full h-[520px] bg-slate-50" srcDoc={preview.html} />
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-white border rounded-xl p-4">
              <h3 className="font-semibold text-sm mb-2">LinkedIn (30s)</h3>
              <pre className="text-xs whitespace-pre-wrap text-slate-700">{preview.channels?.linkedin_post}</pre>
            </div>
            <div className="bg-white border rounded-xl p-4">
              <h3 className="font-semibold text-sm mb-2">Telegram (10 bullets)</h3>
              <pre className="text-xs whitespace-pre-wrap text-slate-700">{preview.channels?.telegram_summary}</pre>
            </div>
            <div className="bg-white border rounded-xl p-4">
              <h3 className="font-semibold text-sm mb-2">X / Twitter thread</h3>
              <pre className="text-xs whitespace-pre-wrap text-slate-700">{(preview.channels?.twitter_thread || []).join('\n\n')}</pre>
            </div>
            <div className="bg-white border rounded-xl p-4">
              <h3 className="font-semibold text-sm mb-2">SEO / social preview</h3>
              <p className="text-sm font-medium">{preview.channels?.seo_title}</p>
              <p className="text-xs text-slate-600 mt-2">{preview.channels?.seo_meta_description}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
