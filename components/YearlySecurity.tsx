"use client";

import { useMemo, useState } from "react";
import { formatPct, type YearlyFile, type YearlySeason } from "@/lib/rankings";

export default function YearlySecurity({ data }: { data: YearlyFile }) {
  const years = data.years;
  const [season, setSeason] = useState(
    years.length ? years[years.length - 1].season : 2006,
  );

  const current: YearlySeason | undefined = useMemo(
    () => years.find((y) => y.season === season),
    [years, season],
  );

  if (!years.length) {
    return (
      <p className="section-note">
        No yearly index yet. Run the rankings pipeline.
      </p>
    );
  }

  return (
    <>
      <p className="section-note">
        Active GM leaderboard by season (rate index to that date), plus who left
        in the following offseason.
      </p>

      <label className="filter-row">
        Season
        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          aria-label="Select season"
        >
          {years.map((y) => (
            <option key={y.season} value={y.season}>
              {y.season}
            </option>
          ))}
        </select>
      </label>

      {current && (
        <>
          <ul className="stats compact">
            <li>
              Active GMs<span>{current.active_gm_count}</span>
            </li>
            <li>
              Offseason exits
              <span>{current.job_security.exits_in_cycle}</span>
            </li>
          </ul>

          <p className="section-note">
            Active GM leaderboard for {current.season} (rate index to date).
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th className="num">Rank</th>
                  <th>GM</th>
                  <th className="num">Seasons</th>
                  <th className="num">Win%</th>
                  <th className="num">Wins/$100M</th>
                  <th className="num">Depth/yr</th>
                  <th className="num">Index</th>
                </tr>
              </thead>
              <tbody>
                {current.leaderboard.slice(0, 25).map((row) => (
                  <tr key={row.person_id}>
                    <td className="num">{row.rank}</td>
                    <td>
                      <span className="summary">{row.name}</span>
                      <span className="meta">{row.teams.join(" · ")}</span>
                    </td>
                    <td className="num">{row.seasons}</td>
                    <td className="num">{formatPct(row.win_pct)}</td>
                    <td className="num">{row.payroll_efficiency.toFixed(1)}</td>
                    <td className="num">{row.playoff_depth_rate.toFixed(2)}</td>
                    <td className="num">
                      {row.composite > 0 ? "+" : ""}
                      {row.composite.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
