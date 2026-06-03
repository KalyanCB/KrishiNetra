# ADR-002: PostgreSQL Schema Migrations with Alembic

| Field | Value |
|-------|-------|
| **Status** | Accepted (implementation standard) |
| **Date** | 2026-06-03 |
| **Deciders** | Lead Architect |
| **Supersedes** | None |

## Context

TDS-006 defines the canonical persistence model without SQL DDL. E-01 requires versioned schema evolution, partitioning, and immutability constraints aligned to PostgreSQL (approved stack).

## Decision

1. Use **SQLAlchemy 2.x** for ORM/models and **Alembic** for migrations.
2. Migrations live in `backend/app/persistence/migrations/`.
3. All schema changes require forward migration; rollbacks supported for dev only.
4. Immutable tables (`forecast_version`, `recommendation_version`) enforced at repository layer—no UPDATE on published numeric columns.
5. Monthly range partitioning on `as_of_date` for observation and forecast tables per TDS-006 §9.

## Alternatives Considered

| Option | Rejected because |
|--------|------------------|
| Raw SQL only | Harder to align with Python types and CI |
| Django ORM | Stack is FastAPI-approved, not Django |

## Consequences

**Positive**
- Industry-standard path for FastAPI + PostgreSQL teams.
- Supports REQ-103 replay testing with stable schema versions.

**Negative**
- Partition management requires manual migration steps when adding months.

## Compliance

| Source | Reference |
|--------|-----------|
| TDS-006 | Full entity spec, §4, §9 |
| REQ-090 | Core entities |
| Stories | E-01-S01 through E-01-S11 |

## Notes

Does not alter TDS-006 entity definitions—only implements them.
