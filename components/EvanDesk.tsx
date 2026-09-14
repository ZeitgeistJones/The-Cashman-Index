"use client";

import {
  clubSplitsThrough,
  formatClubSplit,
  clubSplitTitle,
  type ClubHitIndex,
} from "@/lib/tenureSplit";
import { formatDate, formatMoney, formatWar } from "@/lib/moves";
import type { MetsDeskDeal } from "@/lib/metsDesk";
import { formatPct, type FranchiseRow, type GmRow, type SeasonFile } from "@/lib/rankings";
import type { LensId } from "@/lib/lenses";

type SeasonMark = { year: number; rank: number; of: number };

function metsSeasonMarks(
  seasonIndex: SeasonFile | null | undefined,
  personId: string,
  years: number[],
): SeasonMark[] {
  if (!seasonIndex) return [];
  const marks: SeasonMark[] = [];
  for (const year of years) {
    const block = seasonIndex.years.find((y) => y.season === year);
    const row = block?.leaderboard.find((g) => g.person_id === personId);
    if (!block || !row) continue;
    if (!row.teams.includes("NYM")) continue;
    marks.push({ year, rank: row.rank, of: block.gm_count });
  }
  return marks;
}

function scoreClass(value: number | null): string {
  if (value === null) return "muted";
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "";
}

export default function EvanDesk({
  mets,
  stearns,
  clubHits,
  throughSeason,
  seasonIndex,
  deals,
  lensLabel,
  onOpenMets,
  onOpenStearnsSeasons,
  onOpenStearnsYear,
  onOpenDraft,
  onOpenTrades,
  onOpenDeal,
  onChooseLens,
}: {
  mets: FranchiseRow | undefined;
  stearns: GmRow | undefined;
  clubHits?: ClubHitIndex;
  throughSeason?: number;
  seasonIndex?: SeasonFile | null;
  deals: MetsDeskDeal[];
  lensLabel: string;
  onOpenMets: () => void;
  onOpenStearnsSeasons: () => void;
  onOpenStearnsYear: (year: number) => void;
  onOpenDraft: () => void;
  onOpenTrades: () => void;
  onOpenDeal: (moveId: string) => void;
  onChooseLens: (id: LensId) => void;
}) {
  if (!mets) return null;

  const ranks = mets.category_ranks ?? {};
  const stearnsSplits =
    stearns && throughSeason != null
      ? clubSplitsThrough(clubHits, stearns.person_id, throughSeason)
      : [];
  const stearnsSplitLabel = formatClubSplit(stearnsSplits);
  const metsYears = metsSeasonMarks(
    seasonIndex,
    "david-stearns",
    [2024, 2025],
  );
  const good = deals.filter((d) => d.side === "good");
  const bad = deals.filter((d) => d.side === "bad");
  const open = deals.filter((d) => d.side === "open");

  return (
    <section className="evan-desk" id="evan-desk" aria-labelledby="evan-desk-heading">
      <p className="start-here-kicker" id="evan-desk-heading">
        Evan Roberts · Mets desk
      </p>
      <h2>Mets nerd starter pack</h2>
      <p className="start-here-lede">
        The fights a Mets fan actually has — spend vs rings, Stearns{" "}
        <em>here</em>, the farm, and a few deals that still start arguments.
        Same numbers as the boards. Not a WFAN show, not a home-team card.
      </p>

      <div className="evan-cards">
        <article className="evan-card">
          <p className="evan-card-kicker">The club · {lensLabel}</p>
          <h3>
            #{mets.rank} Mets
          </h3>
          <p>
            {formatPct(mets.win_pct)} over {mets.seasons} years · {mets.world_series}{" "}
            World Series · {mets.pennants} pennant
            {mets.pennants === 1 ? "" : "s"}. Playoff years:{" "}
            {mets.playoff_years.join(", ") || "—"}.
          </p>
          <p>
            Draft is the quiet good thing (#{ranks.draft_vos ?? "—"}). Thrift is
            not (#{ranks.payroll_efficiency ?? "—"} ·{" "}
            {mets.payroll_efficiency.toFixed(2)}× league). They spend. They
            don&apos;t win cheap.
          </p>
          <button type="button" className="start-here-cta" onClick={onOpenMets}>
            Mets on the club board
          </button>
        </article>

        <article className="evan-card">
          <p className="evan-card-kicker">Stearns here vs there</p>
          <h3>
            {stearns ? `#${stearns.rank} career` : "David Stearns"}
          </h3>
          <p>
            {stearnsSplitLabel ? (
              <>
                Career is{" "}
                <span title={clubSplitTitle(stearnsSplits)}>{stearnsSplitLabel}</span>
                . Milwaukee cheap years still lift thrift and the composite.
                That is not a Mets grade.
              </>
            ) : (
              <>Career still includes Milwaukee. That is not a Mets-only grade.</>
            )}
          </p>
          {metsYears.length ? (
            <p>
              Mets season grades:{" "}
              {metsYears.map((m, i) => (
                <span key={m.year}>
                  {i ? " · " : ""}
                  <button
                    type="button"
                    className="link-name"
                    onClick={() => onOpenStearnsYear(m.year)}
                  >
                    {m.year} #{m.rank}/{m.of}
                  </button>
                </span>
              ))}
              . Use those if the question is “what has he done in Queens.”
            </p>
          ) : null}
          <button
            type="button"
            className="start-here-cta"
            onClick={onOpenStearnsSeasons}
          >
            Stearns season run
          </button>
        </article>

        <article className="evan-card">
          <p className="evan-card-kicker">Spend vs October</p>
          <h3>Did the money buy a title?</h3>
          <p>
            Value weights thrift. October weights rings and depth. Flip the lens
            and watch the Mets move — the ingredients stay the same.
          </p>
          <div className="evan-card-actions">
            <button
              type="button"
              className="start-here-cta secondary"
              onClick={() => onChooseLens("value")}
            >
              Value lens
            </button>
            <button
              type="button"
              className="start-here-cta secondary"
              onClick={() => onChooseLens("october")}
            >
              October lens
            </button>
          </div>
        </article>

        <article className="evan-card">
          <p className="evan-card-kicker">The farm</p>
          <h3>Draft #{ranks.draft_vos ?? "—"}</h3>
          <p>
            Over the whole window the Mets are a top-five draft shop. Trades sit
            around #{ranks.trade_net_rate ?? "—"}. If the take is “they never
            develop anyone,” the draft board disagrees.
          </p>
          <div className="evan-card-actions">
            <button type="button" className="start-here-cta" onClick={onOpenDraft}>
              Draft board
            </button>
            <button
              type="button"
              className="start-here-cta secondary"
              onClick={onOpenTrades}
            >
              Trade rates
            </button>
          </div>
        </article>
      </div>

      {deals.length ? (
        <div className="evan-deals">
          <p className="evan-card-kicker">Deals that still start arguments</p>
          <p className="start-here-lede">
            Ledger net WAR after the deal — not “who won the press conference.”
            Surplus is dollars vs performance; a deal can win WAR and lose money.
          </p>
          <div className="evan-deal-cols">
            <div>
              <h3>Ones they got</h3>
              <ul>
                {good.map((deal) => (
                  <DealRow key={deal.id} deal={deal} onOpen={onOpenDeal} />
                ))}
              </ul>
            </div>
            <div>
              <h3>Ones that still sting</h3>
              <ul>
                {bad.map((deal) => (
                  <DealRow key={deal.id} deal={deal} onOpen={onOpenDeal} />
                ))}
              </ul>
            </div>
          </div>
          {open.length ? (
            <ul className="evan-deal-open">
              {open.map((deal) => (
                <DealRow key={deal.id} deal={deal} onOpen={onOpenDeal} />
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function DealRow({
  deal,
  onOpen,
}: {
  deal: MetsDeskDeal;
  onOpen: (id: string) => void;
}) {
  return (
    <li>
      <button type="button" className="evan-deal" onClick={() => onOpen(deal.id)}>
        <span className="evan-deal-head">
          <strong>{deal.headline}</strong>
          <span className={scoreClass(deal.netWar)}>{formatWar(deal.netWar)}</span>
        </span>
        <span className="evan-deal-meta">
          {formatDate(deal.date)}
          {deal.surplus != null ? ` · surplus ${formatMoney(deal.surplus)}` : ""}
          {deal.stillPaying ? " · still paying" : ""}
        </span>
        <span className="evan-deal-note">{deal.note}</span>
      </button>
    </li>
  );
}
