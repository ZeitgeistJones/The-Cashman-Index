# The Cashman Index

Brian Cashman's Yankees front-office moves, scored with objective baseball math
instead of talk-radio opinion.

This is the **first-pass MVP**: one Python script that builds the dataset, one
page that shows it as a sortable table. No chained asset trees, no confidence
scores, no postseason WPA yet.

```
scripts/build_moves.py   MLB Stats API + pybaseball  ->  data/moves.json
app/page.tsx             data/moves.json             ->  the table
```

---

## Quickstart

### Refresh the data (no local setup needed)

**Actions tab → "Refresh moves data" → Run workflow.**

That runs the whole pipeline on GitHub's runners, which have unrestricted
network access, and commits the new `data/moves.json` straight back to the
branch. Vercel redeploys on the commit. It also runs itself every Monday.

If the run goes red, the data may still be fine — open the run and download the
`moves-data` artifact. The last step is a strict check that every salary
override matched a real move, and it deliberately runs *after* the data is
committed.

### Or run it locally

```bash
npm install
npm run dev            # http://localhost:3000

pip install -r scripts/requirements.txt
python scripts/build_moves.py
```

`data/moves.json` is checked in, so the app runs before you ever touch Python.

> **The checked-in `data/moves.json` is placeholder data.** Transactions, dates,
> player names, salaries and contract terms in it are real and sourced — but
> **every WAR figure is a made-up illustrative number**, so both scores are
> fiction, and `mlbam_id` is `0` throughout. The page shows a yellow banner
> while that file has `"data_source": "sample"`. One pipeline run overwrites it
> and the banner disappears.
>
> It ships that way because the sandbox it was built in blocks outbound
> connections to `statsapi.mlb.com` and `baseball-reference.com`. That is
> exactly why the GitHub Action above exists. The logic itself is covered by
> offline tests (`python scripts/test_build_moves.py`, 40 checks).

---

## The script

`scripts/build_moves.py` does both stages in one run.

**Stage 1 — transactions.** Pulls Yankees transactions from the MLB Stats API
(`/api/v1/transactions?teamId=147`), one calendar year per request, for the last
10 years. The API returns one row *per player*, so a five-player trade arrives as
five rows; the script folds them back into one move by grouping trades on
`(date, counterparty club)`. Two separate trades on the same deadline day with
different clubs stay separate. Raw rows are cached to
`data/transactions.raw.json` so you can re-run the scoring without re-hitting
the API.

By default it keeps only real front-office decisions — trades, signings, waiver
claims, purchases, selections, releases, free-agency departures, outrights.
Options, recalls, DFAs, status changes and uniform-number rows are roster
paperwork and would bury the actual moves. Pass `--all-types` to keep them.

**Stage 2 — scoring.** Downloads Baseball Reference's WAR tables via
`pybaseball.bwar_bat()` / `bwar_pitch()`, which key on MLBAM player id and split
each season by **team stint** — so a midseason trade is credited correctly on
both sides.

### Options

| Flag | Default | What it does |
|---|---|---|
| `--years N` | `10` | How far back to pull |
| `--no-war` | off | Transactions only; scores left `null` (fast, no pybaseball) |
| `--use-cache` | off | Re-score cached transactions without calling the API |
| `--dollars-per-war N` | `8000000` | Re-price the whole index |
| `--all-types` | off | Keep roster paperwork too |
| `--out PATH` | `data/moves.json` | Output location |
| `--overrides PATH` | `data/salary_overrides.json` | Manual contract terms |

---

## The two scores

**`surplus_value`** — what the Yankees got on the field, priced, minus what they
paid:

```
surplus_value = (WAR the acquired players produced FOR THE YANKEES after the move)
                x $8,000,000 per win
              - salary actually paid
```

Positive means the move returned more value than it cost. It is `null`, not `0`,
when no reliable salary figure exists — a missing salary is not a free player.

**`net_war_exchange`** — who won the talent swap:

```
net_war_exchange = WAR the acquired players produced for the Yankees after the move
                 - WAR the departing players produced elsewhere after the move
```

Both sides are counted strictly after the move date. A player's Yankees WAR from
*before* he was traded away never counts against the trade that sent him out.

### Season attribution

A move in November or December is credited from the *following* season. That is
what makes offseason moves line up with the contract that follows, and it stops
a re-signed free agent's pre-signing Yankees WAR from being counted as a
"result" of re-signing him. In-season moves use the current year, where the
team-stint split already isolates the post-move portion.

---

## Salaries

The MLB Stats API carries **no contract data at all**. The script fills
`salary_paid` from Baseball Reference's per-season salary column, summed over
the Yankees seasons that follow the move — a real, sourced number, but one that
thins out for the most recent seasons and reflects salary *paid so far*, not the
total guarantee.

`contract_years` has no automated source and is `null` unless you supply it.

For anything you want exact, use `data/salary_overrides.json`, which ships with
researched terms for the fifteen biggest Yankees commitments of the last decade
(Cole, Judge, Rodón, Fried, Stanton, both LeMahieu deals, both Bellinger deals,
Chapman, Donaldson, Rizzo, Soto, Goldschmidt, Grisham):

```json
[
  {
    "match": { "player": "Gerrit Cole", "date": "2019-12-18" },
    "salary_paid": 324000000,
    "contract_years": 9,
    "contract_through": 2028
  }
]
```

Entries match by `move_id` (copy it out of `data/moves.json`) or by
`player` + `date`. Reported signing dates routinely differ from the league's
filing date, so a player match **within 14 days** counts. Overrides beat scraped
salaries and force `surplus_value` to be recomputed. Each move records where its
salary came from in `salary_source`: `"override"`, `"bref"`, or `null`.

Every entry carries `confidence`, `source` and `note` fields for auditing. The
script ignores them; they exist so you can see which figures are solid and which
are approximations. The ones flagged `medium` are Stanton (how the Marlins' $30M
offset is dated), the Bellinger trade (he opted out early), Rizzo (two separate
deals in 2022), Goldschmidt (exact date) and Grisham (qualifying-offer
acceptances are recorded inconsistently upstream).

**An override that matches nothing is never silently dropped.** The script lists
unmatched entries at the end of every run, and `--strict-overrides` turns that
into a non-zero exit so CI catches it.

### Contracts still being paid

`contract_through` marks the final season of a deal. Anything at or beyond the
current season sets `contract_active`, and the table tags those rows **still
paying**. It matters: a nine-year contract signed in 2022 has banked only part
of the WAR it was bought for, so charging the full guarantee against it makes an
unfinished deal look like a disaster. Those scores are midpoints, not verdicts.

---

## Known limitations of this pass

- **Three-team trades** split into two Yankees-vs-counterparty moves.
- **Two salary semantics coexist.** Overridden moves use the total guarantee;
  Baseball-Reference-sourced ones use money paid to date. The difference only
  bites on long active deals, which is what `contract_active` flags.
- **Prospects who never reach the majors** contribute `0.0` WAR, which is
  correct for realized value but reads harshly on trades that are still open.
- **No chained asset trees.** If a traded prospect is later flipped for someone
  good, that value is not traced back.
- **One flat $/WAR benchmark** across all ten years, rather than a
  year-by-year market rate.
- **No postseason WPA, no confidence scores** — deliberately out of scope here.

---

## Deploying to Vercel

Zero-config. Import the repo at [vercel.com/new](https://vercel.com/new); Vercel
detects Next.js and uses `npm run build`. The page is fully static — `moves.json`
is imported at build time, so there is no runtime filesystem access and no
environment variables to set.

To refresh the data: run the script, commit the new `data/moves.json`, push.
Vercel rebuilds.

## Layout

```
.github/workflows/           refresh-data (the pipeline) + ci (tests and build)
app/page.tsx                 the page (server component, static)
app/globals.css              styles, light + dark
components/MovesTable.tsx    the sortable table (client component)
lib/moves.ts                 types + formatters
data/moves.json              the dataset the app reads
data/salary_overrides.json   hand-entered contract terms
scripts/build_moves.py       the pipeline
scripts/test_build_moves.py  offline tests, no network needed
```
