/** Shared column-header tooltip copy for ranking tables. */

export const COLUMN_TIPS = {
  rank: "Competition rank in this table (1 = best)",
  franchise: "Club name",
  gm: "General manager / head of baseball ops",
  seasons: "Seasons attributed to this executive in the window",
  ws: "World Series titles in the graded window",
  pennants: "League pennants (AL/NL champions) in the graded window",
  poDepth:
    "Sum of playoff depth scores (wild card = 1 … World Series = 4) across seasons",
  winPct: "Wins ÷ games over attributed seasons",
  thrift:
    "Wins per $100M of opening-day payroll, divided by that year’s league mean, then averaged (1.0 ≈ league-average thrift)",
  draftVos:
    "Draft value over slot — WAR vs historical expectation for that pick’s slot (franchise-tenure WAR for the drafting club)",
  tradeYr:
    "Peer trade net WAR per season (player-movement ledger; league sum ≈ 0)",
  index:
    "Weighted z-score composite of the seven components under the active success lens",
  maturePicks: "Draft picks old enough to have produced measurable MLB WAR",
  avgVos: "Average value-over-slot across mature picks",
  totalVos: "Sum of value-over-slot across mature picks",
  moveDate: "Transaction date",
  move: "What changed hands",
  surplus:
    "Estimated surplus $ vs expected WAR cost while players were on the club",
  netWar:
    "Closed-market net WAR on the move (buyer credit − seller charge on shared player movements)",
  tradesCount: "Number of peer trades in the window",
  netWarSum: "Sum of peer-trade net WAR",
  netWarSeason: "Net trade WAR ÷ seasons in the window",
  acqMoves: "Acquisition events of this type",
  warIn: "WAR produced after arrival for the acquiring club",
  acqNet: "Net WAR contribution from this acquisition channel",
  exitDate: "Date the executive left the chair",
  exitGm: "Executive and club at exit",
  exitResume: "Plain-language career rates through the exit date",
  exitPool:
    "Composite among exited GMs only — not the live active-GM board that day",
  yearlyRank: "Rank among peers on this board for the selected season",
  yearlyIndex: "Composite under the active lens (career grade or construction)",
  stockShare: "Share of club season WAR from this GM’s own regime stock",
  otherArrivals: "FA / waiver / other arrival WAR in the season window",
  clubYear: "Thin results strip — win% / depth / thrift for the Jul-1 chair that year",
} as const;
