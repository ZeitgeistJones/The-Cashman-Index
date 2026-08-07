"use client";

import { useMemo, useState } from "react";
import { formatDate } from "@/lib/moves";
import {
  formatPct,
  type SeasonFile,
  type YearlyFile,
  type YearlySeason,
} from "@/lib/rankings";

type Mode = "resume" | "construction";

export default function YearlySecurity({
  data,
  seasonData,
}: {
  data: YearlyFile;
  seasonData?: SeasonFile | null;
}) {
  const years = data.years;
  const constructionYears = seasonData?.years ?? [];
  const hasConstruction = constructionYears.length > 0;
  const [mode, setMode] = useState<Mode>("resume");
  const [season, setSeason] = useState(
    years.length ? years[years.length - 1].season : 2006,
  );

  const seasonOptions = useMemo(() => {
    if (mode === "construction" && hasConstruction) {
      return constructionYears.map((y) => y.season);
    }
    return years.map((y) => y.season);
  }, [mode, hasConstruction, constructionYears, years]);

  const current: YearlySeason | undefined = useMemo(
    () => years.find((y) => y.season === season),
    [years, season],
  );

  const construction = useMemo(
    () => constructionYears.find((y) => y.season === season),
    [constructionYears, season],
  );

  const exits = current?.job_security.exits ?? [];

  if (!years.length && !hasConstruction) {
    return (
      <p className="section-note">
        No yearly index yet. Run the rankings pipeline.
      </p>
    );
  }

  return (
    <>
      <p className="section-note">
        <strong>Resume</strong> = career-to-date rate index through that season
        (plus who left in the offseason). <strong>Construction</strong> = true
        single-season FO craft: moves in the Nov–Oct window, WAR through a{" "}
        {seasonData?.horizon_years ?? 3}-year horizon, own-regime roster share,
        and a thin club-results strip — living revision, not what people thought
        in October.
      </p>
      <p className="scroll-hint">Swipe tables sideways for more columns.</p>

      <div className="filter-row mode-toggle">
        <button
          type="button"
          className={mode === "resume" ? "active" : undefined}
          onClick={() => {
            setMode("resume");
            if (years.length) setSeason(years[years.length - 1].season);
          }}
        >
          Resume as of season
        </button>
        <button
          type="button"
          className={mode === "construction" ? "active" : undefined}
          disabled={!hasConstruction}
          onClick={() => {
            setMode("construction");
            if (constructionYears.length) {
              setSeason(constructionYears[constructionYears.length - 1].season);
            }
          }}
        >
          Season construction
        </button>
      </div>

      <label className="filter-row">
        Season
        <select
          value={season}
          onChange={(e) => setSeason(Number(e.target.value))}
          aria-label="Select season"
        >
          {seasonOptions.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </label>

      {mode === "resume" && current && (
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
            Resume leaderboard for {current.season} (career rates to date).
          </p>
          <div className="table-wrap sticky-2">
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

          <p className="section-note">
            Offseason exits after {current.season} (fired / contract expired
            before the next July 1).
          </p>
          {exits.length === 0 ? (
            <p className="section-note">No tracked exits in this cycle.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Exit</th>
                    <th>GM</th>
                    <th>Type</th>
                    <th className="num">Seasons</th>
                    <th className="num">Win%</th>
                    <th className="num">Wins/$100M</th>
                    <th className="num">Depth/yr</th>
                  </tr>
                </thead>
                <tbody>
                  {exits.map((row) => (
                    <tr
                      key={`${row.person_id}-${row.exit_date}-${row.team_abbr}`}
                    >
                      <td className="num">
                        {row.exit_date ? formatDate(row.exit_date) : "—"}
                      </td>
                      <td>
                        <span className="summary">{row.name}</span>
                        <span className="meta">{row.team_abbr}</span>
                      </td>
                      <td>{row.exit_type?.replace(/_/g, " ") ?? "—"}</td>
                      <td className="num">{row.seasons ?? "—"}</td>
                      <td className="num">
                        {row.win_pct != null ? formatPct(row.win_pct) : "—"}
                      </td>
                      <td className="num">
                        {row.payroll_efficiency != null
                          ? row.payroll_efficiency.toFixed(1)
                          : "—"}
                      </td>
                      <td className="num">
                        {row.playoff_depth_rate != null
                          ? row.playoff_depth_rate.toFixed(2)
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {mode === "construction" && construction && (
        <>
          <ul className="stats compact">
            <li>
              GMs graded<span>{construction.gm_count}</span>
            </li>
            <li>
              Window
              <span>
                {construction.attribution_window[0]?.slice(0, 10)} →{" "}
                {construction.attribution_window[1]?.slice(0, 10)}
              </span>
            </li>
            <li>
              Draft
              <span>
                {construction.draft_immature ? "immature" : "scored"}
              </span>
            </li>
          </ul>

          <p className="section-note">
            Construction grades for {construction.season}. Draft VOS is null
            until the class clears the mature lag (
            {seasonData?.mature_lag_years ?? 6} years). Trade/FA WAR clipped to
            deal date + {seasonData?.horizon_years ?? 3} years.
          </p>
          <div className="table-wrap sticky-2">
            <table>
              <thead>
                <tr>
                  <th className="num">Rank</th>
                  <th>GM</th>
                  <th className="num">Trade net</th>
                  <th className="num">Draft VOS</th>
                  <th className="num">FA WAR</th>
                  <th className="num">Own stock</th>
                  <th className="num">Results</th>
                  <th className="num">Index</th>
                </tr>
              </thead>
              <tbody>
                {construction.leaderboard.slice(0, 30).map((row) => (
                  <tr key={row.person_id}>
                    <td className="num">{row.rank}</td>
                    <td>
                      <span className="summary">{row.name}</span>
                      <span className="meta">{row.teams.join(" · ")}</span>
                    </td>
                    <td className="num">
                      {row.trade_vintage_net > 0 ? "+" : ""}
                      {row.trade_vintage_net.toFixed(2)}
                      <span className="meta">{row.trade_count} deals</span>
                    </td>
                    <td className="num">
                      {row.draft_vintage_vos == null
                        ? "—"
                        : `${row.draft_vintage_vos > 0 ? "+" : ""}${row.draft_vintage_vos.toFixed(2)}`}
                    </td>
                    <td className="num">
                      {row.fa_vintage_war > 0 ? "+" : ""}
                      {row.fa_vintage_war.toFixed(2)}
                    </td>
                    <td className="num">
                      {(row.stock_share * 100).toFixed(0)}%
                    </td>
                    <td className="num">{row.season_results.toFixed(2)}</td>
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

      {mode === "construction" && !construction && (
        <p className="section-note">
          No construction grades for {season}. Run{" "}
          <code>python scripts/build_season_index.py</code>.
        </p>
      )}
    </>
  );
}
