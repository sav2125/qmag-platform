import Link from "next/link";

export default function TBPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-blue-600 text-white text-sm font-bold px-3 py-1 rounded">TB</span>
        <h1 className="text-3xl font-bold text-gray-900">Tight Base</h1>
        <span className="text-2xl">📦</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;A flat, quiet consolidation before a powerful breakout&rdquo;
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is a Tight Base?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          A Tight Base forms when a leading stock pauses its uptrend and consolidates in a
          very narrow price range. The tightness proves that sellers are exhausted — every
          dip is bought quickly, keeping the range compressed.
        </p>
        <p className="text-gray-700 leading-relaxed">
          The longer and tighter the base, the more explosive the eventual breakout tends to
          be. Institutions use this period to quietly accumulate shares before the next leg up.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Pattern Structure</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Price
  │                                    ╭──── Breakout (≥1.2× vol)
  │   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─╯ ← Resistance line
  │   █ █ ▇ █ ▇ █ █ ▇ █ ▇ █ ▇ █ ▇ █
  │   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Support line
  │                                        Range ≤8%
  │
  └─────────────────────────────────────────── Time
        ←────── 10–60 bar base ──────→
        Volume contracts throughout base
`}</pre>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            { label: "Tight range", detail: "Base spans ≤8% from its highest high to lowest low — the tighter the better (3–5% is ideal)" },
            { label: "Duration", detail: "At least 10 bars (2 weeks), but can be as long as 60 bars. Longer bases = more explosive breakouts" },
            { label: "Resistance tests", detail: "The resistance level must be touched or approached ≥2 times, proving supply is being absorbed" },
            { label: "Volume contraction", detail: "Volume should dry up during the base — low volume = low selling pressure, institutions holding" },
            { label: "Breakout trigger", detail: "Buy when price closes above resistance on volume ≥1.2× the 50-day average" },
            { label: "Near highs", detail: "The base should form near 52-week highs, not in the middle of a downtrend" },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <span className="text-blue-600 font-bold mt-0.5">✓</span>
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
            Place stop just below the <strong>base low</strong>. A close below the base
            invalidates the setup — the stock failed to hold the support that defined the pattern.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> Add the base depth (high − low) to the breakout point.<br />
            <strong>T2:</strong> 2× the base depth. Trail stop to rising 10-day MA once
            the stock is 10%+ extended.
          </p>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Qullamaggie&apos;s Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>Tight is a relative term.</strong> A 7% base in a volatile sector may be tight; a 7% base in a utility stock is not. Compare to the stock&apos;s own ATR.</p>
          <p>💡 <strong>Volume tells the real story.</strong> If volume is low throughout the base, that&apos;s bullish. High-volume down days within a base are a red flag.</p>
          <p>💡 <strong>Don&apos;t buy inside the base.</strong> Wait for the confirmed breakout above resistance. Early entries inside the range often stop out on whipsaws.</p>
          <p>💡 <strong>The best TBs are in the best stocks.</strong> Combine a tight base with RS ≥75 and strong fundamentals for the highest-probability setups.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/pp" className="flex-1 border border-green-300 text-green-700 rounded-lg p-4 text-center hover:bg-green-50 transition-colors font-medium text-sm">
          Next: Pocket Pivot →
        </Link>
        <Link href="/" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run TB Scan →
        </Link>
      </div>
    </div>
  );
}
