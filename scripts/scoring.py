"""Shared z-score composite scoring for franchise and GM indexes."""

from __future__ import annotations

import math
import statistics
from typing import Any


# Rate-based components — titles/depth per season so longevity does not accumulate a free pass.
COMPONENT_KEYS = (
    "world_series_rate",
    "pennants_rate",
    "playoff_depth_rate",
    "win_pct",
    "payroll_efficiency",
    "draft_vos",
    "trade_net_rate",
)

CATEGORY_KEYS = COMPONENT_KEYS

ROUND_DEPTH = {
    "F": 1,
    "D": 2,
    "L": 3,
    "W": 4,
}

# 2020 COVID season: ~60 games, roughly full opening-day payrolls.
# Rate metrics (win%) need no special case. Counting wins vs full payroll would
# systematically tank payroll efficiency for that year — prorate wins to a
# 162-game pace for efficiency only. Titles / pennants / playoff depth still
# count as one full championship season (a World Series is a World Series).
COVID_SEASON = 2020
FULL_SEASON_GAMES = 162


def efficiency_wins(season: int, wins: int, losses: int) -> float:
    """Wins counted toward payroll efficiency (2020 paced to 162 games)."""
    if int(season) != COVID_SEASON:
        return float(wins)
    games = int(wins) + int(losses)
    if games <= 0:
        return 0.0
    return float(wins) * (FULL_SEASON_GAMES / games)


def zscore(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [0.0]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev < 1e-12:
        return [0.0 for _ in values]
    return [(v - mean) / stdev for v in values]


def composite_scores(
    rows: list[dict[str, Any]],
    weights: dict[str, float],
) -> list[float]:
    if not rows:
        return []

    z_by_key: dict[str, list[float]] = {}
    for key in COMPONENT_KEYS:
        raw = [float(r.get(key) or 0.0) for r in rows]
        z_by_key[key] = zscore(raw)

    out: list[float] = []
    for i in range(len(rows)):
        total = 0.0
        for key in COMPONENT_KEYS:
            total += weights.get(key, 0.0) * z_by_key[key][i]
        out.append(round(total, 4))
    return out


def category_ranks(rows: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Per-component competition ranks (1 = best) for each row."""
    result = [{} for _ in rows]
    for key in CATEGORY_KEYS:
        values = [float(r.get(key) or 0.0) for r in rows]
        ranks = rank_descending(values)
        for i, rank in enumerate(ranks):
            result[i][key] = rank
    return result


def tenure_shrink(score: float, seasons: int, prior: int = 4) -> float:
    if seasons <= 0:
        return 0.0
    weight = seasons / (seasons + max(prior, 0))
    return round(score * weight, 4)


def rank_descending(scores: list[float]) -> list[int]:
    indexed = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    ranks = [0] * len(scores)
    i = 0
    ordered = indexed
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and math.isclose(ordered[j + 1][1], ordered[i][1]):
            j += 1
        shared = i + 1
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = shared
        i = j + 1
    return ranks


def wins_per_100m(wins: float | int, payroll: float | None) -> float:
    if not payroll or payroll <= 0:
        return 0.0
    return float(wins) / (payroll / 100_000_000.0)


def attach_rates(metrics: dict[str, Any]) -> dict[str, Any]:
    """Add per-season rates; keep counts under *_count aliases when present."""
    seasons = max(int(metrics.get("seasons") or 0), 1)
    ws = int(metrics.get("world_series") or metrics.get("world_series_count") or 0)
    pennants = int(metrics.get("pennants") or metrics.get("pennants_count") or 0)
    depth = int(metrics.get("playoff_depth") or metrics.get("playoff_depth_count") or 0)
    metrics["world_series_count"] = ws
    metrics["pennants_count"] = pennants
    metrics["playoff_depth_count"] = depth
    metrics["world_series_rate"] = round(ws / seasons, 4)
    metrics["pennants_rate"] = round(pennants / seasons, 4)
    metrics["playoff_depth_rate"] = round(depth / seasons, 4)
    # Composite keys expect rates; keep legacy names as counts for display.
    metrics["world_series"] = ws
    metrics["pennants"] = pennants
    metrics["playoff_depth"] = depth
    return metrics
