/** July-1 chair attribution — same rule as scripts/build_rankings.py. */

export type TenureStint = {
  person_id: string;
  team_id: number;
  team_abbr?: string;
  start?: string | null;
  end?: string | null;
};

export type TeamSeasonRef = {
  team_id: number;
  season: number;
};

export type ClubHit = {
  season: number;
  abbr: string;
};

export type ClubSplit = {
  abbr: string;
  seasons: number;
  first: number;
  last: number;
};

/** person_id → attributed seasons in order */
export type ClubHitIndex = Record<string, ClubHit[]>;

function day(value: string | null | undefined, fallback: string): string {
  if (!value) return fallback;
  return value.slice(0, 10);
}

function chairOnJuly1(
  teamId: number,
  season: number,
  stints: TenureStint[],
): { person_id: string; abbr: string } | null {
  const mid = `${season}-07-01`;
  for (const stint of stints) {
    if (stint.team_id !== teamId) continue;
    const start = day(stint.start, "1900-01-01");
    const end = day(stint.end, "9999-12-31");
    if (start <= mid && mid <= end) {
      return {
        person_id: stint.person_id,
        abbr: stint.team_abbr || String(teamId),
      };
    }
  }
  return null;
}

export function buildClubHits(
  stints: TenureStint[],
  seasons: TeamSeasonRef[],
  windowStart: number,
  windowEnd: number,
): ClubHitIndex {
  const hits: ClubHitIndex = {};
  for (const row of seasons) {
    const year = Number(row.season);
    if (year < windowStart || year > windowEnd) continue;
    const chair = chairOnJuly1(row.team_id, year, stints);
    if (!chair) continue;
    (hits[chair.person_id] ??= []).push({ season: year, abbr: chair.abbr });
  }
  for (const list of Object.values(hits)) {
    list.sort((a, b) => a.season - b.season || a.abbr.localeCompare(b.abbr));
  }
  return hits;
}

export function clubSplitsThrough(
  index: ClubHitIndex | undefined,
  personId: string,
  throughSeason: number,
): ClubSplit[] {
  const events = index?.[personId];
  if (!events?.length) return [];
  const grouped = new Map<string, ClubSplit>();
  const order: string[] = [];
  for (const ev of events) {
    if (ev.season > throughSeason) continue;
    let slot = grouped.get(ev.abbr);
    if (!slot) {
      slot = { abbr: ev.abbr, seasons: 0, first: ev.season, last: ev.season };
      grouped.set(ev.abbr, slot);
      order.push(ev.abbr);
    }
    slot.seasons += 1;
    slot.last = ev.season;
  }
  return order.map((abbr) => grouped.get(abbr)!);
}

export function formatClubSplit(splits: ClubSplit[]): string {
  return splits.map((s) => `${s.abbr} ${s.seasons}`).join(" · ");
}

export function clubSplitTitle(splits: ClubSplit[]): string {
  return splits
    .map((s) =>
      s.first === s.last
        ? `${s.abbr} ${s.first} (${s.seasons})`
        : `${s.abbr} ${s.first}–${s.last} (${s.seasons})`,
    )
    .join(" · ");
}
