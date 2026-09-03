import type { Metadata } from "next";
import Link from "next/link";
import BrandMark from "@/components/BrandMark";
import weights from "@/data/weights.json";

export const metadata: Metadata = {
  title: "About",
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
        <Link href="/" className="brand-lockup about-brand">
          <BrandMark size={22} />
          Front Office Index
        </Link>
      </p>

      <header>
        <h1>About the Index</h1>
        <p className="tagline">
          Same ruler for every MLB front office — payroll efficiency, draft,
          trades, and October results. Not a home-team thesis.
        </p>
        <p className="section-note">
          Rankings use seasons through the last <em>complete</em> championship
          year (currently {weights.window_start}–2025 while {weights.window_end}{" "}
          is still in progress). Scoring pin{" "}
          <code>as_of</code> = {weights.as_of} (methodology cutoff for draft
          maturity and WAR horizons — not the site&apos;s last data refresh).
          Peer trade ledger coverage starts mid-2009. Details below; start with
          the weight table if you only want the recipe.
        </p>
      </header>

      <section className="about-section" aria-labelledby="weights">
        <h2 id="weights">Composite weights</h2>
        <p>
          Each piece is z-scored among peers, then weighted (sum{" "}
          {WEIGHT_SUM.toFixed(2)}). Tunable in <code>data/weights.json</code>.
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

      <section className="about-section" aria-labelledby="lenses">
        <h2 id="lenses">Success lenses</h2>
        <p>
          On <strong>Clubs</strong> and <strong>GMs</strong> (Career and After
          this year), compact lens pills sit immediately above the ranking table
          (after the short intro). They reweight the same seven components — no
          new metrics. Guardrails: every component stays on (no zeros), and no
          single weight exceeds ~42%. Hover a pill for that lens&apos;s blurb.
        </p>
        <p>
          <strong>Lenses move less than they look.</strong> Titles, pennants,
          playoff depth, and win% are highly correlated (playoff depth ↔ win%
          ≈ +0.88). Together they are ~0.41 of Balanced and more under October —
          four channels measuring nearly the same “winning” construct. Mean rank
          shifts between lenses are only a few places. That is honest overlap,
          not a broken toggle. Craft-heavy lenses (Value / Builder) move thrift,
          draft, and trade more than October vs Balanced does.
        </p>
        <ul className="about-examples">
          {Object.entries(
            (weights as { lenses?: Record<string, { label: string; blurb: string }> })
              .lenses ?? {},
          ).map(([id, lens]) => (
            <li key={id}>
              <strong>{lens.label}.</strong> {lens.blurb}
            </li>
          ))}
        </ul>
        <p>
          Draft, Trades, Acquisition, Exits, and Trade detail keep
          their own recipes and are <em>not</em> reweighted by these lenses.
          Under <strong>GMs</strong>, switch Career / After this year / Season
          grades — only Career and After this year take lenses. Season grades
          score one year of moves and ignore the lens.
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
          spike is damped toward <em>0</em> (not the peer mean); a long book
          approaches its raw composite. After-this-year freeze-frames and
          exit-pool scores use the same shrink. Rows with fewer than{" "}
          {weights.min_seasons_for_full_rank} seasons are flagged as small
          samples but still ranked.
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
            seasons. Payroll thrift is <em>league-relative</em>: paced wins /
            $100M for each team-season, divided by that year&apos;s league mean,
            then averaged over the tenure (missing-payroll years drop out).
            Each season counts once — not weighted by payroll size — so seven
            cheap years still outvote two expensive ones. 1.0 ≈ average thrift
            for the years played; early low-payroll decades no longer look
            automatically thrifty.
          </li>
          <li>
            Attach draft value-over-slot (franchise-tenure WAR vs slot curve) and
            peer trade net WAR per season from the league trade ledger. After
            this year and exit resumes cut draft picks and trades at the as-of
            date, and clip observed WAR to that cutoff so living rebuild totals
            cannot leak into a historical score.
          </li>
          <li>
            Z-score each of the seven components across the peer set; weighted
            sum → composite. Missing components (blank, not zero) are dropped and
            weights renormalized for that row. Competition ranks (1 = best) are
            shown per category as well.
          </li>
        </ol>
        <p>
          Playoff depth scores how far you went that year, not merely “made the
          dance.” A wild-card exit and a World Series appearance are not the
          same October. Titles, pennants, depth, and win% nest — stacked October
          influence is higher than the three small weights imply (~
          {pct(
            (COMPONENTS.world_series_rate ?? 0) +
              (COMPONENTS.pennants_rate ?? 0) +
              (COMPONENTS.playoff_depth_rate ?? 0) +
              (COMPONENTS.win_pct ?? 0),
          )}
          when win% is included).
        </p>
      </section>

      <section className="about-section" aria-labelledby="examples">
        <h2 id="examples">Plain examples</h2>
        <ul className="about-examples">
          <li>
            <strong>Cheap contention vs expensive titles.</strong> League-relative
            payroll thrift is the largest weight ({pct(COMPONENTS.payroll_efficiency)}
            ). A club that wins a lot relative to that year&apos;s league payroll
            bar outranks a bigger spender with the same October hardware on that
            axis — titles still count separately via rates.
          </li>
          <li>
            <strong>Trade net WAR.</strong> Scored as player movements: buyer
            credit and seller charge share one ledger entry, so multi-team
            packages cancel in a closed market (league sum of net ≈ 0). Matching
            post-move WAR on both sides; surplus still uses during-club
            production. Divide by seasons for <code>trade_net_rate</code>. The
            daily refresh pulls transactions through <em>today</em>;{" "}
            <code>weights.as_of</code> is only the scoring pin (complete seasons
            / contract flags), not the fetch cutoff.
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

      <section className="about-section" aria-labelledby="every-season">
        <h2 id="every-season">Season grades</h2>
        <p>
          Under <strong>GMs</strong>, three tabs answer three questions.{" "}
          <strong>Career</strong> is the whole book right now.{" "}
          <strong>After this year</strong> is the same recipe frozen after a
          chosen season — earlier clubs still count.{" "}
          <strong>Season grades</strong> scores one year of moves, not the
          career.
        </p>
        <p>
          Season grades defaults to <strong>All years</strong>: every graded
          executive-year since {weights.window_start} in one pool. Trade cells
          for 2006–2008 stay blank (ledger begins 2009); immature draft classes
          stay blank until the six-year lag. Columns lead with{" "}
          <strong>#</strong> (all-time place in that pool — #1 is the best FO
          season on the site), then executive, year, and <strong>Score</strong>{" "}
          (construction grade). <strong>In that year</strong> is only the peer
          place among executives graded the same calendar year. Names repeat on
          purpose — many elite seasons for one executive is the finding. Hover
          column headers for short definitions.
        </p>
        <p>
          Pick a single year to see that season&apos;s construction table
          (trades, draft, other arrivals, own stock). Seasons still too young to
          grade (immature drafts) hide by default on All years and do not take
          an all-time number.
        </p>
      </section>

      <section className="about-section" aria-labelledby="season-grade">
        <h2 id="season-grade">Single-season construction grades</h2>
        <p>
          <strong>After this year</strong> is a career freeze-frame through
          season Y (same composite as the GM board, tenure-shrunk, lenses on).{" "}
          <strong>Season grades</strong> answers a different question: how good
          was FO craft <em>in</em> season Y?
        </p>
        <p>
          A championship season mixes inherited players from a prior{" "}
          <strong>regime</strong>, this GM’s earlier construction, and moves
          dated in Y. Construction grades separate those:
        </p>
        <ul className="about-examples">
          <li>
            <strong>Attribution window:</strong> Nov 1 of Y−1 through Oct 31 of
            Y. GM on the move/draft date gets the credit.
          </li>
          <li>
            <strong>Horizon H = {weights.season?.horizon_years ?? 3} years:</strong>{" "}
            trade and FA/other arrival WAR is observed through{" "}
            <code>min(as_of, event_date + H)</code>. Career boards still use full
            during-club WAR.
          </li>
          <li>
            <strong>Draft:</strong> June Y class enters once{" "}
            <code>draft_year ≤ as_of − {weights.season?.mature_lag_years ?? 6}</code>
            ; immature years show “—” not a fake zero. Scores are living
            revisions, not contemporaneous prospect grades.
          </li>
          <li>
            <strong>StockShare:</strong> share of that club’s season WAR from
            players acquired under this GM’s regime (own prior + same-year), not
            inherited from the previous chair.
          </li>
          <li>
            <strong>Thin results strip:</strong> win%, playoff depth, and payroll
            efficiency for the Jul-1 GM — labeled club results under the chair,
            not pure FO skill.
          </li>
        </ul>
        <p>
          Season component weights live under <code>weights.season</code> in{" "}
          <code>data/weights.json</code>.
        </p>
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
            <strong>Exit-pool index.</strong> The Exits tab scores a resume among
            other exits — not the live active-GM board on that calendar day.
          </li>
          <li>
            <strong>Payroll thrift is league-relative, and seasons are equal.</strong>{" "}
            Raw wins/$100M trends down as payrolls inflate; we divide each
            season by that year&apos;s league mean so early tenures are not
            automatic thrift leaders. Those yearly ratios are then averaged
            equally. Dollars spent do not weight the mean — two $300M Mets
            years do not outweigh seven cheaper Brewers years. A top-payroll
            club is still structurally weak on this heaviest weight — that is
            the house formula, disclosed here.
          </li>
          <li>
            <strong>Winning-block collinearity.</strong> World Series, pennant,
            playoff depth, and win% nest. Stacked influence exceeds the three
            small October weights alone — disclosed here, not collapsed in this
            release.
          </li>
          <li>
            <strong>Call-ups vs acquisitions.</strong> Ledger promotions are not
            yet separated from true FO acquisitions; treat arrival channels as
            approximate.
          </li>
          <li>
            <strong>Contemporaneous prospect values.</strong> Season construction
            grades revise with observed WAR after the horizon / mature lag — we
            do not invent “what scouts thought in draft week.”
          </li>
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
