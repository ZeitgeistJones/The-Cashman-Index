"use client";

import { useMemo, useState } from "react";
import {
  formatComposite,
  formatSigned,
  type SeasonFile,
  type YearlyFile,
} from "@/lib/rankings";

/** One executive, one season — graded against every other season in the pool. */
type SeasonRow = {
  key: string;
  season: number;
  person_id: string;
  name: string;
  team: string;
  /** Grade for this season alone. */
  season_score: number | null;
  /** All-time place among graded executive-seasons (#1 = best ever in the pool). */
  all_time_rank: number | null;
  /** Place among executives graded that calendar year only. */
  year_rank: number | null;
  gm_count: number;
  /** Whether this season's inputs are complete (young drafts stay unscored). */
  fully_scored: boolean;
  /** Where the whole career-to-date stood that year. */
  resume_rank: number | null;
  trade_net: number | null;
  draft_vos: number | null;
};

type SortKey =
  | "all_time_rank"
  | "season"
  | "name"
  | "season_score"
  | "year_rank"
  | "resume_rank";
type Direction = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean; help: string }[] = [
  {
    key: "all_time_rank",
    label: "#",
    numeric: true,
    help: "All-time rank among graded FO seasons — #1 is the best executive-season in the pool",
  },
  {
    key: "name",
    label: "Executive",
    numeric: false,
    help: "Who ran the club that year",
  },
  {
    key: "season",
    label: "Year",
    numeric: true,
    help: "The season being graded",
  },
  {
    key: "season_score",
    label: "Score",
    numeric: true,
    help: "Construction grade for that year alone — not career reputation",
  },
  {
    key: "year_rank",
    label: "In that year",
    numeric: true,
    help: "Place among executives graded that same year (often ~30)",
  },
];

function competitionRanks(scores: (number | null)[]): (number | null)[] {
  const indexed = scores
    .map((score, i) => ({ score, i }))
    .filter((x): x is { score: number; i: number } => x.score !== null)
    .sort((a, b) => b.score - a.score);
  const ranks: (number | null)[] = scores.map(() => null);
  let i = 0;
  while (i < indexed.length) {
    let j = i;
    while (
      j + 1 < indexed.length &&
      Math.abs(indexed[j + 1].score - indexed[i].score) < 1e-12
    ) {
      j += 1;
    }
    const shared = i + 1;
    for (let k = i; k <= j; k++) ranks[indexed[k].i] = shared;
    i = j + 1;
  }
  return ranks;
}

function compare(a: SeasonRow, b: SeasonRow, key: SortKey, dir: Direction): number {
  const left = a[key];
  const right = b[key];
  const leftMissing = left === null || left === undefined;
  const rightMissing = right === null || right === undefined;
  if (leftMissing && rightMissing) return 0;
  if (leftMissing) return 1;
  if (rightMissing) return -1;
  const sign = dir === "asc" ? 1 : -1;
  if (typeof left === "number" && typeof right === "number") {
    return (left - right) * sign;
  }
  return String(left).localeCompare(String(right)) * sign;
}

function scoreClass(v: number | null): string {
  if (v === null) return "num muted";
  if (v > 0.35) return "num positive";
  if (v < -0.35) return "num negative";
  return "num";
}

export default function SeasonLedger({
  seasonIndex,
  yearly,
}: {
  seasonIndex?: SeasonFile | null;
  yearly: YearlyFile;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("all_time_rank");
  const [direction, setDirection] = useState<Direction>("asc");
  const [focus, setFocus] = useState<string | null>(null);
  const [onlyScored, setOnlyScored] = useState(true);

  const rows = useMemo<SeasonRow[]>(() => {
    const resume = new Map<string, number>();
    for (const year of yearly.years ?? []) {
      for (const leader of year.leaderboard ?? []) {
        resume.set(`${leader.person_id}|${year.season}`, leader.rank);
      }
    }

    const raw: Omit<SeasonRow, "all_time_rank">[] = [];
    for (const year of seasonIndex?.years ?? []) {
      for (const row of year.leaderboard ?? []) {
        raw.push({
          key: `${row.person_id}|${year.season}`,
          season: year.season,
          person_id: row.person_id,
          name: row.name,
          team: row.teams?.[0] ?? "",
          season_score: row.composite ?? null,
          year_rank: row.rank ?? null,
          gm_count: year.gm_count,
          fully_scored: year.fully_scored !== false,
          resume_rank: resume.get(`${row.person_id}|${year.season}`) ?? null,
          trade_net: row.trade_vintage_net,
          draft_vos: row.draft_immature ? null : row.draft_vintage_vos,
        });
      }
    }

    // All-time ranks only among seasons mature enough to grade — like a
    // single-season leaderboard (#1 = best FO year in the pool).
    const scoreForRank = raw.map((r) =>
      r.fully_scored && r.season_score !== null ? r.season_score : null,
    );
    const allTime = competitionRanks(scoreForRank);
    return raw.map((r, i) => ({ ...r, all_time_rank: allTime[i] }));
  }, [seasonIndex, yearly]);

  const hiddenRecent = useMemo(
    () => rows.filter((r) => !r.fully_scored).length,
    [rows],
  );

  const gradedCount = useMemo(
    () => rows.filter((r) => r.all_time_rank !== null).length,
    [rows],
  );

  const visible = useMemo(() => {
    let list = rows;
    if (onlyScored) list = list.filter((r) => r.fully_scored);
    if (focus) list = list.filter((r) => r.person_id === focus);
    return [...list].sort((a, b) => compare(a, b, sortKey, direction));
  }, [rows, focus, onlyScored, sortKey, direction]);

  const focused = focus
    ? rows.filter((r) => r.person_id === focus && (!onlyScored || r.fully_scored))
    : [];
  const focusName =
    focused[0]?.name ?? rows.find((r) => r.person_id === focus)?.name ?? "";

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection(
        key === "name" || key === "all_time_rank" || key.endsWith("rank")
          ? "asc"
          : "desc",
      );
    }
  }

  if (!seasonIndex?.years?.length) {
    return (
      <p className="empty-note">
        No season data yet. Run <code>python scripts/build_season_index.py</code>.
      </p>
    );
  }

  return (
    <div className="season-ledger">
      <p className="lede">
        Best FO seasons since 2006 — a single-season leaderboard.{" "}
        <strong>#1</strong> is the highest-graded executive-year in the pool
        {gradedCount > 0 ? ` (${gradedCount.toLocaleString()} graded)` : ""}.
        Names can repeat: many elite years for one GM is the finding. Click a
        name to see that executive’s run.
      </p>

      <div className="ledger-controls">
        <label className="toggle">
          <input
            type="checkbox"
            checked={onlyScored}
            onChange={(e) => setOnlyScored(e.target.checked)}
          />
          Hide seasons still too young to grade
          {hiddenRecent > 0 ? ` (${hiddenRecent.toLocaleString()} recent)` : ""}
        </label>
        {focus && (
          <button type="button" className="clear-focus" onClick={() => setFocus(null)}>
            ← Full leaderboard
          </button>
        )}
        <span className="count">
          {visible.length.toLocaleString()} shown
          {focus ? ` · ${focusName}` : ""}
        </span>
      </div>

      {focus && focused.length > 0 && (
        <FocusTimeline rows={focused} name={focusName} />
      )}

      <div className="table-scroll sticky-2">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((col) => {
                const active = col.key === sortKey;
                return (
                  <th
                    key={col.key}
                    className={col.numeric ? "num" : undefined}
                    title={col.help}
                    aria-sort={
                      active ? (direction === "asc" ? "ascending" : "descending") : "none"
                    }
                  >
                    <button type="button" onClick={() => toggleSort(col.key)}>
                      {col.label}
                      <span className="arrow" aria-hidden="true">
                        {active ? (direction === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.key}>
                <td className="num all-time-rank">
                  {r.all_time_rank === null ? "—" : r.all_time_rank}
                </td>
                <td>
                  <button
                    type="button"
                    className="link-name"
                    onClick={() => setFocus(r.person_id)}
                    title={`Show every season for ${r.name}`}
                  >
                    {r.name}
                  </button>
                  <span className="meta">
                    {r.team}
                    {r.trade_net !== null ? ` · trades ${formatSigned(r.trade_net)}` : ""}
                    {r.draft_vos !== null ? ` · draft ${formatSigned(r.draft_vos)}` : ""}
                  </span>
                </td>
                <td className="num date">{r.season}</td>
                <td className={scoreClass(r.season_score)}>
                  {r.season_score === null ? "—" : formatComposite(r.season_score)}
                </td>
                <td
                  className="num muted"
                  title={
                    r.gm_count > 30
                      ? `${r.gm_count} executives that year — mid-season chair changes`
                      : "Rank among GMs graded that calendar year only"
                  }
                >
                  {r.year_rank === null ? "—" : `#${r.year_rank}/${r.gm_count}`}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="empty">
                  Nothing matches. Try unchecking the filter above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** A single executive's career as a run of seasons, best to worst visible at a glance. */
function FocusTimeline({ rows, name }: { rows: SeasonRow[]; name: string }) {
  const ordered = [...rows].sort((a, b) => a.season - b.season);
  const graded = ordered.filter((r) => r.all_time_rank !== null);
  const best = graded.reduce<SeasonRow | null>(
    (acc, r) =>
      !acc || (r.all_time_rank ?? 9999) < (acc.all_time_rank ?? 9999) ? r : acc,
    null,
  );
  const worst = graded.reduce<SeasonRow | null>(
    (acc, r) =>
      !acc || (r.all_time_rank ?? 0) > (acc.all_time_rank ?? 0) ? r : acc,
    null,
  );

  return (
    <div className="focus-timeline">
      <h3>{name}</h3>
      {best && worst && (
        <p className="focus-summary">
          Best all-time finish <strong>#{best.all_time_rank}</strong> ({best.season})
          · worst <strong>#{worst.all_time_rank}</strong> ({worst.season}) ·{" "}
          {graded.length} graded seasons on the leaderboard.
        </p>
      )}
      <ol className="spark">
        {ordered.map((r) => {
          const pct =
            r.all_time_rank === null
              ? 0
              : Math.max(
                  6,
                  Math.min(100, 100 - ((r.all_time_rank - 1) / Math.max(graded.length, 1)) * 94),
                );
          return (
            <li
              key={r.key}
              title={`${r.season}: all-time #${r.all_time_rank ?? "—"} · score ${r.season_score ?? "—"}`}
            >
              <span
                className={
                  r.all_time_rank === null
                    ? "bar none"
                    : (r.all_time_rank ?? 99) <= 10
                      ? "bar top"
                      : (r.all_time_rank ?? 0) >= graded.length - 9
                        ? "bar bottom"
                        : "bar"
                }
                style={{ height: `${pct}%` }}
              />
              <span className="yr">{`'${String(r.season).slice(2)}`}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
