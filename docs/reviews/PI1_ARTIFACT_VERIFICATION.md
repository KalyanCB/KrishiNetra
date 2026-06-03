# PI1 Artifact Verification

| Field | Value |
|-------|-------|
| **Verification timestamp** | 2026-06-03 21:51:51 IST |
| **Repository** | `/Users/kalyancb/KrishiNetra` |
| **Remote** | `https://github.com/KalyanCB/KrishiNetra` (`origin`) |
| **Local `HEAD`** | `30583fc475b5d720ca52b4607b27d557d21450b8` |
| **`origin/main`** | `30583fc475b5d720ca52b4607b27d557d21450b8` |
| **Unpushed commits** (`origin/main..HEAD`) | **0** |
| **Verifier note** | verification only, no document regeneration. |

## Summary

| Metric | Count |
|--------|------:|
| Artifacts **EXIST** on disk | 9 |
| Artifacts **MISSING** on disk | 0 |
| Committed (in git history for path) | 1 |
| Untracked (not in index) | 8 |
| Modified vs last commit | 1 (`DS001`) |

## Per-artifact table

| Status | Path | Size (bytes) | Size (human) | Last modified (local) | Git porcelain | Committed | Pushed |
|--------|------|-------------:|--------------|----------------------|---------------|-----------|--------|
| EXISTS | `docs/reviews/REPO_AUDIT_CURRENT_STATE.md` | 8,596 | 8.4 KiB | 2026-06-03 21:43 | `??` untracked | **no** — no `git log` entry for path | **no** — not in any commit on `main` |
| EXISTS | `docs/implementation/E01_FOUNDATION_REPORT.md` | 6,541 | 6.4 KiB | 2026-06-03 21:43 | `??` untracked | **no** | **no** |
| EXISTS | `docs/implementation/E02_EXECUTION_PLAN.md` | 5,095 | 5.0 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |
| EXISTS | `docs/research/DS001_FUTURES_VENDOR_DECISION.md` | 16,890 | 16.5 KiB | 2026-06-03 21:44 | ` M` modified (tracked) | **yes** — `30583fc475b5d720ca52b4607b27d557d21450b8` (2026-06-03 21:37:55 +0530, *E-00 M0 + E-01 Phase 1 foundation*) | **partial** — last committed revision matches `origin/main` (0 unpushed commits); **17 lines** of local working-tree changes are **not** committed or pushed |
| EXISTS | `docs/research/E03_DATA_INGESTION_READINESS.md` | 7,646 | 7.5 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |
| EXISTS | `docs/reviews/GOVERNANCE_AUDIT_PI1.md` | 5,225 | 5.1 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |
| EXISTS | `docs/reviews/TECHNICAL_DEBT_REGISTER.md` | 3,579 | 3.5 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |
| EXISTS | `docs/implementation/PI1_PROGRAM_STATUS.md` | 3,425 | 3.3 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |
| EXISTS | `docs/reviews/PI1_EXECUTIVE_SUMMARY.md` | 4,724 | 4.6 KiB | 2026-06-03 21:44 | `??` untracked | **no** | **no** |

## Methods

- Size and mtime: `stat` / `ls -la` on each path.
- Git status: `git status --porcelain -- <path>`.
- Committed: `git log -1 --format=%H -- <path>` (empty ⇒ never committed for that path).
- Push: `git rev-parse HEAD` vs `git rev-parse origin/main`; `git log origin/main..HEAD --oneline` (count **0** at verification time).

## This report

| Item | Value |
|------|-------|
| Path | `docs/reviews/PI1_ARTIFACT_VERIFICATION.md` |
| Created by | PI1 verification run (this file only) |
| Commit | Not performed (per instruction unless explicitly requested) |
