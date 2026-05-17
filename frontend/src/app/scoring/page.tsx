import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scoring Algorithm — Qullamaggie Platform",
  description: "Full explanation of how the composite score, grade, and quality signals are computed",
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
  // Q Score
  { id: "qscore",       label: "Q Score — Qullamaggie Formula" },
  { id: "quality",      label: "  Step 1 — Quality Score" },
  { id: "composite",    label: "  Step 2 — Composite Score" },
  { id: "grade",        label: "  Step 3 — Grade Thresholds" },
  // P Score
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
          Every scan result carries <strong>two independent scores</strong>, each producing its own letter grade:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <div className="font-bold text-indigo-800 mb-1">Q Score — Qullamaggie Formula</div>
            <div className="text-xs text-indigo-700 space-y-1">
              <p>A fixed 4-component formula based on Kristjan Qullamaggie&apos;s methodology:</p>
              <code className="block font-mono bg-indigo-100 px-2 py-1 rounded text-[11px]">
                quality×60 + RS×25 + stage×10 + A/D×5
              </code>
              <p>Grade: <strong>A≥72 / B≥58 / C≥44 / D&lt;44</strong></p>
            </div>
          </div>
          <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
            <div className="font-bold text-teal-800 mb-1">P Score — Probability Scorer</div>
            <div className="text-xs text-teal-700 space-y-1">
              <p>A signal-voting model ported from the <em>technical-analysis</em> reference repo:</p>
              <code className="block font-mono bg-teal-100 px-2 py-1 rounded text-[11px]">
                Σ (strength × weight × accuracy × regime_mult)
              </code>
              <p>Grade: <strong>A≥75 / B≥60 / C≥45 / D&lt;45</strong></p>
            </div>
          </div>
        </div>
        <Note>
          <strong>Why two scores?</strong> The Q Score is anchored to Qullamaggie&apos;s explicit methodology —
          simple, interpretable, formula-driven. The P Score independently measures signal alignment across
          multiple indicators with backtested accuracy factors and regime-aware weighting. When both agree
          (e.g. QA + PA), conviction is highest. When they disagree, investigate why before trading.
        </Note>
      </Section>

      {/* Q Score — header section */}
      <Section id="qscore" title="📐 Q Score — Qullamaggie Formula">
        <p>
          The Q Score is a <strong>fixed, transparent formula</strong> directly derived from Kristjan Qullamaggie&apos;s
          publicly described methodology. It bundles pattern quality, relative strength, Weinstein stage,
          and institutional footprint into a single 0–100 number. The goal: rank setups so the genuinely
          best opportunities — tight pattern, RS leader, Stage 2, institutional accumulation — float to
          the top.
        </p>
        <p>Scoring happens in three steps:</p>
        <ol className="list-decimal list-inside space-y-1 pl-2">
          <li><strong>Quality score</strong> — adjusts raw pattern confidence for stop width and R:R</li>
          <li><strong>Q Score (composite)</strong> — adds RS, Weinstein stage, and A/D net on top</li>
          <li><strong>Q Grade</strong> — maps Q Score to A/B/C/D via calibrated thresholds</li>
        </ol>
        <Note>
          <strong>Why one unified score?</strong> Early versions showed RS, stage, and A/D as display-only
          columns. They looked nice but didn&apos;t affect ranking. A strong RS 90 stock with a mediocre pattern
          ranked the same as a weak RS 30 stock with the same pattern. The Q Score fixes this: all signals
          directly affect the grade, so an A grade truly means &quot;best across every dimension.&quot;
        </Note>
      </Section>

      {/* Step 1 — Quality Score */}
      <Section id="quality" title="Step 1 — Quality Score">
        <p>
          Raw pattern <strong>confidence</strong> (0.0–1.0) is output by each detector (EP, TB, PP, PULL, FBD).
          Confidence alone is a poor ranking signal because a pattern with a 10% stop width and 1:1 R:R can
          score identically to one with a 2% stop and 4:1 R:R. The quality score corrects for this.
        </p>

        <CodeBlock>{`# stop_factor: penalises wide stops
# 0% stop → 1.00 (no penalty)
# 7.5% stop → 0.50 (half credit)
# ≥15% stop → 0.40 (floor — still tradeable but tight)
stop_pct    = (entry - stop) / entry
stop_factor = clip(1 - stop_pct / 0.15, 0.40, 1.00)

# rr_factor: rewards good risk:reward
# R:R = 1.0 → 0.50 (unacceptable, barely viable)
# R:R = 2.0 → 1.00 (target — neutral)
# R:R ≥ 2.4 → 1.20 (bonus for exceptional setups)
rr_factor = clip(rr / 2.0, 0.50, 1.20)

# quality_score: capped at 1.0
quality_score = min(1.0, confidence × stop_factor × rr_factor)`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-2">Why these numbers?</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse mt-2">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Parameter</th>
                <th className="text-left py-2 px-3 border border-gray-200">Value</th>
                <th className="text-left py-2 px-3 border border-gray-200">Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["stop_factor floor", "0.40", "A 15%+ stop is too wide for Qullamaggie's style but not unacceptable — it still gets 40% credit rather than zero"],
                ["stop_factor divisor", "0.15 (15%)", "Qullamaggie rarely takes setups with stops wider than 10–12%. 15% is the absolute outer limit."],
                ["rr target", "2.0×", "Minimum viable R:R for a swing trade targeting at least 2× the risk"],
                ["rr cap", "1.20", "Capped so exceptional R:R can't mask a terrible pattern — maximum 20% bonus"],
                ["quality_score cap", "1.0", "Prevents the rr bonus from inflating the score above the natural ceiling"],
              ].map(([p, v, r]) => (
                <tr key={p} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono text-indigo-700">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono">{v}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{r}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4">Example</h3>
        <CodeBlock>{`# EP with confidence=0.85, stop_pct=6%, R:R=3.0
stop_factor   = clip(1 - 0.06/0.15, 0.40, 1.00) = clip(0.60, …) = 0.60
rr_factor     = clip(3.0/2.0, 0.50, 1.20)        = clip(1.50, …) = 1.20
quality_score = min(1.0, 0.85 × 0.60 × 1.20)    = min(1.0, 0.612) = 0.612`}
        </CodeBlock>
      </Section>

      {/* Step 2 — Composite Score */}
      <Section id="composite" title="Step 2 — Composite Score (0–100)">
        <p>
          The composite score adds market context signals on top of the pattern quality:
        </p>

        <CodeBlock>{`# ── Component breakdown ──────────────────────────────────────
base     = quality_score × 60      # pattern quality:  0–60 pts
rs_pts   = rs_score × 0.25         # relative strength: 0–25 pts
stg_pts  = {S2:10, S1:4, S3:2, S4:0, unknown:5}  # Weinstein: 0–10 pts
ad_pts   = clamp(ad_net × 0.5, -5, +5)            # A/D net:  -5 to +5 pts

composite = base + rs_pts + stg_pts + ad_pts   # 0–100`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-2">Weight rationale</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse mt-2">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Signal</th>
                <th className="text-left py-2 px-3 border border-gray-200">Max pts</th>
                <th className="text-left py-2 px-3 border border-gray-200">% of total</th>
                <th className="text-left py-2 px-3 border border-gray-200">Why this weight?</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Pattern quality", "60", "60%", "The chart pattern is the primary signal — without a real setup, everything else is noise"],
                ["Relative Strength", "25", "25%", "Qullamaggie explicitly filters for RS leaders. A great pattern in a laggard stock is far less likely to work"],
                ["Weinstein Stage", "10", "10%", "Stage 2 is a necessary condition, not just a nice-to-have. Non-S2 setups are penalised hard (S3=2pts, S4=0pts)"],
                ["A/D Net", "±5", "±5%", "A tiebreaker, not a primary signal. Institutional footprint is confirming evidence — used to tip close calls"],
              ].map(([s, m, p, r]) => (
                <tr key={s} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-semibold">{s}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center">{m}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono text-center text-indigo-700">{p}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{r}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="font-semibold text-gray-800 mt-4">Perfect score example</h3>
        <CodeBlock>{`# EP: confidence=0.90, stop_pct=4%, R:R=3.5, RS=90, Stage 2, A/D net=+8
stop_factor   = clip(1 - 0.04/0.15, …) = 0.733
rr_factor     = clip(3.5/2.0, …)       = 1.20  (capped)
quality_score = min(1.0, 0.90 × 0.733 × 1.20) = min(1.0, 0.792) = 0.792

base     = 0.792 × 60  = 47.5
rs_pts   = 90 × 0.25   = 22.5
stg_pts  = 10          (S2)
ad_pts   = clamp(8×0.5, -5, +5) = +5.0

composite = 47.5 + 22.5 + 10 + 5 = 85.0  → Grade A`}
        </CodeBlock>

        <Warn>
          <strong>Design intent:</strong> A great pattern with weak RS or non-Stage-2 <em>cannot</em> reach
          Grade A. For example, RS=30 + Stage 3 caps the external signal contribution at{" "}
          <code className="font-mono bg-amber-100 px-1 rounded">30×0.25 + 2 = 9.5 pts</code> versus the
          maximum 35 pts from a leader in Stage 2. This is intentional — Qullamaggie only trades leaders
          in uptrends.
        </Warn>
      </Section>

      {/* Step 3 — Grade */}
      <Section id="grade" title="Step 3 — Grade Thresholds">
        <CodeBlock>{`A  →  composite ≥ 72   (elite setup — all signals aligned)
B  →  composite ≥ 58   (good setup — most signals positive)
C  →  composite ≥ 44   (marginal — something is weak)
D  →  composite  < 44   (avoid — multiple signals poor)`}
        </CodeBlock>

        <h3 className="font-semibold text-gray-800 mt-2">Calibration story</h3>
        <p>
          The original thresholds (A≥80, B≥65, C≥50) were set theoretically. After testing with real data,
          a textbook-perfect setup — high confidence EP, tight stop, 3:1 R:R, RS 90, Stage 2,
          accumulation — only scored <strong>74.9</strong>. That should clearly be an A.
        </p>
        <p>
          The root cause: pattern confidence outputs from the detectors typically range 0.60–0.90, not
          0.90–1.00. A confidence of 0.85 with a good stop and R:R gives quality_score ≈ 0.75, which
          means <code className="font-mono bg-gray-100 px-1 rounded">base = 45 pts</code> — not 60.
          The thresholds were recalibrated to match real-world detector outputs:
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs border-collapse mt-2">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Grade</th>
                <th className="text-left py-2 px-3 border border-gray-200">Old threshold</th>
                <th className="text-left py-2 px-3 border border-gray-200">New threshold</th>
                <th className="text-left py-2 px-3 border border-gray-200">What it represents</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["A", "≥ 80", "≥ 72", "Strong pattern + RS leader + Stage 2 + some accumulation"],
                ["B", "≥ 65", "≥ 58", "Good pattern with one signal slightly weak"],
                ["C", "≥ 50", "≥ 44", "Pattern exists but RS, stage, or A/D is poor"],
                ["D", "< 50", "< 44", "Multiple signals negative — not worth trading"],
              ].map(([g, o, n, w]) => (
                <tr key={g} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-bold text-indigo-700">{g}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono line-through text-gray-400">{o}</td>
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold">{n}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{w}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
# Then apply overextension penalty (same RSI/EMA21 rules as Q Score)`}
        </CodeBlock>

        <Note>
          <strong>P Score vs Q Score:</strong> The Q Score is a fixed formula — it always gives the same
          weights. The P Score adapts: in a trending regime, trend signals are worth more; in a ranging
          regime, mean-reversion signals get a boost. An agreement bonus rewards when ≥70% of signals agree,
          reflecting the principle that conviction grows when independent indicators converge.
        </Note>
      </Section>

      <Section id="pscore-signals" title="P Score: Signals, Weights & Accuracy">
        <p>
          Every setup result uses these 12 signals. Each contributes to the P Score proportionally
          to its effective weight and its historical accuracy factor:
        </p>

        <div className="overflow-x-auto mt-2">
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
                ["TB (Tight Base)", "Trend", "2.5", "70%", "Confidence from detector"],
                ["Weinstein Stage", "Trend", "2.5", "72%", "1.0=S2, 0.5=S1, 0.0=S4"],
                ["EMA Stack", "Trend", "1.5", "70%", "full_bull=0.9, partial_bull=0.6"],
                ["ICS", "Trend", "1.2", "68%", "ICS score / 100"],
                ["FBD (Failed Breakdown)", "Trend", "2.0", "68%", "Confidence from detector"],
                ["PP (Pocket Pivot)", "Trend", "2.0", "65%", "Confidence from detector"],
                ["MACD", "Trend", "1.0", "65%", "Bullish/bearish histogram sign"],
                ["A/D Net", "Trend", "1.0", "65%", "Clipped ad_net / 10"],
                ["PULL (EMA Pullback)", "Trend", "1.5", "63%", "Confidence from detector"],
                ["RSI", "Mean Rev.", "1.0", "62%", "Distance from 50 ÷ 50"],
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

        <h3 className="font-semibold text-gray-800 mt-4">Agreement bonus</h3>
        <CodeBlock>{`# If ≥70% of active signals agree on direction:
agreement_bonus = 1.20  # +20% to final score

# Rationale: independent indicators rarely converge by chance.
# When 7 out of 9 signals all say "bullish", the conviction
# is qualitatively stronger than 5 out of 9.`}
        </CodeBlock>
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
        <CodeBlock>{`# P Grade thresholds (different from Q Grade — higher bar for A)
A  →  prob_score ≥ 75   (strong signal alignment — high probability setup)
B  →  prob_score ≥ 60   (good alignment — most signals agree)
C  →  prob_score ≥ 45   (partial alignment — some signals conflict)
D  →  prob_score  < 45  (weak alignment — signals disagreeing or absent)`}
        </CodeBlock>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-500 uppercase">
                <th className="text-left py-2 px-3 border border-gray-200">Condition</th>
                <th className="text-left py-2 px-3 border border-gray-200">Interpretation</th>
                <th className="text-left py-2 px-3 border border-gray-200">Trade implication</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["QA + PA", "Both formulas agree: elite setup", "Maximum conviction — size up"],
                ["QA + PB", "Q says elite, P says good", "Strong setup — normal size"],
                ["QB + PA", "P more confident than Q formula", "Worth investigating — check chart"],
                ["QA + PD", "Signals diverging sharply", "Pattern strong but signals mixed — wait or reduce size"],
                ["QD + PD", "Both poor", "Skip — no edge"],
              ].map(([c, i, t]) => (
                <tr key={c} className="border-b border-gray-100">
                  <td className="py-2 px-3 border border-gray-200 font-mono font-semibold text-indigo-700">{c}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-700">{i}</td>
                  <td className="py-2 px-3 border border-gray-200 text-gray-600">{t}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Warn>
          <strong>P Grade is not a replacement for Q Grade</strong> — it&apos;s a second opinion.
          The P Score uses backtested accuracy estimates (not live-calibrated against your broker fills).
          Treat it as a signal-alignment gauge: when it agrees with Q, trade normally. When it disagrees,
          reduce size and investigate the conflicting signals on the Analyzer page.
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
          short-term mean), chasing the entry carries higher reversal risk. The penalty is applied
          directly to the raw pattern confidence <em>before</em> the composite score is computed.
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
          <strong>ADX is checklist-only — it does not feed the composite score.</strong>{" "}
          A strong EP setup can fire on a low-ADX day (the catalyst itself creates the momentum).
          Adding ADX to the composite would unfairly penalise early breakouts before trend strength
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

# Display colour thresholds (frontend only — not in composite score)
≥ 2.0×  → violet/purple  (volume surge — strong participation)
≥ 1.3×  → gray           (above average, worth noting)
< 1.3×  → light gray     (ordinary volume)`}
        </CodeBlock>
        <Note>
          <strong>Why not in the composite score?</strong> RVOL is a raw daily number that&apos;s already
          partially captured by the pattern detectors themselves — EP requires ≥2× vol, TB requires
          ≥1.2× vol, PP compares to the highest down-day volume. Adding it again to the composite
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
          <strong>ICS vs A/D Net in the composite score:</strong> The A/D Net (O&apos;Neil style day count)
          contributes ±5 pts to the composite score. ICS is shown separately as additional context —
          it&apos;s a more comprehensive signal but uses a different methodology. Together they give you
          both the &quot;discrete day&quot; view (A/D Net) and the &quot;continuous flow&quot; view (ICS).
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
          <li>Institutions are buying or selling (A/D Net)</li>
          <li>The stop loss is tight enough to make the trade viable (stop_factor)</li>
          <li>The R:R justifies the risk (rr_factor)</li>
        </ul>
        <p className="mt-2">
          The composite score bundles all of this into one number so the grade reflects the full
          picture — not just the shape on the chart.
        </p>

        <h3 className="font-semibold text-gray-800 mt-4">Why not weight pattern quality even higher?</h3>
        <p>
          60% feels low for the primary signal, but consider: a perfect EP in a Stage 4 declining
          stock (RS=20, S4) would score <code className="font-mono bg-gray-100 px-1 rounded">
          60 + 5 + 0 + neutral = ~65</code> — Grade B at best. That&apos;s intentional.
          Qullamaggie would never take that trade, and the scanner shouldn&apos;t give it Grade A either.
        </p>

        <h3 className="font-semibold text-gray-800 mt-4">Comparison with the technical-analysis reference repo</h3>
        <p>
          The <em>technical-analysis</em> reference repo uses a config-driven probability scorer with
          backtested accuracy factors, regime multipliers, and signal-class categorisation. We have
          ported this architecture as the <strong>P Score</strong>, using our six setup types as primary
          signals and recalibrating the accuracy factors against publicly available win-rate estimates.
          The ICS (OBV + CMF + A/D line + MFI) was also ported as a standalone display signal.
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
