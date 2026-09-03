"use client";

import { useMemo, useState } from "react";
import LensToggle from "@/components/LensToggle";
import TipTh from "@/components/TipTh";
import { COLUMN_TIPS } from "@/lib/columnTips";
import { formatDate } from "@/lib/moves";
import {
  LENSES,
  TENURE_PRIOR,
  lensWeights,
  rescoreRows,
  type LensId,
} from "@/lib/lenses";
import {
  formatPct,
  type SeasonFile,
  type SeasonYear,
  type YearlyFile,
  type YearlySeason,
} from "@/lib/rankings";
import {
  clubSplitTitle,
  clubSplitsThrough,
  formatClubSplit,
  type ClubHitIndex,
} from "@/lib/tenureSplit";

export type YearlyMode = "resume" | "construction";

function bestConstructionSeason(years: SeasonYear[]): number | null {
  if (!years.length) return null;
  const fully = [...years].reverse().find((y) => y.fully_scored);
  if (fully) return fully.season;
  const traded = [...years].reverse().find((y) => y.trades_available !== false);
  if (traded) return traded.season;
  return years[years.length - 1].season;
}

function clampPct(share: number): number {
  return Math.round(Math.max(0, Math.min(1, share)) * 100);
}

export default function YearlySecurity({
  data,
  seasonData,
  lensId = "balanced",
  onLensChange,
  lockedMode,
  season: seasonProp,
  onSeasonChange,
  hideSeasonSelect = false,
  onOpenSeasonGrades,
  onOpenAfterYear,
  clubHits,
  onOpenPerson,
}: {
  data: YearlyFile;
  seasonData?: SeasonFile | null;
  lensId?: LensId;
  onLensChange?: (id: LensId) => void;
  /** One question per mount — no inner career-vs-moves toggle. */
  lockedMode: YearlyMode;
  season?: number;
  onSeasonChange?: (year: number) => void;
  hideSeasonSelect?: boolean;
  onOpenSeasonGrades?: (year: number) => void;
  onOpenAfterYear?: (year: number) => void;
  clubHits?: ClubHitIndex;
  onOpenPerson?: (personId: string) => void;
}) {
  const years = data.years;
  const constructionYears = seasonData?.years ?? [];
  const isResume = lockedMode === "resume";
  const seasonOptions = isResume
    ? years.map((y) => y.season)
    : constructionYears.map((y) => y.season);
  const fallbackSeason = isResume
    ? (years.length ? years[years.length - 1].season : 2006)
    : (bestConstructionSeason(constructionYears) ?? 2006);

  const [internalSeason, setInternalSeason] = useState(
    seasonProp ?? fallbackSeason,
  );
  const season = seasonProp ?? internalSeason;

  function chooseSeason(year: number) {
    if (onSeasonChange) onSeasonChange(year);
    else setInternalSeason(year);
  }

  const current: YearlySeason | undefined = useMemo(
    () => years.find((y) => y.season === season),
    [years, season],
  );

  const construction = useMemo(
    () => constructionYears.find((y) => y.season === season),
    [constructionYears, season],
  );

  const resumeBoard = useMemo(() => {
    if (!current) return [];
    const weights = lensWeights(lensId);
    return rescoreRows(current.leaderboard, weights, {
      tenurePrior: TENURE_PRIOR,
    }).sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name));
  }, [current, lensId]);

  const exits = current?.job_security.exits ?? [];
  const lensLabel = LENSES[lensId].label;

  if (isResume && !years.length) {
    return (
      <p className="section-note">No yearly index yet.</p>
    );
  }
  if (!isResume && !constructionYears.length) {
    return (
      <p className="section-note">No season construction grades yet.</p>
    );
  }

  return (
    <>
      {isResume ? (
        <p className="section-note">
          <strong>Standing after {season}.</strong> Full career through this
          season. Earlier clubs still count. For moves in {season} only, use{" "}
          {onOpenSeasonGrades ? (
            <button
              type="button"
              className="link-name"
              onClick={() => onOpenSeasonGrades(season)}
            >
              Season grades
            </button>
          ) : (
            "Season grades"
          )}
          .
        </p>
      ) : (
        <p className="section-note">
          Only moves in that Nov–Oct window. Not the career. Value counted for
          about {seasonData?.horizon_years ?? 3} years after each deal — not
          reweighted by lens. For career standing after {season}, use{" "}
          {onOpenAfterYear ? (
            <button
              type="button"
              className="link-name"
              onClick={() => onOpenAfterYear(season)}
            >
              After this year
            </button>
          ) : (
            "After this year"
          )}
          .
        </p>
      )}
      <p className="scroll-hint">Swipe tables sideways for more columns.</p>

      {!hideSeasonSelect && seasonOptions.length > 0 ? (
        <label className="filter-row">
          Season
          <select
            value={season}
            onChange={(e) => chooseSeason(Number(e.target.value))}
            aria-label="Select season"
          >
            {seasonOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {isResume && current && (
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

          {onLensChange ? (
            <LensToggle value={lensId} onChange={onLensChange} />
          ) : (
            <p className="section-note">{lensLabel} lens.</p>
          )}
          <div className="table-wrap sticky-2">
            <table>
              <thead>
                <tr>
                  <TipTh label="Rank" help={COLUMN_TIPS.yearlyRank} numeric static />
                  <TipTh label="GM" help={COLUMN_TIPS.gm} static />
                  <TipTh label="Seasons" help={COLUMN_TIPS.seasons} numeric static />
                  <TipTh label="Win%" help={COLUMN_TIPS.winPct} numeric static />
                  <TipTh
                    label="Thrift vs league"
                    help={COLUMN_TIPS.thrift}
                    numeric
                    static
                  />
                  <TipTh
                    label="Depth/yr"
                    help="Playoff depth rate through this season"
                    numeric
                    static
                  />
                  <TipTh
                    label="Index"
                    help={COLUMN_TIPS.yearlyIndex}
                    numeric
                    static
                  />
                </tr>
              </thead>
              <tbody>
                {resumeBoard.slice(0, 25).map((row) => (
                  <tr key={row.person_id}>
                    <td className="num">{row.rank}</td>
                    <td>
                      {onOpenPerson ? (
                        <button
                          type="button"
                          className="link-name summary"
                          onClick={() => onOpenPerson(row.person_id)}
                          title={`Season grades for ${row.name}`}
                        >
                          {row.name}
                        </button>
                      ) : (
                        <span className="summary">{row.name}</span>
                      )}
                      <span
                        className="meta"
                        title={
                          clubSplitTitle(
                            clubSplitsThrough(
                              clubHits,
                              row.person_id,
                              season,
                            ),
                          ) || undefined
                        }
                      >
                        {formatClubSplit(
                          clubSplitsThrough(clubHits, row.person_id, season),
                        ) || row.teams.join(" · ")}
                      </span>
                    </td>
                    <td className="num">{row.seasons}</td>
                    <td className="num">{formatPct(row.win_pct)}</td>
                    <td className="num">{row.payroll_efficiency.toFixed(2)}</td>
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
                    <TipTh label="Exit" help={COLUMN_TIPS.exitDate} static />
                    <TipTh label="GM" help={COLUMN_TIPS.gm} static />
                    <TipTh
                      label="Type"
                      help="How the executive left (fired, resigned, contract expired, …)"
                      static
                    />
                    <TipTh label="Seasons" help={COLUMN_TIPS.seasons} numeric static />
                    <TipTh label="Win%" help={COLUMN_TIPS.winPct} numeric static />
                    <TipTh
                      label="Thrift vs league"
                      help={COLUMN_TIPS.thrift}
                      numeric
                      static
                    />
                    <TipTh
                      label="Depth/yr"
                      help="Playoff depth rate through exit"
                      numeric
                      static
                    />
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
                          ? row.payroll_efficiency.toFixed(2)
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

      {isResume && !current && (
        <p className="section-note">No resume board for {season}.</p>
      )}

      {!isResume && construction && (
        <>
          <ul className="stats compact">
            <li>
              GMs graded<span>{construction.gm_count}</span>
            </li>
            <li>
              Trades in window
              <span>
                {construction.trades_available === false
                  ? "none in ledger"
                  : (construction.window_trade_count ?? "—")}
              </span>
            </li>
            <li>
              Draft
              <span>
                {construction.draft_immature ? "too recent" : "scored"}
              </span>
            </li>
          </ul>

          {(construction.trades_available === false ||
            construction.draft_immature) && (
            <p className="section-note">
              {construction.trades_available === false
                ? "Peer trade ledger has no deals in this window (coverage starts 2009) — trade is left blank and dropped from the index, not scored as zero. "
                : null}
              {construction.draft_immature
                ? `Draft class is still inside the ${seasonData?.mature_lag_years ?? 6}-year wait — shown as — and dropped from the index. `
                : null}
              Other arrivals = first club seasons that are not in our draft or
              trade files (FA, Rule 5, intl, gaps) — approximate.
            </p>
          )}

          {!construction.draft_immature &&
            construction.trades_available !== false && (
              <p className="section-note">
                {construction.season} moves window. Trade and other-arrival WAR
                counted for {seasonData?.horizon_years ?? 3} years after the
                deal. Own stock = share of that year’s club WAR from players
                this GM’s regime brought in (0–100%).
              </p>
            )}

          <div className="table-wrap sticky-2">
            <table>
              <thead>
                <tr>
                  <TipTh label="Rank" help={COLUMN_TIPS.yearlyRank} numeric static />
                  <TipTh label="GM" help={COLUMN_TIPS.gm} static />
                  <TipTh
                    label="Trade net"
                    help="H-horizon trade net WAR for moves in this season’s window"
                    numeric
                    static
                  />
                  <TipTh
                    label="Draft VOS"
                    help={COLUMN_TIPS.draftVos}
                    numeric
                    static
                  />
                  <TipTh
                    label="Other arrivals"
                    help={COLUMN_TIPS.otherArrivals}
                    numeric
                    static
                  />
                  <TipTh
                    label="Own stock"
                    help={COLUMN_TIPS.stockShare}
                    numeric
                    static
                  />
                  <TipTh
                    label="Club year"
                    help={COLUMN_TIPS.clubYear}
                    numeric
                    static
                  />
                  <TipTh
                    label="Index"
                    help={COLUMN_TIPS.yearlyIndex}
                    numeric
                    static
                  />
                </tr>
              </thead>
              <tbody>
                {construction.leaderboard.slice(0, 30).map((row) => (
                  <tr key={row.person_id}>
                    <td className="num">{row.rank}</td>
                    <td>
                      {onOpenPerson ? (
                        <button
                          type="button"
                          className="link-name summary"
                          onClick={() => onOpenPerson(row.person_id)}
                          title={`Season grades for ${row.name}`}
                        >
                          {row.name}
                        </button>
                      ) : (
                        <span className="summary">{row.name}</span>
                      )}
                      <span className="meta">{row.teams.join(" · ")}</span>
                    </td>
                    <td
                      className="num"
                      title={
                        row.trade_vintage_net == null
                          ? "Peer trade ledger coverage starts mid-2009 — blank means not collected, not zero trades"
                          : undefined
                      }
                    >
                      {row.trade_vintage_net == null ? (
                        "—"
                      ) : (
                        <>
                          {row.trade_vintage_net > 0 ? "+" : ""}
                          {row.trade_vintage_net.toFixed(2)}
                          <span className="meta">{row.trade_count} deals</span>
                        </>
                      )}
                    </td>
                    <td className="num">
                      {row.draft_vintage_vos == null
                        ? "—"
                        : `${row.draft_vintage_vos > 0 ? "+" : ""}${row.draft_vintage_vos.toFixed(2)}`}
                    </td>
                    <td className="num">
                      {row.fa_vintage_war > 0 ? "+" : ""}
                      {row.fa_vintage_war.toFixed(2)}
                      <span className="meta">{row.fa_arrivals} arrivals</span>
                    </td>
                    <td className="num">{clampPct(row.stock_share)}%</td>
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

      {!isResume && !construction && (
        <p className="section-note">No construction grades for {season}.</p>
      )}
    </>
  );
}
