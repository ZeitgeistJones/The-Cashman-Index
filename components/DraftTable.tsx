"use client";

import { useMemo, useState } from "react";
import type { DraftFile, DraftFranchiseRow } from "@/lib/rankings";

type SortKey = "rank" | "team_abbr" | "picks" | "avg_vos" | "total_vos";
type Direction = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "rank", label: "Rank", numeric: true },
  { key: "team_abbr", label: "Franchise", numeric: false },
  { key: "picks", label: "Mature picks", numeric: true },
  { key: "avg_vos", label: "Avg VOS", numeric: true },
  { key: "total_vos", label: "Total VOS", numeric: true },
];

function compare(
  a: DraftFranchiseRow,
  b: DraftFranchiseRow,
  key: SortKey,
  direction: Direction,
): number {
  const left = a[key];
  const right = b[key];
  const sign = direction === "asc" ? 1 : -1;
  if (typeof left === "number" && typeof right === "number") {
    return (left - right) * sign;
  }
  return String(left).localeCompare(String(right)) * sign;
}

export default function DraftTable({ data }: { data: DraftFile }) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [direction, setDirection] = useState<Direction>("asc");

  const sorted = useMemo(
    () =>
      [...data.franchises].sort((a, b) => compare(a, b, sortKey, direction)),
    [data.franchises, sortKey, direction],
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection(key === "team_abbr" || key === "rank" ? "asc" : "desc");
    }
  }

  return (
    <>
      <p className="section-note">{data.framing}</p>
      <p className="section-note">
        Mature classes through {data.mature_through} only (need time to produce
        MLB WAR). Slot #1 historically ~{data.slot_curve["1"]} WAR; late rounds
        near zero. Same curve for every club.
      </p>
      <p className="scroll-hint">Swipe tables sideways for more columns.</p>
      <ul className="stats compact">
        <li>
          Franchises graded
          <span>{data.franchises.length}</span>
        </li>
        <li>
          Mature through
          <span>{data.mature_through}</span>
        </li>
      </ul>
      <div className="table-wrap sticky-2">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((column) => {
                const active = column.key === sortKey;
                return (
                  <th
                    key={column.key}
                    className={column.numeric ? "num" : undefined}
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
            {sorted.map((row) => (
              <tr key={row.team_id}>
                <td className="num">{row.rank}</td>
                <td>
                  <span className="summary">{row.team_name}</span>
                  <span className="meta">{row.team_abbr}</span>
                </td>
                <td className="num">{row.picks}</td>
                <td className="num">
                  {row.avg_vos > 0 ? "+" : ""}
                  {row.avg_vos.toFixed(2)}
                </td>
                <td className="num">
                  {row.total_vos > 0 ? "+" : ""}
                  {row.total_vos.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
