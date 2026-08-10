from app.ui.conversation_context import ConversationStore


ALIASES = {
    "icici bank": "ICICIBANK",
    "hdfc bank": "HDFCBANK",
    "infosys": "INFY",
}


def extract(question: str) -> list[str]:
    q = question.lower()
    return [ticker for name, ticker in ALIASES.items() if name in q]


def resolve(store: ConversationStore, question: str, cid: str = "test-thread", **kwargs):
    return store.resolve(
        question,
        conversation_id=cid,
        ticker=kwargs.get("ticker"),
        ticker_extractor=extract,
        reset=kwargs.get("reset", False),
    )


def test_company_comparison_and_focus_follow_ups_keep_context():
    store = ConversationStore()
    _, ticker, first = resolve(store, "Analyse ICICI Bank in detail")
    assert ticker == "ICICIBANK"
    assert first["active_entities"] == ["ICICIBANK"]

    effective, ticker, second = resolve(store, "Compare it with HDFC Bank")
    assert effective.startswith("Compare ICICIBANK vs HDFCBANK")
    assert ticker is None
    assert second["inherited_entities"] == ["ICICIBANK"]
    assert second["active_entities"] == ["ICICIBANK", "HDFCBANK"]

    effective, _, third = resolve(store, "Now show only valuation")
    assert effective == "Compare ICICIBANK vs HDFCBANK on valuation."
    assert third["research_focus"] == "valuation"
    assert third["context_used"] is True


def test_explicit_company_instead_overrides_memory():
    store = ConversationStore()
    resolve(store, "Analyse ICICI Bank")
    _, ticker, trace = resolve(store, "Analyse Infosys instead")
    assert ticker == "INFY"
    assert trace["active_entities"] == ["INFY"]
    assert trace["inherited_entities"] == []


def test_explicit_company_without_instead_also_replaces_old_comparison():
    store = ConversationStore()
    resolve(store, "Compare ICICI Bank with HDFC Bank")
    _, ticker, trace = resolve(store, "Analyse Infosys")
    assert ticker == "INFY"
    assert trace["active_entities"] == ["INFY"]


def test_unbound_pronoun_is_reported_not_invented():
    store = ConversationStore()
    effective, ticker, trace = resolve(store, "What about its valuation?")
    assert effective == "What about its valuation?"
    assert ticker is None
    assert trace["reference_status"] == "unresolved"
    assert trace["active_entities"] == []


def test_horizon_benchmark_depth_and_reset():
    store = ConversationStore()
    resolve(store, "Give a detailed 5D forecast for ICICI Bank versus Nifty")
    _, _, trace = resolve(store, "Now make it brief")
    assert trace["horizon"] == "5D"
    assert trace["benchmark"] == "NIFTY"
    assert trace["answer_depth"] == "brief"
    _, _, reset_trace = resolve(store, "What about it?", reset=True)
    assert reset_trace["reference_status"] == "unresolved"
    assert reset_trace["turn_count"] == 1


def test_conversations_are_isolated():
    store = ConversationStore()
    resolve(store, "Analyse ICICI Bank", cid="one")
    _, _, trace = resolve(store, "What about it?", cid="two")
    assert trace["reference_status"] == "unresolved"


def test_theme_and_time_window_survive_follow_up():
    store = ConversationStore()
    resolve(store, "What does AI capex mean for markets this week?")
    effective, _, trace = resolve(store, "Now show the risks")
    assert effective.startswith("Regarding the ai capex theme")
    assert trace["theme"] == "ai_capex"
    assert trace["time_window"] == "this week"


def test_answer_controls_persist_without_changing_entity():
    store = ConversationStore()
    resolve(store, "Analyse ICICI Bank")
    effective, ticker, trace = resolve(store, "Show sources only")
    assert effective.startswith("Regarding ICICIBANK")
    assert ticker == "ICICIBANK"
    assert trace["output_style"] == "sources"
    _, _, trace = resolve(store, "Now explain simply and make it brief")
    assert trace["audience"] == "general"
    assert trace["answer_depth"] == "brief"


def test_unresolved_reference_requests_clarification():
    store = ConversationStore()
    _, _, trace = resolve(store, "What about its valuation?")
    assert trace["clarification"]["required"] is True
    assert trace["clarification"]["reason"] == "missing_reference"


def test_ambiguous_hdfc_and_incomplete_comparison_request_clarification():
    store = ConversationStore()
    _, _, trace = resolve(store, "Analyse HDFC")
    assert trace["clarification"]["reason"] == "ambiguous_entity"
    assert len(trace["clarification"]["options"]) == 3
    _, _, trace = resolve(store, "Compare ICICI Bank", cid="compare")
    assert trace["clarification"]["reason"] == "missing_comparison_entity"


def test_action_question_does_not_block_recommendation_policy():
    """Buy/sell asks must reach recommendation_policy, not horizon clarification."""
    store = ConversationStore()
    _, _, trace = resolve(store, "Should I buy ICICI Bank?")
    assert trace["clarification"]["required"] is False
    _, _, trace = resolve(store, "Should I buy HDFC Bank tomorrow?")
    assert trace["clarification"]["required"] is False


def test_standalone_explain_and_concept_prompts_do_not_clarify():
    store = ConversationStore()
    for prompt in (
        "Explain Costco's membership model.",
        "Explain a SaaS business model.",
        "Explain network effects as a moat.",
        "Explain EBITDA",
        "Explain XYZ Quantum Robotics Pvt Ltd.",
    ):
        _, _, trace = resolve(store, prompt, cid=f"explain-{prompt[:12]}", reset=True)
        assert trace["clarification"]["required"] is False, prompt
        assert trace["reference_status"] == "resolved", prompt


def test_lexical_two_sided_compare_skips_missing_partner_clarification():
    store = ConversationStore()
    _, _, trace = resolve(store, "Compare DMart vs Reliance Retail.")
    assert trace["clarification"]["required"] is False
    _, _, trace = resolve(store, "Compare Indigo vs Air India business models.", cid="indigo")
    assert trace["clarification"]["required"] is False


def test_control_verb_follow_up_still_clarifies_without_thread():
    """Pronoun / incomplete follow-ups without context must still clarify."""
    store = ConversationStore()
    _, _, trace = resolve(store, "What about its valuation?")
    assert trace["clarification"]["reason"] == "missing_reference"
    _, _, trace = resolve(store, "Now show only valuation", cid="control-no-thread", reset=True)
    assert trace["clarification"]["reason"] == "missing_reference"
