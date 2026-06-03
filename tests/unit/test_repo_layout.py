"""E-00-S01: Validate repository layout against TDS-013 manifest.

Run without pytest (stdlib only):
    python tests/unit/test_repo_layout.py

Or with pytest (after E-00-S02):
    pytest tests/unit/test_repo_layout.py -v
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "tests" / "fixtures" / "repo_layout_manifest.txt"


def _load_manifest_paths() -> list[str]:
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    paths: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)
    return paths


def test_repo_layout_manifest_paths_exist() -> None:
    """Every path in the layout manifest must exist (TDS-013 §2, E-00-S01)."""
    missing: list[str] = []
    for rel in _load_manifest_paths():
        target = REPO_ROOT / rel
        if not target.exists():
            missing.append(rel)
    assert not missing, "Missing repository paths:\n  " + "\n  ".join(missing)


def test_explainability_is_llm_agent_root() -> None:
    """Only agents/explainability/ is designated for future LLM code (ADR-001)."""
    explainability = REPO_ROOT / "agents" / "explainability"
    assert explainability.is_dir(), "agents/explainability/ must exist"
    conversation = explainability / "conversation"
    assert conversation.is_dir(), "agents/explainability/conversation/ must exist"


def test_no_inventory_persistence_phase2() -> None:
    """Inventory persistence is Phase 2 — must not exist in E-00-S01 (TDS-013 §10)."""
    forbidden = REPO_ROOT / "backend" / "app" / "persistence" / "inventory"
    assert not forbidden.exists(), (
        "inventory persistence must not be created in Phase 1 scaffold"
    )


if __name__ == "__main__":
    test_repo_layout_manifest_paths_exist()
    test_explainability_is_llm_agent_root()
    test_no_inventory_persistence_phase2()
    print("E-00-S01 layout validation: PASSED")
