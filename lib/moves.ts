export type Player = {
  mlbam_id: number;
  name: string;
  war_after_move?: number | null;
};

export type Move = {
  move_id: string;
  move_date: string;
  move_type: string;
  summary: string;
  players_acquired: Player[];
  players_sent_away: Player[];
  salary_paid: number | null;
  contract_years: number | null;
  /** True while the deal is still being paid — the surplus is a midpoint, not a verdict. */
  contract_active?: boolean | null;
  surplus_value: number | null;
  net_war_exchange: number | null;
  war_acquired?: number | null;
  war_sent_away?: number | null;
  salary_source?: string | null;
  counterparty?: string | null;
};

export type MovesFile = {
  generated_at: string;
  /** "sample" means the checked-in placeholder data, not a real pipeline run. */
  data_source: string;
  /** [firstYear, lastYear] — a plain array so the JSON import widens cleanly. */
  season_range: number[];
  dollars_per_war: number;
  move_count: number;
  moves: Move[];
};

export function isSampleData(file: MovesFile): boolean {
  return file.data_source === "sample";
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) return iso;
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

/** Compact signed dollars: -$12.4M, $1.03B. */
export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

/** Signed WAR to one decimal: +3.4, -1.2, 0.0. */
export function formatWar(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const rounded = value.toFixed(1);
  return value > 0 ? `+${rounded}` : rounded;
}
