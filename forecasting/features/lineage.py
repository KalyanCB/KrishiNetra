"""Group forecast features by lineage prefix (market / weather / futures)."""

from __future__ import annotations

from shared.domain.enums import AgentType

LINEAGE_FEATURE_PREFIXES: tuple[str, ...] = ("market", "weather", "futures")

_AGENT_TO_PREFIX: dict[str, str] = {
    AgentType.MARKET.value: "market",
    AgentType.WEATHER.value: "weather",
    AgentType.FUTURES.value: "futures",
}


def feature_lineage_prefix(feature_name: str) -> str | None:
    """Return the lineage prefix for a namespaced feature key."""
    if "." not in feature_name:
        return None
    prefix = feature_name.split(".", 1)[0].lower()
    if prefix in LINEAGE_FEATURE_PREFIXES:
        return prefix
    return None


def prefixes_from_lineage(feature_lineage: dict[str, object]) -> tuple[str, ...]:
    """Derive active lineage prefixes from ``feature_lineage.agents`` keys."""
    agents = feature_lineage.get("agents")
    if not isinstance(agents, dict):
        return LINEAGE_FEATURE_PREFIXES
    prefixes: list[str] = []
    for agent_key in sorted(agents):
        mapped = _AGENT_TO_PREFIX.get(str(agent_key))
        if mapped is not None and mapped not in prefixes:
            prefixes.append(mapped)
    return tuple(prefixes) if prefixes else LINEAGE_FEATURE_PREFIXES


def group_importances(
    importances: dict[str, float],
    *,
    active_prefixes: tuple[str, ...] = LINEAGE_FEATURE_PREFIXES,
) -> dict[str, tuple[tuple[str, float], ...]]:
    """Bucket importances by lineage prefix; within group sort desc by score."""
    buckets: dict[str, list[tuple[str, float]]] = {p: [] for p in active_prefixes}
    for name, score in importances.items():
        prefix = feature_lineage_prefix(name)
        if prefix is None or prefix not in buckets:
            continue
        buckets[prefix].append((name, score))
    return {
        prefix: tuple(sorted(items, key=lambda item: (-item[1], item[0])))
        for prefix, items in buckets.items()
    }


def top_features_per_group(
    grouped: dict[str, tuple[tuple[str, float], ...]],
    *,
    top_k: int = 10,
) -> dict[str, tuple[tuple[str, float], ...]]:
    """Keep top-k features per lineage group."""
    return {prefix: rows[:top_k] for prefix, rows in grouped.items()}


def group_aggregate_scores(
    grouped: dict[str, tuple[tuple[str, float], ...]],
) -> dict[str, float]:
    """Sum feature importances within each lineage group."""
    return {
        prefix: round(sum(score for _, score in rows), 10)
        for prefix, rows in grouped.items()
    }
