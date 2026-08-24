import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  DISCLOSURE, DISCLOSURE_VERSION, SEBI_REGISTRATION, STORAGE_KEY,
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
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        version: DISCLOSURE_VERSION,
        acknowledgedAt: new Date().toISOString(),
      }));
    } catch {
      // Private mode or a full quota. The notice was still shown and read;
      // failing to record that is not a reason to trap the user behind it.
    }
    setOpen(false);
    restoreFocusTo.current?.focus?.();
  }, []);

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

  // Never guessed. If the status has not been configured the notice says so
  // rather than implying a registration that may not exist, or denying one
  // that does.
  const registrationLine = SEBI_REGISTRATION === null
    ? 'AGI has not configured its regulatory status for display. Please contact us before relying on any content as regulated research or advice.'
    : SEBI_REGISTRATION.registered
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
          <p className="rd-ack">{DISCLOSURE.acknowledgement}</p>
          <button type="button" className="rd-accept" onClick={accept} ref={acceptRef}>
            I understand and agree
          </button>
        </div>
      </div>
    </div>
  );
}
