"""Import / layer dependency rules — prevent architectural drift (RC-01)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from institutional_architecture.schema import FORBIDDEN_IMPORTS, OWNERSHIP

# intelligence-engine root
ENGINE_ROOT = Path(__file__).resolve().parents[1]


def _iter_py_files(package: str) -> List[Path]:
    root = ENGINE_ROOT / package
    if not root.is_dir():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def extract_imports(path: Path) -> Set[str]:
    """Return top-level imported package names (institutional_* / app)."""
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except Exception:
        return set()
    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                found.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                found.add(top)
    return found


def scan_package_imports(package: str) -> Set[str]:
    imports: Set[str] = set()
    for path in _iter_py_files(package):
        imports |= extract_imports(path)
    imports.discard(package)
    return imports


def build_import_graph(packages: List[str] | None = None) -> dict[str, Any]:
    pkgs = packages or sorted(OWNERSHIP.keys())
    # Also include common intelligence packages for the graph
    extra = [
        "institutional_decision",
        "institutional_portfolio_risk",
        "institutional_policy",
        "institutional_portfolio_decision",
        "institutional_committee",
        "institutional_forecasting",
    ]
    all_pkgs = sorted(set(pkgs) | set(extra))
    edges = []
    nodes = []
    for pkg in all_pkgs:
        if not (ENGINE_ROOT / pkg).is_dir():
            continue
        nodes.append({"id": pkg, "ownership": OWNERSHIP.get(pkg, {})})
        for imp in sorted(scan_package_imports(pkg)):
            if imp.startswith("institutional_") or imp in {"mission_control"}:
                edges.append({"from": pkg, "to": imp})
    return {"nodes": nodes, "edges": edges}


def check_forbidden_imports() -> dict[str, Any]:
    violations: List[dict[str, Any]] = []
    evidence: List[dict[str, Any]] = []
    for src, dst in FORBIDDEN_IMPORTS:
        src_root = ENGINE_ROOT / src
        if not src_root.is_dir():
            continue
        for path in _iter_py_files(src):
            imports = extract_imports(path)
            if dst in imports:
                row = {
                    "from": src,
                    "to": dst,
                    "file": str(path.relative_to(ENGINE_ROOT)),
                    "rule": f"{src} must not import {dst}",
                }
                violations.append(row)
                evidence.append(row)
    return {
        "ok": not violations,
        "violations": violations,
        "checked_rules": [
            {"from": a, "to": b, "rule": f"{a} ↛ {b}"} for a, b in FORBIDDEN_IMPORTS
        ],
        "evidence": evidence,
    }


def layer_isolation_summary() -> dict[str, Any]:
    """Summarize which layers exist and their allowed direction."""
    return {
        "layers": [
            {
                "id": "intelligence",
                "packages": [
                    "institutional_graph",
                    "institutional_decision",
                    "institutional_portfolio_risk",
                    "institutional_policy",
                    "institutional_portfolio_decision",
                    "institutional_committee",
                    "institutional_cross_company",
                ],
                "may_depend_on": ["intelligence peers (limited)", "shared utils"],
                "must_not_depend_on": ["security", "observability", "workspace UI"],
            },
            {
                "id": "orchestration",
                "packages": [
                    "institutional_orchestrator",
                    "institutional_workspace",
                    "institutional_publishing",
                    "institutional_multi_portfolio",
                ],
                "may_depend_on": ["intelligence", "production soft hooks"],
            },
            {
                "id": "production",
                "packages": [
                    "institutional_performance",
                    "institutional_security",
                    "institutional_observability",
                ],
                "may_depend_on": ["platform façades"],
                "must_not": ["own intelligence", "change execution meaning"],
            },
        ],
        "forbidden_edges": [
            {"from": a, "to": b} for a, b in FORBIDDEN_IMPORTS
        ],
    }
