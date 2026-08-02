# Front Office Index

Every MLB franchise and GM from **2006–present**, ranked with the same weights:
payroll efficiency, draft value over slot, peer trade net WAR, and on-field results.

```
scripts/build_rankings.py          standings + payroll + draft + trades -> indexes
scripts/build_league_moves.py      all 30 clubs' trades                 -> league_moves.json
scripts/build_league_acquisition.py all clubs' FO channels              -> acquisition_index.json
scripts/build_trade_index.py       peer trade rates                     -> trade_index.json
app/page.tsx                       those JSON files                     -> the site
```

## What you get

1. **Franchises** — one composite score per club.
2. **GMs** — career ranking; multi-team careers roll into one person.
3. **Trades** — club-perspective net WAR for every franchise/GM.
4. **Acquisition channels** — FA / trade / waiver / Rule 5 WAR by club.
5. **Trade ledger** — filterable peer trade book.
6. **GM exits / yearly** — exit resumes and season-by-season active GM boards.

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

Tunable in [`data/weights.json`](data/weights.json).

---

## Quickstart

```bash
npm install
npm run dev            # http://localhost:3000
```

```bash
pip install -r scripts/requirements.txt
python scripts/build_rankings.py --use-cache
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
