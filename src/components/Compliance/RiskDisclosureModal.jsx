import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  DISCLOSURE, DISCLOSURE_VERSION, SEBI_REGISTRATION, STORAGE_KEY, disclosureHash,
} from '@/lib/riskDisclosure';
import './riskDisclosure.css';

/**
 * Risk disclosure shown on a visitor's first arrival.
 *
 * Acknowledgement is stored against the disclosure version, so changing the
 * wording re-prompts everybody. An acknowledgement of text a user never saw is
 * worth nothing if it is ever examined, which is the only reason to keep this
 * record at all.
 *
 * Deliberately not a hard gate. The notice must be acknowledged to dismiss it,
 * but the page behind stays rendered: a modal that blanks the site punishes
 * anyone who arrives from search and does not make the disclosure any more
 * effective.
 */
function readAck() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.version === DISCLOSURE_VERSION ? parsed : null;
  } catch {
    return null;
  }
}

export default function RiskDisclosureModal() {
  const [open, setOpen] = useState(false);
  // Continue stays disabled until this is ticked. A button that dismisses on
  // one click records a dismissal; a tick records an acknowledgement.
  const [acknowledged, setAcknowledged] = useState(false);
  const dialogRef = useRef(null);
  const acceptRef = useRef(null);
  const restoreFocusTo = useRef(null);

  useEffect(() => {
    // Deferred so it never competes with first paint.
    const timer = setTimeout(() => {
      if (!readAck()) {
        restoreFocusTo.current = document.activeElement;
        setOpen(true);
      }
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  const accept = useCallback(() => {
    if (!acknowledged) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        version: DISCLOSURE_VERSION,
        // Which words were on screen, not merely which version number. If this
        // is ever examined, "they accepted v2026-08-2" is worth much less than
        // a fingerprint of the text itself.
        disclosureHash: disclosureHash(),
        acknowledgedAt: new Date().toISOString(),
        acknowledged: true,
      }));
    } catch {
      // Private mode or a full quota. The notice was still shown and read;
      // failing to record that is not a reason to trap the user behind it.
    }
    setOpen(false);
    restoreFocusTo.current?.focus?.();
  }, [acknowledged]);

  // Focus moves into the dialog, and stays there while it is open.
  useEffect(() => {
    if (!open) return undefined;
    acceptRef.current?.focus();
    const onKey = (event) => {
      if (event.key !== 'Tab') return;
      const focusable = dialogRef.current?.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  // No "not configured" branch. The owner has confirmed the position, and an
  // unanswered regulatory question on screen reads as an unfinished site while
  // telling the visitor nothing.
  const registrationLine = SEBI_REGISTRATION?.registered
      ? `AGI is registered with SEBI as a ${SEBI_REGISTRATION.type}${
          SEBI_REGISTRATION.number ? ` (registration number ${SEBI_REGISTRATION.number})` : ''
        }. Registration does not guarantee performance or assure returns.`
      : 'AGI is not registered with SEBI as a Research Analyst or Investment Adviser. '
        + 'Nothing on this website should be treated as regulated research or investment advice.';

  return (
    <div className="rd-scrim" role="presentation">
      <div
        className="rd-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rd-title"
        ref={dialogRef}
      >
        <div className="rd-head">
          <h2 id="rd-title">{DISCLOSURE.title}</h2>
        </div>

        <div className="rd-body">
          <p className="rd-intro">{DISCLOSURE.intro}</p>

          <section className="rd-section rd-reg">
            <h3>{DISCLOSURE.registrationHeading}</h3>
            <p>{registrationLine}</p>
          </section>

          {DISCLOSURE.sections.map((section) => (
            <section className="rd-section" key={section.heading}>
              <h3>{section.heading}</h3>
              <p>{section.body}</p>
            </section>
          ))}

          <section className="rd-section">
            <h3>Jurisdiction</h3>
            <p>{DISCLOSURE.jurisdiction}</p>
          </section>

          <p className="rd-links">
            Full <Link to="/terms">Terms of Service</Link> and{' '}
            <Link to="/privacy">Privacy Policy</Link>.
          </p>
        </div>

        <div className="rd-foot">
          <label className="rd-tick" htmlFor="rd-ack">
            <input
              id="rd-ack"
              type="checkbox"
              checked={acknowledged}
              onChange={(event) => setAcknowledged(event.target.checked)}
              ref={acceptRef}
            />
            <span>{DISCLOSURE.acknowledgement}</span>
          </label>
          <button
            type="button"
            className="rd-accept"
            onClick={accept}
            disabled={!acknowledged}
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
