"""Getting text out of a CAS PDF, without keeping anything we were given.

Three rules this module exists to enforce, because they are easy to state and
easy to violate accidentally:

* The password is used and dropped. It is never written to a table, a log, a
  temp file, or an exception message. A traceback that quotes the password
  turns an error report into a credential leak, so failures here name the
  failure and not the input.
* Extraction is in memory. The bytes arrive, the text comes out, and nothing
  touches disk. There is no temp file to forget to delete.
* Nothing here writes to the warehouse. Parsing produces a result for a human
  to confirm; the caller decides whether it ever becomes a holding.

A CAS is a client's entire financial position in one file. It deserves to be
handled as though it were a password, because for this purpose it is worth
more than one.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Beyond this a file is not a statement, it is a denial-of-service. NSDL CAS
# for a large portfolio runs to a few hundred KB; ten megabytes is generous.
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 400

NSDL = "NSDL"
CDSL = "CDSL"
CAMS_KFINTECH = "CAMS_KFINTECH"
UNKNOWN = "UNKNOWN"


class CasError(Exception):
    """A failure that is safe to show a client.

    Deliberately carries no fragment of the document or the password. The
    caller renders `code`; the message is for a log that a support engineer
    reads, not for anything that quotes the input back.
    """

    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


@dataclass
class ExtractedText:
    provider: str
    pages: list[str] = field(default_factory=list)
    page_count: int = 0
    encrypted: bool = False
    # Identifies the statement, not its contents. Two uploads of the same file
    # produce the same value, which is what makes a re-import idempotent -
    # and it is a digest, so it cannot be turned back into the document.
    fingerprint: str = ""

    @property
    def text(self) -> str:
        return "\n".join(self.pages)


def fingerprint_bytes(data: bytes) -> str:
    """A stable id for a statement that retains none of it."""
    return hashlib.sha256(data).hexdigest()


# Provider markers, checked against extracted text rather than the filename.
# A filename is client-supplied and means nothing.
_PROVIDER_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (NSDL, ("NATIONAL SECURITIES DEPOSITORY", "NSDL CONSOLIDATED ACCOUNT",
            "NSDL DEMAT ACCOUNT")),
    (CDSL, ("CENTRAL DEPOSITORY SERVICES", "CDSL CONSOLIDATED ACCOUNT",
            "CDSL DEMAT ACCOUNT")),
    (CAMS_KFINTECH, ("CAMS", "KFINTECH", "KARVY FINTECH",
                     "CONSOLIDATED ACCOUNT STATEMENT - MUTUAL FUND")),
)


def detect_provider(text: str) -> str:
    upper = (text or "").upper()
    # Depositories first: an NSDL CAS also mentions CAMS in its mutual fund
    # section, so matching CAMS first would misfile every NSDL statement.
    for provider, markers in _PROVIDER_MARKERS:
        if any(marker in upper for marker in markers):
            return provider
    return UNKNOWN


def extract(data: bytes, *, password: Optional[str] = None) -> ExtractedText:
    """Decrypt if needed and pull text, in memory.

    `password` is consumed here and must not be stored by the caller. It is
    never included in any exception raised from this function.
    """
    if not data:
        raise CasError("empty_file")
    if len(data) > MAX_PDF_BYTES:
        raise CasError("file_too_large")
    if not data.startswith(b"%PDF"):
        raise CasError("not_a_pdf")

    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - dependency presence
        raise CasError("pdf_reader_unavailable", str(exc)) from None

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        # The underlying message can quote file internals; do not propagate it.
        raise CasError("unreadable_pdf") from None

    encrypted = bool(getattr(reader, "is_encrypted", False))
    if encrypted:
        if not password:
            raise CasError("password_required")
        try:
            opened = reader.decrypt(password)
        except Exception:
            raise CasError("decrypt_failed") from None
        if not opened:
            # Wrong password. Say so without echoing what was tried.
            raise CasError("wrong_password")

    page_count = len(reader.pages)
    if page_count > MAX_PAGES:
        raise CasError("too_many_pages")

    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            # One unreadable page should not lose the statement; the parser
            # reports coverage and the client sees what was found.
            pages.append("")

    joined = "\n".join(pages)
    if not joined.strip():
        raise CasError("no_text_extracted")

    return ExtractedText(
        provider=detect_provider(joined),
        pages=pages,
        page_count=page_count,
        encrypted=encrypted,
        fingerprint=fingerprint_bytes(data),
    )


_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_ACCOUNT_RE = re.compile(r"\b(?:IN)?[0-9]{8,16}\b")


def redact(text: str) -> str:
    """Mask identifiers before anything reaches a log or an error report.

    Parsing failures are worth diagnosing, and the natural way to diagnose them
    is to log the line that failed. A CAS line carries a PAN and a demat
    account number, so the natural way is the wrong way.
    """
    out = _PAN_RE.sub("*****PAN*****", text or "")
    return _ACCOUNT_RE.sub(lambda m: m.group(0)[:2] + "*" * (len(m.group(0)) - 6) + m.group(0)[-4:], out)
