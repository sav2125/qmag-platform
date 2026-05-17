import Link from "next/link";

const SETUPS = [
  {
    slug: "ep",
    name: "Episodic Pivot",
    short: "EP",
    color: "bg-purple-100 border-purple-400 text-purple-800",
    badge: "bg-purple-600",
    icon: "⚡",
    tagline: "A catalyst-driven surge that resets a stock's trajectory",
    description:
      "An EP occurs when a major news event — earnings beat, FDA approval, contract win — causes a stock to gap up ≥5% on ≥2× average volume, breaking out of a prior base. Qullamaggie considers this his highest-conviction setup.",
    criteria: [
      "Gap or surge ≥5% on the catalyst day",
      "Volume ≥2× the 50-day average",
      "Stock was in a prior base (consolidation) before the move",
      "Consolidates within 12% of the EP high over the next few weeks",
      "Entry on breakout above the EP day's high",
    ],
    risk: "Stop below the EP day's low or the base low",
    target: "1.5–3× risk (R:R), measured move based on prior base depth",
  },
  {
    slug: "tb",
    name: "Tight Base",
    short: "TB",
    color: "bg-blue-100 border-blue-400 text-blue-800",
    badge: "bg-blue-600",
    icon: "📦",
    tagline: "A flat, quiet consolidation before a powerful breakout",
    description:
      "A Tight Base forms when a stock trades in a very narrow range (≤8%) for multiple weeks, showing that sellers are exhausted and buyers are absorbing supply. The tighter the range, the more explosive the eventual breakout.",
    criteria: [
      "Base range ≤8% from high to low over 10–60 bars",
      "Resistance level tested ≥2 times (proving supply is being absorbed)",
      "Volume contracts during the base (sellers drying up)",
      "Breakout on volume ≥1.2× average",
      "Stock near 52-week highs — not a base in the middle of nowhere",
    ],
    risk: "Stop just below the base low",
    target: "Measured move: depth of base added to breakout point",
  },
  {
    slug: "pp",
    name: "Pocket Pivot",
    short: "PP",
    color: "bg-green-100 border-green-400 text-green-800",
    badge: "bg-green-600",
    icon: "🎯",
    tagline: "Institutional accumulation showing up in the volume signature",
    description:
      "A Pocket Pivot signals that big money (institutions) is quietly buying. It occurs when a stock has an up day on volume greater than any down-day volume in the prior 10 sessions — revealing hidden demand. The stock must be above its 10-day MA.",
    criteria: [
      "Up day with volume > highest down-day volume in prior 10 sessions",
      "Stock is above its 10-day moving average",
      "EMA10 is above EMA20 (short-term trend is up)",
      "Not extended — ideally near a base or recent support",
      "RS score ≥50 (stock is a market leader)",
    ],
    risk: "Stop below the 10-day MA or the pocket pivot bar's low",
    target: "Next resistance level or prior highs; 1.5–2× risk",
  },
  {
    slug: "pull",
    name: "EMA Pullback",
    short: "PULL",
    color: "bg-orange-100 border-orange-400 text-orange-800",
    badge: "bg-orange-500",
    icon: "↩️",
    tagline: "Buy the dip in a confirmed uptrend",
    description:
      "In a strong uptrend, stocks rarely go straight up — they pull back to their moving averages and bounce. The EMA Pullback setup catches these low-risk entries where a leading stock touches its rising 21-day EMA and resumes its trend.",
    criteria: [
      "EMA21 is above EMA50 (confirmed uptrend)",
      "Both EMAs are rising (not flattening or turning down)",
      "Stock touched the EMA21 within the last 1–5 bars",
      "RSI between 38–68 (not overbought, not oversold)",
      "Volume is low on the pullback (no distribution)",
    ],
    risk: "Stop below the EMA50 or the recent swing low",
    target: "Prior highs or measured move; typically 2–3× risk in strong trends",
  },
  {
    slug: "fbd",
    name: "Failed Breakdown",
    short: "FBD",
    color: "bg-rose-100 border-rose-400 text-rose-800",
    badge: "bg-rose-600",
    icon: "🪤",
    tagline: "The bear trap that becomes a rocket launch",
    description:
      "A Failed Breakdown triggers when a stock breaks below established support — flushing out weak longs and luring in short sellers — then reverses sharply back above support within 1–3 bars. Trapped shorts covering add enormous fuel to the upside.",
    criteria: [
      "Clear support level tested ≥2× in the prior 1–2 months",
      "Stock closes below support by 0.4–6% (the shakeout)",
      "Snaps back above support within 1–3 bars (the trap springs)",
      "Current price still above support (recovery holding)",
      "High breakdown volume preferred (more trapped shorts = more fuel)",
    ],
    risk: "Stop below the low of the breakdown bar",
    target: "Prior resistance / swing highs; 2–4× risk possible on a violent short squeeze",
  },
];

export default function SetupsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Qullamaggie Setups</h1>
        <p className="text-gray-500 text-lg">
          Kristjan Qullamaggie&apos;s four core patterns — each targeting a different phase of a
          stock&apos;s institutional accumulation cycle.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {SETUPS.map((s) => (
          <Link key={s.slug} href={`/setups/${s.slug}`}>
            <div className={`border-2 rounded-xl p-6 hover:shadow-lg transition-all cursor-pointer bg-white ${s.color.split(" ").slice(1).join(" ")}`}>
              <div className="flex items-center gap-3 mb-3">
                <span className={`${s.badge} text-white text-xs font-bold px-2 py-1 rounded`}>
                  {s.short}
                </span>
                <span className="text-xl">{s.icon}</span>
                <span className="font-bold text-gray-900 text-lg">{s.name}</span>
              </div>
              <p className="text-sm font-medium text-gray-700 mb-2 italic">&ldquo;{s.tagline}&rdquo;</p>
              <p className="text-sm text-gray-600 line-clamp-2">{s.description}</p>
              <div className="mt-4 text-xs font-semibold text-indigo-600">Learn more →</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Scanner signal guide */}
      <div className="mt-10 bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-bold text-gray-800 mb-1">Reading the Scanner Signals</h2>
        <p className="text-sm text-gray-500 mb-5">
          Every result in the scanner includes these enrichment signals. Here&apos;s what they mean.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="bg-green-100 text-green-700 border border-green-300 text-xs font-bold px-1.5 py-0.5 rounded">S2</span>
                <span className="font-semibold text-gray-800">Weinstein Stage</span>
              </div>
              <p className="text-gray-600">
                Classifies each stock into one of four stages using the 30-week (150-bar) moving average.
                <strong> Only trade Stage 2</strong> (rising MA, price above it).
              </p>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
                {[
                  { label: "S1 Basing", color: "bg-gray-100 text-gray-500", desc: "Flat MA — wait" },
                  { label: "S2 Advancing", color: "bg-green-100 text-green-700", desc: "Rising MA — trade" },
                  { label: "S3 Topping", color: "bg-amber-100 text-amber-700", desc: "MA rolling over — avoid" },
                  { label: "S4 Declining", color: "bg-red-100 text-red-600", desc: "Falling MA — short only" },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-1.5">
                    <span className={`${s.color} border px-1 rounded font-bold`}>{s.label.split(" ")[0]}</span>
                    <span className="text-gray-500">{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-600 font-mono font-bold text-xs">+5</span>
                <span className="font-semibold text-gray-800">A/D Net (Accumulation/Distribution)</span>
              </div>
              <p className="text-gray-600">
                O&apos;Neill-style institutional footprint over the last 25 bars. Positive = institutions are accumulating.
                Negative = they&apos;re distributing.
              </p>
              <div className="mt-2 text-xs text-gray-500 space-y-0.5">
                <p><span className="text-green-600 font-mono font-semibold">Acc day:</span> up ≥0.2%, volume &gt; prior bar, close in upper 50% of range</p>
                <p><span className="text-red-500 font-mono font-semibold">Dist day:</span> down ≥0.2%, volume &gt; prior bar</p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-orange-500 text-xs font-semibold">⚠ Overextended</span>
                <span className="font-semibold text-gray-800">Overextension Penalty</span>
              </div>
              <p className="text-gray-600">
                When RSI &gt; 80 or price is &gt;8% above EMA21, a penalty is applied to the confidence
                score. The notes column shows the penalty amount. Avoid chasing extended setups.
              </p>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="bg-green-100 text-green-700 font-bold text-xs px-1.5 py-0.5 rounded">A</span>
                <span className="font-semibold text-gray-800">Quality Score &amp; Grade</span>
              </div>
              <p className="text-gray-600">
                Grade is based on a quality-adjusted score, not just raw confidence. It penalises wide
                stops and rewards good R:R ratios — so tight setups rank higher than sloppy ones with
                the same pattern score.
              </p>
              <div className="mt-2 text-xs text-gray-500 font-mono">
                quality = confidence × stop_factor × rr_factor
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-indigo-950 text-white rounded-xl p-8">
        <h2 className="text-xl font-bold mb-4">The Qullamaggie Philosophy</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
          <div>
            <div className="font-semibold text-indigo-300 mb-2">Only Trade Leaders</div>
            <p className="text-indigo-100">
              Focus on stocks with RS ≥75. If a stock can&apos;t outperform the market in a bull
              run, avoid it. Leaders lead — laggards lag.
            </p>
          </div>
          <div>
            <div className="font-semibold text-indigo-300 mb-2">Risk Management First</div>
            <p className="text-indigo-100">
              Every trade has a defined stop before entry. Never risk more than 0.5–1% of
              portfolio per trade. Cut losers fast, let winners run.
            </p>
          </div>
          <div>
            <div className="font-semibold text-indigo-300 mb-2">Size Up on Conviction</div>
            <p className="text-indigo-100">
              Grade A setups (high confidence + high RS + Stage 2) get larger position sizes. Grade C
              setups get smaller. Match size to setup quality — the scanner does the ranking for you.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
