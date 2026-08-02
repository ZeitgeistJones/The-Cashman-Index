"use client";

import { useMemo, useState } from "react";
import { formatMoney, formatWar } from "@/lib/moves";

type ClubRow = {
  team_id: number;
  team_abbr: string;
  team_name: string;
  moves: number;
  war_acquired: number | null;
  net_war: number | null;
  channels: {
    channel: string;
    moves: number;
    war_acquired: number | null;
    net_war: number | null;
  }[];
};

type AcquisitionFile = {
  framing: string;
  clubs: ClubRow[];
  league_channels: {
    channel: string;
    moves: number;
    war_acquired: number | null;
    net_war: number | null;
  }[];
  limitations: string[];
};

const CHANNEL_LABELS: Record<string, string> = {
  free_agent: "Free agents",
  trade: "Trades",
  waiver: "Waivers",
  rule5_or_selected: "Selected / Rule 5",
  signing: "Other signings",
  release: "Releases",
  outright: "Outrights",
  purchase: "Purchases",
  other: "Other",
};

export default function AcquisitionPanel({ data }: { data: AcquisitionFile }) {
  const [teamId, setTeamId] = useState<number | "league">(
    data.clubs[0]?.team_id ?? "league",
  );

  const clubs = useMemo(
    () => [...data.clubs].sort((a, b) => (b.war_acquired || 0) - (a.war_acquired || 0)),
    [data.clubs],
  );

  const selected = useMemo(() => {
    if (teamId === "league") return null;
    return clubs.find((c) => c.team_id === teamId) || null;
  }, [clubs, teamId]);

  const channelRows =
    teamId === "league"
      ? data.league_channels
      : selected?.channels || [];

  return (
    <>
      <p className="section-note">{data.framing}</p>

      <label className="filter-row">
        Club
        <select
          value={teamId === "league" ? "league" : String(teamId)}
          onChange={(e) => {
            const v = e.target.value;
            setTeamId(v === "league" ? "league" : Number(v));
          }}
          aria-label="Select club"
        >
          <option value="league">League totals</option>
          {clubs.map((c) => (
            <option key={c.team_id} value={c.team_id}>
              {c.team_abbr} — {c.team_name}
            </option>
          ))}
        </select>
      </label>

      {selected && (
        <ul className="stats compact">
          <li>
            Moves<span>{selected.moves}</span>
          </li>
          <li>
            WAR in<span>{formatWar(selected.war_acquired)}</span>
          </li>
          <li>
            Net WAR<span>{formatWar(selected.net_war)}</span>
          </li>
        </ul>
      )}

      <p className="section-note">WAR acquired by channel.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Channel</th>
              <th className="num">Moves</th>
              <th className="num">WAR in</th>
              <th className="num">Net WAR</th>
            </tr>
          </thead>
          <tbody>
            {[...channelRows]
              .sort((a, b) => (b.war_acquired || 0) - (a.war_acquired || 0))
              .map((row) => (
                <tr key={row.channel}>
                  <td>{CHANNEL_LABELS[row.channel] || row.channel}</td>
                  <td className="num">{row.moves}</td>
                  <td className="num">{formatWar(row.war_acquired)}</td>
                  <td className="num">{formatWar(row.net_war)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <p className="section-note">
        Club ranking by total WAR acquired (all FO channels).
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Club</th>
              <th className="num">Moves</th>
              <th className="num">WAR in</th>
              <th className="num">Net WAR</th>
            </tr>
          </thead>
          <tbody>
            {clubs.map((row) => (
              <tr key={row.team_id}>
                <td>
                  <span className="summary">{row.team_abbr}</span>
                  <span className="meta">{row.team_name}</span>
                </td>
                <td className="num">{row.moves}</td>
                <td className="num">{formatWar(row.war_acquired)}</td>
                <td className="num">{formatWar(row.net_war)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="section-note">
        Limitations: {data.limitations.join(" ")}
      </p>
    </>
  );
}
