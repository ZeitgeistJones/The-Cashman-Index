/** Curated Mets deals a fan actually argues about — numbers come from the ledger. */

import type { Move } from "@/lib/moves";

export type MetsDeskSide = "good" | "bad" | "open";

export type MetsDeskDealSpec = {
  id: string;
  side: MetsDeskSide;
  headline: string;
  note: string;
};

export type MetsDeskDeal = MetsDeskDealSpec & {
  date: string;
  netWar: number | null;
  surplus: number | null;
  stillPaying: boolean;
};

/**
 * Famous Mets arguments, not raw leaderboard extremes.
 * Lindor +28 is omitted: that row is incoming-only (outgoing package missing).
 */
export const METS_DESK_SPECS: MetsDeskDealSpec[] = [
  {
    id: "121-2012-12-17-TR-51a7b8",
    side: "good",
    headline: "Syndergaard + d'Arnaud for Dickey",
    note: "The one they got right — a Cy Young season for two pieces who became the rotation and the pennant catcher.",
  },
  {
    id: "121-2018-12-03-TR-e8b0a4",
    side: "good",
    headline: "Díaz + Canó for Kelenic, Dunn, Bruce",
    note: "Díaz became a star. Canó and Kelenic are why people still yell. Net WAR up; surplus down. Both can be true.",
  },
  {
    id: "121-2021-07-30-TR-e33d58",
    side: "bad",
    headline: "Báez + Williams for Crow-Armstrong",
    note: "Deadline rental. PCA became a Cubs star. This is the wound.",
  },
  {
    id: "121-2015-07-31-TR-371a34",
    side: "bad",
    headline: "Céspedes for Fulmer + Cessa",
    note: "Helped win a pennant. Fulmer won a Cy Young in Detroit. The Mets nerd fight in one deal.",
  },
  {
    id: "121-2025-11-24-TR-c97c58",
    side: "open",
    headline: "Semien for Nimmo",
    note: "Too new to treat as a verdict — still moving.",
  },
];

export function pickMetsDeskDeals(moves: Move[]): MetsDeskDeal[] {
  const wanted = new Set(METS_DESK_SPECS.map((spec) => spec.id));
  const byId = new Map<string, Move>();
  for (const move of moves) {
    if (wanted.has(move.move_id)) byId.set(move.move_id, move);
  }
  const out: MetsDeskDeal[] = [];
  for (const spec of METS_DESK_SPECS) {
    const move = byId.get(spec.id);
    if (!move) continue;
    out.push({
      ...spec,
      date: move.move_date,
      netWar: move.net_war_exchange ?? null,
      surplus: move.surplus_value ?? null,
      stillPaying: Boolean(move.contract_active),
    });
  }
  return out;
}
