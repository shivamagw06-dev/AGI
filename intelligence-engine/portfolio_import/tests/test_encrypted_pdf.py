"""The encrypted-PDF path, exercised against real PDFs rather than mocks.

A CAS is password-protected, so the decryption gate is the part of this whole
feature a client actually touches first. These build genuine PDFs in memory
with pypdf and run them through the real reader.
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from portfolio_import import extract
from portfolio_import.extract import CasError

try:
    from pypdf import PdfWriter
    HAVE_PYPDF = True
except Exception:  # pragma: no cover
    HAVE_PYPDF = False


def make_pdf(*, password: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    if password:
        writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@unittest.skipUnless(HAVE_PYPDF, "pypdf not installed")
class EncryptedPdf(unittest.TestCase):
    def test_an_encrypted_pdf_without_a_password_is_refused(self):
        with self.assertRaises(CasError) as ctx:
            extract.extract(make_pdf(password="SECRET123"))
        self.assertEqual(ctx.exception.code, "password_required")

    def test_a_wrong_password_is_reported_without_echoing_it(self):
        attempted = "WRONGPASSWORD9"
        with self.assertRaises(CasError) as ctx:
            extract.extract(make_pdf(password="SECRET123"), password=attempted)
        self.assertEqual(ctx.exception.code, "wrong_password")
        self.assertNotIn(attempted, str(ctx.exception))
        self.assertNotIn("SECRET123", str(ctx.exception))

    def test_the_correct_password_gets_past_decryption(self):
        """A blank page then fails on text, which proves decryption succeeded."""
        with self.assertRaises(CasError) as ctx:
            extract.extract(make_pdf(password="SECRET123"), password="SECRET123")
        self.assertEqual(ctx.exception.code, "no_text_extracted")

    def test_an_unencrypted_pdf_needs_no_password(self):
        with self.assertRaises(CasError) as ctx:
            extract.extract(make_pdf())
        # Reaches text extraction rather than stopping at a password gate.
        self.assertEqual(ctx.exception.code, "no_text_extracted")

    def test_a_fingerprint_is_taken_from_the_bytes_not_the_content(self):
        one = make_pdf(password="SECRET123")
        self.assertEqual(extract.fingerprint_bytes(one),
                         extract.fingerprint_bytes(one))
        self.assertNotEqual(extract.fingerprint_bytes(one),
                            extract.fingerprint_bytes(make_pdf()))

    def test_nothing_is_written_to_disk(self):
        """Extraction is in memory; there is no temp file to forget to delete."""
        import inspect
        source = inspect.getsource(extract)
        for forbidden in ("open(", "NamedTemporaryFile", "mkstemp", "Path("):
            self.assertNotIn(forbidden, source,
                             f"{forbidden} suggests the PDF touches disk")


if __name__ == "__main__":
    unittest.main()
