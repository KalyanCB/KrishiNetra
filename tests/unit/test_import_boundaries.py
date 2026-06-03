"""E-00-S05: Import boundary enforcement tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_imports.py"
VIOLATION_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "import_violations"
    / "forbidden_explainability_import.py"
)


def test_import_rules_pass() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_import_rules_fail_fixture() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), str(VIOLATION_FIXTURE)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "domain_agents_no_explainability" in result.stderr
