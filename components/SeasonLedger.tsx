"use client";

import { useMemo, useState } from "react";
import {
  formatComposite,
  formatSigned,
  type SeasonFile,
  type YearlyFile,
} from "@/lib/rankings";

/** One executive, one season, scored two different ways. */
type SeasonRow = {
  key: string;
  season: number;
  person_id: string;
  name: string;
  team: string;
  /** Grade for this season alone. */
  season_score: number | null;
  season_rank: number | null;
  gm_count: number;
  /** Whether this season's inputs are complete (young drafts stay unscored). */
  fully_scored: boolean;
  /** Where the whole career-to-date stood that year. */
  resume_rank: number | null;
  resume_score: number | null;
  trade_net: number | null;
  draft_vos: number | null;
  stock_share: number | null;
};

type SortKey =
  | "season"
  | "name"
  | "season_score"
  | "season_rank"
  | "resume_rank";
type Direction = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean; help: string }[] = [
  { key: "season", label: "Season", numeric: true, help: "The year being graded" },
  { key: "name", label: "Executive", numeric: false, help: "Who ran the club" },
  {
    key: "season_score",
    label: "This season",
    numeric: true,
    help: "Graded on this year alone — the moves made, not the reputation carried in",
  },
  {
    key: "season_rank",
    label: "Rank that year",
    numeric: true,
    help: "Where this season placed among the 30 clubs in the same year",
  },
  {
    key: "resume_rank",
    label: "Career rank then",
    numeric: true,
    help: "Where the whole career-to-date stood that year — moves slowly, by design",
  },
];

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
  const [sortKey, setSortKey] = useState<SortKey>("season_score");
  const [direction, setDirection] = useState<Direction>("desc");
  const [focus, setFocus] = useState<string | null>(null);
  const [onlyScored, setOnlyScored] = useState(true);

  const rows = useMemo<SeasonRow[]>(() => {
    // Career-to-date standing, keyed by person and year, to sit alongside the
    // standalone grade. The two answer different questions and often disagree.
    const resume = new Map<string, { rank: number; composite: number }>();
    for (const year of yearly.years ?? []) {
      for (const leader of year.leaderboard ?? []) {
        resume.set(`${leader.person_id}|${year.season}`, {
          rank: leader.rank,
          composite: leader.composite,
        });
      }
    }

    const out: SeasonRow[] = [];
    for (const year of seasonIndex?.years ?? []) {
      for (const row of year.leaderboard ?? []) {
        const prior = resume.get(`${row.person_id}|${year.season}`);
        out.push({
          key: `${row.person_id}|${year.season}`,
          season: year.season,
          person_id: row.person_id,
          name: row.name,
          team: row.teams?.[0] ?? "",
          season_score: row.composite ?? null,
          season_rank: row.rank ?? null,
          gm_count: year.gm_count,
          fully_scored: year.fully_scored !== false,
          resume_rank: prior?.rank ?? null,
          resume_score: prior?.composite ?? null,
          trade_net: row.trade_vintage_net,
          draft_vos: row.draft_immature ? null : row.draft_vintage_vos,
          stock_share: row.stock_share ?? null,
        });
      }
    }
    return out;
  }, [seasonIndex, yearly]);

  const visible = useMemo(() => {
    let list = rows;
    if (onlyScored) list = list.filter((r) => r.fully_scored);
    if (focus) list = list.filter((r) => r.person_id === focus);
    return [...list].sort((a, b) => compare(a, b, sortKey, direction));
  }, [rows, focus, onlyScored, sortKey, direction]);

  // Same filter as the table, so the timeline and the row count never disagree
  // about how many seasons this executive has.
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
      // Ranks read best smallest-first; scores and years biggest-first.
      setDirection(key === "name" || key.endsWith("rank") ? "asc" : "desc");
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
        Every executive-season since 2006 in one pool, so a 2011 can be compared
        against a 2008 directly. <strong>This season</strong> grades the year on
        its own; <strong>career rank then</strong> is where the whole record
        stood at the time. A good executive having many good years is a real
        result, so names repeat — that is the finding, not a flaw.
      </p>

      <div className="ledger-controls">
        <label className="toggle">
          <input
            type="checkbox"
            checked={onlyScored}
            onChange={(e) => setOnlyScored(e.target.checked)}
          />
          Hide seasons too recent to grade
        </label>
        {focus && (
          <button type="button" className="clear-focus" onClick={() => setFocus(null)}>
            ← All {rows.length.toLocaleString()} seasons
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

      <div className="table-scroll">
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
                <td className="num date">{r.season}</td>
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
                <td className={scoreClass(r.season_score)}>
                  {r.season_score === null ? "—" : formatComposite(r.season_score)}
                </td>
                <td className="num">
                  {r.season_rank === null ? "—" : `#${r.season_rank} of ${r.gm_count}`}
                </td>
                <td className="num muted">
                  {r.resume_rank === null ? "—" : `#${r.resume_rank}`}
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
  const graded = ordered.filter((r) => r.season_rank !== null);
  const best = graded.reduce<SeasonRow | null>(
    (acc, r) => (!acc || (r.season_rank ?? 99) < (acc.season_rank ?? 99) ? r : acc),
    null,
  );
  const worst = graded.reduce<SeasonRow | null>(
    (acc, r) => (!acc || (r.season_rank ?? 0) > (acc.season_rank ?? 0) ? r : acc),
    null,
  );

  return (
    <div className="focus-timeline">
      <h3>{name}</h3>
      {best && worst && (
        <p className="focus-summary">
          Best season <strong>{best.season}</strong> (#{best.season_rank}) · worst{" "}
          <strong>{worst.season}</strong> (#{worst.season_rank}) · a swing of{" "}
          {(worst.season_rank ?? 0) - (best.season_rank ?? 0)} places across{" "}
          {graded.length} graded seasons.
        </p>
      )}
      <ol className="spark">
        {ordered.map((r) => {
          // Bar height reads as "how high did this season place", so taller is better.
          const pct =
            r.season_rank === null
              ? 0
              : Math.max(6, ((r.gm_count - r.season_rank + 1) / r.gm_count) * 100);
          return (
            <li key={r.key} title={`${r.season}: #${r.season_rank ?? "—"} of ${r.gm_count}`}>
              <span
                className={
                  r.season_rank === null
                    ? "bar none"
                    : r.season_rank <= 5
                      ? "bar top"
                      : r.season_rank >= r.gm_count - 4
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
