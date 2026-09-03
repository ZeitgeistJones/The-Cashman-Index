# Front Office Index

Every MLB franchise and GM from **2006–present**, ranked with the same weights:
payroll efficiency, draft value over slot, peer trade net WAR, and on-field results.
Peer trade coverage in the MLB Stats API ledger starts **mid-April 2009** — earlier
seasons leave trade cells blank (not zero) and drop that component from the row.

See [CHANGELOG.md](CHANGELOG.md) for notable changes from 2026-08-06 onward.

```
scripts/build_rankings.py          standings + payroll + draft + trades -> indexes
scripts/build_season_index.py      single-season FO construction grades -> season_index.json
scripts/build_league_moves.py      all 30 clubs' trades                 -> league_moves.json
scripts/build_league_acquisition.py all clubs' FO channels              -> acquisition_index.json
scripts/build_trade_index.py       peer trade rates                     -> trade_index.json
app/page.tsx                       those JSON files                     -> the site
```

## What you get

1. **Clubs** — one composite score per franchise.
2. **GMs → Career** — whole book right now; multi-team careers stay one person.
3. **GMs → After this year** — same career recipe, frozen after a chosen season (earlier clubs still count).
4. **GMs → Season grades** — one year of moves (All years = best FO seasons; pick a year for that season’s construction table).
5. **Draft / Trades / How they acquire** — channel boards. Trade ledger coverage starts mid-2009.
6. **Exits / Trade detail** — exit-pool resumes and the full peer trade book.

### Index weights

| Component | Weight |
|---|---|
| Payroll efficiency (wins / $100M) | 36% |
| Titles / season | 12% |
| Playoff depth / season | 12% |
| Trade net WAR / season | 12% |
| Draft value over slot | 11% |
| Win% | 10% |
| Pennants / season | 7% |

Tunable in [`data/weights.json`](data/weights.json). Season construction weights live under `weights.season`.

---

## Quickstart

```bash
npm install
npm run dev            # http://localhost:3000
```

```bash
pip install -r scripts/requirements.txt
python scripts/build_rankings.py --use-cache
python scripts/build_season_index.py
python scripts/build_league_moves.py --use-cache
python scripts/build_trade_index.py
python scripts/build_league_acquisition.py --use-cache
```

## Known limitations

- GM tenure dates are curated / best-effort.
- Salary ledger sparse outside hand overrides.
- International amateur pools not scored yet.
- Transaction history thin before ~2009 for some clubs.
- No postseason WPA / clutch model; Jul/Aug trades get a win-now tag only.
- Season construction grades are living revisions (horizon / mature lag), not contemporaneous scout grades.
- Payroll thrift averages each season’s league-relative ratio equally — not weighted by dollars spent.
