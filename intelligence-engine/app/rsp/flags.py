"""RSP feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class RspFlags:
    rsp: bool = True
    rsp_consensus: bool = True
    rsp_contradictions: bool = True
    rsp_reasoning: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "RspFlags":
        s = settings or get_settings()
        return cls(
            rsp=bool(getattr(s, "rsp", True)),
            rsp_consensus=bool(getattr(s, "rsp_consensus", True)),
            rsp_contradictions=bool(getattr(s, "rsp_contradictions", True)),
            rsp_reasoning=bool(getattr(s, "rsp_reasoning", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "RSP": self.rsp,
            "RSP_CONSENSUS": self.rsp_consensus,
            "RSP_CONTRADICTIONS": self.rsp_contradictions,
            "RSP_REASONING": self.rsp_reasoning,
        }
