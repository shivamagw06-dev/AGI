"""Bounded conversation context for finance follow-up questions.

This layer resolves references; it never creates research evidence or changes scores.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from app.ui.conversation_checkpoints import (
    CheckpointBackend,
    SupabaseConversationCheckpointBackend,
)


_FOLLOW_UP_RE = re.compile(
    r"\b(it|its|that company|this company|them|those companies|the first|the second|now|also)\b",
    re.I,
)
_CONTROL_ONLY_RE = re.compile(
    r"^(?:please\s+)?(?:make|show|give|rewrite|explain|format|summari[sz]e)\b",
    re.I,
)
_COMPARE_RE = re.compile(r"\b(compare|versus|vs\.?|relative to|against)\b", re.I)
_INSTEAD_RE = re.compile(r"\b(instead|switch to|change to|move to)\b", re.I)
_LEADING_AND_RE = re.compile(r"^\s*(?:and|what about)\b", re.I)
_FOCUS = {
    "valuation": re.compile(r"\b(valuation|fair value|cheap|expensive|multiple|price target)\b", re.I),
    "forecast": re.compile(r"\b(forecast|expect|outlook|probability|horizon)\b", re.I),
    "fundamentals": re.compile(r"\b(fundamental|quality|earnings|margin|cash flow)\b", re.I),
    "risk": re.compile(r"\b(risk|bear case|downside|concern)\b", re.I),
    "catalyst": re.compile(r"\b(catalyst|event|trigger)\b", re.I),
    "thesis_change": re.compile(r"\b(what changed|thesis change|strengthen|weaken)\b", re.I),
    "reliability": re.compile(r"\b(reliability|validated|accuracy|hit rate|rank ic)\b", re.I),
}
_HORIZON_RE = re.compile(r"\b(5m|15m|30m|60m|1d|5d|20d|3m|6m|12m|one day|five days?|twenty days?)\b", re.I)
_BENCHMARK_RE = re.compile(r"\b(nifty\s*50|nifty|sensex|bank\s*nifty|sector(?:\s+index)?)\b", re.I)
_TIME_WINDOW_RE = re.compile(
    r"\b(today|yesterday|this week|last week|this month|last month|last \d+ (?:days?|weeks?|months?))\b",
    re.I,
)
_THEMES = {
    "ai_capex": re.compile(r"\b(ai (?:spending|capex|investment)|data[ -]?cent(?:er|re)|hyperscaler)\b", re.I),
    "interest_rates": re.compile(r"\b(interest rates?|rate cuts?|monetary policy|rbi policy)\b", re.I),
    "energy_transition": re.compile(r"\b(energy transition|renewables?|clean energy)\b", re.I),
    "credit_cycle": re.compile(r"\b(credit cycle|loan growth|asset quality)\b", re.I),
}

_MOVES = (
    ("GREETING", re.compile(r"^(hi|hello|hey|good (morning|afternoon|evening))[!. ]*$", re.I)),
    ("THANKS", re.compile(r"^(thanks|thank you|great|got it|okay thanks)[!. ]*$", re.I)),
    ("CAPABILITY_QUESTION", re.compile(r"\b(what can you do|how can you help|your capabilities)\b", re.I)),
    ("SIMPLIFY", re.compile(r"\b(explain (?:that )?(?:more )?simply|simple language|plain english)\b", re.I)),
    ("SHORTER", re.compile(r"^(make it )?(shorter|brief|summari[sz]e that)[!. ]*$", re.I)),
    ("CHALLENGE", re.compile(r"\b(i disagree|but what about|are you sure|why do you think)\b", re.I)),
    ("CORRECTION", re.compile(r"\b(that(?:'s| is) wrong|you are wrong|incorrect|correct that)\b", re.I)),
    ("CONTINUE", re.compile(r"^(continue|go on|and\?|why\?)[!. ]*$", re.I)),
)


@dataclass
class ConversationState:
    conversation_id: str
    primary_entity: str | None = None
    comparison_entities: list[str] = field(default_factory=list)
    research_focus: str | None = None
    horizon: str | None = None
    benchmark: str | None = None
    theme: str | None = None
    time_window: str | None = None
    answer_depth: str | None = None
    output_style: str | None = None
    audience: str | None = None
    previous_question: str | None = None
    previous_answer_summary: str | None = None
    previous_research_artifact_ref: str | None = None
    conversation_move: str | None = None
    research_intent: str | None = None
    research_execution: str | None = None
    checkpoint_restored: bool = False
    turn_count: int = 0
    updated_at: float = field(default_factory=time.time)

    def entities(self) -> list[str]:
        out: list[str] = []
        for value in [self.primary_entity, *self.comparison_entities]:
            if value and value not in out:
                out.append(value)
        return out


class ConversationStore:
    """TTL-bounded memory with optional durable checkpoints; safe across request threads."""

    def __init__(
        self, *, ttl_seconds: int = 6 * 60 * 60, max_entries: int = 5_000,
        checkpoint_backend: CheckpointBackend | None = None,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._states: dict[str, ConversationState] = {}
        self._lock = threading.RLock()
        self._checkpoint = checkpoint_backend or SupabaseConversationCheckpointBackend.from_env()

    @staticmethod
    def normalize_id(value: str | None) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:80]
        return clean or str(uuid.uuid4())

    def reset(self, conversation_id: str) -> None:
        with self._lock:
            self._states.pop(conversation_id, None)
        self._checkpoint.delete(conversation_id)

    @staticmethod
    def _restore(conversation_id: str, payload: dict[str, Any]) -> ConversationState:
        allowed = set(ConversationState.__dataclass_fields__)
        values = {key: value for key, value in payload.items() if key in allowed}
        values["conversation_id"] = conversation_id
        values["checkpoint_restored"] = True
        return ConversationState(**values)

    @staticmethod
    def _checkpoint_payload(state: ConversationState) -> dict[str, Any]:
        # Explicit allow-list is a privacy boundary: no evidence or prompts can enter checkpoints.
        return {
            "primary_entity": state.primary_entity,
            "comparison_entities": state.comparison_entities[:8],
            "research_focus": state.research_focus,
            "horizon": state.horizon,
            "benchmark": state.benchmark,
            "theme": state.theme,
            "time_window": state.time_window,
            "answer_depth": state.answer_depth,
            "output_style": state.output_style,
            "audience": state.audience,
            "previous_question": (state.previous_question or "")[:500] or None,
            "previous_answer_summary": (state.previous_answer_summary or "")[:2000] or None,
            "previous_research_artifact_ref": (state.previous_research_artifact_ref or "")[:160] or None,
            "conversation_move": state.conversation_move,
            "research_intent": state.research_intent,
            "research_execution": state.research_execution,
            "turn_count": state.turn_count,
            "updated_at": state.updated_at,
        }

    def _persist(self, state: ConversationState) -> None:
        self._checkpoint.save(state.conversation_id, self._checkpoint_payload(state))

    def get(self, conversation_id: str) -> ConversationState:
        now = time.time()
        with self._lock:
            stale = [key for key, state in self._states.items() if now - state.updated_at > self.ttl_seconds]
            for key in stale:
                self._states.pop(key, None)
            state = self._states.get(conversation_id)
            if state is not None:
                return state
        # Never hold the process-wide state lock during an external checkpoint read.
        saved = self._checkpoint.load(conversation_id)
        candidate = self._restore(conversation_id, saved) if saved else ConversationState(conversation_id=conversation_id)
        with self._lock:
            state = self._states.setdefault(conversation_id, candidate)
            if len(self._states) > self.max_entries:
                oldest = min(self._states, key=lambda key: self._states[key].updated_at)
                if oldest != conversation_id:
                    self._states.pop(oldest, None)
            return state

    @staticmethod
    def _conversation_move(question: str, *, is_follow_up: bool, has_context: bool) -> tuple[str, float]:
        for move, pattern in _MOVES:
            if pattern.search(question or ""):
                return move, 0.98
        if is_follow_up and has_context:
            return "FOLLOW_UP", 0.92
        return "NEW_RESEARCH", 0.9

    @staticmethod
    def _research_intent(question: str) -> str:
        focus = ConversationStore._detect_focus(question)
        if focus:
            return focus.upper()
        if _COMPARE_RE.search(question or ""):
            return "PEER_COMPARISON"
        if re.search(r"\b(market|nifty|sensex|macro|economy|rbi)\b", question or "", re.I):
            return "MARKET"
        return "COMPANY_RESEARCH"

    def record_answer(
        self, conversation_id: str, *, question: str, answer_summary: str | None,
        research_artifact_ref: str | None = None,
    ) -> None:
        state = self.get(self.normalize_id(conversation_id))
        state.previous_question = (question or "")[:500] or None
        state.previous_answer_summary = (answer_summary or "")[:2000] or None
        state.previous_research_artifact_ref = (research_artifact_ref or "")[:160] or None
        state.updated_at = time.time()
        self._persist(state)

    def resolve(
        self,
        question: str,
        *,
        conversation_id: str | None,
        ticker: str | None,
        ticker_extractor: Callable[[str], list[str]],
        reset: bool = False,
    ) -> tuple[str, str | None, dict]:
        cid = self.normalize_id(conversation_id)
        if reset:
            self.reset(cid)
        state = self.get(cid)
        original = (question or "").strip()
        explicit = list(dict.fromkeys(ticker_extractor(original)))
        if ticker:
            explicit = [ticker.strip().upper(), *[x for x in explicit if x != ticker.strip().upper()]]

        inherited: list[str] = []
        effective = original
        is_compare = bool(_COMPARE_RE.search(original))
        is_follow_up = bool(
            _FOLLOW_UP_RE.search(original)
            or _CONTROL_ONLY_RE.search(original)
            or _LEADING_AND_RE.search(original)
        )
        prior_entities = state.entities()
        conversation_move, router_confidence = self._conversation_move(
            original, is_follow_up=is_follow_up, has_context=bool(prior_entities or state.theme),
        )
        research_intent = "NONE" if conversation_move in {
            "GREETING", "THANKS", "CAPABILITY_QUESTION", "SIMPLIFY", "SHORTER",
        } else self._research_intent(original)
        if conversation_move in {"GREETING", "THANKS", "CAPABILITY_QUESTION"}:
            research_execution = "SKIP"
        elif conversation_move in {"SIMPLIFY", "SHORTER"}:
            research_execution = "REUSE_PREVIOUS"
        elif conversation_move in {"FOLLOW_UP", "CHALLENGE", "CORRECTION", "CONTINUE"}:
            research_execution = "INCREMENTAL_RETRIEVAL"
        else:
            research_execution = "FULL_RESEARCH"
        contextual_move = conversation_move in {"FOLLOW_UP", "CHALLENGE", "CORRECTION", "CONTINUE"}

        if explicit:
            if _INSTEAD_RE.search(original) and not is_compare:
                state.primary_entity = explicit[0]
                state.comparison_entities = explicit[1:]
            elif (is_compare or _LEADING_AND_RE.search(original)) and len(explicit) == 1 and state.primary_entity and explicit[0] != state.primary_entity:
                inherited = [state.primary_entity]
                state.comparison_entities = [state.primary_entity, explicit[0]]
                effective = f"Compare {state.primary_entity} vs {explicit[0]}. {original}"
            else:
                state.primary_entity = explicit[0]
                state.comparison_entities = explicit[:] if len(explicit) > 1 else []
        elif (is_follow_up or contextual_move) and (prior_entities or state.theme):
            inherited = prior_entities[:]
            focus = self._detect_focus(original)
            if focus and prior_entities:
                if len(prior_entities) >= 2:
                    effective = f"Compare {prior_entities[0]} vs {prior_entities[1]} on {focus}."
                else:
                    effective = f"{focus.replace('_', ' ')} analysis for {prior_entities[0]}. {original}"
            elif prior_entities:
                effective = f"Regarding {', '.join(prior_entities)}: {original}"
            else:
                effective = f"Regarding the {state.theme.replace('_', ' ')} theme: {original}"

        focus = self._detect_focus(original)
        horizon_match = _HORIZON_RE.search(original)
        benchmark_match = _BENCHMARK_RE.search(original)
        time_window_match = _TIME_WINDOW_RE.search(original)
        theme = self._detect_theme(original)
        if focus:
            state.research_focus = focus
        if horizon_match:
            state.horizon = horizon_match.group(1).upper().replace("ONE DAY", "1D").replace("FIVE DAY", "5D").replace("TWENTY DAY", "20D")
        if benchmark_match:
            state.benchmark = benchmark_match.group(1).upper()
        if time_window_match:
            state.time_window = time_window_match.group(1).lower()
        if theme:
            state.theme = theme
        if re.search(r"\b(quick|brief|short)\b", original, re.I):
            state.answer_depth = "brief"
        elif re.search(r"\b(detailed|in detail|deep|full)\b", original, re.I):
            state.answer_depth = "detailed"
        if re.search(r"\b(sources? only|show (?:me )?(?:the )?sources?|provenance only)\b", original, re.I):
            state.output_style = "sources"
        elif re.search(r"\b(table|tabular)\b", original, re.I):
            state.output_style = "table"
        elif re.search(r"\b(bullets?|bullet points?)\b", original, re.I):
            state.output_style = "bullets"
        elif re.search(r"\b(normal format|standard format|reset format)\b", original, re.I):
            state.output_style = "standard"
        if re.search(r"\b(explain simply|simple language|beginner|plain english)\b", original, re.I):
            state.audience = "general"
        elif re.search(r"\b(for an analyst|institutional detail|technical language)\b", original, re.I):
            state.audience = "analyst"
        state.turn_count += 1
        state.conversation_move = conversation_move
        state.research_intent = research_intent
        state.research_execution = research_execution
        state.updated_at = time.time()
        self._persist(state)

        unresolved = bool((is_follow_up or contextual_move) and not prior_entities and not explicit)
        clarification = self._clarification(
            original,
            explicit=explicit,
            active_entities=state.entities(),
            is_compare=is_compare,
            unresolved_reference=unresolved,
            horizon=state.horizon,
        )
        trace = {
            "version": "finance-conversation-v1",
            "conversation_id": cid,
            "context_used": bool(inherited),
            "original_question": original,
            "effective_question": effective,
            "explicit_entities": explicit,
            "inherited_entities": inherited,
            "active_entities": state.entities(),
            "research_focus": state.research_focus,
            "horizon": state.horizon,
            "benchmark": state.benchmark,
            "theme": state.theme,
            "time_window": state.time_window,
            "answer_depth": state.answer_depth,
            "output_style": state.output_style,
            "audience": state.audience,
            "turn_count": state.turn_count,
            "conversation_move": conversation_move,
            "research_intent": research_intent,
            "research_execution": research_execution,
            "research_required": research_execution in {"INCREMENTAL_RETRIEVAL", "FULL_RESEARCH"},
            "research_freshness": {
                "SKIP": "NONE",
                "REUSE_PREVIOUS": "EXISTING",
                "INCREMENTAL_RETRIEVAL": "REFRESH_REQUIRED",
                "FULL_RESEARCH": "FRESH",
            }[research_execution],
            "previous_answer_reused": research_execution == "REUSE_PREVIOUS" and bool(state.previous_answer_summary),
            "previous_evidence_reused": research_execution == "REUSE_PREVIOUS" and bool(state.previous_research_artifact_ref),
            "context_source": (
                "THREAD_CHECKPOINT" if state.checkpoint_restored
                else "PROCESS_MEMORY" if inherited or state.turn_count > 1
                else "CURRENT_TURN"
            ),
            "router_confidence": router_confidence,
            "previous_answer_summary": state.previous_answer_summary if research_execution == "REUSE_PREVIOUS" else None,
            "reference_status": "unresolved" if unresolved else "resolved",
            "clarification": clarification,
        }
        derived_ticker = ticker or (state.primary_entity if len(state.entities()) == 1 else None)
        return effective, derived_ticker, trace

    @staticmethod
    def _detect_focus(question: str) -> str | None:
        for name, pattern in _FOCUS.items():
            if pattern.search(question):
                return name
        return None

    @staticmethod
    def _detect_theme(question: str) -> str | None:
        for name, pattern in _THEMES.items():
            if pattern.search(question):
                return name
        return None

    @staticmethod
    def _clarification(
        question: str,
        *,
        explicit: list[str],
        active_entities: list[str],
        is_compare: bool,
        unresolved_reference: bool,
        horizon: str | None,
    ) -> dict:
        base = {"required": False, "reason": None, "question": None, "options": []}
        if re.search(r"\bhdfc\b", question, re.I) and not re.search(
            r"\bhdfc\s+(bank|amc|life|asset management)\b", question, re.I
        ):
            return {
                "required": True,
                "reason": "ambiguous_entity",
                "question": "Which HDFC entity do you mean?",
                "options": [
                    {"label": "HDFC Bank", "prompt": re.sub(r"\bHDFC\b", "HDFC Bank", question, flags=re.I)},
                    {"label": "HDFC AMC", "prompt": re.sub(r"\bHDFC\b", "HDFC AMC", question, flags=re.I)},
                    {"label": "HDFC Life", "prompt": re.sub(r"\bHDFC\b", "HDFC Life", question, flags=re.I)},
                ],
            }
        if unresolved_reference:
            return {
                "required": True,
                "reason": "missing_reference",
                "question": "Which company, sector, or theme should I apply this to?",
                "options": [],
            }
        if is_compare and len(active_entities) < 2:
            subject = explicit[0] if explicit else (active_entities[0] if active_entities else "that company")
            return {
                "required": True,
                "reason": "missing_comparison_entity",
                "question": f"What should I compare {subject} with?",
                "options": [],
            }
        if re.search(r"\b(should i buy|should i sell|buy or sell|enter now)\b", question, re.I) and active_entities and not horizon:
            return {
                "required": True,
                "reason": "missing_investment_horizon",
                "question": "What investment horizon should AGI evaluate?",
                "options": [
                    {"label": "Tactical · 5D", "prompt": f"{question} Use a 5D tactical horizon."},
                    {"label": "Swing · 20D", "prompt": f"{question} Use a 20D swing horizon."},
                    {"label": "Investment · 12M", "prompt": f"{question} Use a 12M investment horizon."},
                ],
            }
        return base


conversation_store = ConversationStore()
