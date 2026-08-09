"""Bounded conversation context for finance follow-up questions.

This layer resolves references; it never creates research evidence or changes scores.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable


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
_FOCUS = {
    "valuation": re.compile(r"\b(valuation|fair value|cheap|expensive|multiple|price target)\b", re.I),
    "forecast": re.compile(r"\b(forecast|expect|outlook|probability|horizon)\b", re.I),
    "fundamentals": re.compile(r"\b(fundamental|quality|earnings|margin|cash flow)\b", re.I),
    "risk": re.compile(r"\b(risk|bear case|downside|concern)\b", re.I),
    "catalyst": re.compile(r"\b(catalyst|event|trigger)\b", re.I),
    "thesis_change": re.compile(r"\b(what changed|thesis change|strengthen|weaken)\b", re.I),
    "reliability": re.compile(r"\b(reliability|validated|accuracy|hit rate|rank ic)\b", re.I),
}
_HORIZON_RE = re.compile(r"\b(5m|15m|30m|60m|1d|5d|20d|one day|five days?|twenty days?)\b", re.I)
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
    turn_count: int = 0
    updated_at: float = field(default_factory=time.time)

    def entities(self) -> list[str]:
        out: list[str] = []
        for value in [self.primary_entity, *self.comparison_entities]:
            if value and value not in out:
                out.append(value)
        return out


class ConversationStore:
    """Process-local, TTL-bounded store. Safe for concurrent request threads."""

    def __init__(self, *, ttl_seconds: int = 6 * 60 * 60, max_entries: int = 5_000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._states: dict[str, ConversationState] = {}
        self._lock = threading.RLock()

    @staticmethod
    def normalize_id(value: str | None) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:80]
        return clean or str(uuid.uuid4())

    def reset(self, conversation_id: str) -> None:
        with self._lock:
            self._states.pop(conversation_id, None)

    def get(self, conversation_id: str) -> ConversationState:
        now = time.time()
        with self._lock:
            stale = [key for key, state in self._states.items() if now - state.updated_at > self.ttl_seconds]
            for key in stale:
                self._states.pop(key, None)
            state = self._states.get(conversation_id)
            if state is None:
                state = ConversationState(conversation_id=conversation_id)
                self._states[conversation_id] = state
            if len(self._states) > self.max_entries:
                oldest = min(self._states, key=lambda key: self._states[key].updated_at)
                if oldest != conversation_id:
                    self._states.pop(oldest, None)
            return state

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
        is_follow_up = bool(_FOLLOW_UP_RE.search(original) or _CONTROL_ONLY_RE.search(original))
        prior_entities = state.entities()

        if explicit:
            if _INSTEAD_RE.search(original) and not is_compare:
                state.primary_entity = explicit[0]
                state.comparison_entities = explicit[1:]
            elif is_compare and len(explicit) == 1 and state.primary_entity and explicit[0] != state.primary_entity:
                inherited = [state.primary_entity]
                state.comparison_entities = [state.primary_entity, explicit[0]]
                effective = f"Compare {state.primary_entity} vs {explicit[0]}. {original}"
            else:
                state.primary_entity = explicit[0]
                state.comparison_entities = explicit[:] if len(explicit) > 1 else []
        elif is_follow_up and (prior_entities or state.theme):
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
        state.updated_at = time.time()

        unresolved = bool(is_follow_up and not prior_entities and not explicit)
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
            "reference_status": "unresolved" if unresolved else "resolved",
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


conversation_store = ConversationStore()
