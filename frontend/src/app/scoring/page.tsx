import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scoring Algorithm — Qullamaggie Platform",
  description: "Full explanation of how the P Score, grade, setups, and quality signals are computed",
};

// ── Reusable section wrapper ─────────────────────────────────────────────────

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-7 scroll-mt-20">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">{title}</h2>
      <div className="space-y-4 text-sm text-gray-700 leading-relaxed">{children}</div>
    </section>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="bg-gray-900 text-green-300 rounded-lg px-5 py-4 text-xs leading-6 overflow-x-auto font-mono">
      {children}
    </pre>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-indigo-50 border-l-4 border-indigo-400 rounded-r-lg px-4 py-3 text-indigo-800 text-sm">
      {children}
    </div>
  );
}

function Warn({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-amber-50 border-l-4 border-amber-400 rounded-r-lg px-4 py-3 text-amber-800 text-sm">
      {children}
    </div>
  );
}

// ── TOC ──────────────────────────────────────────────────────────────────────

const TOC = [
  { id: "overview",     label: "Overview" },
  // P Score — the single score
  { id: "pscore",       label: "P Score — Probability Scorer" },
  { id: "pscore-signals",  label: "  P Signals & Weights" },
  { id: "pscore-regime",   label: "  Regime Multipliers" },
  { id: "pscore-grades",   label: "  P Grade Thresholds" },
  // Individual signals
  { id: "weinstein",    label: "Signal: Weinstein Stage" },
  { id: "adnet",        label: "Signal: A/D Net" },
  { id: "overext",      label: "Signal: Overextension Penalty" },
  { id: "rs",           label: "Signal: Relative Strength" },
  { id: "adx",          label: "Signal: ADX (Trend Strength)" },
  { id: "rvol",         label: "Signal: Relative Volume" },
  { id: "ics",          label: "Signal: ICS (Institutional Composite)" },
  { id: "exhaustion",   label: "Signal: Bull Exhaustion Warning" },
  { id: "wys",          label: "Setup: Wyckoff Spring (WYS)" },
  { id: "fibonacci",    label: "Analysis: Fibonacci Grid" },
  { id: "options",      label: "Analysis: Options (Leading)" },
  { id: "positioning",  label: "Market Positioning Dial" },
  { id: "philosophy",   label: "Design Philosophy" },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ScoringPage() {
  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scoring Algorithm</h1>
        <p className="text-sm text-gray-500 mt-1">
          Every formula, every weight, every threshold — and the reasoning behind each decision.
        </p>
      </div>

      {/* TOC */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">On this page</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {TOC.map((t) => (
            <a key={t.id} href={`#${t.id}`}
              className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline">
              {t.label}
            </a>
          ))}
        </div>
      </div>

      {/* Overview */}
      <Section id="overview" title="🗺️ Overview">
        <p>
          Every scan result carries a single <strong>P Score</strong> (0–100) plus a flag for which
          Qullamaggie <strong>setup</strong> (if any) is currently firing. The P Score answers
          <em> &quot;how strong is the overall evidence?&quot;</em>; the setup tells you <em>&quot;what
          kind of entry is this?&quot;</em>
        </p>
        <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 mt-3">
          <div className="font-bold text-teal-800 mb-1">P Score — Probability Scorer (the single score)</div>
          <div className="text-xs text-teal-700 space-y-1">
            <p>A signal-voting model ported from the <em>technical-analysis</em> reference repo:</p>
            <code className="block font-mono bg-teal-100 px-2 py-1 rounded text-[11px]">
              Σ (strength × weight × accuracy × regime_mult)  + weekly-TF adjustment − penalties
            </code>
            <p>Grade: <strong>A≥75 / B≥60 / C≥45 / D&lt;45</strong></p>
          </div>
        </div>
        <Note>
          <strong>What about the Qullamaggie setups?</strong> The setup detectors (EP, TB, WYS, PP, PULL, FBD)
          still run on every stock — they decide <em>whether a tradeable entry exists</em> and define the
          entry / stop / targets. They are <strong>not</strong> a separate score. When analyzing a stock you
          simply see which setup is firing (or &quot;None&quot;), and each firing setup also votes inside the
          P Score with a high weight. One number, one verdict.
        </Note>
        <Note>
          <strong>History:</strong> earlier versions also showed a separate &quot;Q Score&quot; (a fixed
          Qullamaggie formula: quality×60 + RS×25 + stage×10 + A/D×5). It was retired to avoid two competing
          numbers — its ingredients (RS, Weinstein stage, A/D, setup pattern, stop tightness) all live on as
          weighted signals inside the P Score.
        </Note>
      </Section>

      {/* ── P SCORE ──────────────────────────────────────────────────────────── */}

      <Section id="pscore" title="🎲 P Score — Probability Scorer">
        <p>
          The P Score is a <strong>probability-weighted signal voting model</strong> ported from the{" "}
          <em>technical-analysis</em> reference repo. Rather than a fixed formula, it aggregates multiple
          independent signals — each weighted by its domain importance and its historical accuracy — into a
          single 0–100 confidence score. It answers: <em>what fraction of the evidence supports this trade,
          and how reliable is that evidence?</em>
        </p>

        <CodeBlock>{`# Core contribution formula for each signal:
contribution = strength × eff_weight × accuracy

#   strength    — signal output, 0.0–1.0
#                 (e.g. RSI strength = (RSI-50)/50 when bullish)
#   eff_weight  = base_weight × regime_multiplier
#                 (regime adjusts how much each signal type matters)
#   accuracy    = backtested win-rate for this signal class

# Raw score = dominant_side_total / dominant_max
# Composite = min(100, raw_score × 100 × agreement_bonus)
# Then apply the weekly-TF adjustment and overextension penalty (RSI>80 / >8% above EMA21)`}
        </CodeBlock>

        <Note>
          <strong>Why a voting model?</strong> Instead of a fixed formula with constant weights, the P Score
          adapts to the market regime: in a trending regime, trend signals are worth more; in a ranging
          regime, mean-reversion signals get a boost. An agreement bonus rewards when ≥70% of signals agree,
          reflecting the principle that conviction grows when independent indicators converge.
        </Note>
      </Section>

      <Section id="pscore-signals" title="P Score: Signals, Weights & Accuracy">
        <p>
          Every setup result uses up to <strong>21 signals</strong> (setup patterns + technical
          indicators). Each contributes to the P Score proportionally to its effective weight and
          its historical accuracy factor. After all signals vote, a{" "}
          <strong>weekly timeframe adjustment</strong> is applied as a flat bonus/penalty.
        </p>

        <h3 className="font-semibold text-gray-800 mt-3 mb-1 text-sm">Setup Pattern Signals (highest weight)</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Signal</th>
                <th className="text-left py-2 px-3 border border-gray-200">Class</th>
                <th className="text-center py-2 px-3 border border-gray-200">Base weight</th>
                <th className="text-center py-2 px-3 border border-gray-200">Accuracy</th>
                <th className="text-left py-2 px-3 border border-gray-200">Strength source</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["EP (Episodic Pivot)", "Trend", "3.0", "72%", "Confidence from detector"],
                ["WYS (Wyckoff Spring)", "Trend", "3.0", "75%", "Confidence from detector"],
                ["VCP (Volatility Contraction)", "Trend", "2.8", "72%", "Confidence from detector"],
                ["TB (Tight Base)", "Trend", "2.5", "70%", "Confidence from detector"],
                ["FBD (Failed Breakdown)", "Trend", "2.0", "68%", "Confidence from detector"],
                ["PP (Pocket Pivot)", "Trend", "2.0", "65%", "Confidence from detector"],
                ["PULL (EMA Pullback)", "Trend", "1.5", "63%", "Confidence from detector"],
              ].map(([s, cls, w, acc, src]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{s}</td>
                  <td className="py-2 px-3 border border-gray-200">
                    <span className={cls === "Trend" ? "text-green-700" : "text-amber-600"}>{cls}</span>
                  </td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center">{w}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-indigo-700">{acc}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{src}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4 mb-1 text-sm">Trend & Momentum Indicators</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Signal</th>
                <th className="text-left py-2 px-3 border border-gray-200">Class</th>
                <th className="text-center py-2 px-3 border border-gray-200">Base weight</th>
                <th className="text-center py-2 px-3 border border-gray-200">Accuracy</th>
                <th className="text-left py-2 px-3 border border-gray-200">Strength / Logic</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Weinstein Stage", "Trend", "2.5", "72%", "S2=1.0, S1=0.5; S3/S4 → bearish 0.7"],
                ["Minervini Trend Template", "Trend", "1.8", "72%", "Fraction of 8 SEPA criteria met (see below)"],
                ["EMA Stack", "Trend", "1.5", "70%", "full_bull=0.9, partial_bull=0.6; full_bear → bearish"],
                ["Supertrend (10, 3.0)", "Trend", "1.0", "68%", "ATR-based trailing stop; direction flip = 0.7 strength"],
                ["OBV", "Trend", "1.5", "65%", "Rising OBV over 20 bars → bullish institutional interest"],
                ["CMF (20)", "Trend", "1.2", "64%", "Chaikin Money Flow; +0.05 threshold to filter noise"],
                ["MACD", "Trend", "1.0", "65%", "Bullish/bearish histogram sign; strength from magnitude"],
                ["A/D Net", "Trend", "1.0", "65%", "O'Neill accumulation days; clipped ad_net / 10"],
                ["ICS", "Trend", "1.2", "68%", "Institutional Composite Score / 100"],
                ["Keltner Channel (20, 1.5×)", "Trend", "0.85", "63%", "Price at/below lower KC = oversold bullish; above upper = bearish"],
              ].map(([s, cls, w, acc, src]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{s}</td>
                  <td className="py-2 px-3 border border-gray-200">
                    <span className={cls === "Trend" ? "text-green-700" : "text-amber-600"}>{cls}</span>
                  </td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center">{w}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-indigo-700">{acc}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{src}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
          <h3 className="font-semibold text-gray-800 text-sm mb-1">
            Minervini Trend Template — the 8 criteria
          </h3>
          <p className="text-xs text-gray-600 mb-2">
            Mark Minervini&apos;s structural leadership filter (from <em>Trade Like a Stock Market
            Wizard</em>). It is emitted as a single voting signal whose <strong>strength = fraction
            of the 8 criteria met</strong> (e.g. 7/8 → strength 0.88). It votes bullish when ≥ 50% of
            criteria pass, bearish otherwise. Some criteria overlap the Weinstein Stage and EMA Stack
            signals — that is why its weight (1.8) is moderate rather than top-tier. Its unique
            contribution is the <strong>SMA200 alignment</strong> and <strong>52-week price
            position</strong>, which no other signal captures.
          </p>
          <ol className="text-xs text-gray-700 list-decimal list-inside space-y-0.5">
            <li>Price above both the 150-day AND 200-day SMA</li>
            <li>150-day SMA above the 200-day SMA</li>
            <li>200-day SMA trending up (rising vs ~1 month ago)</li>
            <li>50-day SMA above both the 150-day and 200-day SMA</li>
            <li>Price above the 50-day SMA</li>
            <li>Price at least 30% above its 52-week low</li>
            <li>Price within 25% of its 52-week high</li>
            <li>RS rank ≥ 70</li>
          </ol>
          <p className="text-[11px] text-gray-500 mt-2">
            The Analyze page shows the live count (e.g. <span className="font-mono">&quot;6/8
            criteria met&quot;</span>) in the signal&apos;s hover tooltip.
          </p>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4 mb-1 text-sm">Mean-Reversion Indicators</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Signal</th>
                <th className="text-left py-2 px-3 border border-gray-200">Class</th>
                <th className="text-center py-2 px-3 border border-gray-200">Base weight</th>
                <th className="text-center py-2 px-3 border border-gray-200">Accuracy</th>
                <th className="text-left py-2 px-3 border border-gray-200">Strength / Logic</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["RSI (14)", "Mean Rev.", "1.0", "62%", "RSI < 40 = bullish (oversold); > 70 = bearish; distance from 50 ÷ 50"],
                ["Stochastic %K (14,3)", "Mean Rev.", "0.8", "61%", "%K < 20 = bullish (oversold); > 80 = bearish; skips neutral zone"],
                ["Bollinger Bands (20, 2σ)", "Mean Rev.", "0.85", "62%", "%B < 0.3 = near lower band = bullish bounce setup; > 0.7 = bearish"],
              ].map(([s, cls, w, acc, src]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{s}</td>
                  <td className="py-2 px-3 border border-gray-200">
                    <span className={cls === "Trend" ? "text-green-700" : "text-amber-600"}>{cls}</span>
                  </td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center">{w}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-indigo-700">{acc}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{src}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4 mb-1 text-sm">Weekly Timeframe Adjustment (post-vote)</h3>
        <p className="text-xs text-gray-600 mb-2">
          After all signals vote, a bonus or penalty is added based on the weekly timeframe direction.
          This is <em>not</em> a voting signal — it&apos;s an adjustment applied to the total. The weekly
          direction is computed by resampling the existing daily bars to weekly — no additional API call.
        </p>
        <Warn>
          <strong>Daily-confirmation gate (anti-top-trap):</strong> the weekly is a <em>lagging</em> signal —
          it stays bullish well after the daily has rolled over, which is exactly what happens at a local top.
          To stop the weekly from propping up scores near tops, the bullish bonus only applies at full
          strength when the <strong>daily vote is also bullish</strong> (direction = long). When the daily has
          rolled over to <strong>neutral</strong>, the bonus is scaled by <code className="font-mono bg-amber-100 px-1 rounded">×0.2</code>{" "}
          (e.g. +7.5 → +1.5). The bearish-weekly <em>penalty</em> is never scaled — a weekly headwind is a
          real risk regardless of the daily.
        </Warn>
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Condition</th>
                <th className="text-center py-2 px-3 border border-gray-200">Adjustment</th>
                <th className="text-left py-2 px-3 border border-gray-200">Rationale</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Bullish weekly + Stage 2 + daily long", "+7.5 pts", "Highest conviction: daily and weekly both confirm in the right stage"],
                ["Bullish weekly (any stage) + daily long", "+5.5 pts", "Higher timeframe tailwind confirming a live daily signal"],
                ["Bullish weekly but daily NOT long (neutral)", "×0.2 (e.g. +1.5)", "Daily has rolled over — likely a local top; weekly tailwind heavily discounted"],
                ["Bearish weekly", "−6.0 pts", "Higher timeframe headwind — daily setup fighting an uphill battle (never scaled)"],
                ["Neutral weekly + Stage 2 + daily long", "+1.0 pts", "Slight bonus for the right stage despite a neutral weekly"],
                ["Otherwise", "0 pts", "No adjustment"],
              ].map(([cond, adj, rationale]) => (
                <tr key={cond} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{cond}</td>
                  <td className={`py-2 px-3 border border-gray-200 font-mono text-center ${adj.startsWith("+") ? "text-teal-700" : adj.startsWith("−") ? "text-red-600" : "text-gray-500"}`}>{adj}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4">Agreement bonus</h3>
        <CodeBlock>{`# If ≥70% of active signals agree on direction:
agreement_bonus = 1.20  # +20% to final score

# Rationale: independent indicators rarely converge by chance.
# When 7 out of 9 signals all say "bullish", the conviction
# is qualitatively stronger than 5 out of 9.`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-4 mb-1 text-sm">Local-top / distribution penalty (post-vote)</h3>
        <p className="text-xs text-gray-600 mb-2">
          A companion to the weekly-confirmation gate. The gate stops the lagging weekly from propping up a
          neutral daily; this penalty actively docks points when a name shows <em>topping</em> behaviour
          even while its daily is still technically long. It only applies to long / neutral (bullish-leaning)
          names — a short-biased name is already scored down. Total capped at <strong>−8 pts</strong>.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Signature</th>
                <th className="text-center py-2 px-3 border border-gray-200">Penalty</th>
                <th className="text-left py-2 px-3 border border-gray-200">Why it matters at a top</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["≥3 distribution days in last 10", "−3.0", "O'Neill institutional-selling tell: down days on rising volume cluster near tops"],
                ["MACD histogram fading at highs", "−2.0", "Histogram positive but falling 3 bars — buying pressure easing while price is elevated"],
                ["Bearish RSI divergence", "−3.0", "Price prints a higher high but RSI prints a lower high — classic exhaustion signal"],
              ].map(([sig, pen, why]) => (
                <tr key={sig} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{sig}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-red-600">{pen}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[11px] text-gray-500 mt-2">
          These stack with the RSI/EMA21 overextension penalty and show up in the Analyze page&apos;s P Score
          breakdown notes (e.g. <span className="font-mono">&quot;3 distribution days in last 10&quot;</span>).
        </p>
      </Section>

      <Section id="pscore-regime" title="P Score: Regime Multipliers">
        <p>
          The market regime modifies how much weight each signal class receives. A trending regime
          rewards trend-following signals; a ranging regime rewards mean-reversion signals.
          Regime is inferred from the Weinstein stage: Stage 2 = trend, Stage 4 = range, else transition.
        </p>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Regime</th>
                <th className="text-left py-2 px-3 border border-gray-200">Detected when</th>
                <th className="text-center py-2 px-3 border border-gray-200">Trend signal mult.</th>
                <th className="text-center py-2 px-3 border border-gray-200">Mean-rev. mult.</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Trend",      "Weinstein Stage 2",           "1.15×", "0.70×"],
                ["Transition", "Stage 1 or 3 (default)",      "0.95×", "0.85×"],
                ["Range",      "Weinstein Stage 4",           "0.75×", "1.15×"],
              ].map(([r, w, t, m]) => (
                <tr key={r} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{r}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{w}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-green-700">{t}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-amber-600">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Note>
          <strong>Why RSI is mean-reversion?</strong> RSI above 70 is conventionally overbought —
          it signals the stock has moved far from equilibrium and a pullback is statistically likely.
          That&apos;s the opposite of a trend-following signal. In a trending regime, the RSI component gets
          downweighted (0.70×) so it doesn&apos;t penalise a stock just because it has momentum.
        </Note>
      </Section>

      <Section id="pscore-grades" title="P Score: Grade Thresholds">
        <CodeBlock>{`# P Grade thresholds
A  →  prob_score ≥ 75   (strong signal alignment — high probability setup)
B  →  prob_score ≥ 60   (good alignment — most signals agree)
C  →  prob_score ≥ 45   (partial alignment — some signals conflict)
D  →  prob_score  < 45  (weak alignment — signals disagreeing or absent)`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">P Grade + setup</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
                <th className="text-left py-2 px-3 border border-gray-200">Trade implication</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["PA + setup firing", "Strong evidence and a defined entry", "Maximum conviction — size up"],
                ["PB + setup firing", "Good evidence with a defined entry", "Normal size"],
                ["PA, no setup firing", "Strong trend but no clean entry yet", "Add to watchlist — wait for a setup to trigger"],
                ["PC / PD + setup firing", "Entry exists but evidence is weak/mixed", "Reduce size or pass — check the conflicting signals"],
                ["PD, no setup", "No edge", "Skip"],
              ].map(([c, i, t]) => (
                <tr key={c} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold text-teal-700">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-700">{i}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{t}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Warn>
          <strong>The P Score uses backtested accuracy estimates</strong> — not live-calibrated against your
          broker fills. Treat it as a signal-alignment gauge, and always confirm the entry, stop, and targets
          from the firing setup on the Analyzer page before trading.
        </Warn>
      </Section>

      {/* ── END P SCORE ───────────────────────────────────────────────────────── */}

      {/* Weinstein Stage */}
      <Section id="weinstein" title="Signal: Weinstein Stage">
        <p>
          Stan Weinstein&apos;s four-stage model classifies every stock into a lifecycle phase based on the
          30-week moving average (approximated as <strong>150 daily bars</strong>).
          Only Stage 2 stocks are in a confirmed uptrend — every other stage carries elevated risk.
        </p>

        <CodeBlock>{`# Classification logic (daily bars, minimum 150 required)
sma150 = close.rolling(150).mean()

slope_pct = (sma150.iloc[-1] - sma150.iloc[-20]) / sma150.iloc[-20]  # 4-week slope
price_above = close.iloc[-1] > sma150.iloc[-1]

if   price_above  and slope_pct >  0.01:  stage = 2  # Advancing
elif price_above  and slope_pct > -0.01:  stage = 1  # Could be basing / early S2
elif not price_above and slope_pct > 0:   stage = 3  # Topping
else:                                     stage = 4  # Declining`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Stage</th>
                <th className="text-left py-2 px-3 border border-gray-200">Name</th>
                <th className="text-left py-2 px-3 border border-gray-200">Condition</th>
                <th className="text-left py-2 px-3 border border-gray-200">Score pts</th>
                <th className="text-left py-2 px-3 border border-gray-200">Action</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["S1", "Basing", "Flat MA, price at/below MA", "4", "Wait — accumulation phase"],
                ["S2", "Advancing", "Rising MA (+1%/4wk), price above", "10", "Trade here — confirmed uptrend"],
                ["S3", "Topping", "MA rolling over, price below", "2", "Avoid new longs"],
                ["S4", "Declining", "Falling MA, price below MA", "0", "Short only"],
                ["?", "Unknown", "Fewer than 150 bars of data", "5", "Insufficient history"],
              ].map(([s, n, c, p, a]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-bold text-indigo-700">{s}</td>
                  <td className="py-2 px-3 border border-gray-200">{n}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold text-center">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{a}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Note>
          <strong>Why 150 bars?</strong> 30 weeks × 5 trading days = 150 daily bars. This maps exactly
          to Weinstein&apos;s original definition. Using a 200-day MA (the common US convention) would be
          slightly different — the 150-bar version matches the weekly chart practitioners use.
        </Note>
      </Section>

      {/* A/D Net */}
      <Section id="adnet" title="Signal: O'Neill A/D Net">
        <p>
          William O&apos;Neil&apos;s accumulation/distribution day concept counts institutional footprint.
          Heavy buying days (accumulation) suggest funds are building positions; heavy selling days
          (distribution) suggest they&apos;re exiting.
        </p>

        <CodeBlock>{`# Computed over the last 25 trading days
lookback = 25

acc_days = 0
dist_days = 0

for each bar in last 25:
    change_pct = (close - prev_close) / prev_close

    # Accumulation: up day on higher volume, closing in upper half
    if (change_pct >= +0.002
        and volume > prev_volume
        and close > (high + low) / 2):
        acc_days += 1

    # Distribution: down day on higher volume
    elif (change_pct <= -0.002 and volume > prev_volume):
        dist_days += 1

ad_net = acc_days - dist_days`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">A/D Net</th>
                <th className="text-left py-2 px-3 border border-gray-200">Score pts</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["+10 or more", "+5", "Strong institutional buying — ideal"],
                ["+4 to +9", "+2 to +4.5", "Moderate accumulation"],
                ["0", "0", "Neutral — funds neither buying nor selling"],
                ["-4 to -1", "-0.5 to -2", "Mild distribution — caution"],
                ["-10 or less", "−5", "Heavy distribution — avoid"],
              ].map(([n, p, i]) => (
                <tr key={n} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono">{n}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold text-center">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{i}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Note>
          <strong>Why ±5 pts cap?</strong> A/D is a confirmation signal, not a primary one. Capping at ±5 pts
          means even extreme accumulation can&apos;t rescue a weak pattern, and extreme distribution can&apos;t sink
          an otherwise perfect setup below Grade B. It&apos;s a tiebreaker — intended to tip borderline calls.
        </Note>
      </Section>

      {/* Overextension Penalty */}
      <Section id="overext" title="Signal: Overextension Penalty">
        <p>
          When a stock is already over-extended (RSI in overbought territory, or price far above its
          short-term mean), chasing the entry carries higher reversal risk. The penalty docks the raw
          pattern confidence, and the P Score applies the same RSI/EMA21 overextension rules after the vote.
        </p>

        <CodeBlock>{`# RSI penalty — each point above RSI 80 costs 0.5 pts
rsi_14 = compute_RSI(close, 14)
if rsi_14 > 80:
    rsi_penalty = (rsi_14 - 80) * 0.005   # e.g., RSI=90 → -0.05 (5 pts)

# EMA21 extension penalty — linear from 8% to 25% above EMA21
ema21 = close.ewm(span=21).mean()
pct_above = (close.iloc[-1] - ema21.iloc[-1]) / ema21.iloc[-1]
if pct_above > 0.08:
    ext_penalty = min(0.10, (pct_above - 0.08) * 0.588)  # up to 10 pts

# Combined cap: maximum 20 pts total penalty
total_penalty = min(0.20, rsi_penalty + ext_penalty)

# Applied to confidence (floor = 0.30)
adjusted_confidence = max(0.30, confidence - total_penalty)

# Shown in the Notes column as: ⚠ Overextended (-Xpts)`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Condition</th>
                <th className="text-left py-2 px-3 border border-gray-200">Penalty</th>
                <th className="text-left py-2 px-3 border border-gray-200">Max</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["RSI > 80", "0.5 pts per RSI point above 80", "10 pts (RSI=100)"],
                ["Price > 8% above EMA21", "Linear from 0 to 10 pts (at 25% extension)", "10 pts"],
                ["Combined cap", "—", "20 pts total"],
                ["Confidence floor", "—", "Minimum 0.30 (30 pts)"],
              ].map(([c, p, m]) => (
                <tr key={c} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-red-600">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Warn>
          <strong>Why not just filter out over-extended stocks?</strong> Filtering removes them entirely,
          which loses information. A penalised Grade B is more useful than no result — it tells you
          &quot;this setup exists but wait for a better entry.&quot; The Notes column shows the penalty amount so
          you know why it was docked.
        </Warn>
      </Section>

      {/* RS */}
      <Section id="rs" title="Signal: Relative Strength Score">
        <p>
          IBD-style RS score: how has this stock performed versus SPY over 3, 6, 9, and 12 months?
          The weighting front-loads recent performance (3 months = 40%) because recent price action
          is most predictive of near-term continuation.
        </p>

        <CodeBlock>{`# Performance ratios vs SPY (not % change — ratio eliminates SPY baseline)
r3m  = (stock_close[-63]  / stock_close[-1])  / (spy_close[-63]  / spy_close[-1])
r6m  = (stock_close[-126] / stock_close[-1])  / (spy_close[-126] / spy_close[-1])
r9m  = (stock_close[-189] / stock_close[-1])  / (spy_close[-189] / spy_close[-1])
r12m = (stock_close[-252] / stock_close[-1])  / (spy_close[-252] / spy_close[-1])

# Weighted average — recent performance weighted more heavily
rs_raw = 0.40 * r3m + 0.20 * r6m + 0.20 * r9m + 0.20 * r12m

# Map to 0–100 (50 = matches SPY exactly, 100 = maximum outperformance)
rs_score = mapped 0–100 across the scanned universe`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Score</th>
                <th className="text-left py-2 px-3 border border-gray-200">Label</th>
                <th className="text-left py-2 px-3 border border-gray-200">Points contributed</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["≥ 90", "RS Elite", "22.5 pts", "Top decile — stock crushing the market"],
                ["≥ 75", "RS Strong", "≥ 18.75 pts", "Clear outperformer — preferred entry zone"],
                ["≥ 50", "RS Average", "≥ 12.5 pts", "Matching SPY — marginal"],
                ["≥ 25", "RS Weak", "≥ 6.25 pts", "Underperforming — avoid unless pattern is exceptional"],
                ["< 25", "RS Laggard", "< 6.25 pts", "Significant underperformer — don't touch"],
              ].map(([s, l, p, i]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold">{s}</td>
                  <td className="py-2 px-3 border border-gray-200">{l}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{i}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Note>
          <strong>Default min RS = 50.</strong> The dashboard defaults to RS ≥ 50 so every result is at
          least matching the market. For high-quality scans, raise it to 70–75 to see only clear leaders.
          Qullamaggie typically trades RS ≥ 70 stocks exclusively.
        </Note>
      </Section>

      {/* ADX */}
      <Section id="adx" title="Signal: ADX — Average Directional Index">
        <p>
          ADX (J. Welles Wilder, 1978) measures <strong>trend strength</strong>, not direction.
          A reading of 40 on a falling stock means the decline is <em>strong</em>.
          It answers the question: <em>is this stock trending cleanly, or chopping around?</em>
          Qullamaggie wants momentum stocks in powerful trends, not range-bound noise.
        </p>

        <CodeBlock>{`# Step 1 — True Range (captures gap-open volatility)
tr   = max(high - low,  |high - prev_close|,  |low - prev_close|)

# Step 2 — Directional Movement (+DM and -DM)
+DM  = max(high - prev_high, 0)  if  high - prev_high  >  prev_low - low  else 0
-DM  = max(prev_low - low,  0)   if  prev_low - low    >  high - prev_high else 0

# Step 3 — Wilder's EWM smoothing (period = 14)
ATR14  = ewm(tr,   span=14)
+DI14  = 100 × ewm(+DM, span=14) / ATR14
-DI14  = 100 × ewm(-DM, span=14) / ATR14

# Step 4 — Directional Index → ADX (second smoothing pass)
DX   = 100 × |+DI14 - -DI14| / (+DI14 + -DI14)
ADX  = ewm(DX, span=14)       # range 0–100, direction-agnostic`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">ADX value</th>
                <th className="text-left py-2 px-3 border border-gray-200">Checklist</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
                <th className="text-left py-2 px-3 border border-gray-200">What it means for your trade</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["≥ 30", "✅ Trending",   "Strong, established trend",  "Momentum stocks love this zone — breakouts extend, pullbacks are buyable"],
                ["20–29", "⚠️ Developing", "Trend building, not mature", "Could be early in a move or consolidating — confirm with RS and stage"],
                ["< 20",  "❌ Weak",       "Range-bound / choppy",        "Avoid new longs — setups fail more often without trend momentum"],
              ].map(([v, c, i, m]) => (
                <tr key={v} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold">{v}</td>
                  <td className="py-2 px-3 border border-gray-200">{c}</td>
                  <td className="py-2 px-3 border border-gray-200">{i}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Note>
          <strong>ADX is checklist-only — it does not feed the P Score.</strong>{" "}
          A strong EP setup can fire on a low-ADX day (the catalyst itself creates the momentum).
          Adding ADX to the score would unfairly penalise early breakouts before trend strength
          has had time to register. Use it as confirmation: high ADX (30+) makes existing setups
          more reliable, but a low ADX alone is not a reason to skip an otherwise excellent setup.
        </Note>

        <Warn>
          <strong>ADX does not tell you the direction</strong> — only that a trend exists.
          A stock with ADX = 60 and +DI below -DI is in a strong <em>downtrend</em>.
          Always read ADX alongside the MA stack and Weinstein stage (Stage 2 = advancing, the only tradeable stage).
        </Warn>
      </Section>

      {/* Relative Volume */}
      <Section id="rvol" title="Signal: Relative Volume (RVOL)">
        <p>
          RVOL answers the simplest question a trader can ask: <em>is today unusual?</em> A breakout on
          3× normal volume is far more meaningful than one on 0.8× — institutions are participating.
          Every scan result now shows RVOL as a sub-line under the Price column.
        </p>
        <CodeBlock>{`# Today's volume / 20-day average volume
avg_20  = volume.iloc[-21:-1].mean()   # excludes today
rvol    = round(today_volume / avg_20, 2)

# Display colour thresholds (frontend only — not a P Score signal)
≥ 2.0×  → violet/purple  (volume surge — strong participation)
≥ 1.3×  → gray           (above average, worth noting)
< 1.3×  → light gray     (ordinary volume)`}
        </CodeBlock>
        <Note>
          <strong>Why not a P Score signal?</strong> RVOL is a raw daily number that&apos;s already
          partially captured by the pattern detectors themselves — EP requires ≥2× vol, TB requires
          ≥1.2× vol, PP compares to the highest down-day volume. Adding it again as its own signal
          would double-count it. It&apos;s shown as context, not scored.
        </Note>
      </Section>

      {/* ICS */}
      <Section id="ics" title="Signal: ICS — Institutional Composite Score (0–100)">
        <p>
          The ICS combines four independent volume-flow indicators into one institutional conviction
          score. Unlike the O&apos;Neil A/D Net (which counts discrete accumulation/distribution days),
          the ICS measures <em>continuous flow</em> — OBV, Chaikin Money Flow, the A/D line slope,
          and Money Flow Index. It&apos;s adapted from the institutional scoring system in the
          technical-analysis reference repo.
        </p>
        <CodeBlock>{`# Each component contributes 0-25 pts → total 0-100

# OBV trend (25 pts): On-Balance Volume rising over 20 bars?
obv      = cumsum(sign(close.diff()) × volume)
obv_pts  = 25  if obv[-1] > obv[-20]  else 0

# CMF — Chaikin Money Flow (0-25 pts, proportional):
mf_mult  = ((close - low) - (high - close)) / (high - low)
cmf      = sum(mf_mult × volume, 20 bars) / sum(volume, 20 bars)
cmf_pts  = clamp(cmf × 125, 0, 25)   # +0.20 CMF → full 25 pts

# A/D line trend (25 pts): Chaikin A/D cumulative line rising?
ad_line  = cumsum(mf_mult × volume)
ad_pts   = 25  if ad_line[-1] > ad_line[-20]  else 0

# MFI — Money Flow Index (0-25 pts, proportional above 50):
mfi_pts  = clamp((MFI(14) - 50) × 0.5, 0, 25)

ICS = obv_pts + cmf_pts + ad_pts + mfi_pts`}
        </CodeBlock>
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">ICS Range</th>
                <th className="text-left py-2 px-3 border border-gray-200">Colour</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["75 – 100", "Green", "All 4 indicators positive — institutions clearly accumulating"],
                ["40 – 74",  "Amber", "Mixed signals — some buying, some selling, or neutral"],
                ["0 – 39",   "Red",   "Multiple indicators negative — distribution or lack of interest"],
              ].map(([r, c, i]) => (
                <tr key={r} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono">{r}</td>
                  <td className="py-2 px-3 border border-gray-200">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{i}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>
          <strong>ICS vs A/D Net in the P Score:</strong> both vote in the P Score — A/D Net (O&apos;Neil
          style day count) at weight 1.0 and ICS at weight 1.2. They use different methodologies, so
          together they give you both the &quot;discrete day&quot; view (A/D Net) and the
          &quot;continuous flow&quot; view (ICS).
        </Note>
      </Section>

      {/* Bull Exhaustion Warning */}
      <Section id="exhaustion" title="Signal: Bull Exhaustion Early Warning">
        <p>
          When three conditions align, a warning is appended to the Notes column:
          the stock is overbought (RSI &gt; 70), buying volume is drying up, and price is already
          extended above its short-term mean. This doesn&apos;t invalidate the setup — but it signals
          that chasing here carries elevated reversal risk.
        </p>
        <CodeBlock>{`# All three must be true to trigger the warning:

# 1. RSI(14) > 70 — overbought momentum
rsi_val > 70

# 2. Volume fading — recent 5-bar avg < prior 5-bar avg × 0.75
recent_5_vol_avg < prior_5_vol_avg × 0.75

# 3. Price extended — > 3% above EMA21
(price - EMA21) / EMA21 > 0.03

# Output (appended to Notes): "Bull exhaustion: RSI 74, vol fading"`}
        </CodeBlock>
        <h3 className="font-semibold text-gray-800 mt-2">Why these thresholds?</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse mt-2">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Condition</th>
                <th className="text-left py-2 px-3 border border-gray-200">Threshold</th>
                <th className="text-left py-2 px-3 border border-gray-200">Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["RSI overbought", "> 70", "RSI 70–80 is extended but not yet extreme. Above 80 triggers the overextension penalty separately."],
                ["Volume fading", "< 75% of prior 5-bar", "Buyers visibly stepping back — momentum divergence. 25% drop is meaningful, not just noise."],
                ["EMA21 extension", "> 3%", "Above 3% suggests the move is already priced in for the short term. Below 3% is still tractable."],
              ].map(([c, t, r]) => (
                <tr key={c} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono">{t}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{r}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Warn>
          <strong>Exhaustion ≠ exit signal.</strong> This warning is a &quot;wait for a better entry&quot; flag,
          not a &quot;sell&quot; signal. Qullamaggie stocks in strong uptrends can stay overbought for weeks.
          The warning tells you to be patient — let RSI reset to 40–60 before adding or entering.
        </Warn>
      </Section>

      {/* Wyckoff Spring */}
      <Section id="wys" title="Setup: Wyckoff Spring (WYS)">
        <p>
          The Wyckoff Spring is a <strong>shakeout</strong> below the floor of a tight accumulation range.
          Weak holders are forced out; institutions absorb the supply. The snap-back above range floor
          traps the shorts who sold the breakdown, fuelling the next leg up. It&apos;s the highest-quality
          variant of the &quot;bear trap&quot; pattern family — more specific and more reliable than FBD because
          it requires confirmed prior consolidation.
        </p>

        <CodeBlock>{`# 1. Accumulation range: 40 bars ending 3 bars before spring
#    Range must be tight: (range_high - range_floor) / mean < 15%
range_pct < 0.15   # tight trading range confirmed

# 2. Spring candle: breaks below range floor by ≤ 3%
penetration = (range_floor - spring_close) / range_floor
0 < penetration ≤ 0.03   # shallow shakeout = Wyckoff signature

# 3. Recovery within 3 bars: closes back above floor
close[spring+1 to spring+3] > range_floor

# 4. Current price still above floor (spring held — not retested)
curr_close > range_floor

# ── Confidence scoring ────────────────────────────────────
base conf = 0.60
penetration < 1%    → +0.10   # ultra-shallow = textbook Wyckoff
penetration < 2%    → +0.06
recovery in 1 bar   → +0.07   # immediate snap = very strong rejection
spring vol > 1.5×   → +0.05   # trapped sellers visible in volume
range_pct < 8%      → +0.05   # tighter range = stronger accumulation

# ── Levels ───────────────────────────────────────────────
Entry  = current price (active state — already recovering)
Stop   = spring low × 0.99 (below the shakeout wick)
T1     = top of accumulation range
T2     = range_high + (range_high - range_floor)  # measured move`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-2">WYS vs FBD — what&apos;s the difference?</h3>
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Dimension</th>
                <th className="text-left py-2 px-3 border border-gray-200">WYS (Wyckoff Spring)</th>
                <th className="text-left py-2 px-3 border border-gray-200">FBD (Failed Breakdown)</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Prior context", "Requires tight trading range (range_pct < 15%, 40 bars)", "Any support level — no range requirement"],
                ["Penetration depth", "≤ 3% below floor", "0.4% – 6% below support"],
                ["Conviction", "Higher — confirmed accumulation phase", "Lower — could be any support test"],
                ["Priority in engine", "2 (above PP/PULL/FBD)", "4 (lowest priority trap)"],
                ["Best timeframe", "Weeks-long consolidations", "Any support level"],
              ].map(([d, w, f]) => (
                <tr key={d} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{d}</td>
                  <td className="py-2 px-3 border border-gray-200 text-violet-700">{w}</td>
                  <td className="py-2 px-3 border border-gray-200 text-rose-600">{f}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {/* Fibonacci Grid */}
      <Section id="fibonacci" title="Analysis: Fibonacci Grid">
        <p>
          Fibonacci is <strong>not a score input</strong> — it doesn&apos;t move the P Score. It&apos;s a
          confluence map shown on the analyze page: where a pullback is likely to find support and where a
          trend might run to. The hard part of Fibonacci is the <strong>anchor</strong> — pick the wrong
          swing and every level is wrong. We remove that judgment call by anchoring deterministically.
        </p>

        <CodeBlock>{`# 1. Anchor: dominant swing in the last 120 bars (≈ 6 months)
hi = max(high[-120:]);  lo = min(low[-120:])
range = hi - lo
direction = "uptrend" if hi prints AFTER lo else "downtrend"
#   → the extreme that printed LAST defines the active leg

# 2. Retracement ladder (pullback support, measured from the high in an uptrend)
level(r) = hi - range * r      for r in [0.236, 0.382, 0.50, 0.618, 0.786]
#   0.50 is not a true Fib ratio but is a key psychological level (kept by convention)

# 3. Golden pocket — the highest-probability reaction band
golden = [hi - range*0.65, hi - range*0.618]   # 61.8%–65%

# 4. Extension targets (project the leg beyond the swing)
ext(e) = lo + range * e        for e in [1.272, 1.618, 2.0, 2.618]

# 5. Where price sits
retrace_depth = (hi - price) / range           # shallow = strong trend
in_golden_pocket = golden.low <= price <= golden.high`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-3">Why these choices</h3>
        <ul className="list-disc ml-5 space-y-1 text-sm">
          <li>
            <strong>Deterministic anchor (high &amp; low, ordered by time).</strong> Arbitrary/forced
            anchoring is the #1 way Fibonacci misleads. Using the dominant swing in a fixed window makes the
            levels reproducible and removes hindsight bias.
          </li>
          <li>
            <strong>Golden pocket (61.8–65%).</strong> Retail, institutions and algos all watch this band,
            so reactions there are more probable — but a tag alone is not a reversal.
          </li>
          <li>
            <strong>Depth as a trend-strength read.</strong> A shallow retrace (holds 23.6–38.2%) signals a
            strong trend; a deep one (78.6%) signals a weakening leg at risk of failing.
          </li>
          <li>
            <strong>Extensions for targets.</strong> 1.272 / 1.618 are the primary trend targets; reconcile
            with the setup&apos;s own measured-move / prior-S&amp;R targets and take the more conservative —
            and let polarity / prior resistance in the path override the Fibonacci number.
          </li>
        </ul>

        <p className="mt-3 text-sm bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-amber-900">
          <strong>Confluence, not a trigger.</strong> A Fibonacci level on its own is just a line. It earns a
          trade only when it overlaps prior S/R, a moving average or a trendline <em>and</em> a reversal
          candle prints at it. Treat it as one vote in the convergence, never a standalone entry.
        </p>
      </Section>

      {/* Options (leading) */}
      <Section id="options" title="Analysis: Options (Leading)">
        <p>
          Options are one of the few genuinely <strong>leading</strong> datasets: their prices encode the
          market&apos;s <em>expectations</em> about future volatility and direction, whereas price / volume /
          moving averages only describe what already happened. The analyze page distils a near-dated chain
          (≤ 45 days) into a handful of forward-looking tells. Like Fibonacci, it&apos;s a <strong>context /
          confluence layer — not a P Score input</strong>.
        </p>

        <CodeBlock>{`# Near-dated chain (nearest expiry for IV/skew; ≤3 expiries summed for ratios)
ATM IV            = avg(impliedVol of nearest-strike call & put)        # how big a move is priced
expected_move     = ATM call mid + ATM put mid     (± $ and ± % of spot) # the straddle range by expiry
skew              = IV(OTM put −10%) − IV(OTM call +10%)   in IV points
                    # positive = downside hedging (fear); negative = call demand (upside)
put_call_vol      = put volume  / call volume       # sentiment (contrarian at extremes)
put_call_oi       = put OI      / call OI            # resting positioning
vol_oi_ratio      = total volume / total OI          # ≥0.5 = fresh positioning ("unusual activity")

# Sentiment lean (context, contrarian-aware)
bullish  if call-heavy flow (P/C vol < 0.7) or call-skewed IV (skew < −1)
bearish  if put-heavy flow  (P/C vol > 1.2) or fear skew     (skew > +3)`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-3">The four kinds of &quot;leading&quot; (and how we weight them)</h3>
        <ul className="list-disc ml-5 space-y-1 text-sm">
          <li><strong>Expectation-pricing</strong> (IV, expected move) — the strongest, cleanest use. The expected move pairs directly with <strong>EP / catalyst setups</strong>: it sizes realistic targets and stops around the event.</li>
          <li><strong>Sentiment</strong> (put/call ratio, skew) — leading <em>at extremes</em>, and contrarian: extreme fear is bullish, extreme complacency bearish.</li>
          <li><strong>Smart-money positioning</strong> (unusual activity, OI build) — sometimes informed, but noisy (could be hedges/spreads), so treated as a flag, not a signal.</li>
          <li><strong>Dealer flow</strong> (gamma / max pain) — leading intraday, less for swing trades; deferred (see below).</li>
        </ul>

        <p className="mt-3 text-sm bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-amber-900">
          <strong>Leading ≠ crystal ball.</strong> Options tell you what the market <em>expects</em> and how it&apos;s
          positioned — context and confluence, not a directional guarantee. Use the expected move for sizing and the
          skew / P-C as a sentiment overlay; confirm direction with price and the firing setup.
        </p>

        <p className="mt-2 text-xs text-gray-500">
          <strong>Data:</strong> yfinance option chains (free, includes IV/OI/volume). 15-min cache.
          <strong> Deferred (Phase 2):</strong> IV rank/percentile (needs stored IV history), gamma exposure / max pain,
          and optionally feeding an options vote into the P Score once the layer is validated.
        </p>
      </Section>

      {/* Market Positioning Dial */}
      <Section id="positioning" title="🧭 Market Positioning Dial">
        <p>
          Everything above is computed from <em>price and volume</em> — which makes it inherently
          backward-looking. The Market Positioning panel on the Dashboard adds the one genuinely
          forward-looking dimension available for free: <strong>who is exposed, and how crowded is
          the boat?</strong> Positioning extremes are contrarian — maximum fear precedes rallies
          (forced sellers are done), maximum complacency precedes air pockets (no marginal buyer left).
        </p>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Source</th>
                <th className="text-left py-2 px-3 border border-gray-200">What it measures</th>
                <th className="text-left py-2 px-3 border border-gray-200">Contrarian extremes</th>
                <th className="text-center py-2 px-3 border border-gray-200">Updates</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["CFTC COT — leveraged funds", "Net position of hedge funds / CTAs in E-mini S&P 500 + Nasdaq futures, as % of open interest, z-scored vs ~3 years of weekly history. The closest free proxy to 'CTA positioning'.", "z ≤ −1.5 = crowded short (squeeze fuel, +1) · z ≥ +1.5 = crowded long (no marginal buyer, −1)", "Weekly (Fri, data as of Tue)"],
                ["SPY put/call volume ratio", "Puts ÷ calls traded across SPY expirations within ~35 days, computed from Alpaca options data. A hedging-demand gauge. (CBOE's equity-only ratio blocks server access — SPY skews put-heavy, so thresholds are calibrated for it.)", "≥ 2.0 = fear extreme (+1) · ≤ 1.1 = call-chasing complacency (−1)", "Daily"],
                ["NAAIM Exposure Index", "Average equity exposure reported by active money managers (0 = flat, 200 = leveraged long). Scraped from naaim.org's weekly publication.", "< 30 = washed out (+1) · > 90 = fully invested (−1)", "Weekly (Wed)"],
              ].map(([src, what, ext, upd]) => (
                <tr key={src} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{src}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{what}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600 text-[11px]">{ext}</td>
                  <td className="py-2 px-3 border border-gray-200 text-center text-[11px]">{upd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4">The dial</h3>
        <CodeBlock>{`# Each source votes contrarian at extremes:
#   fear / washed-out / crowded-short   → +1  (opportunity)
#   neutral                             →  0
#   complacent / crowded-long           → −1  (reduce aggression)
dial = sum(votes)        # −3 … +3

+2/+3  Fear extreme — breakouts have fuel, historically the best forward returns
+1     Cautiously supportive
 0     Neutral — trade the setups, normal sizing
−1     Getting crowded — tighten stops
−2/−3  Complacent / crowded — late-cycle, smaller size, defensive`}
        </CodeBlock>

        <Note>
          <strong>How to use it with the scanner:</strong> the dial is a <em>sizing and aggression
          gate</em>, not a per-stock signal — exactly how Qullamaggie sizes up or down with market
          conditions. A P-Grade A breakout in a +2 environment deserves full size; the same setup at
          −2 deserves a starter position and a tighter leash. The dial deliberately does NOT feed the
          P Score — it describes the market, not the stock.
        </Note>
        <Warn>
          <strong>Caveats:</strong> COT data is as-of Tuesday published Friday (3-day lag); NAAIM is a
          survey of a subset of managers; the SPY P/C proxy uses static thresholds until enough
          history accumulates to use percentiles. Positioning extremes can stay extreme for weeks —
          they are context, not timing triggers.
        </Warn>
      </Section>

      {/* Design Philosophy */}
      <Section id="philosophy" title="Design Philosophy">
        <h3 className="font-semibold text-gray-800">Why not just use raw confidence?</h3>
        <p>
          Pattern detectors (EP, TB, etc.) output a confidence value based purely on how well the chart
          matches the pattern criteria. Confidence knows nothing about whether:
        </p>
        <ul className="list-disc list-inside pl-2 space-y-1 text-gray-600">
          <li>The stock is in a confirmed uptrend (Weinstein Stage)</li>
          <li>The stock is outperforming the market (RS)</li>
          <li>Institutions are buying or selling (A/D Net, ICS, OBV, CMF)</li>
          <li>The higher timeframe agrees (weekly direction)</li>
          <li>The structure is that of a market leader (Minervini Trend Template)</li>
        </ul>
        <p className="mt-2">
          The <strong>P Score</strong> bundles all of this into one number — a weighted, regime-aware vote
          across up to 21 signals — so the grade reflects the full picture, not just the shape on the chart.
          The firing <strong>setup</strong> (EP, TB, …) then tells you the specific entry, stop, and targets.
        </p>

        <h3 className="font-semibold text-gray-800 mt-4">One score, not two</h3>
        <p>
          An earlier version of this tool also showed a fixed &quot;Q Score&quot; formula
          (quality×60 + RS×25 + stage×10 + A/D×5) side-by-side with the P Score. Two competing numbers
          created more confusion than insight, so the Q Score was retired. Everything it measured — RS
          leadership, Weinstein stage, A/D accumulation, the firing setup pattern, and stop tightness via
          each detector&apos;s confidence — now lives on as weighted signals <em>inside</em> the P Score.
        </p>

        <h3 className="font-semibold text-gray-800 mt-4">Comparison with the technical-analysis reference repo</h3>
        <p>
          The <em>technical-analysis</em> reference repo uses a config-driven probability scorer with
          backtested accuracy factors, regime multipliers, and signal-class categorisation. We have
          ported this architecture as the <strong>P Score</strong> — now the single score — using our six
          setup types as high-weight signals and recalibrating the accuracy factors against publicly
          available win-rate estimates.
        </p>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4">
          <p className="text-xs text-gray-500 uppercase font-semibold tracking-wide mb-2">Future improvements under consideration</p>
          <ul className="list-disc list-inside pl-2 space-y-1 text-gray-600 text-sm">
            <li>Live-calibrate accuracy factors from your own trade journal (P Score becomes personalised)</li>
            <li>Multi-timeframe P Score — run the same signal voting on weekly bars and blend results</li>
            <li>Volume profile score — breakout on above-average volume gets a precision boost</li>
            <li>Sector RS — stock outperforming both SPY and its sector ETF earns a multiplier</li>
            <li>Wyckoff accumulation phase detection (full cycle: PS→SC→AR→ST→LPS→SOS→BU)</li>
          </ul>
        </div>
      </Section>

      {/* Footer note */}
      <p className="text-xs text-gray-400 text-center pb-4">
        Not financial advice. All scores and grades are algorithmic approximations — always confirm on your own chart before trading.
      </p>
    </div>
  );
}
