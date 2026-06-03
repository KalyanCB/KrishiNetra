# Reference seed fixtures (E-01 framework)

Place JSON fixtures here for `SeedRunner.apply()`. **No cotton seed in E-01** — E-02 adds `cotton.json` per TDS-009 §11.1.

Example layout (E-02):

```json
{
  "commodity": { "commodity_id": "cotton", "name": "Cotton", "status": "active" },
  "commodity_profile": { "display_name": "Cotton", "unit": "quintal" }
}
```

Run (after E-02 implementation):

```bash
uv run python -m backend.app.persistence.seeds.cli cotton
```
