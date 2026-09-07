"""Company Thesis Intelligence — completeness, specificity and uniqueness."""

from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Spec thresholds: unrelated companies <60%, same-industry peers <70%.
UNRELATED_MAX = 0.60
SAME_INDUSTRY_MAX = 0.70

GOLDEN_THESIS = (
    "AXISBANK", "HDFCBANK", "ICICIBANK", "SBIN",
    "INFY", "TCS", "WIPRO", "HCLTECH",
    "RELIANCE", "ONGC", "BPCL", "IOC",
    "ULTRACEMCO", "JSWSTEEL", "TITAN", "DMART",
    "APOLLOHOSP", "SUNPHARMA", "BHARTIARTL", "NTPC",
)

BANKS = ("AXISBANK", "HDFCBANK", "ICICIBANK", "SBIN")
IT = ("INFY", "TCS", "WIPRO", "HCLTECH")


@pytest.fixture(autouse=True)
def _store(monkeypatch):
    monkeypatch.setenv("VALUATION_CONSENSUS_ROOT", str(ROOT / "data" / "valuation_consensus"))
    from company_identity.service import invalidate_cache as ci_invalidate
    from investment_intelligence.company_thesis import invalidate_cache

    ci_invalidate()
    invalidate_cache()
    yield
    invalidate_cache()


def _seeded() -> bool:
    from valuation_consensus.store import load_live

    return bool(load_live().get("rows"))


def _text(ticker: str) -> str:
    from investment_intelligence.company_thesis import thesis_narrative

    pack = thesis_narrative(ticker)
    assert pack, f"no thesis for {ticker}"
    return pack["summary"] + " " + " ".join(pack["why"])


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", folded.lower())


def test_every_golden_company_has_all_twelve_sections():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    from investment_intelligence.company_thesis import THESIS_SECTIONS, build_thesis

    for ticker in GOLDEN_THESIS:
        pack = build_thesis(ticker)
        assert pack.get("ok"), ticker
        for section in THESIS_SECTIONS:
            body = (pack["sections"].get(section) or "").strip()
            assert body, f"{ticker} missing {section}"
            assert len(body) > 25, f"{ticker} {section} too thin: {body!r}"


def test_thesis_names_the_company_and_carries_its_own_numbers():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    from investment_intelligence.company_thesis import build_thesis

    for ticker in GOLDEN_THESIS:
        pack = build_thesis(ticker)
        blob = " ".join(pack["sections"].values())
        first_token = _norm(pack["company_name"]).split()[0]
        assert first_token in _norm(blob), f"{ticker} thesis never names the company"
        assert re.search(r"\d", blob), f"{ticker} thesis carries no figures"


def test_same_industry_theses_are_distinguishable():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    for group in (BANKS, IT):
        texts = {t: _norm(_text(t)) for t in group}
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                ratio = SequenceMatcher(None, texts[a], texts[b]).ratio()
                assert ratio < SAME_INDUSTRY_MAX, f"{a} vs {b} similarity {ratio:.2f}"


def test_unrelated_companies_are_clearly_different():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    pairs = (("AXISBANK", "INFY"), ("RELIANCE", "TITAN"), ("NTPC", "SUNPHARMA"))
    for a, b in pairs:
        ratio = SequenceMatcher(None, _norm(_text(a)), _norm(_text(b))).ratio()
        assert ratio < UNRELATED_MAX, f"{a} vs {b} similarity {ratio:.2f}"


def test_risks_and_catalysts_are_company_level_not_industry_level():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    from investment_intelligence.company_thesis import build_thesis

    for ticker in BANKS:
        sections = build_thesis(ticker)["sections"]
        for key in ("key_risks", "key_catalysts"):
            body = sections[key]
            assert re.search(r"\d", body), f"{ticker} {key} has no company figure"
        # Distinct banks must not share an identical risk paragraph.
    risk_texts = {t: _norm(build_thesis(t)["sections"]["key_risks"]) for t in BANKS}
    assert len(set(risk_texts.values())) == len(BANKS), "banks share a risk paragraph"


def test_thesis_never_issues_a_recommendation():
    if not _seeded():
        pytest.skip("CapIQ master not seeded")
    from investment_intelligence.company_thesis import build_thesis

    banned = re.compile(r"\b(we recommend|you should buy|you should sell|rating\s*[:=]\s*buy)\b", re.I)
    for ticker in GOLDEN_THESIS:
        blob = " ".join(build_thesis(ticker)["sections"].values())
        assert not banned.search(blob), ticker
        assert "cheap" not in blob.lower() and "expensive" not in blob.lower(), ticker
