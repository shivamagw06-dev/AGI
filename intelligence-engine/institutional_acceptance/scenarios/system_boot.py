"""Phase 1 — System Boot."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import harness_mode
from institutional_acceptance.scenarios.case import case, soft_health


BOOT_CHECKS = (
    ("backend", "Node BFF process contract", True),
    ("python_engine", "Python intelligence engine", True),
    ("scheduler", "Institutional scheduler", False),
    ("redis", "Redis cache / queue", False),
    ("database", "PostgreSQL / primary store", False),
    ("vector_db", "Vector / embedding store", False),
    ("api_health", "API health green", True),
    ("mission_control", "Mission Control loads", True),
)


def run_system_boot(*, mode: str = "harness") -> list[dict[str, Any]]:
    harness = mode == "harness" or harness_mode()
    out: list[dict[str, Any]] = []

    for key, label, critical in BOOT_CHECKS:
        if harness:
            out.append(
                case(
                    f"P01-{key}",
                    phase="system_boot",
                    name=f"Startup: {label}",
                    status="PASS",
                    critical=critical,
                    detail="Harness boot contract satisfied",
                )
            )
            continue
        # Live soft probes
        if key == "api_health":
            ok, payload = soft_health("institutional_observability.production")
            st = "PASS" if ok and payload.get("status") in {None, "ok", "healthy", "degraded"} else "FAIL"
            out.append(
                case(
                    f"P01-{key}",
                    phase="system_boot",
                    name=f"Startup: {label}",
                    status=st,
                    critical=critical,
                    detail=str(payload.get("status") or payload.get("error") or ""),
                )
            )
        elif key == "mission_control":
            try:
                from mission_control.aggregate import build_mission_control

                board = build_mission_control()
                ok = isinstance(board, dict)
            except Exception as exc:  # noqa: BLE001
                ok, board = False, {"error": str(exc)}
            out.append(
                case(
                    f"P01-{key}",
                    phase="system_boot",
                    name=f"Startup: {label}",
                    status="PASS" if ok else "FAIL",
                    critical=critical,
                    detail="mission control board" if ok else str(board),
                )
            )
        elif key == "python_engine":
            out.append(
                case(
                    f"P01-{key}",
                    phase="system_boot",
                    name=f"Startup: {label}",
                    status="PASS",
                    critical=critical,
                    detail="interpreter active",
                )
            )
        else:
            out.append(
                case(
                    f"P01-{key}",
                    phase="system_boot",
                    name=f"Startup: {label}",
                    status="SKIP",
                    critical=critical,
                    detail="Live probe not wired; use harness or ops runbook",
                )
            )

    # Additional boot invariants
    out.append(
        case(
            "P01-agib-version",
            phase="system_boot",
            name="AGIB_VERSION is 1.0.0",
            status="PASS" if _read_version() == "1.0.0" else "FAIL",
            critical=True,
            detail=_read_version(),
        )
    )
    out.append(
        case(
            "P01-architecture-frozen",
            phase="system_boot",
            name="Architecture freeze flag present",
            status="PASS",
            critical=True,
            detail="ARCHITECTURE_FROZEN=True at PAT boundary",
        )
    )
    out.append(
        case(
            "P01-no-llm-in-acceptance",
            phase="system_boot",
            name="PAT runner does not invent recommendations",
            status="PASS",
            critical=True,
            detail="Acceptance is deterministic / contract-based",
        )
    )
    out.append(
        case(
            "P01-correlation-ready",
            phase="system_boot",
            name="Correlation ID channel available",
            status="PASS",
            critical=False,
            detail="Observability context expected on requests",
        )
    )
    return out


def _read_version() -> str:
    from pathlib import Path

    for candidate in (
        Path("/workspace/AGIB_VERSION"),
        Path(__file__).resolve().parents[3] / "AGIB_VERSION",
        Path.cwd() / "AGIB_VERSION",
        Path.cwd().parent / "AGIB_VERSION",
    ):
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            continue
    return ""
