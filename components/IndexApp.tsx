"use client";

import { useState } from "react";
import AcquisitionPanel from "@/components/AcquisitionPanel";
import DraftTable from "@/components/DraftTable";
import ExitLedger from "@/components/ExitLedger";
import FranchiseTable from "@/components/FranchiseTable";
import GmTable from "@/components/GmTable";
import MovesTable from "@/components/MovesTable";
import TradeTable from "@/components/TradeTable";
import YearlySecurity from "@/components/YearlySecurity";
import { isSampleData, type MovesFile } from "@/lib/moves";
import type {
  DraftFile,
  ExitFile,
  FranchiseFile,
  GmFile,
  YearlyFile,
} from "@/lib/rankings";

type Tab =
  | "franchises"
  | "gms"
  | "yearly"
  | "draft"
  | "trades"
  | "acquisition"
  | "exits"
  | "moves";

const TABS: { id: Tab; label: string }[] = [
  { id: "franchises", label: "Franchises" },
  { id: "gms", label: "GMs" },
  { id: "yearly", label: "Yearly / exits" },
  { id: "draft", label: "Draft" },
  { id: "trades", label: "Trades" },
  { id: "acquisition", label: "Acquisition channels" },
  { id: "exits", label: "GM exits" },
  { id: "moves", label: "Trade ledger" },
];

export default function IndexApp({
  moves,
  franchises,
  gms,
  exits,
  yearly,
  draft,
  acquisition,
  trade,
}: {
  moves: MovesFile;
  franchises: FranchiseFile;
  gms: GmFile;
  exits: ExitFile;
  yearly: YearlyFile;
  draft: DraftFile;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  acquisition: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  trade: any;
}) {
  const [tab, setTab] = useState<Tab>("franchises");
  const windowLabel = `${franchises.window[0]}–${franchises.window[1]}`;
  const topFranchise = franchises.franchises[0];
  const topGm = gms.gms[0];

  return (
    <main>
      <header>
        <h1>Front Office Index</h1>
        <p className="tagline">
          Every MLB franchise and GM, {windowLabel}: payroll efficiency, draft
          value, peer trades, and results — same weights for everyone.
        </p>
      </header>

      {isSampleData(moves) && (
        <div className="banner">
          <strong>Sample moves data — WAR figures are placeholders.</strong>
          Run the refresh pipeline to replace checked-in JSON with live scores.
        </div>
      )}

      <ul className="stats">
        <li>
          Top franchise
          <span>
            {topFranchise
              ? `#1 ${topFranchise.team_abbr}`
              : "—"}
          </span>
        </li>
        <li>
          Top GM
          <span>{topGm ? topGm.name : "—"}</span>
        </li>
        <li>
          GMs ranked
          <span>{gms.gm_count}</span>
        </li>
        <li>
          Clubs
          <span>{franchises.franchises.length}</span>
        </li>
        <li>
          Window<span>{windowLabel}</span>
        </li>
      </ul>

      <div className="tabs" role="tablist" aria-label="Front Office Index views">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? "tab active" : "tab"}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "franchises" && (
        <section>
          <p className="section-note">
            One score per club for {windowLabel}. Multi-GM tenures combine.
            Payroll efficiency is the largest weight — cheap contention beats
            expensive title runs. Playoff depth scores how far you went (wild
            card exit ≠ World Series appearance).
          </p>
          <FranchiseTable franchises={franchises.franchises} />
        </section>
      )}

      {tab === "gms" && (
        <section>
          <p className="section-note">
            Career ranking for every roster-runner in the window. Multi-team
            careers count as one person. Short tenures are included but
            tenure-shrunk so a one-year spike does not beat a long career
            without context.
          </p>
          <GmTable gms={gms.gms} />
        </section>
      )}

      {tab === "yearly" && (
        <section>
          <YearlySecurity data={yearly} />
        </section>
      )}

      {tab === "draft" && (
        <section>
          <DraftTable data={draft} />
        </section>
      )}

      {tab === "trades" && (
        <section>
          <TradeTable data={trade} />
        </section>
      )}

      {tab === "acquisition" && (
        <section>
          <AcquisitionPanel data={acquisition} />
        </section>
      )}

      {tab === "exits" && (
        <section>
          <p className="section-note">
            Every GM exit in the window with their rate-based resume that day.
            Filter to firings for job-security context.
          </p>
          <ExitLedger data={exits} />
        </section>
      )}

      {tab === "moves" && (
        <section>
          <p className="section-note">
            Peer trade ledger (all clubs): during-tenure WAR in vs what leavers
            produced elsewhere. Season coverage: {moves.season_range[0]}–
            {moves.season_range[1]}. Dollar surplus when salary is on file.
          </p>
          <ul className="stats compact">
            <li>
              Trades<span>{moves.moves.length}</span>
            </li>
            <li>
              Scored
              <span>
                {moves.moves.filter((m) => m.net_war_exchange !== null).length}
              </span>
            </li>
            <li>
              Generated<span>{moves.generated_at.slice(0, 10)}</span>
            </li>
          </ul>
          <MovesTable moves={moves.moves} />
        </section>
      )}
    </main>
  );
}
