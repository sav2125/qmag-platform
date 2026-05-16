import Link from "next/link";

export default function EPPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-purple-600 text-white text-sm font-bold px-3 py-1 rounded">EP</span>
        <h1 className="text-3xl font-bold text-gray-900">Episodic Pivot</h1>
        <span className="text-2xl">⚡</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;A catalyst-driven surge that resets a stock&apos;s trajectory&rdquo;
      </p>

      {/* What is it */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is an Episodic Pivot?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          An Episodic Pivot is Qullamaggie&apos;s highest-conviction setup. It occurs when a major
          unexpected news event — a blowout earnings report, FDA drug approval, a massive contract
          win, or a short squeeze — causes a stock to gap up aggressively on huge volume.
        </p>
        <p className="text-gray-700 leading-relaxed">
          The key insight: the event <strong>fundamentally changes the story</strong> of the stock.
          Institutions that were on the sidelines suddenly need to own it, creating sustained buying
          pressure for days or weeks after the initial move.
        </p>
      </section>

      {/* Visual */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Pattern Structure</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Price
  │                        ╭──── Breakout entry (above EP high)
  │                   ╭───╯
  │              ╭────╯  ← EP day: +8% on 3× vol
  │         ─────╯
  │    ─────╯  ← Prior base (quiet consolidation)
  │────╯
  └─────────────────────────────────────────── Time
       Base      EP Day   Consolidation  Entry
                           (≤12% range)
`}</pre>
        </div>
      </section>

      {/* Criteria */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            { label: "Catalyst move", detail: "Gap or surge ≥5% on the EP day due to a meaningful news event (earnings, FDA, contract, etc.)" },
            { label: "Volume surge", detail: "EP day volume must be ≥2× the 50-day average volume — proving institutional participation" },
            { label: "Prior base", detail: "Stock was in a quiet consolidation before the event — not already extended or in a runaway trend" },
            { label: "Consolidation", detail: "After the EP day, stock holds within 12% of the EP high for days/weeks — a tight follow-through base" },
            { label: "Entry trigger", detail: "Buy on the breakout above the EP day's intraday high on rising volume" },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-purple-50 border border-purple-200 rounded-lg p-4">
              <span className="text-purple-600 font-bold mt-0.5">✓</span>
              <div>
                <span className="font-semibold text-gray-800">{c.label}: </span>
                <span className="text-gray-600">{c.detail}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Risk / Target */}
      <section className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <h3 className="font-bold text-red-700 mb-2">🛑 Stop Loss</h3>
          <p className="text-sm text-gray-700">
            Place stop below the <strong>EP day&apos;s intraday low</strong>. If the stock
            reclaims the EP day, the setup is invalidated — institutions are not holding it.
            Some traders use the base low as an alternative if it&apos;s close.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> 1× the base depth added to the breakout point.<br />
            <strong>T2:</strong> 2–3× risk (R:R). Let the winner run as long as price
            holds above the rising 10-day MA. Sell into strength on climactic volume.
          </p>
        </div>
      </section>

      {/* Tips */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Qullamaggie&apos;s Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>The catalyst must be a surprise.</strong> Expected events (known earnings date) carry less edge than truly unexpected news.</p>
          <p>💡 <strong>The tighter the post-EP consolidation, the better.</strong> A stock that holds within 5% of the EP high is far stronger than one that gives back 11%.</p>
          <p>💡 <strong>Don&apos;t chase the EP day itself.</strong> Wait for the follow-through base and buy the breakout — the risk/reward is much cleaner.</p>
          <p>💡 <strong>RS doesn&apos;t matter as much here.</strong> A stock can have low RS going into the EP and completely reset its trajectory after it.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/tb" className="flex-1 border border-blue-300 text-blue-700 rounded-lg p-4 text-center hover:bg-blue-50 transition-colors font-medium text-sm">
          Next: Tight Base →
        </Link>
        <Link href="/" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run EP Scan →
        </Link>
      </div>
    </div>
  );
}
