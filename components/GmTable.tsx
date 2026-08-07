"use client";

import { useMemo, useState } from "react";
import TipTh from "@/components/TipTh";
import { COLUMN_TIPS } from "@/lib/columnTips";
import {
  formatComposite,
  formatPct,
  formatSigned,
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

const COLUMNS: {
  key: SortKey;
  label: string;
  numeric: boolean;
  help: string;
}[] = [
  { key: "rank", label: "Rank", numeric: true, help: COLUMN_TIPS.rank },
  { key: "name", label: "GM", numeric: false, help: COLUMN_TIPS.gm },
  { key: "seasons", label: "Seasons", numeric: true, help: COLUMN_TIPS.seasons },
  { key: "world_series", label: "WS", numeric: true, help: COLUMN_TIPS.ws },
  { key: "pennants", label: "Pennants", numeric: true, help: COLUMN_TIPS.pennants },
  { key: "playoff_depth", label: "PO depth", numeric: true, help: COLUMN_TIPS.poDepth },
  { key: "win_pct", label: "Win%", numeric: true, help: COLUMN_TIPS.winPct },
  {
    key: "payroll_efficiency",
    label: "Thrift vs era",
    numeric: true,
    help: COLUMN_TIPS.thrift,
  },
  { key: "draft_vos", label: "Draft", numeric: true, help: COLUMN_TIPS.draftVos },
  {
    key: "trade_net_rate",
    label: "Trade/yr",
    numeric: true,
    help: COLUMN_TIPS.tradeYr,
  },
  { key: "composite", label: "Index", numeric: true, help: COLUMN_TIPS.index },
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
          index shrunk toward 0.
        </span>
      </label>
      <div className="table-wrap sticky-2">
        <table>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <TipTh
                  key={column.key}
                  label={column.label}
                  help={column.help}
                  numeric={column.numeric}
                  active={column.key === sortKey}
                  direction={direction}
                  onSort={() => toggleSort(column.key)}
                />
              ))}
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
                <td className="num">
                  {row.payroll_sum ? row.payroll_efficiency.toFixed(2) : "—"}
                </td>
                <td className="num">{formatSigned(row.draft_vos)}</td>
                <td
                  className="num"
                  title={
                    row.trade_net_rate == null
                      ? "Peer trade ledger coverage starts mid-2009 — blank means not collected, not zero trades"
                      : undefined
                  }
                >
                  {formatSigned(row.trade_net_rate)}
                </td>
                <td className="num">
                  {formatComposite(row.composite)}
                  {row.small_sample && row.tenure_weight !== undefined && (
                    <span
                      className="pending"
                      title={`Raw index ${row.composite_raw?.toFixed(2) ?? "—"}; tenure weight ${(row.tenure_weight * 100).toFixed(0)}% after shrink toward 0.`}
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
