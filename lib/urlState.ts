/** Shareable query string for tab / GM view / year / lens / who / club. */

import { DEFAULT_LENS, isLensId, type LensId } from "@/lib/lenses";

export type AppTab =
  | "franchises"
  | "gms"
  | "draft"
  | "trades"
  | "acquisition"
  | "exits"
  | "moves";

export type AppGmView = "career" | "after-year" | "season-grades";

export type AppUrlState = {
  tab: AppTab;
  gmView: AppGmView;
  afterYear: number;
  seasonYear: number | "all";
  lens: LensId;
  who: string | null;
  club: string | null;
};

const TAB_IN: Record<string, AppTab> = {
  clubs: "franchises",
  franchises: "franchises",
  gms: "gms",
  draft: "draft",
  trades: "trades",
  acquire: "acquisition",
  acquisition: "acquisition",
  exits: "exits",
  detail: "moves",
  moves: "moves",
};

const TAB_OUT: Record<AppTab, string> = {
  franchises: "clubs",
  gms: "gms",
  draft: "draft",
  trades: "trades",
  acquisition: "acquire",
  exits: "exits",
  moves: "detail",
};

const VIEW_IN: Record<string, AppGmView> = {
  career: "career",
  after: "after-year",
  seasons: "season-grades",
};

const VIEW_OUT: Record<AppGmView, string> = {
  career: "career",
  "after-year": "after",
  "season-grades": "seasons",
};

export function isAppTab(value: string | null | undefined): value is AppTab {
  return !!value && value in TAB_IN;
}

export function readUrlState(search: string): Partial<AppUrlState> {
  const q = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const out: Partial<AppUrlState> = {};
  const tabRaw = q.get("tab");
  if (tabRaw && TAB_IN[tabRaw]) out.tab = TAB_IN[tabRaw];
  const viewRaw = q.get("view");
  if (viewRaw && VIEW_IN[viewRaw]) out.gmView = VIEW_IN[viewRaw];
  const yearRaw = q.get("year");
  if (yearRaw === "all") {
    out.seasonYear = "all";
  } else if (yearRaw && /^\d{4}$/.test(yearRaw)) {
    const year = Number(yearRaw);
    out.afterYear = year;
    out.seasonYear = year;
  }
  const lensRaw = q.get("lens");
  if (isLensId(lensRaw)) out.lens = lensRaw;
  const who = q.get("who");
  if (who) out.who = who;
  const club = q.get("club");
  if (club) out.club = club.toUpperCase();
  return out;
}

export function writeUrlState(
  state: AppUrlState,
  defaults: { afterYear: number; seasonYear: number | "all" },
): string {
  const q = new URLSearchParams();
  if (state.tab !== "franchises") q.set("tab", TAB_OUT[state.tab]);
  if (state.tab === "gms" && state.gmView !== "career") {
    q.set("view", VIEW_OUT[state.gmView]);
  }
  if (state.tab === "gms" && state.gmView === "after-year") {
    if (state.afterYear !== defaults.afterYear) {
      q.set("year", String(state.afterYear));
    }
  }
  if (state.tab === "gms" && state.gmView === "season-grades") {
    if (state.seasonYear !== "all") q.set("year", String(state.seasonYear));
  }
  if (state.lens !== DEFAULT_LENS) q.set("lens", state.lens);
  if (state.who) q.set("who", state.who);
  if (state.club && state.tab === "franchises") q.set("club", state.club);
  const body = q.toString();
  return body ? `?${body}` : "";
}

export function replaceAppUrl(search: string): void {
  const path = `${window.location.pathname}${search}${window.location.hash}`;
  window.history.replaceState(null, "", path);
}
