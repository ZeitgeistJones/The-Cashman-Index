export type CategoryRanks = Record<string, number>;

export type FranchiseRow = {
  team_id: number;
  team_abbr: string;
  team_name: string;
  seasons: number;
  wins: number;
  losses: number;
  win_pct: number;
  playoff_appearances: number;
  playoff_depth: number;
  playoff_years: number[];
  pennants: number;
  world_series: number;
  world_series_rate?: number;
  pennants_rate?: number;
  playoff_depth_rate?: number;
  payroll_sum: number | null;
  payroll_efficiency: number;
  draft_vos?: number;
  trade_net_rate?: number;
  composite: number;
  rank: number;
  category_ranks?: CategoryRanks;
};

export type FranchiseFile = {
  generated_at: string;
  window: number[];
  weights: Record<string, number>;
  franchises: FranchiseRow[];
};

export type GmRow = {
  person_id: string;
  name: string;
  teams: string[];
  still_active: boolean;
  small_sample: boolean;
  seasons: number;
  wins: number;
  losses: number;
  win_pct: number;
  playoff_appearances: number;
  playoff_depth: number;
  pennants: number;
  world_series: number;
  world_series_rate?: number;
  pennants_rate?: number;
  playoff_depth_rate?: number;
  payroll_sum: number | null;
  payroll_efficiency: number;
  draft_vos?: number;
  trade_net_rate?: number;
  composite: number;
  composite_raw?: number;
  tenure_weight?: number;
  rank: number;
  category_ranks?: CategoryRanks;
};

export type GmFile = {
  generated_at: string;
  window: number[];
  weights: Record<string, number>;
  gm_count: number;
  gms: GmRow[];
};

export type Resume = {
  seasons: number;
  wins: number;
  losses: number;
  win_pct: number;
  playoff_appearances: number;
  playoff_depth: number;
  pennants: number;
  world_series: number;
  world_series_rate?: number;
  playoff_depth_rate?: number;
  payroll_sum: number | null;
  payroll_efficiency: number;
};

export type ExitRow = {
  exit_date: string;
  exit_type: string;
  person_id: string;
  name: string;
  team_id: number;
  team_abbr: string;
  peer_resume: Resume;
  peer_score?: number;
};

export type ExitFile = {
  generated_at: string;
  window: number[];
  as_of: string;
  exit_count: number;
  summary: {
    fired_count: number;
  };
  exits: ExitRow[];
};

export type YearlyLeader = {
  rank: number;
  person_id: string;
  name: string;
  teams: string[];
  composite: number;
  category_ranks: CategoryRanks;
  seasons: number;
  win_pct: number;
  payroll_efficiency: number;
  world_series_rate: number;
  playoff_depth_rate: number;
};

export type YearlySeason = {
  season: number;
  active_gm_count: number;
  job_security: {
    exits_in_cycle: number;
    exits?: {
      person_id?: string;
      name: string;
      team_abbr?: string;
      exit_type?: string;
      exit_date?: string;
      seasons?: number;
      payroll_efficiency?: number;
      win_pct?: number;
      world_series_rate?: number;
      playoff_depth_rate?: number;
    }[];
  };
  leaderboard: YearlyLeader[];
};

export type YearlyFile = {
  generated_at: string;
  window: number[];
  weights: Record<string, number>;
  framing: string;
  summary: {
    years: number;
    cycles_with_exits: number;
  };
  years: YearlySeason[];
};

export type SeasonConstructionRow = {
  person_id: string;
  name: string;
  teams: string[];
  trade_vintage_net: number;
  trade_count: number;
  draft_vintage_vos: number | null;
  draft_immature: boolean;
  draft_picks: number;
  fa_vintage_war: number;
  fa_arrivals: number;
  stock_share: number;
  season_results: number;
  composite: number;
  rank: number;
};

export type SeasonYear = {
  season: number;
  attribution_window: string[];
  draft_immature: boolean;
  gm_count: number;
  leaderboard: SeasonConstructionRow[];
};

export type SeasonFile = {
  generated_at: string;
  as_of: string;
  window: number[];
  horizon_years: number;
  mature_lag_years: number;
  weights: Record<string, number>;
  framing: string;
  years: SeasonYear[];
};

export type DraftFranchiseRow = {
  team_id: number;
  team_abbr: string;
  team_name: string;
  picks: number;
  avg_vos: number;
  total_vos: number;
  rank: number;
};

export type DraftGmRow = {
  person_id: string;
  name: string;
  teams: string[];
  picks: number;
  avg_vos: number;
  total_vos: number;
  rank: number;
};

export type DraftFile = {
  generated_at: string;
  window: number[];
  mature_through: number;
  slot_curve: Record<string, number>;
  framing: string;
  franchises: DraftFranchiseRow[];
  gms: DraftGmRow[];
};

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(3).replace(/^0/, "");
}

export function formatComposite(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}

export function formatResume(r: Resume): string {
  const depthRate =
    r.playoff_depth_rate !== undefined
      ? r.playoff_depth_rate.toFixed(2)
      : String(r.playoff_depth);
  return `${r.world_series} WS · ${r.pennants} pennants · depth/yr ${depthRate} · ${formatPct(r.win_pct)} · ${r.payroll_efficiency.toFixed(1)} wins/$100M · ${r.seasons} seasons`;
}
