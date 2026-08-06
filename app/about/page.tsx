import type { Metadata } from "next";
import Link from "next/link";
import weights from "@/data/weights.json";

export const metadata: Metadata = {
  title: "About · Front Office Index",
  description:
    "Methodology for the Front Office Index: composite weights, franchise vs GM scoring, 2020 treatment, and what we intentionally leave out.",
};

const COMPONENTS = weights.components as Record<string, number>;
const LABELS = weights.category_labels as Record<string, string>;
const WEIGHT_ROWS = Object.entries(COMPONENTS).sort((a, b) => b[1] - a[1]);
const WEIGHT_SUM = WEIGHT_ROWS.reduce((s, [, w]) => s + w, 0);

function pct(w: number): string {
  return `${Math.round(w * 100)}%`;
}

export default function AboutPage() {
  return (
    <main className="about">
      <p className="about-nav">
        <Link href="/">← Front Office Index</Link>
      </p>

      <header>
        <h1>About the Index</h1>
        <p className="tagline">
          How every MLB front office is scored — same ruler, same window, no
          home-team thesis.
        </p>
      </header>

      <section className="about-section" aria-labelledby="what-it-is">
        <h2 id="what-it-is">What this is</h2>
        <p>
          <strong>Front Office Index</strong> ranks all 30 franchises and every
          roster-running GM in the window{" "}
          <strong>
            {weights.window_start}–{weights.window_end}
          </strong>{" "}
          on the same composite. It is a league-wide evaluation of front-office
          results and acquisition — not a Yankees or Cashman profile piece.
        </p>
        <p>
          The score blends how efficiently you win relative to payroll, how you
          draft and trade, and how often you actually advance in October. One
          weight file drives both franchise and GM boards.
        </p>
      </section>

      <section className="about-section" aria-labelledby="weights">
        <h2 id="weights">Composite weights</h2>
        <p>
          Each component is converted to a z-score among peers, then weighted.
          Weights live in <code>data/weights.json</code> (sum{" "}
          {WEIGHT_SUM.toFixed(2)}):
        </p>
        <div className="table-wrap about-weights">
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th className="num">Weight</th>
              </tr>
            </thead>
            <tbody>
              {WEIGHT_ROWS.map(([key, w]) => (
                <tr key={key}>
                  <td>
                    {LABELS[key] ?? key}
                    <span className="meta">{key}</span>
                  </td>
                  <td className="num">{pct(w)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section-note" style={{ marginTop: "1rem" }}>
          Titles, pennants, and playoff depth enter as <em>rates per season</em>
          , not career totals — a 20-year tenure does not get a free pass for
          racking up counting stats.
        </p>
      </section>

      <section className="about-section" aria-labelledby="franchise-vs-gm">
        <h2 id="franchise-vs-gm">Franchise vs GM boards</h2>
        <p>
          <strong>Franchises</strong> roll every season in the window for that
          club, regardless of who sat in the chair. Multi-GM eras combine into
          one club score. No tenure shrink — the franchise is the continuous
          entity.
        </p>
        <p>
          <strong>GMs</strong> get seasons attributed by curated tenure dates
          (July 1 mid-season rule). Careers that span clubs stay one person.
          After the same z-score composite as franchises, GM scores are{" "}
          <em>tenure-shrunk</em>:
        </p>
        <p className="formula">
          adjusted = raw × seasons / (seasons + {weights.tenure_prior_seasons})
        </p>
        <p>
          With a prior of {weights.tenure_prior_seasons} seasons, a one-year
          spike is damped; a long book approaches its raw composite. Rows with
          fewer than {weights.min_seasons_for_full_rank} seasons are flagged as
          small samples but still ranked.
        </p>
      </section>

      <section className="about-section" aria-labelledby="formula">
        <h2 id="formula">Ranking logic</h2>
        <ol className="about-steps">
          <li>
            Build season rows: wins, losses, opening-day payroll, playoff depth
            (wild card = 1 … World Series = 4), pennant, title.
          </li>
          <li>
            Aggregate to franchise or GM through the last <em>complete</em>{" "}
            championship season (drop the in-progress year before October).
            Win% = wins / games; title / pennant / depth rates = counts ÷
            seasons; payroll efficiency = paced wins per $100M using only
            seasons that have opening-day payroll on file (missing-payroll years
            drop out of both sides).
          </li>
          <li>
            Attach draft value-over-slot (franchise-tenure WAR vs slot curve) and
            peer trade net WAR per season from the league trade ledger. Yearly
            and exit resumes cut draft picks and trades at the as-of date so
            future deals cannot leak into a historical score.
          </li>
          <li>
            Z-score each of the seven components across the peer set; weighted
            sum → composite. Competition ranks (1 = best) are shown per category
            as well.
          </li>
        </ol>
        <p>
          Playoff depth scores how far you went that year, not merely “made the
          dance.” A wild-card exit and a World Series appearance are not the
          same October.
        </p>
      </section>

      <section className="about-section" aria-labelledby="examples">
        <h2 id="examples">Plain examples</h2>
        <ul className="about-examples">
          <li>
            <strong>Cheap contention vs expensive titles.</strong> Payroll
            efficiency is the largest weight ({pct(COMPONENTS.payroll_efficiency)}
            ). A club that wins a lot on a modest opening-day payroll outranks a
            bigger spender with the same October hardware on that axis — titles
            still count separately via rates.
          </li>
          <li>
            <strong>Trade net WAR.</strong> For each peer trade, credit WAR the
            club received during the relevant tenure and debit WAR produced by
            players it sent away elsewhere. Divide by seasons for{" "}
            <code>trade_net_rate</code>. One bad deadline can be offset by a
            decade of good ones — the rate keeps longevity honest.
          </li>
          <li>
            <strong>Draft = franchise-tenure WAR only.</strong> A pick’s grade
            uses WAR produced <em>for the drafting club</em> before a trade away.
            Post-trade WAR belongs to the trade ledger so the same wins are not
            double-counted. Immature classes (recent drafts) are listed but
            excluded from the primary VOS grade.
          </li>
        </ul>
      </section>

      <section className="about-section" aria-labelledby="covid-2020">
        <h2 id="covid-2020">How 2020 is treated</h2>
        <p>
          2020 was ~60 games with opening-day payrolls that still look like full
          seasons. Blindly dividing those wins by full payroll would tank every
          club’s efficiency that year. The rule:
        </p>
        <ul className="about-examples">
          <li>
            <strong>Payroll efficiency only:</strong> wins are paced to a
            162-game schedule (
            <code>wins × 162 / (wins + losses)</code>) before wins / $100M.
          </li>
          <li>
            <strong>Win%, titles, pennants, playoff depth:</strong> used as-is.
            Rates already handle a short schedule; a World Series still counts as
            one title season.
          </li>
          <li>
            <strong>Draft &amp; trades:</strong> no special 2020 scalar. WAR for
            a short season is naturally smaller; dividing by seasons (rates)
            keeps books comparable without inventing phantom WAR.
          </li>
        </ul>
      </section>

      <section className="about-section" aria-labelledby="left-out">
        <h2 id="left-out">Intentionally left out</h2>
        <ul className="about-examples">
          <li>
            <strong>Clutch / postseason WPA.</strong> July–August trades get a
            light “win-now” window tag in the ledger. We do not invent clutch
            metrics or October leverage grades.
          </li>
          <li>
            <strong>Coaches, managers, hiring trees.</strong> This index scores
            roster construction and results attribution to the FO chair — not
            dugout coaching or farm-system staff charts.
          </li>
          <li>
            <strong>Thin salary / control overrides.</strong> Dollar surplus and
            remaining control years appear only when hand-entered terms exist.
            Sparse public salary ledgers are not dressed up as precision.
          </li>
          <li>
            <strong>International amateur pools.</strong> Still deferred in the
            acquisition roadmap — draft and peer trades ship first; intl bonus
            pools are not in the composite yet.
          </li>
          <li>
            <strong>Prospect-count vanity.</strong> Raw “number of prospects
            acquired” is not skill. Assets are scored in WAR (and money when
            known).
          </li>
        </ul>
      </section>

      <footer>
        <p>
          Tunable weights and window: <code>data/weights.json</code>. Scoring:{" "}
          <code>scripts/scoring.py</code>. Pipeline notes: README.
        </p>
        <p>
          <Link href="/">Back to the rankings</Link>
        </p>
      </footer>
    </main>
  );
}
