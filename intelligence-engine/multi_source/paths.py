"""Shared filesystem roots for multi-source adapters."""

from __future__ import annotations

from pathlib import Path


def workspace_root() -> Path:
    # intelligence-engine/multi_source/paths.py → repo root
    return Path(__file__).resolve().parents[2]


def intelligence_platform_dir() -> Path:
    return workspace_root() / "server" / "data" / "intelligence_platform"


def intelligence_cms_records() -> Path:
    return workspace_root() / "server" / "data" / "intelligence_cms" / "records.json"
