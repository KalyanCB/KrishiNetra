#!/usr/bin/env python3
"""Import boundary checker (E-00-S05, TDS-013 §3.1, ADR-001)."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LLM_MODULES = frozenset(
    {
        "openai",
        "anthropic",
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langchain_anthropic",
        "langsmith",
    }
)

UPWARD_PREFIXES = frozenset(
    {
        "backend",
        "agents",
        "forecasting",
        "decision_engine",
        "market_intelligence",
    }
)


@dataclass(frozen=True)
class Violation:
    rule: str
    file: Path
    lineno: int
    module: str


def _python_files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts
    )


def _imports_in_file(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
    return found


def _top_level_package(module: str) -> str:
    return module.split(".", 1)[0]


def _check_decision_engine_no_llm(files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        for lineno, module in _imports_in_file(path):
            top = _top_level_package(module)
            if top in LLM_MODULES:
                violations.append(
                    Violation("decision_engine_no_llm", path, lineno, module)
                )
    return violations


def _check_forecasting_no_decision_engine(files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        for lineno, module in _imports_in_file(path):
            if module == "decision_engine" or module.startswith("decision_engine."):
                violations.append(
                    Violation("forecasting_no_decision_engine", path, lineno, module)
                )
    return violations


def _check_domain_agents_no_explainability(files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        for lineno, module in _imports_in_file(path):
            if module == "agents.explainability" or module.startswith(
                "agents.explainability."
            ):
                violations.append(
                    Violation("domain_agents_no_explainability", path, lineno, module)
                )
    return violations


def _check_shared_no_upward(files: list[Path]) -> list[Violation]:
    violations: list[Violation] = []
    for path in files:
        for lineno, module in _imports_in_file(path):
            top = _top_level_package(module)
            if top in UPWARD_PREFIXES:
                violations.append(Violation("shared_no_upward", path, lineno, module))
    return violations


def _check_file_all_rules(path: Path) -> list[Violation]:
    """Apply every rule to a single file (negative-test fixtures)."""
    violations: list[Violation] = []
    violations.extend(_check_decision_engine_no_llm([path]))
    violations.extend(_check_forecasting_no_decision_engine([path]))
    violations.extend(_check_domain_agents_no_explainability([path]))
    violations.extend(_check_shared_no_upward([path]))
    return violations


def run_checks(extra_paths: list[Path] | None = None) -> list[Violation]:
    """Run import boundary rules on repo packages and optional extra paths."""
    violations: list[Violation] = []

    de_root = REPO_ROOT / "decision_engine"
    violations.extend(_check_decision_engine_no_llm(_python_files_under(de_root)))

    fc_root = REPO_ROOT / "forecasting"
    violations.extend(
        _check_forecasting_no_decision_engine(_python_files_under(fc_root))
    )

    agents_root = REPO_ROOT / "agents"
    domain_files: list[Path] = []
    for sub in agents_root.iterdir() if agents_root.exists() else []:
        if sub.is_dir() and sub.name != "explainability":
            domain_files.extend(_python_files_under(sub))
    violations.extend(_check_domain_agents_no_explainability(domain_files))

    shared_root = REPO_ROOT / "shared"
    violations.extend(_check_shared_no_upward(_python_files_under(shared_root)))

    if extra_paths:
        for extra in extra_paths:
            if extra.is_file() and extra.suffix == ".py":
                violations.extend(_check_file_all_rules(extra))
            else:
                for path in _python_files_under(extra):
                    violations.extend(_check_file_all_rules(path))

    return violations


def main() -> int:
    extra: list[Path] = []
    if len(sys.argv) > 1:
        extra = [Path(p).resolve() for p in sys.argv[1:]]
    violations = run_checks(extra_paths=extra or None)
    if violations:
        print("Import boundary violations:", file=sys.stderr)
        for v in violations:
            rel = v.file.relative_to(REPO_ROOT)
            print(
                f"  [{v.rule}] {rel}:{v.lineno} imports {v.module!r}", file=sys.stderr
            )
        return 1
    print("Import boundaries OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
