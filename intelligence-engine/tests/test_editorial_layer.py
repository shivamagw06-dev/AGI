"""Editorial Intelligence Layer — rewrite-only soft-wire tests."""

from __future__ import annotations

from editorial.cache import EditorialCache
from editorial.glossary import PERMANENT_RULE, plain_english, simplify_jargon
from editorial.package import build_structured_package, contains_forbidden_payload, sanitize_structured
from editorial.production import health, package_for_ask_agi, quality_gates
from editorial.prompts import EDITORIAL_SYSTEM, build_prompt
from editorial.service import (
    EditorialService,
    generateQuickAnalysis,
    generateQuickSummary,
    generateRecommendation,
    strip_advice_language,
    unsupported_numeric_claims,
)
from editorial.template_fallback import render_template


SAMPLE = {
    "recommendation": "BUY",
    "conviction": "Medium",
    "business_quality": "Excellent",
    "financial_quality": "Stable",
    "valuation": "Attractive",
    "company": "HDFC Bank",
    "top_reasons": [
        "Strong deposit franchise",
        "Reasonable valuation",
        "Stable asset quality",
    ],
    "top_risks": ["NIM pressure"],
    "investment_horizon": "3-5 Years",
}


def test_health_and_gates():
    h = health()
    assert h["role"] == "writer_only"
    assert h["agib_is_brain"] is True
    assert h["never_generates_advice"] is True
    g = quality_gates()
    assert g["checks"]["never_reads_pdfs"] is True
    assert g["checks"]["never_recommends_actions"] is True
    assert g["checks"]["word_limits"]["quick_summary"] == 80
    assert g["checks"]["word_limits"]["quick_analysis"] == 150
    assert g["checks"]["word_limits"]["detailed_analysis"] == 400


def test_permanent_rule_in_prompts():
    assert "Never assume the reader understands finance" in PERMANENT_RULE
    assert PERMANENT_RULE in EDITORIAL_SYSTEM
    prompt = build_prompt(mode="quick_summary", structured=SAMPLE, question="Should I buy HDFC Bank?")
    assert "Never assume the reader understands finance" in prompt
    assert "gross npa" in prompt.lower()
    assert "never say" in prompt.lower()


def test_glossary_simplifies_banking_and_business_terms():
    text = simplify_jargon(
        "Strong deposit franchise with stable asset quality and NIM pressure; Gross NPA low; ROE solid."
    )
    lower = text.lower()
    assert "franchise" not in lower
    assert "business strength" in lower or "customer base" in lower
    assert "asset quality" not in lower
    assert "loan quality" in lower
    assert "nim" not in lower
    assert "lending profit" in lower or "deposit costs" in lower
    assert "gross npa" not in lower
    assert "roe" not in lower


def test_investment_language_replaced():
    out = plain_english("Hold. Upside remains. Entry point attractive. Avoid weak names.")
    lower = out.lower()
    assert "hold" not in lower.split()
    assert "upside" not in lower
    assert "entry point" not in lower
    assert "avoid" not in lower.split()
    assert (
        "balanced" in lower
        or "potential improvement" in lower
        or "monitoring" in lower
        or "risks outweigh" in lower
    )


def test_sanitize_drops_forbidden_document_fields():
    dirty = {
        **SAMPLE,
        "annual_report": "huge pdf text",
        "news": [{"title": "x"}],
        "financial_statements": {"revenue": 1},
        "transcript": "call notes",
    }
    assert contains_forbidden_payload(dirty) is True
    clean = sanitize_structured(dirty)
    assert "annual_report" not in clean
    assert clean["recommendation"] == "BUY"


def test_template_fallback_is_plain_english_rewrite():
    text = render_template("quick_summary", SAMPLE)
    assert "Recommendation:" not in text
    lower = text.lower()
    assert "you should" not in lower
    assert "target price" not in lower
    assert "franchise" not in lower
    assert "nim" not in lower
    assert "business strength" in lower or "deposit" in lower


def test_generate_quick_summary_never_emits_advice():
    out = generateQuickSummary(SAMPLE, question="Should I buy HDFC Bank?")
    assert out["enabled"] is True
    # Template fallback or live rewrite provider — both must stay rewrite-only.
    assert out["mode"] == "quick_summary"
    assert out["max_words"] == 80
    assert out["word_count"] <= 80
    assert "Recommendation:" not in (out.get("rewritten_summary") or "")
    assert "Recommendation:" not in (out.get("text") or "")
    lower = (out.get("rewritten_summary") or out.get("text") or "").lower()
    assert "you should" not in lower
    assert "target price" not in lower
    text = out.get("text") or out.get("rewritten_summary") or ""
    assert "HDFC" in text or "hdfc" in text.lower()


def test_generate_recommendation_is_plain_summary_not_action():
    out = generateRecommendation(SAMPLE, question="Should I buy HDFC Bank?")
    assert not (out.get("text") or "").startswith("Recommendation:")
    assert "Recommendation:" not in (out.get("rewritten_summary") or "")
    assert out["recommendation_from_agib_only"] is True
    assert out["never_recommends_actions"] is True


def test_generate_quick_analysis_word_limit():
    out = generateQuickAnalysis(SAMPLE, question="Quick view on HDFC Bank")
    assert out["mode"] == "quick_analysis"
    assert out["max_words"] == 150
    assert out["word_count"] <= 150
    assert "Recommendation:" not in out["text"]


def test_strip_advice_language():
    dirty = "Recommendation: SELL\nYou should exit the stock.\nDeposit franchise remains resilient."
    clean = strip_advice_language(dirty)
    assert "Recommendation:" not in clean
    assert "you should" not in clean.lower()
    assert "franchise" not in clean.lower()
    assert "business strength" in clean.lower() or "deposit" in clean.lower()


def test_service_strips_provider_advice(monkeypatch):
    class FakeProvider:
        name = "fake"

        def health(self):
            return {"provider": "fake", "available": True}

        async def rewrite(self, **kwargs):
            return {
                "text": (
                    "Recommendation: SELL\n"
                    "A position is only justified when NIM expands.\n"
                    "Strong deposit franchise supports resilience."
                ),
                "provider": "fake",
                "model": "fake",
                "usage": {},
                "latency_ms": 1,
                "prompt": "x",
            }

    service = EditorialService(provider=FakeProvider())
    out = service.generateQuickSummary(SAMPLE, question="Should I buy?")
    text = out.get("rewritten_summary") or ""
    assert "Recommendation:" not in text
    assert "SELL" not in text
    assert "only justified" not in text.lower()
    assert "franchise" not in text.lower()


def test_numeric_grounding_allows_figures_present_in_structured_evidence():
    unsupported = unsupported_numeric_claims(
        "Revenue was 4,820 crore and margin was 18.40%.",
        {"top_reasons": ["Revenue 4820 crore", "Margin 18.4%"]},
    )
    assert unsupported == []


def test_numeric_grounding_finds_invented_financial_figures():
    unsupported = unsupported_numeric_claims(
        "Revenue was 4,820 crore, up 18.4%, with margin of 22.6%.",
        {"company": "TCS", "top_reasons": ["Revenue remained stable"]},
    )
    assert unsupported == ["18.4", "22.6", "4820"]


def test_numeric_grounding_handles_zero_scientific_and_indian_grouping():
    unsupported = unsupported_numeric_claims(
        "Loss was 0 and exposure was 1e6 rupees.",
        {"loss": 0, "exposure": "10,00,000"},
    )
    assert unsupported == []
    assert unsupported_numeric_claims("Exposure was 1e6 rupees.", {}) == ["1000000"]


def test_service_rejects_invented_figures_and_uses_safe_fallback():
    class FabricatingProvider:
        name = "fabricating"

        def health(self):
            return {"provider": self.name, "available": True}

        async def rewrite(self, **kwargs):
            return {
                "text": "HDFC Bank revenue was 4,820 crore, up 18.4%.",
                "provider": self.name,
                "model": "fake",
                "usage": {},
                "latency_ms": 1,
            }

    service = EditorialService(provider=FabricatingProvider())
    out = service.generateQuickSummary(
        SAMPLE,
        question="Summarise HDFC Bank without inventing figures",
    )
    assert out["fallback"] is True
    assert out["provider"] == "template_fallback"
    assert out["provider_output_rejected"] is True
    assert out["numeric_grounding"]["ok"] is False
    assert out["numeric_grounding"]["unsupported"] == ["18.4", "4820"]
    assert "4,820" not in out["text"] and "18.4%" not in out["text"]


def test_cache_identical_summary_requests():
    cache = EditorialCache(ttl_seconds=60)
    key = cache.make_key("quick_summary", SAMPLE, "Should I buy HDFC Bank?")
    cache.set(key, {"text": "cached", "provider": "gemini"})
    assert cache.get(key)["text"] == "cached"


def test_package_for_ask_agi_soft_wire_rewrite_only():
    ac = {
        "enabled": True,
        "house_label": "Constructive",
        "bull": ["Strong deposit franchise"],
        "risks": ["NIM pressure"],
        "institutional_answer": {
            "enabled": True,
            "is_recommendation_query": True,
            "recommendation": "Buy",
            "conviction": "Medium Conviction",
            "reason": "Strong deposit franchise and reasonable valuation.",
            "risk": "NIM pressure",
            "horizon": "Medium Term",
        },
    }
    out = package_for_ask_agi(
        query="Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        answer_construction=ac,
        company="HDFC Bank",
    )
    assert out["enabled"] is True
    assert out["never_generates_advice"] is True
    assert out["never_recommends_actions"] is True
    assert out["executive"]
    assert out["structured_intelligence"]["recommendation"] in {"Buy", "BUY"}
    assert out["rewritten_summary"]
    assert "Recommendation:" not in out["rewritten_summary"]
    assert "Recommendation:" not in (out["executive"] or "")
    assert not (out["executive"] or "").lower().startswith("recommendation")
    assert "franchise" not in (out["executive"] or "").lower()
    assert "nim" not in (out["executive"] or "").lower()


def test_build_structured_package_from_agib_outputs():
    structured = build_structured_package(
        question="Should I buy HDFC Bank?",
        institutional_answer={
            "enabled": True,
            "recommendation": "Buy",
            "conviction": "Medium Conviction",
            "reason": "Strong deposit franchise",
            "risk": "NIM pressure",
            "horizon": "3-5 Years",
        },
        company="HDFC Bank",
        ticker="HDFCBANK",
    )
    assert structured["recommendation"] == "Buy"
    assert structured["top_reasons"] == ["Strong deposit franchise"]
