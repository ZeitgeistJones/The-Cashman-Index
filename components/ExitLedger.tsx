"use client";

import { useMemo, useState } from "react";
import TipTh from "@/components/TipTh";
import { COLUMN_TIPS } from "@/lib/columnTips";
import { formatDate } from "@/lib/moves";
import { formatResume, type ExitFile, type ExitRow } from "@/lib/rankings";

export default function ExitLedger({ data }: { data: ExitFile }) {
  const [firedOnly, setFiredOnly] = useState(false);

  const rows = useMemo(() => {
    const list = firedOnly
      ? (data.exits ?? []).filter((e) => e.exit_type === "fired")
      : (data.exits ?? []);
    return [...list].sort((a, b) =>
      String(b.exit_date ?? "").localeCompare(String(a.exit_date ?? "")),
    );
  }, [data.exits, firedOnly]);

  return (
    <>
      <ul className="stats compact">
        <li>
          Exits<span>{data.exit_count ?? rows.length}</span>
        </li>
        <li>
          Firings<span>{data.summary?.fired_count ?? "—"}</span>
        </li>
      </ul>

      <label className="filter-row">
        <input
          type="checkbox"
          checked={firedOnly}
          onChange={(e) => setFiredOnly(e.target.checked)}
        />
        Firings only
      </label>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <TipTh label="Date" help={COLUMN_TIPS.exitDate} static />
              <TipTh label="GM / Club" help={COLUMN_TIPS.exitGm} static />
              <TipTh label="Resume at exit" help={COLUMN_TIPS.exitResume} static />
              <TipTh
                label="Exit-pool index"
                help={COLUMN_TIPS.exitPool}
                numeric
                static
              />
            </tr>
          </thead>
          <tbody>
            {rows.map((row: ExitRow) => (
              <tr key={`${row.person_id}-${row.exit_date}-${row.team_abbr}`}>
                <td className="date">
                  {row.exit_date ? formatDate(row.exit_date) : "—"}
                </td>
                <td>
                  <span className="summary">{row.name}</span>
                  <span className="meta">
                    {row.team_abbr} ·{" "}
                    {(row.exit_type ?? "other").replaceAll("_", " ")}
                  </span>
                </td>
                <td className="resume-cell">
                  {row.peer_resume ? formatResume(row.peer_resume) : "—"}
                </td>
                <td className="num">
                  {row.peer_score != null
                    ? row.peer_score.toFixed(2)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
