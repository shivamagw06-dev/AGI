import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import useResearchNotesPreview from '@/hooks/useResearchNotesPreview';
import { formatTimeAgo } from '@/lib/articleUtils';

export default function ResearchNotesPreview() {
  const { notes, loading } = useResearchNotesPreview();

  return (
    <section className="py-8 border-b border-[#dddddd]">
      <div className="flex items-end justify-between mb-5 pb-3 border-b border-[#eeeeee]">
        <div>
          <h2 className="text-lg font-bold text-[#111111]">Latest Research Notes</h2>
          <p className="text-xs text-[#767676] mt-1">Short-form observations from the AGI research desk</p>
        </div>
        <Link to="/sections/research-notes" className="text-xs font-bold text-[#111111] hover:text-[#ff6600] shrink-0">
          View notes →
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((item) => <div key={item} className="h-40 bg-[#f4f4f4] animate-pulse" />)}
        </div>
      ) : notes.length ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {notes.map((note) => (
            <Link
              key={note.id}
              to="/sections/research-notes"
              className="group border border-[#dddddd] p-5 hover:border-[#999999] transition-colors"
            >
              <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#ff6600]">
                <FileText className="w-3.5 h-3.5" />
                Research note
              </div>
              <h3 className="mt-4 text-base font-bold leading-snug text-[#111111] group-hover:underline decoration-[#ff6600] underline-offset-2 line-clamp-2">
                {note.title}
              </h3>
              {note.summary && <p className="mt-2 text-xs leading-relaxed text-[#555555] line-clamp-3">{note.summary}</p>}
              <div className="mt-4 flex items-center justify-between gap-3 text-[10px] text-[#767676]">
                <span>{formatTimeAgo(note.published_at || note.created_at)}</span>
                {note.tags?.[0] && <span className="truncate">{note.tags[0]}</span>}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[#767676]">Research notes published from the CMS will appear here.</p>
      )}
    </section>
  );
}
