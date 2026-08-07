"use client";

import { useMemo, useState } from "react";
import TipTh from "@/components/TipTh";
import { COLUMN_TIPS } from "@/lib/columnTips";
import { formatWar } from "@/lib/moves";

type TradeFranchise = {
  team_id: number;
  team_abbr: string;
  team_name: string;
  trades: number;
  net_war: number;
  trade_net_rate: number;
  rank: number;
};

type TradeGm = {
  person_id: string;
  name: string;
  teams: string[];
  trades: number;
  net_war: number;
  trade_net_rate: number;
  rank: number;
};

type TradeFile = {
  framing: string;
  franchises: TradeFranchise[];
  gms: TradeGm[];
};

export default function TradeTable({ data }: { data: TradeFile }) {
  const [view, setView] = useState<"franchises" | "gms">("franchises");

  const franchises = useMemo(
    () => [...data.franchises].sort((a, b) => a.rank - b.rank),
    [data.franchises],
  );
  const gms = useMemo(
    () => [...data.gms].sort((a, b) => a.rank - b.rank).slice(0, 40),
    [data.gms],
  );

  return (
    <>
      <p className="section-note">{data.framing}</p>
      <p className="scroll-hint">Swipe tables sideways for more columns.</p>
      <div className="tabs" role="tablist" aria-label="Trade view">
        <button
          type="button"
          className={view === "franchises" ? "tab active" : "tab"}
          onClick={() => setView("franchises")}
        >
          Franchises
        </button>
        <button
          type="button"
          className={view === "gms" ? "tab active" : "tab"}
          onClick={() => setView("gms")}
        >
          GMs
        </button>
      </div>

      {view === "franchises" ? (
        <div className="table-wrap sticky-2">
          <table>
            <thead>
              <tr>
                <TipTh label="Rank" help={COLUMN_TIPS.rank} static />
                <TipTh label="Franchise" help={COLUMN_TIPS.franchise} static />
                <TipTh
                  label="Trades"
                  help={COLUMN_TIPS.tradesCount}
                  numeric
                  static
                />
                <TipTh
                  label="Net WAR"
                  help={COLUMN_TIPS.netWarSum}
                  numeric
                  static
                />
                <TipTh
                  label="Net/season"
                  help={COLUMN_TIPS.netWarSeason}
                  numeric
                  static
                />
              </tr>
            </thead>
            <tbody>
              {franchises.map((row) => (
                <tr key={row.team_id}>
                  <td className="num">{row.rank}</td>
                  <td>
                    <span className="summary">{row.team_name}</span>
                    <span className="meta">{row.team_abbr}</span>
                  </td>
                  <td className="num">{row.trades}</td>
                  <td className="num">{formatWar(row.net_war)}</td>
                  <td className="num">{formatWar(row.trade_net_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="table-wrap sticky-2">
          <table>
            <thead>
              <tr>
                <TipTh label="Rank" help={COLUMN_TIPS.rank} static />
                <TipTh label="GM" help={COLUMN_TIPS.gm} static />
                <TipTh
                  label="Trades"
                  help={COLUMN_TIPS.tradesCount}
                  numeric
                  static
                />
                <TipTh
                  label="Net WAR"
                  help={COLUMN_TIPS.netWarSum}
                  numeric
                  static
                />
                <TipTh
                  label="Net/season"
                  help={COLUMN_TIPS.netWarSeason}
                  numeric
                  static
                />
              </tr>
            </thead>
            <tbody>
              {gms.map((row) => (
                <tr key={row.person_id}>
                  <td className="num">{row.rank}</td>
                  <td>
                    <span className="summary">{row.name}</span>
                    <span className="meta">{row.teams.join(" · ")}</span>
                  </td>
                  <td className="num">{row.trades}</td>
                  <td className="num">{formatWar(row.net_war)}</td>
                  <td className="num">{formatWar(row.trade_net_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
