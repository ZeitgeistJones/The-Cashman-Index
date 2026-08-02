"use client";

import { useMemo, useState } from "react";
import { formatDate, formatMoney, formatWar, type Move } from "@/lib/moves";

type SortKey = "move_date" | "summary" | "surplus_value" | "net_war_exchange";
type Direction = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "move_date", label: "Date", numeric: false },
  { key: "summary", label: "Move", numeric: false },
  { key: "surplus_value", label: "Surplus Value", numeric: true },
  { key: "net_war_exchange", label: "Net WAR Exchange", numeric: true },
];

function compare(a: Move, b: Move, key: SortKey, direction: Direction): number {
  const left = a[key];
  const right = b[key];
  const leftMissing = left === null || left === undefined;
  const rightMissing = right === null || right === undefined;
  if (leftMissing && rightMissing) return 0;
  if (leftMissing) return 1;
  if (rightMissing) return -1;
  const sign = direction === "asc" ? 1 : -1;
  if (typeof left === "number" && typeof right === "number") {
    return (left - right) * sign;
  }
  return String(left).localeCompare(String(right)) * sign;
}

function scoreClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return "num muted";
  if (value > 0) return "num positive";
  if (value < 0) return "num negative";
  return "num";
}

export default function MovesTable({ moves }: { moves: Move[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("move_date");
  const [direction, setDirection] = useState<Direction>("desc");
  const [club, setClub] = useState<string>("all");

  const clubs = useMemo(() => {
    const set = new Set<string>();
    for (const m of moves) {
      if (m.team_abbr) set.add(m.team_abbr);
    }
    return [...set].sort();
  }, [moves]);

  const filtered = useMemo(
    () =>
      club === "all" ? moves : moves.filter((m) => m.team_abbr === club),
    [moves, club],
  );

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => compare(a, b, sortKey, direction)),
    [filtered, sortKey, direction],
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection(key === "summary" ? "asc" : "desc");
    }
  }

  return (
    <>
      <label className="filter-row">
        Club
        <select
          value={club}
          onChange={(e) => setClub(e.target.value)}
          aria-label="Filter by club"
        >
          <option value="all">All clubs</option>
          {clubs.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((column) => {
                const active = column.key === sortKey;
                return (
                  <th
                    key={column.key}
                    className={column.numeric ? "num" : undefined}
                    aria-sort={
                      active
                        ? direction === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                  >
                    <button type="button" onClick={() => toggleSort(column.key)}>
                      {column.label}
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
            {sorted.map((move) => (
              <tr key={move.move_id}>
                <td className="date">{formatDate(move.move_date)}</td>
                <td>
                  <span className="summary">{move.summary}</span>
                  <span className="meta">
                    {move.team_abbr ? `${move.team_abbr} · ` : ""}
                    {move.move_type}
                    {move.deal_archetype
                      ? ` · ${move.deal_archetype.replaceAll("_", " ")}`
                      : ""}
                    {move.win_now_window ? " · win-now window" : ""}
                    {move.war_acquired !== null && move.war_acquired !== undefined
                      ? ` · during ${formatWar(move.war_acquired)} / sent→ ${formatWar(move.war_sent_away)}`
                      : ""}
                    {move.salary_paid !== null
                      ? ` · ${formatMoney(move.salary_paid)} paid`
                      : ""}
                  </span>
                </td>
                <td className={scoreClass(move.surplus_value)}>
                  {formatMoney(move.surplus_value)}
                  {move.contract_active && move.surplus_value !== null && (
                    <span
                      className="pending"
                      title="Contract still being paid — surplus is a midpoint."
                    >
                      still paying
                    </span>
                  )}
                </td>
                <td className={scoreClass(move.net_war_exchange)}>
                  {formatWar(move.net_war_exchange)}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="empty">
                  No trades for this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
