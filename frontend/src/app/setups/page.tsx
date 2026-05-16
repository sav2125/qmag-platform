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

      <div className="mt-12 bg-indigo-950 text-white rounded-xl p-8">
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
              Grade A setups (high confidence + high RS) get larger position sizes. Grade C
              setups get smaller. Match size to setup quality.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
