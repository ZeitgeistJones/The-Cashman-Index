import MovesTable from "@/components/MovesTable";
import movesFile from "@/data/moves.json";
import { formatMoney, isSampleData, type MovesFile } from "@/lib/moves";

// Statically imported so the data ships with the bundle — no filesystem reads
// at request time, which keeps this working on Vercel without any extra config.
const data = movesFile as MovesFile;

export default function Home() {
  const { moves, dollars_per_war, season_range, generated_at } = data;
  const scored = moves.filter((m) => m.net_war_exchange !== null);

  return (
    <main>
      <header>
        <h1>The Cashman Index</h1>
        <p className="tagline">
          Every Yankees front-office move from {season_range[0]}–{season_range[1]},
          scored with objective baseball math instead of talk-radio opinion.
        </p>
      </header>

      {isSampleData(data) && (
        <div className="banner">
          <strong>Sample data — the WAR numbers here are made up.</strong>
          Transactions, dates and contract terms are real and sourced, but every
          WAR figure is a placeholder, so both scores are illustrative only. Run
          the <em>Refresh moves data</em> GitHub Action to replace{" "}
          <code>data/moves.json</code> with live MLB Stats API transactions and
          real Baseball Reference WAR.
        </div>
      )}

      <ul className="stats">
        <li>
          Moves<span>{moves.length}</span>
        </li>
        <li>
          Scored<span>{scored.length}</span>
        </li>
        <li>
          $/WAR benchmark<span>{formatMoney(dollars_per_war)}</span>
        </li>
        <li>
          Generated<span>{generated_at.slice(0, 10)}</span>
        </li>
      </ul>

      <MovesTable moves={moves} />

      <footer>
        <p>
          <strong>Surplus value</strong> — the WAR the acquired players produced
          for the Yankees after the move, priced at {formatMoney(dollars_per_war)}{" "}
          per win, minus the salary actually paid. Positive means the Yankees got
          more on the field than they paid for. Blank means no reliable salary
          figure is on file for that move.
        </p>
        <p>
          Moves marked <em>still paying</em> are on contracts that have not
          finished. Their score charges the full guarantee against only the wins
          banked so far, so it reads harsher than the deal will finish — treat it
          as a midpoint, not a verdict.
        </p>
        <p>
          <strong>Net WAR exchange</strong> — WAR the acquired players produced
          for the Yankees after the move, minus WAR the departing players
          produced elsewhere over the same stretch. Positive means the Yankees
          won the talent swap.
        </p>
        <p>
          Transactions from the MLB Stats API. WAR and salaries from Baseball
          Reference via pybaseball. Seasons are attributed by team stint, so a
          midseason trade only credits the games actually played after the move.
        </p>
      </footer>
    </main>
  );
}
