import Link from "next/link";

export default function PPPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-green-600 text-white text-sm font-bold px-3 py-1 rounded">PP</span>
        <h1 className="text-3xl font-bold text-gray-900">Pocket Pivot</h1>
        <span className="text-2xl">🎯</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;Institutional accumulation showing up in the volume signature&rdquo;
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is a Pocket Pivot?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          Developed by Chris Kacher and Gil Morales, the Pocket Pivot reveals when institutional
          money is quietly accumulating a stock before a major move. It identifies days where
          the up-day volume is unusually large relative to recent down days — a footprint of
          big buyers.
        </p>
        <p className="text-gray-700 leading-relaxed">
          Qullamaggie uses it as an early entry signal — often catching a move <em>before</em>{" "}
          the full breakout, providing a tighter stop and better risk/reward.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">The Volume Rule — Simply Explained</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Last 10 sessions:
  Day  Type   Volume
  ─────────────────────
  -10  DOWN   1.2M
  -9   UP     0.9M
  -8   DOWN   2.1M   ← Highest down-day volume = 2.1M
  -7   UP     1.5M
  -6   DOWN   0.8M
  -5   UP     1.1M
  -4   DOWN   1.8M
  -3   UP     0.7M
  -2   DOWN   1.3M
  -1   UP     0.6M
  TODAY UP   2.4M  ✓  ← 2.4M > 2.1M = POCKET PIVOT!
`}</pre>
        </div>
        <p className="text-sm text-gray-500 mt-3">
          Today&apos;s up-day volume (2.4M) exceeds the highest down-day volume (2.1M) in the prior
          10 sessions. That&apos;s the signal — buyers are more aggressive than sellers have been.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            { label: "Volume rule", detail: "Up day with volume greater than the highest down-day volume in the prior 10 trading sessions" },
            { label: "Above 10-day MA", detail: "Stock must be trading above its 10-day moving average — confirms short-term trend is positive" },
            { label: "EMA alignment", detail: "EMA10 must be above EMA20 — the short-term moving average stack is bullish" },
            { label: "Not extended", detail: "Ideally within 5–10% of a base or recent support, not 20%+ extended from the last base" },
            { label: "RS ≥50", detail: "Stock should be outperforming the market — pocket pivots in laggards rarely lead to big moves" },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-green-50 border border-green-200 rounded-lg p-4">
              <span className="text-green-600 font-bold mt-0.5">✓</span>
              <div>
                <span className="font-semibold text-gray-800">{c.label}: </span>
                <span className="text-gray-600">{c.detail}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <h3 className="font-bold text-red-700 mb-2">🛑 Stop Loss</h3>
          <p className="text-sm text-gray-700">
            Place stop below the <strong>10-day moving average</strong> or the{" "}
            <strong>pocket pivot bar&apos;s low</strong> — whichever is closer. A close
            below the 10-day MA invalidates the signal.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> Prior resistance or recent swing high.<br />
            <strong>T2:</strong> 1.5–2× risk. Trail stop to 10-day MA as the stock
            extends. Sell into volume spikes on up days.
          </p>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Qullamaggie&apos;s Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>Context matters.</strong> A pocket pivot near the top of a base is more powerful than one in the middle of a downtrend.</p>
          <p>💡 <strong>Cluster of PPs is a strong signal.</strong> Multiple pocket pivots over 2–3 weeks signals sustained institutional accumulation.</p>
          <p>💡 <strong>Combine with base analysis.</strong> The best pocket pivots occur just before a full breakout from a tight base — you get in early with a tight stop.</p>
          <p>💡 <strong>Avoid gap-up pocket pivots.</strong> If the stock gaps up significantly on the PP day, the risk/reward deteriorates — wait for a better entry.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/pull" className="flex-1 border border-orange-300 text-orange-700 rounded-lg p-4 text-center hover:bg-orange-50 transition-colors font-medium text-sm">
          Next: EMA Pullback →
        </Link>
        <Link href="/" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run PP Scan →
        </Link>
      </div>
    </div>
  );
}
