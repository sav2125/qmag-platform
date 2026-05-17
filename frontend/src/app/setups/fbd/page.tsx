import Link from "next/link";

export default function FBDPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-rose-600 text-white text-sm font-bold px-3 py-1 rounded">FBD</span>
        <h1 className="text-3xl font-bold text-gray-900">Failed Breakdown</h1>
        <span className="text-2xl">🪤</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;The bear trap that becomes a rocket launch&rdquo;
      </p>

      {/* What is it */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is a Failed Breakdown?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          A Failed Breakdown — also called a bear trap or shakeout — occurs when a stock breaks below
          a well-established support level, triggering stops and luring in short sellers, then
          reverses sharply and closes back above support within 1–3 days.
        </p>
        <p className="text-gray-700 leading-relaxed mb-3">
          The key insight: the breakdown was fake. The stock found <strong>aggressive buyers at
          lower prices</strong>, overwhelming the sellers. Every short who entered on the breakdown
          is now trapped, and their forced buying (covering) adds fuel to the upside move.
        </p>
        <p className="text-gray-700 leading-relaxed">
          This is one of the most explosive setups because it combines two sources of buying:
          new longs entering the recovery <em>and</em> trapped shorts being forced to cover.
        </p>
      </section>

      {/* Visual */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Pattern Structure</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Price
  │
  │  ════════════════════  ← Support level (tested multiple times)
  │  ══════╮     ╭══════
  │        ╰─────╯       ← Breakdown: -2.5% below support
  │           ↑
  │      Bears short here (TRAPPED)
  │
  │  ════════════════════╮
  │                      ╰─────→  Snap-back recovery + rally
  │
  └───────────────────────────────────────────── Time
       Base    Break  Recover   Entry & Rally
`}</pre>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          The sharper the recovery, the more trapped shorts there are, and the more violent the squeeze.
        </p>
      </section>

      {/* Why it works */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Why It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: "🎣",
              title: "Shakes Out Weak Hands",
              desc: "Long holders with tight stops get flushed out at the worst possible moment — right before the real move begins.",
            },
            {
              icon: "🪤",
              title: "Traps Short Sellers",
              desc: "Bears see a 'confirmed breakdown' and pile in short. When the stock reverses, their covering becomes forced buying.",
            },
            {
              icon: "🏦",
              title: "Reveals Institutional Demand",
              desc: "For a stock to snap back that fast, big money must be aggressively buying the dip. That demand doesn't disappear overnight.",
            },
          ].map((item) => (
            <div key={item.title} className="bg-rose-50 border border-rose-200 rounded-xl p-4">
              <div className="text-2xl mb-2">{item.icon}</div>
              <div className="font-semibold text-gray-800 mb-1">{item.title}</div>
              <p className="text-sm text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Criteria */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            {
              label: "Established support",
              detail: "A clear support level that has been tested and held at least twice in the prior 1–2 months. The more times it has held, the more stops are clustered just below it.",
            },
            {
              label: "Breakdown depth",
              detail: "Price closes below support by 0.4–6%. Too shallow = might not trigger enough stops. Too deep (>6%) = the breakdown may be genuine, not a trap.",
            },
            {
              label: "Fast recovery",
              detail: "The stock must close back above support within 1–3 bars of the breakdown. A 1-bar snap-back is the strongest signal — it shows immediate absorption.",
            },
            {
              label: "Still above support",
              detail: "Current price must be above the original support level. If it has drifted back below, the setup is invalidated.",
            },
            {
              label: "Volume on breakdown",
              detail: "High volume on the breakdown bar (≥1.5× average) is ideal — it means more shorts entered and more longs got stopped out. More fuel for the reversal.",
            },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-rose-50 border border-rose-200 rounded-lg p-4">
              <span className="text-rose-600 font-bold mt-0.5">✓</span>
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
            Place stop <strong>below the low of the breakdown bar</strong> (the wick that pierced
            support). If price returns to those levels, the bear trap has failed and the breakdown
            may be real. A close back below the support level is also an exit signal.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> Midpoint between entry and prior resistance (first area of supply).<br />
            <strong>T2:</strong> Prior resistance / swing high — where trapped shorts started their
            positions. Often 2–4× risk in strong setups. Trail stops as stock advances.
          </p>
        </div>
      </section>

      {/* Volume table example */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Breakdown Volume Matters</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-600 text-xs uppercase">
                <th className="text-left py-2 px-3">Scenario</th>
                <th className="text-center py-2 px-3">Breakdown Vol</th>
                <th className="text-center py-2 px-3">Recovery Speed</th>
                <th className="text-center py-2 px-3">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                { s: "High vol breakdown, 1-bar snap", vol: "≥1.5× avg", rec: "1 bar", conf: "🟢 Highest" },
                { s: "High vol breakdown, 2-bar snap", vol: "≥1.5× avg", rec: "2 bars", conf: "🟢 High" },
                { s: "Avg vol breakdown, 1-bar snap", vol: "~1× avg", rec: "1 bar", conf: "🟡 Moderate" },
                { s: "Low vol breakdown, slow recover", vol: "<1× avg", rec: "3 bars", conf: "🔴 Lower" },
              ].map((row) => (
                <tr key={row.s} className="hover:bg-gray-50">
                  <td className="py-2 px-3 text-gray-700">{row.s}</td>
                  <td className="py-2 px-3 text-center font-mono text-gray-600">{row.vol}</td>
                  <td className="py-2 px-3 text-center text-gray-600">{row.rec}</td>
                  <td className="py-2 px-3 text-center">{row.conf}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Tips */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>Context is everything.</strong> A failed breakdown in a Stage 2 uptrend (rising 30-week MA, price above it) is far more powerful than one in a Stage 1 base or Stage 3 topping pattern.</p>
          <p>💡 <strong>The tighter the breakdown, the better.</strong> A 1–2% fake-out is cleaner than a 5% one. Deeper breakdowns may indicate real distribution rather than a shakeout.</p>
          <p>💡 <strong>Look for prior RS strength.</strong> Failed breakdowns in stocks with high RS (≥70) tend to lead to strong recoveries. Weak RS stocks may just grind sideways after recovery.</p>
          <p>💡 <strong>Combine with accumulation evidence.</strong> A positive A/D net (institutions buying) alongside a failed breakdown is a very high-conviction combination — big money absorbed the selling.</p>
          <p>💡 <strong>Don&apos;t enter on the breakdown bar.</strong> Wait for the close back above support. The confirmation day is your entry — not the bottom tick.</p>
        </div>
      </section>

      {/* Comparison vs EP */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">FBD vs EP — What&apos;s the Difference?</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-600 text-xs uppercase">
                <th className="text-left py-2 px-3">Attribute</th>
                <th className="text-center py-2 px-3">FBD</th>
                <th className="text-center py-2 px-3">EP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700">
              <tr><td className="py-2 px-3 font-medium">Trigger</td><td className="py-2 px-3 text-center">Failed breakdown below support</td><td className="py-2 px-3 text-center">Catalyst news event</td></tr>
              <tr><td className="py-2 px-3 font-medium">Fuel</td><td className="py-2 px-3 text-center">Short covering + new longs</td><td className="py-2 px-3 text-center">New institutional buying</td></tr>
              <tr><td className="py-2 px-3 font-medium">Direction on trigger day</td><td className="py-2 px-3 text-center">Down then up</td><td className="py-2 px-3 text-center">Strong gap up</td></tr>
              <tr><td className="py-2 px-3 font-medium">State in scanner</td><td className="py-2 px-3 text-center">Active</td><td className="py-2 px-3 text-center">Base or Breakout</td></tr>
              <tr><td className="py-2 px-3 font-medium">Stop location</td><td className="py-2 px-3 text-center">Below breakdown wick</td><td className="py-2 px-3 text-center">Below EP day low</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/pull" className="flex-1 border border-orange-300 text-orange-700 rounded-lg p-4 text-center hover:bg-orange-50 transition-colors font-medium text-sm">
          ← EMA Pullback
        </Link>
        <Link href="/" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run FBD Scan →
        </Link>
      </div>
    </div>
  );
}
