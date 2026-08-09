from semantic_research_retrieval.production import expand_query, package_for_ask_agi

import pytest


class FakeKip:
    def __init__(self):
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        relevant = "AI" in query or "hyperscaler" in query or "rotation" in query
        return {
            "hits": [
                {
                    "document_id": "doc_b3733303faa7",
                    "title": "Global Investment Monitor: AI Capital, Policy Shifts and the Next Market Rotation",
                    "document_type": "agi_research",
                    "semantic_score": 0.82 if relevant else 0.25,
                    "keyword_score": 0.55 if relevant else 0.1,
                    "freshness": 0.95,
                    "confidence": 0.9,
                    "themes": ["AI capital expenditure", "market rotation"],
                    "snippet": "Sustained AI capital spending can broaden sector leadership.",
                }
            ]
        }


def test_expands_hyperscaler_language_without_exposing_terms_as_answer():
    expanded = expand_query("What happens if hyperscalers keep spending?")
    assert "AI infrastructure spending" in expanded
    assert "power demand" in expanded


def test_paraphrase_retrieves_and_reranks_agi_article():
    kip = FakeKip()
    result = package_for_ask_agi(
        "Could massive spending on AI infrastructure change which industries lead the market?",
        kip=kip,
    )
    assert result["AGI_HOUSE_VIEW"]["documents"][0]["document_id"] == "doc_b3733303faa7"
    assert result["answerability"]["status"] == "SUFFICIENT"
    assert result["query_expansion"]["applied"] is True
    assert len(kip.calls) > 1


def test_explicit_agi_question_prioritizes_proprietary_research():
    result = package_for_ask_agi("What did AGI write about AI spending?", kip=FakeKip())
    assert result["source_hierarchy"][0] == "AGI_PROPRIETARY_RESEARCH"


def test_multi_hop_keeps_current_confirmation_separate():
    current = {"matched": True, "sections": {"CURRENT_EVIDENCE": {"status": "LIVE"}}}
    result = package_for_ask_agi(
        "Which sectors benefit and where does AGI currently see confirmation?",
        kip=FakeKip(),
        current_intelligence=current,
        sector_intelligence={"sector": "Power", "confirmation": "positive"},
    )
    assert result["multi_hop"]["required"] is True
    assert result["multi_hop"]["stage_2"]["available"] is True
    assert result["CURRENT_EVIDENCE"] == {"status": "LIVE"}
    assert result["multi_hop"]["stage_2"]["sector_intelligence"]["sector"] == "Power"


def test_no_kip_fails_closed():
    result = package_for_ask_agi("What did AGI write?", kip=None)
    assert result["answerability"]["may_answer"] is False


@pytest.mark.parametrize(
    "question",
    [
        "What does AGI think AI spending means for sector rotation?",
        "Could hyperscaler capex benefit power and industrial names?",
        "How do policy shifts interact with AI investment?",
        "Which sectors may gain if data-center investment stays elevated?",
        "What was AGI's house view in the Global Investment Monitor?",
    ],
)
def test_acceptance_prompts_reach_semantic_retrieval_with_provenance(question):
    kip = FakeKip()
    result = package_for_ask_agi(question, kip=kip)
    assert kip.calls
    assert result["enabled"] is True
    assert result["AGI_HOUSE_VIEW"]["documents"][0]["document_id"] == "doc_b3733303faa7"
    assert result["SOURCES"][0]["title"].startswith("Global Investment Monitor")
    assert result["CURRENT_EVIDENCE"] == {}
    assert result["answerability"]["status"] in {"SUFFICIENT", "PARTIAL"}
