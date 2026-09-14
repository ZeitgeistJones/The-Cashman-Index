"use client";

import { useMemo, useRef, useState, type KeyboardEvent } from "react";

export type FindHit =
  | { kind: "gm"; id: string; label: string; hint: string }
  | { kind: "club"; id: string; label: string; hint: string };

function normalize(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, " ");
}

function scoreHit(query: string, hay: string): number {
  const q = normalize(query);
  const h = normalize(hay);
  if (!q || !h) return 0;
  if (h === q) return 100;
  if (h.startsWith(q)) return 80;
  if (h.includes(q)) return 50;
  const parts = q.split(" ").filter(Boolean);
  if (parts.length && parts.every((p) => h.includes(p))) return 40;
  return 0;
}

export default function FindBox({
  gms,
  clubs,
  onPickGm,
  onPickClub,
}: {
  gms: { person_id: string; name: string; teams: string[] }[];
  clubs: { team_abbr: string; team_name: string }[];
  onPickGm: (personId: string) => void;
  onPickClub: (abbr: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const hits = useMemo<FindHit[]>(() => {
    const q = query.trim();
    if (q.length < 1) return [];
    const gmHits: { hit: FindHit; score: number }[] = [];
    for (const gm of gms) {
      const score = Math.max(
        scoreHit(q, gm.name),
        scoreHit(q, gm.person_id.replace(/-/g, " ")),
        scoreHit(q, gm.teams.join(" ")),
      );
      if (score > 0) {
        gmHits.push({
          score,
          hit: {
            kind: "gm",
            id: gm.person_id,
            label: gm.name,
            hint: gm.teams.join(" · "),
          },
        });
      }
    }
    const clubHits: { hit: FindHit; score: number }[] = [];
    for (const club of clubs) {
      const score = Math.max(
        scoreHit(q, club.team_name),
        scoreHit(q, club.team_abbr),
      );
      if (score > 0) {
        clubHits.push({
          score,
          hit: {
            kind: "club",
            id: club.team_abbr,
            label: club.team_name,
            hint: club.team_abbr,
          },
        });
      }
    }
    return [...gmHits, ...clubHits]
      .sort((a, b) => b.score - a.score || a.hit.label.localeCompare(b.hit.label))
      .slice(0, 8)
      .map((x) => x.hit);
  }, [query, gms, clubs]);

  function pick(hit: FindHit) {
    if (hit.kind === "gm") onPickGm(hit.id);
    else onPickClub(hit.id);
    setQuery("");
    setOpen(false);
    setActive(0);
    inputRef.current?.blur();
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setOpen(false);
      setQuery("");
      return;
    }
    if (!hits.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % hits.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i - 1 + hits.length) % hits.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(hits[Math.min(active, hits.length - 1)]);
    }
  }

  const showList = open && hits.length > 0;

  return (
    <div className="find-box">
      <label className="find-box-label" htmlFor="foi-find">
        Find
      </label>
      <input
        id="foi-find"
        ref={inputRef}
        type="search"
        autoComplete="off"
        placeholder="Stearns, Mets, Cashman…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          window.setTimeout(() => setOpen(false), 120);
        }}
        onKeyDown={onKey}
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls="foi-find-list"
      />
      {showList ? (
        <ul className="find-box-list" id="foi-find-list" role="listbox">
          {hits.map((hit, i) => (
            <li key={`${hit.kind}-${hit.id}`} role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={i === active}
                className={i === active ? "active" : undefined}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(hit)}
              >
                <span className="find-box-kind">
                  {hit.kind === "gm" ? "GM" : "Club"}
                </span>
                <span className="find-box-label-row">{hit.label}</span>
                <span className="find-box-hint">{hit.hint}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
