/**
 * What a manager wrote about itself, from a document someone pasted in.
 *
 * Every line is the filer's own sentence. Nothing here is a summary, because a
 * summary of a filing cannot be checked against the filing by looking at it,
 * and the whole reason this section is publishable is that the reader sees the
 * evidence rather than a claim about the evidence.
 *
 * Three deliberate absences.
 *
 * A step with nothing approved does not get a heading. An empty "Why did it
 * happen?" reads as "the document gave no reasons", which is false: the
 * reasons are in a review queue, and the queue is named at the bottom instead.
 *
 * A position the filer only tabulated is not listed. Berkshire disclosed Apple
 * in a table and wrote about it nowhere, so "Apple — no comment" would invent
 * a silence that is really an accounting boundary: an equity-method investee
 * gets discussed in the notes, a fair-value holding does not.
 *
 * Rendered in full on the manager's own page, where a reader has already
 * chosen this manager and came for the why. The index lists fifty managers and
 * links here instead; six of them have a document at all.
 *
 * The last two steps of the chain carry their reason. Catalysts and the
 * so-what are analysis across disclosures, no sentence states either, and
 * showing seven steps as though they were the whole chain is the thing that
 * line prevents.
 */
export default function ManagerSaid({ said }) {
  if (!said) return null;
  const documents = said.publications || [];
  const [document] = documents;
  // With one document the heading names it and repeating it on every sentence
  // is noise. With several, the heading cannot name them and a sentence with
  // no label is a sentence attributed to whichever is newest.
  const many = documents.length > 1;
  const holdings = (said.by_holding || []).filter((entry) => entry.commentary > 0);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#6f6f6f]">
          In its own words
        </div>
        {many ? (
          <span className="shrink-0 text-[11px] text-[#8a8a8a]" title={documents.map((entry) => entry.title).join(' · ')}>
            {documents.length} documents
          </span>
        ) : document ? (
          <span className="shrink-0 text-[11px] text-[#8a8a8a]" title={document.title}>
            {document.source_url ? (
              <a href={document.source_url} target="_blank" rel="noreferrer" className="underline decoration-[#d5d5d5] underline-offset-2 hover:text-[#ff8000]">{document.title}</a>
            ) : document.title}
          </span>
        ) : null}
      </div>

      {said.by_step?.length ? (
        <ul className="mt-2 space-y-2">
          {said.by_step.map((group) => (
            <li key={group.slot}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[11px] font-semibold text-[#444444]">{group.question}</span>
                <span className="shrink-0 text-[11px] tabular-nums text-[#767676]">{group.claims.length}</span>
              </div>
              {/* One sentence, in full to the width of the card. The count
                  beside the question says how many more there are; a second
                  truncated line would spend the space without adding a fact. */}
              <p className="mt-0.5 text-[12px] leading-[1.55] text-[#333333]">
                {group.claims[0].source_excerpt}
              </p>
              {/* Which document this sentence is from. Shown only when the
                  manager has more than one, because that is when an unlabelled
                  sentence is a wrong attribution rather than a redundant one. */}
              {many && group.claims[0].document ? (
                <p className="mt-0.5 text-[10.5px] text-[#8a8a8a]">
                  {group.claims[0].document.title}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {holdings.length ? (
        <div className="mt-3">
          <div className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#6f6f6f]">
            Positions it wrote about
          </div>
          <ul className="mt-1.5 space-y-1">
            {holdings.slice(0, 4).map((entry) => (
              <li key={entry.issuer} className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 truncate text-[12px] text-[#333333]">{entry.issuer}</span>
                <span className="shrink-0 text-[11px] tabular-nums text-[#767676]">{entry.commentary}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Named rather than hidden. The interesting sentences about a position
          are usually causes, and causes are cue-matched, so they wait. */}
      {said.awaiting_review?.length ? (
        <div className="mt-2.5 text-[11px] leading-[1.6] text-[#8a8a8a]">
          {said.awaiting_review.reduce((total, step) => total + step.pending, 0)} more
          {' '}
          {said.awaiting_review.map((step) => step.question.replace(/\?$/, '').toLowerCase()).join(', ')}
          {' '}awaiting review before they are shown.
        </div>
      ) : null}

      {said.unreachable?.length ? (
        <details className="group mt-2">
          <summary className="cursor-pointer list-none text-[10px] font-extrabold uppercase tracking-[.16em] text-[#6f6f6f] hover:text-[#111111]">
            What the document cannot answer
          </summary>
          <ul className="mt-2 space-y-1.5 text-[11px] leading-[1.6] text-[#767676]">
            {said.unreachable.map((gap) => <li key={gap.slot}><span className="text-[#444444]">{gap.question}</span> {gap.reason}</li>)}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
