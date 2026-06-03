"""Negative fixture: domain agent must not import explainability (E-00-S05)."""

from agents.explainability import conversation  # noqa: F401
