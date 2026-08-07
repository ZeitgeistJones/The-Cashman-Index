/** Client-side success-lens scoring (same math as scripts/scoring.py). */

import weightsFile from "@/data/weights.json";

export const COMPONENT_KEYS = [
  "world_series_rate",
  "pennants_rate",
  "playoff_depth_rate",
  "win_pct",
  "payroll_efficiency",
  "draft_vos",
  "trade_net_rate",
] as const;

export type ComponentKey = (typeof COMPONENT_KEYS)[number];
export type ComponentWeights = Record<ComponentKey, number>;

export type LensId = "balanced" | "october" | "value" | "builder";

export type LensDef = {
  label: string;
  blurb: string;
  components: ComponentWeights;
};

export const LENS_STORAGE_KEY = "foi-lens";

const lensesRaw = (weightsFile as { lenses?: Record<string, LensDef> }).lenses ?? {};

export const LENSES: Record<LensId, LensDef> = {
  balanced: lensesRaw.balanced as LensDef,
  october: lensesRaw.october as LensDef,
  value: lensesRaw.value as LensDef,
  builder: lensesRaw.builder as LensDef,
};

export const DEFAULT_LENS: LensId =
  ((weightsFile as { default_lens?: string }).default_lens as LensId) ||
  "balanced";

export const TENURE_PRIOR = Number(
  (weightsFile as { tenure_prior_seasons?: number }).tenure_prior_seasons ?? 4,
);

export const LENS_ORDER: LensId[] = ["balanced", "october", "value", "builder"];

export type ScoreableRow = {
  world_series_rate?: number;
  pennants_rate?: number;
  playoff_depth_rate?: number;
  win_pct?: number;
  payroll_efficiency?: number;
  draft_vos?: number;
  trade_net_rate?: number;
  seasons?: number;
  composite?: number;
  composite_raw?: number;
  rank?: number;
  tenure_weight?: number;
};

export function isLensId(value: string | null | undefined): value is LensId {
  return !!value && value in LENSES;
}

export function zscore(values: number[]): number[] {
  if (!values.length) return [];
  if (values.length === 1) return [0];
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance =
    values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  const stdev = Math.sqrt(variance);
  if (stdev < 1e-12) return values.map(() => 0);
  return values.map((v) => (v - mean) / stdev);
}

export function tenureShrink(
  score: number,
  seasons: number,
  prior: number = TENURE_PRIOR,
): number {
  if (seasons <= 0) return 0;
  return round4(score * (seasons / (seasons + Math.max(prior, 0))));
}

function round4(n: number): number {
  return Math.round(n * 10000) / 10000;
}

function componentValue(row: ScoreableRow, key: ComponentKey): number {
  const v = row[key];
  return typeof v === "number" && !Number.isNaN(v) ? v : 0;
}

/** Competition ranks (1 = best); ties share the minimum rank. */
export function rankDescending(scores: number[]): number[] {
  const indexed = scores
    .map((score, i) => ({ score, i }))
    .sort((a, b) => b.score - a.score);
  const ranks = new Array(scores.length).fill(0);
  let i = 0;
  while (i < indexed.length) {
    let j = i;
    while (
      j + 1 < indexed.length &&
      Math.abs(indexed[j + 1].score - indexed[i].score) < 1e-12
    ) {
      j += 1;
    }
    const shared = i + 1;
    for (let k = i; k <= j; k++) ranks[indexed[k].i] = shared;
    i = j + 1;
  }
  return ranks;
}

export function compositeScores(
  rows: ScoreableRow[],
  weights: ComponentWeights,
): number[] {
  if (!rows.length) return [];
  const zByKey: Record<ComponentKey, number[]> = {} as Record<
    ComponentKey,
    number[]
  >;
  for (const key of COMPONENT_KEYS) {
    zByKey[key] = zscore(rows.map((r) => componentValue(r, key)));
  }
  return rows.map((_, i) => {
    let total = 0;
    for (const key of COMPONENT_KEYS) {
      total += (weights[key] ?? 0) * zByKey[key][i];
    }
    return round4(total);
  });
}

export type Rescored<T extends ScoreableRow> = T & {
  composite: number;
  composite_raw: number;
  rank: number;
  tenure_weight: number;
};

/**
 * Recompute composite + rank for a peer set under a lens.
 * When tenurePrior is set (GMs), apply tenure shrink like build_gm_index.
 */
export function rescoreRows<T extends ScoreableRow>(
  rows: T[],
  weights: ComponentWeights,
  opts?: { tenurePrior?: number },
): Rescored<T>[] {
  const rawScores = compositeScores(rows, weights);
  const prior = opts?.tenurePrior;
  const finals = rawScores.map((raw, i) => {
    if (prior === undefined) return raw;
    return tenureShrink(raw, Number(rows[i].seasons ?? 0), prior);
  });
  const ranks = rankDescending(finals);
  return rows.map((row, i) => {
    const seasons = Number(row.seasons ?? 0);
    const tenure_weight =
      prior === undefined || seasons <= 0
        ? 1
        : round4(seasons / (seasons + Math.max(prior, 0)));
    return {
      ...row,
      composite_raw: rawScores[i],
      composite: finals[i],
      rank: ranks[i],
      tenure_weight,
    };
  });
}

export function lensWeights(id: LensId): ComponentWeights {
  return LENSES[id].components;
}
