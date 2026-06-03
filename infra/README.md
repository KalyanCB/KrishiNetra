# Infrastructure

Production infrastructure (Terraform, Docker images for deployment, Kubernetes, etc.) is **out of scope** for Wave 1–3 and Sprint 0.

## Phase 1 local development

Local PostgreSQL and Redis for developers are introduced in **E-00-S06** via `docker-compose.dev.yml` at the repository root (development only—not production IaC).

## Future work (Wave 4+)

- Environment-specific Terraform
- Production container orchestration
- Secrets management integration

Do not add production IaC in this directory until explicitly scheduled in the delivery roadmap.
