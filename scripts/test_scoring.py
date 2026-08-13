#!/usr/bin/env python3
"""Offline tests for ranking composite scoring."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datetime as dt

from scoring import (
    attach_league_relative_payroll,
    attach_rates,
    composite_scores,
    efficiency_wins,
    last_complete_season,
    payroll_efficiency_from_seasons,
    rank_descending,
    raw_season_payroll_efficiency,
    tenure_shrink,
    wins_per_100m,
    zscore,
)

WEIGHTS = {
    "world_series_rate": 0.12,
    "pennants_rate": 0.07,
    "playoff_depth_rate": 0.12,
    "win_pct": 0.10,
    "payroll_efficiency": 0.36,
    "draft_vos": 0.11,
    "trade_net_rate": 0.12,
}


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_zscore_identity() -> None:
    zs = zscore([1.0, 2.0, 3.0])
    check(abs(sum(zs)) < 1e-9, "z-scores should sum ~0")
    check(zs[2] > zs[1] > zs[0], "higher raw → higher z")


def test_wins_per_100m() -> None:
    check(abs(wins_per_100m(90, 180_000_000) - 50.0) < 1e-9, "90 wins / $180M = 50")
    check(wins_per_100m(90, None) == 0.0, "missing payroll → 0")


def test_efficiency_wins_2020_proration() -> None:
    # 40-20 in 60 games → 108 paced wins (40 * 162/60)
    paced = efficiency_wins(2020, 40, 20)
    check(abs(paced - 108.0) < 1e-9, f"2020 40-20 → 108 paced, got {paced}")
    check(efficiency_wins(2019, 40, 20) == 40.0, "non-2020 wins unchanged")
    check(efficiency_wins(2020, 0, 0) == 0.0, "zero games → 0")
    # Relative efficiency preserved: better 2020 team still scores higher.
    good = wins_per_100m(efficiency_wins(2020, 40, 20), 120_000_000)
    bad = wins_per_100m(efficiency_wins(2020, 20, 40), 120_000_000)
    check(good > bad, "proration keeps 2020 relative order")


def test_rates_normalize_longevity() -> None:
    short = attach_rates({"seasons": 2, "world_series": 1, "pennants": 1, "playoff_depth": 6})
    long = attach_rates({"seasons": 20, "world_series": 1, "pennants": 1, "playoff_depth": 6})
    check(short["world_series_rate"] > long["world_series_rate"], "same titles: short tenure has higher rate")
    check(short["playoff_depth_rate"] > long["playoff_depth_rate"], "same depth: short tenure has higher rate")


def test_payroll_heavy_prefers_cheap_contention() -> None:
    rows = [
        {
            "world_series_rate": 0.15,
            "pennants_rate": 0.2,
            "playoff_depth_rate": 2.2,
            "win_pct": 0.58,
            "payroll_efficiency": 0.7,
            "draft_vos": 0.0,
            "trade_net_rate": 0.0,
        },
        {
            "world_series_rate": 0.0,
            "pennants_rate": 0.1,
            "playoff_depth_rate": 1.4,
            "win_pct": 0.53,
            "payroll_efficiency": 1.4,
            "draft_vos": 0.1,
            "trade_net_rate": 0.5,
        },
        {
            "world_series_rate": 0.05,
            "pennants_rate": 0.05,
            "playoff_depth_rate": 0.9,
            "win_pct": 0.50,
            "payroll_efficiency": 1.0,
            "draft_vos": 0.0,
            "trade_net_rate": 0.0,
        },
        {
            "world_series_rate": 0.0,
            "pennants_rate": 0.0,
            "playoff_depth_rate": 0.2,
            "win_pct": 0.45,
            "payroll_efficiency": 0.6,
            "draft_vos": -0.1,
            "trade_net_rate": -0.2,
        },
    ]
    scores = composite_scores(rows, WEIGHTS)
    check(scores[1] > scores[0], f"cheap club should outrank spendy titles: {scores}")
    check(scores[0] > scores[3], f"titles+spend still beats bad+spend: {scores}")


def test_missing_trade_net_not_fake_zero() -> None:
    """Null trade_net must not z-score as if 0 when the peer mean is negative."""
    rows = [
        {
            "world_series_rate": 0.05,
            "pennants_rate": 0.05,
            "playoff_depth_rate": 1.0,
            "win_pct": 0.50,
            "payroll_efficiency": 1.0,
            "draft_vos": 0.0,
            "trade_net_rate": -2.0,
        },
        {
            "world_series_rate": 0.05,
            "pennants_rate": 0.05,
            "playoff_depth_rate": 1.0,
            "win_pct": 0.50,
            "payroll_efficiency": 1.0,
            "draft_vos": 0.0,
            "trade_net_rate": -1.0,
        },
        {
            "world_series_rate": 0.05,
            "pennants_rate": 0.05,
            "playoff_depth_rate": 1.0,
            "win_pct": 0.50,
            "payroll_efficiency": 1.0,
            "draft_vos": 0.0,
            "trade_net_rate": None,  # missing — must not become 0
        },
    ]
    # With fake-zero, row 2 would get a strong positive trade z and outrank peers.
    # With drop+renorm, trade is ignored for row 2; identical other comps → same score
    # as a peer after renorm on shared keys only… actually row 2 renormalizes without
    # trade, while rows 0/1 keep trade. Row 2 should not crush them via fake +z(0).
    scores = composite_scores(rows, WEIGHTS)
    # Row with null trade should not be the clear #1 solely from fake zero.
    check(
        scores[2] < scores[1] + 0.5,
        f"null trade_net must not dominate via fake 0: {scores}",
    )
    # Explicit: treating None as 0 would flip the ranking vs drop+renorm.
    fake_rows = [{**r, "trade_net_rate": 0.0 if r["trade_net_rate"] is None else r["trade_net_rate"]} for r in rows]
    fake_scores = composite_scores(fake_rows, WEIGHTS)
    check(
        fake_scores[2] > scores[2] + 0.05,
        f"fake-zero path should inflate missing row vs null-aware: fake={fake_scores} real={scores}",
    )


def test_legitimate_zero_trade_net_is_present() -> None:
    rows = [
        {**{k: 0.5 for k in WEIGHTS}, "trade_net_rate": -1.0},
        {**{k: 0.5 for k in WEIGHTS}, "trade_net_rate": 0.0},
        {**{k: 0.5 for k in WEIGHTS}, "trade_net_rate": 1.0},
    ]
    for k in ("world_series_rate", "pennants_rate", "playoff_depth_rate", "win_pct", "payroll_efficiency", "draft_vos"):
        for r in rows:
            r[k] = 0.5
    scores = composite_scores(rows, WEIGHTS)
    check(scores[2] > scores[1] > scores[0], f"0.0 trade is real mid value: {scores}")


def test_tenure_shrink() -> None:
    check(tenure_shrink(2.0, 20, 4) > tenure_shrink(2.0, 2, 4), "long tenure keeps more score")
    check(abs(tenure_shrink(2.0, 0, 4)) < 1e-9, "zero seasons → 0")
    check(abs(tenure_shrink(2.0, 4, 4) - 1.0) < 1e-9, "equal prior → half toward 0")


def test_rank_ties() -> None:
    ranks = rank_descending([1.0, 1.0, 0.5])
    check(ranks == [1, 1, 3], f"tied scores share rank 1, got {ranks}")


def test_payroll_efficiency_league_relative() -> None:
    seasons = [
        {"season": 2010, "wins": 90, "losses": 72, "payroll": 50_000_000},
        {"season": 2010, "wins": 70, "losses": 92, "payroll": 100_000_000},
        {"season": 2024, "wins": 90, "losses": 72, "payroll": 200_000_000},
        {"season": 2024, "wins": 70, "losses": 92, "payroll": 300_000_000},
    ]
    means = attach_league_relative_payroll(seasons)
    check(2010 in means and 2024 in means, "year means present")
    # Cheap 2010 club should be >1 relative to 2010 mean.
    check(seasons[0]["payroll_efficiency_lg"] > 1.0, "cheap 2010 above league mean")
    # Aggregate for team that played both decades as the cheap club each year.
    cheap = [seasons[0], seasons[2]]
    eff, pay = payroll_efficiency_from_seasons(cheap, means)
    check(pay == 250_000_000, "payroll sum")
    check(eff > 1.0, f"league-avg thrift > 1, got {eff}")
    empty_eff, empty_sum = payroll_efficiency_from_seasons(
        [{"season": 2022, "wins": 80, "losses": 82, "payroll": None}], means
    )
    check(empty_sum is None and empty_eff == 0.0, "all-missing → 0")


def test_era_corr_improves_on_synthetic() -> None:
    """Relativizing removes a planted year trend in raw PE."""
    import statistics

    seasons = []
    for year in range(2006, 2025):
        # League payroll inflates; wins stay ~81 → raw PE falls with year.
        league_pay = 50_000_000 + (year - 2006) * 8_000_000
        for i in range(5):
            seasons.append(
                {
                    "season": year,
                    "wins": 75 + i * 3,
                    "losses": 87 - i * 3,
                    "payroll": league_pay * (0.8 + i * 0.1),
                }
            )
    raw_pairs = []
    for row in seasons:
        raw = raw_season_payroll_efficiency(row)
        if raw is not None:
            raw_pairs.append((row["season"], raw))
    mx = statistics.mean(x for x, _ in raw_pairs)
    my = statistics.mean(y for _, y in raw_pairs)
    num = sum((x - mx) * (y - my) for x, y in raw_pairs)
    den = (
        sum((x - mx) ** 2 for x, _ in raw_pairs)
        * sum((y - my) ** 2 for _, y in raw_pairs)
    ) ** 0.5
    raw_corr = num / den
    attach_league_relative_payroll(seasons)
    lg_pairs = [
        (r["season"], r["payroll_efficiency_lg"])
        for r in seasons
        if r.get("payroll_efficiency_lg") is not None
    ]
    mx = statistics.mean(x for x, _ in lg_pairs)
    my = statistics.mean(y for _, y in lg_pairs)
    num = sum((x - mx) * (y - my) for x, y in lg_pairs)
    den = (
        sum((x - mx) ** 2 for x, _ in lg_pairs)
        * sum((y - my) ** 2 for _, y in lg_pairs)
    ) ** 0.5
    lg_corr = num / den
    check(raw_corr < -0.3, f"synthetic raw corr should be strongly negative, got {raw_corr}")
    check(abs(lg_corr) < abs(raw_corr) / 2, f"league corr {lg_corr} should be much closer to 0 than {raw_corr}")


def test_last_complete_season() -> None:
    check(last_complete_season(dt.date(2026, 8, 1), 2026) == 2025, "Aug → prior year")
    check(last_complete_season(dt.date(2026, 10, 15), 2026) == 2026, "Oct → current ok")
    check(last_complete_season(dt.date(2026, 11, 1), 2025) == 2025, "window_end caps")


def test_lens_presets() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    weights = json.loads((root / "data" / "weights.json").read_text(encoding="utf-8"))
    lenses = weights["lenses"]
    check(set(lenses) >= {"balanced", "october", "value", "builder"}, "four lenses")
    keys = set(WEIGHTS)
    for name, lens in lenses.items():
        comps = lens["components"]
        check(set(comps) == keys, f"{name} keys")
        total = sum(comps.values())
        check(abs(total - 1.0) < 1e-9, f"{name} sum {total}")
        check(min(comps.values()) >= 0.05 - 1e-12, f"{name} min weight")
        check(max(comps.values()) <= 0.42 + 1e-12, f"{name} max weight")
        check(lens.get("label") and lens.get("blurb"), f"{name} copy")
    bal = lenses["balanced"]["components"]
    for k, v in WEIGHTS.items():
        check(abs(bal[k] - v) < 1e-12, f"balanced matches house {k}")


def test_balanced_matches_franchise_index() -> None:
    """Balanced lens z-score composite should match shipped franchise composites."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    payload = json.loads((root / "data" / "franchise_index.json").read_text(encoding="utf-8"))
    rows = payload["franchises"]
    scores = composite_scores(rows, WEIGHTS)
    for row, score in zip(rows, scores):
        check(
            abs(score - float(row["composite"])) < 0.015,
            f"{row['team_abbr']}: got {score} shipped {row['composite']}",
        )


def main() -> int:
    test_zscore_identity()
    test_wins_per_100m()
    test_efficiency_wins_2020_proration()
    test_rates_normalize_longevity()
    test_payroll_heavy_prefers_cheap_contention()
    test_missing_trade_net_not_fake_zero()
    test_legitimate_zero_trade_net_is_present()
    test_tenure_shrink()
    test_rank_ties()
    test_payroll_efficiency_league_relative()
    test_era_corr_improves_on_synthetic()
    test_last_complete_season()
    test_lens_presets()
    # Franchise golden check runs after rebuild; skip if PE scale looks pre-relativization.
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    payload = json.loads((root / "data" / "franchise_index.json").read_text(encoding="utf-8"))
    sample_pe = float(payload["franchises"][0].get("payroll_efficiency") or 0)
    if sample_pe < 5:  # league-relative scale is ~0.5–2
        test_balanced_matches_franchise_index()
    else:
        print("skip franchise golden (pre-relativization payroll scale still on disk)")
    print("all ranking checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
