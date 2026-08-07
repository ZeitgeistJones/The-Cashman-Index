"use client";

import { useMemo, useState } from "react";
import {
  formatComposite,
  formatPct,
  formatSigned,
  type FranchiseRow,
} from "@/lib/rankings";
import { formatMoney } from "@/lib/moves";

type SortKey =
  | "rank"
  | "team_abbr"
  | "win_pct"
  | "playoff_depth"
  | "pennants"
  | "world_series"
  | "payroll_efficiency"
  | "draft_vos"
  | "trade_net_rate"
  | "composite";
type Direction = "asc" | "desc";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "rank", label: "Rank", numeric: true },
  { key: "team_abbr", label: "Franchise", numeric: false },
  { key: "world_series", label: "WS", numeric: true },
  { key: "pennants", label: "Pennants", numeric: true },
  { key: "playoff_depth", label: "PO depth", numeric: true },
  { key: "win_pct", label: "Win%", numeric: true },
    { key: "payroll_efficiency", label: "Thrift vs era", numeric: true },
  { key: "draft_vos", label: "Draft VOS", numeric: true },
  { key: "trade_net_rate", label: "Trade/yr", numeric: true },
  { key: "composite", label: "Index", numeric: true },
];

function compare(
  a: FranchiseRow,
  b: FranchiseRow,
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

export default function FranchiseTable({
  franchises,
}: {
  franchises: FranchiseRow[];
}) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [direction, setDirection] = useState<Direction>("asc");

  const sorted = useMemo(
    () => [...franchises].sort((a, b) => compare(a, b, sortKey, direction)),
    [franchises, sortKey, direction],
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
            {sorted.map((row) => (
              <tr key={row.team_id}>
              <td className="num">{row.rank}</td>
              <td>
                <span className="summary">{row.team_name}</span>
                <span className="meta">
                  {row.team_abbr} · {row.wins}-{row.losses}
                  {row.payroll_sum
                    ? ` · ${formatMoney(row.payroll_sum)} payroll`
                    : ""}
                </span>
              </td>
              <td className="num">{row.world_series}</td>
              <td className="num">{row.pennants}</td>
              <td className="num">
                {row.playoff_depth}
                <span className="meta">{row.playoff_appearances} years</span>
              </td>
              <td className="num">{formatPct(row.win_pct)}</td>
              <td className="num">
                {row.payroll_sum
                  ? row.payroll_efficiency.toFixed(2)
                  : "—"}
              </td>
              <td className="num">{formatSigned(row.draft_vos)}</td>
              <td className="num">{formatSigned(row.trade_net_rate)}</td>
              <td className="num">{formatComposite(row.composite)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
