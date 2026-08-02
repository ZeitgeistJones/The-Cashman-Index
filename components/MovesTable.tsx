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

/** Nulls always sort to the bottom, whichever direction is active. */
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

  const sorted = useMemo(
    () => [...moves].sort((a, b) => compare(a, b, sortKey, direction)),
    [moves, sortKey, direction],
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Numbers and dates are most useful biggest-first; text reads best A-Z.
      setDirection(key === "summary" ? "asc" : "desc");
    }
  }

  return (
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
                  {move.move_type}
                  {move.war_acquired !== null && move.war_acquired !== undefined
                    ? ` · in ${formatWar(move.war_acquired)} WAR / out ${formatWar(move.war_sent_away)} WAR`
                    : ""}
                  {move.salary_paid !== null
                    ? ` · ${formatMoney(move.salary_paid)} paid`
                    : ""}
                </span>
              </td>
              <td className={scoreClass(move.surplus_value)}>
                {formatMoney(move.surplus_value)}
                {move.contract_active && move.surplus_value !== null && (
                  <span className="pending" title="This contract is still being paid, so the score counts the full guarantee against only the WAR banked so far.">
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
                No moves in <code>data/moves.json</code>. Run{" "}
                <code>python scripts/build_moves.py</code> to populate it.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
