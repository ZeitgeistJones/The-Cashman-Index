"use client";

import Link from "next/link";
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
  FranchiseRow,
  GmFile,
  SeasonFile,
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

const TABS: { id: Tab; label: string; short: string }[] = [
  { id: "franchises", label: "Clubs", short: "Clubs" },
  { id: "gms", label: "GMs", short: "GMs" },
  { id: "yearly", label: "By year", short: "Year" },
  { id: "draft", label: "Draft", short: "Draft" },
  { id: "trades", label: "Trades", short: "Trades" },
  { id: "acquisition", label: "How they acquire", short: "Acquire" },
  { id: "exits", label: "Exits", short: "Exits" },
  { id: "moves", label: "Trade detail", short: "Detail" },
];

function whyTopFranchise(row: FranchiseRow): string[] {
  const ranks = row.category_ranks ?? {};
  const bullets: string[] = [];
  const add = (text: string) => {
    if (bullets.length < 3) bullets.push(text);
  };

  if ((ranks.world_series_rate ?? 99) <= 5 || row.world_series > 0) {
    add(
      `${row.world_series} World Series in the window` +
        ((ranks.world_series_rate ?? 99) === 1 ? " (best title rate)" : ""),
    );
  }
  if ((ranks.playoff_depth_rate ?? 99) <= 5) {
    add("Deep Octobers — playoff depth ranks near the top");
  }
  if ((ranks.draft_vos ?? 99) <= 5) {
    add(
      `Draft value over slot ${row.draft_vos != null && row.draft_vos > 0 ? "positive" : "competitive"} (category rank #${ranks.draft_vos})`,
    );
  }
  if ((ranks.win_pct ?? 99) <= 5) {
    add(`Wins a lot of regular-season games (${(row.win_pct * 100).toFixed(1)}%)`);
  }
  if ((ranks.payroll_efficiency ?? 99) <= 10) {
    add("Wins efficiently relative to opening-day payroll");
  } else if ((ranks.payroll_efficiency ?? 0) >= 20) {
    add(
      "Not a cheap-payroll story — the index still rewards titles and depth heavily enough to lead",
    );
  }
  if ((ranks.trade_net_rate ?? 99) <= 5) {
    add("Peer trade ledger ranks among the better books");
  }
  if (!bullets.length) {
    add(`Composite ${row.composite > 0 ? "+" : ""}${row.composite.toFixed(2)} leads the league window`);
  }
  return bullets.slice(0, 3);
}

export default function IndexApp({
  moves,
  franchises,
  gms,
  exits,
  yearly,
  seasonIndex,
  draft,
  acquisition,
  trade,
}: {
  moves: MovesFile;
  franchises: FranchiseFile;
  gms: GmFile;
  exits: ExitFile;
  yearly: YearlyFile;
  seasonIndex?: SeasonFile | null;
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
  const why = topFranchise ? whyTopFranchise(topFranchise) : [];

  return (
    <main>
      <header>
        <div className="site-header-row">
          <h1>Front Office Index</h1>
          <Link href="/about" className="about-link">
            About
          </Link>
        </div>
        <p className="tagline">
          All 30 clubs and every GM, {windowLabel} — same weights for everyone.
        </p>
      </header>

      {isSampleData(moves) && (
        <div className="banner">
          <strong>Sample trade ledger — WAR figures are placeholders.</strong>
        </div>
      )}

      {topFranchise && (
        <section className="start-here" aria-labelledby="start-here-heading">
          <p className="start-here-kicker" id="start-here-heading">
            Start here
          </p>
          <h2>
            #{topFranchise.rank} {topFranchise.team_name}
          </h2>
          <p className="start-here-lede">
            Leads the franchise board
            {topGm ? (
              <>
                {" "}
                · top GM right now: <strong>{topGm.name}</strong>
              </>
            ) : null}
            .
          </p>
          <ul className="start-here-why">
            {why.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <div className="start-here-actions">
            <button
              type="button"
              className="start-here-cta"
              onClick={() => setTab("franchises")}
            >
              See all clubs
            </button>
            <button
              type="button"
              className="start-here-cta secondary"
              onClick={() => setTab("yearly")}
            >
              Grades by year
            </button>
            <Link href="/about" className="start-here-more">
              How scoring works
            </Link>
          </div>
        </section>
      )}

      <p className="meta-line">
        {franchises.franchises.length} clubs · {gms.gm_count} GMs · {windowLabel}
      </p>

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
            <span className="tab-label-full">{item.label}</span>
            <span className="tab-label-short">{item.short}</span>
          </button>
        ))}
      </div>

      {tab === "franchises" && (
        <section>
          <p className="section-note">
            One score per club. Payroll efficiency is the biggest weight; blank
            cells mean missing data, not a zero.
          </p>
          <p className="scroll-hint">Swipe tables sideways for more columns.</p>
          <FranchiseTable franchises={franchises.franchises} />
        </section>
      )}

      {tab === "gms" && (
        <section>
          <p className="section-note">
            Career grades. Short tenures are shrunk so a one-year spike does not
            win by default. “Small sample” means fewer seasons on file.
          </p>
          <p className="scroll-hint">Swipe tables sideways for more columns.</p>
          <GmTable gms={gms.gms} />
        </section>
      )}

      {tab === "yearly" && (
        <section>
          <YearlySecurity data={yearly} seasonData={seasonIndex} />
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
            Who left the chair and what their rate resume looked like that day.
          </p>
          <p className="scroll-hint">Swipe tables sideways for more columns.</p>
          <ExitLedger data={exits} />
        </section>
      )}

      {tab === "moves" && (
        <section>
          <p className="section-note">
            Deep dive: every scored peer trade in the ledger (
            {moves.season_range[0]}–{moves.season_range[1]}). Start with Clubs or
            Trades if you just want the rankings.
          </p>
          <p className="scroll-hint">Swipe for surplus &amp; net WAR.</p>
          <MovesTable moves={moves.moves} />
        </section>
      )}
    </main>
  );
}
