"use client";

import { useMemo, useState } from "react";
import {
  formatComposite,
  formatPct,
  type GmRow,
} from "@/lib/rankings";

type SortKey =
  | "rank"
  | "name"
  | "seasons"
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
  { key: "name", label: "GM", numeric: false },
  { key: "seasons", label: "Seasons", numeric: true },
  { key: "world_series", label: "WS", numeric: true },
  { key: "pennants", label: "Pennants", numeric: true },
  { key: "playoff_depth", label: "PO depth", numeric: true },
  { key: "win_pct", label: "Win%", numeric: true },
  { key: "payroll_efficiency", label: "Wins/$100M", numeric: true },
  { key: "draft_vos", label: "Draft", numeric: true },
  { key: "trade_net_rate", label: "Trade/yr", numeric: true },
  { key: "composite", label: "Index", numeric: true },
];

function compare(a: GmRow, b: GmRow, key: SortKey, direction: Direction): number {
  const left = a[key];
  const right = b[key];
  const sign = direction === "asc" ? 1 : -1;
  if (typeof left === "number" && typeof right === "number") {
    return (left - right) * sign;
  }
  return String(left).localeCompare(String(right)) * sign;
}

export default function GmTable({ gms }: { gms: GmRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [direction, setDirection] = useState<Direction>("asc");
  const [hideSmall, setHideSmall] = useState(false);

  const filtered = useMemo(
    () => (hideSmall ? gms.filter((g) => !g.small_sample) : gms),
    [gms, hideSmall],
  );

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => compare(a, b, sortKey, direction)),
    [filtered, sortKey, direction],
  );

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setDirection(key === "name" || key === "rank" ? "asc" : "desc");
    }
  }

  return (
    <>
      <label className="filter-row">
        <input
          type="checkbox"
          checked={hideSmall}
          onChange={(e) => setHideSmall(e.target.checked)}
        />
        <span>
          Hide small samples (&lt; 3 seasons). Short tenures stay in by default,
          index shrunk toward average.
        </span>
      </label>
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
              <tr key={row.person_id}>
                <td className="num">{row.rank}</td>
                <td>
                  <span className="summary">{row.name}</span>
                  <span className="meta">
                    {row.teams.join(" · ")}
                    {row.still_active ? " · active" : ""}
                    {row.small_sample ? " · small sample" : ""}
                  </span>
                </td>
                <td className="num">{row.seasons}</td>
                <td className="num">{row.world_series}</td>
                <td className="num">{row.pennants}</td>
                <td className="num">{row.playoff_depth}</td>
                <td className="num">{formatPct(row.win_pct)}</td>
                <td className="num">{row.payroll_efficiency.toFixed(1)}</td>
                <td className="num">
                  {row.draft_vos !== undefined
                    ? `${row.draft_vos > 0 ? "+" : ""}${row.draft_vos.toFixed(2)}`
                    : "—"}
                </td>
                <td className="num">
                  {row.trade_net_rate !== undefined
                    ? `${row.trade_net_rate > 0 ? "+" : ""}${row.trade_net_rate.toFixed(2)}`
                    : "—"}
                </td>
                <td className="num">
                  {formatComposite(row.composite)}
                  {row.small_sample && row.tenure_weight !== undefined && (
                    <span
                      className="pending"
                      title={`Raw index ${row.composite_raw?.toFixed(2) ?? "—"}; tenure weight ${(row.tenure_weight * 100).toFixed(0)}% after shrink toward average.`}
                    >
                      {(row.tenure_weight * 100).toFixed(0)}% tenure
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
