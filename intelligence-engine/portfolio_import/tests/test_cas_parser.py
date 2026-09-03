"""Reading a CAS, and refusing to guess when it cannot be read."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from portfolio_import import cas_parser, extract
from portfolio_import.extract import CAMS_KFINTECH, CDSL, NSDL, CasError, ExtractedText
from portfolio_import.tests import fixtures


def as_extracted(text: str, provider: str | None = None) -> ExtractedText:
    return ExtractedText(
        provider=provider or extract.detect_provider(text),
        pages=[text], page_count=1, encrypted=False, fingerprint="f" * 64)


class ProviderDetection(unittest.TestCase):
    def test_each_provider_is_recognised(self):
        self.assertEqual(extract.detect_provider(fixtures.NSDL_TEXT), NSDL)
        self.assertEqual(extract.detect_provider(fixtures.CDSL_TEXT), CDSL)
        self.assertEqual(extract.detect_provider(fixtures.CAMS_TEXT), CAMS_KFINTECH)

    def test_an_nsdl_statement_mentioning_cams_is_still_nsdl(self):
        """NSDL statements carry a mutual fund section; order of checks matters."""
        text = fixtures.NSDL_TEXT + "\nCAMS serviced folios follow\n"
        self.assertEqual(extract.detect_provider(text), NSDL)

    def test_an_unknown_document_is_not_guessed(self):
        self.assertEqual(extract.detect_provider("Some other statement"), "UNKNOWN")


class DematParsing(unittest.TestCase):
    def test_holdings_are_read_with_isin_quantity_and_account(self):
        result = cas_parser.parse(as_extracted(fixtures.NSDL_TEXT))
        by_isin = {h.isin: h for h in result.holdings}
        self.assertIn("INE002A01018", by_isin)
        self.assertAlmostEqual(by_isin["INE002A01018"].quantity, 25)
        self.assertEqual(by_isin["INE002A01018"].account_ref, "IN30001234567890")
        self.assertIn("Reliance", by_isin["INE002A01018"].name)

    def test_the_statement_date_is_read(self):
        result = cas_parser.parse(as_extracted(fixtures.NSDL_TEXT))
        self.assertIsNotNone(result.statement_date)
        self.assertIn("2026", result.statement_date)

    def test_an_inf_isin_is_a_mutual_fund_not_an_equity(self):
        """The ISIN prefix decides; a scheme named 'Flexi Cap' is not equity."""
        result = cas_parser.parse(as_extracted(fixtures.NSDL_TEXT))
        fund = [h for h in result.holdings if h.isin == "INF090I01239"]
        self.assertEqual(len(fund), 1)
        self.assertEqual(fund[0].asset_type, "MUTUAL_FUND")

    def test_accounts_are_collected(self):
        result = cas_parser.parse(as_extracted(fixtures.NSDL_TEXT))
        self.assertEqual(result.accounts, ["IN30001234567890"])


class MutualFundParsing(unittest.TestCase):
    def test_cams_folios_are_read_without_an_isin(self):
        result = cas_parser.parse(as_extracted(fixtures.CAMS_TEXT))
        self.assertEqual(len(result.holdings), 2)
        first = result.holdings[0]
        self.assertEqual(first.asset_type, "MUTUAL_FUND")
        self.assertEqual(first.folio, "91234567/22")
        self.assertAlmostEqual(first.quantity, 1250.5)


class Failures(unittest.TestCase):
    def test_an_isin_line_that_does_not_parse_becomes_unmatched(self):
        """A wrong pattern must show as a gap, not silently shrink a portfolio."""
        result = cas_parser.parse(as_extracted(fixtures.MALFORMED_TEXT))
        self.assertTrue(result.unmatched)
        self.assertTrue(any(u["reason"].startswith("isin_line") or u["reason"] == "no_quantity"
                            for u in result.unmatched))

    def test_a_statement_with_no_holdings_warns_and_imports_nothing(self):
        result = cas_parser.parse(as_extracted(fixtures.EMPTY_TEXT))
        self.assertEqual(result.holdings, [])
        self.assertTrue(any("Nothing will be imported" in w for w in result.warnings))

    def test_excerpts_are_redacted(self):
        """A CAS line carries a PAN and an account number."""
        result = cas_parser.parse(as_extracted(fixtures.MALFORMED_TEXT))
        for row in result.unmatched:
            self.assertNotIn("ABCDE1234F", row.get("excerpt", ""))

    def test_redaction_masks_pan_and_account(self):
        masked = extract.redact("PAN: ABCDE1234F account IN30001234567890")
        self.assertNotIn("ABCDE1234F", masked)
        self.assertNotIn("IN30001234567890", masked)
        self.assertIn("7890", masked)  # last four kept so a client can recognise it


class PdfGuards(unittest.TestCase):
    def test_a_non_pdf_is_refused(self):
        with self.assertRaises(CasError) as ctx:
            extract.extract(b"not a pdf at all")
        self.assertEqual(ctx.exception.code, "not_a_pdf")

    def test_an_empty_file_is_refused(self):
        with self.assertRaises(CasError) as ctx:
            extract.extract(b"")
        self.assertEqual(ctx.exception.code, "empty_file")

    def test_an_oversized_file_is_refused_before_parsing(self):
        big = b"%PDF" + b"0" * (extract.MAX_PDF_BYTES + 1)
        with self.assertRaises(CasError) as ctx:
            extract.extract(big)
        self.assertEqual(ctx.exception.code, "file_too_large")

    def test_the_password_never_appears_in_an_error(self):
        secret = "SUPERSECRETPAN123"
        try:
            extract.extract(b"%PDF-1.4 broken", password=secret)
        except CasError as exc:
            self.assertNotIn(secret, str(exc))
            self.assertNotIn(secret, repr(exc))
        else:
            self.fail("expected a CasError")

    def test_a_fingerprint_is_stable_and_not_reversible(self):
        one = extract.fingerprint_bytes(b"%PDF-1.4 hello")
        two = extract.fingerprint_bytes(b"%PDF-1.4 hello")
        self.assertEqual(one, two)
        self.assertEqual(len(one), 64)
        self.assertNotIn("hello", one)


if __name__ == "__main__":
    unittest.main()
