"""AWS feature flags — Architecture v1.0.1 P0 defaults."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AwsFlags:
    aws: bool = True
    aws_copilot: bool = True
    aws_replay: bool = True
    aws_cre: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "AwsFlags":
        s = settings or get_settings()
        return cls(
            aws=bool(getattr(s, "aws", True)),
            aws_copilot=bool(getattr(s, "aws_copilot", True)),
            aws_replay=bool(getattr(s, "aws_replay", True)),
            aws_cre=bool(getattr(s, "aws_cre", True)),
        )

    def as_dict(self) -> dict[str, bool]:
        return {
            "AWS": self.aws,
            "AWS_COPILOT": self.aws_copilot,
            "AWS_REPLAY": self.aws_replay,
            "AWS_CRE": self.aws_cre,
        }
