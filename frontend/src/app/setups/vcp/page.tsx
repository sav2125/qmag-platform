import Link from "next/link";

export default function VCPPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-fuchsia-600 text-white text-sm font-bold px-3 py-1 rounded">VCP</span>
        <h1 className="text-3xl font-bold text-gray-900">Volatility Contraction Pattern</h1>
        <span className="text-2xl">🪗</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;Mark Minervini&apos;s signature: a coil that tightens before it springs&rdquo;
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is a VCP?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          The Volatility Contraction Pattern is Mark Minervini&apos;s signature setup (from{" "}
          <em>Trade Like a Stock Market Wizard</em>). After a strong advance, a leading stock pauses
          and digests its gains through a series of <strong>progressively shallower pullbacks</strong>.
          A first dip might be 25%, the next 12%, the next 6% — each contraction shaking out weaker
          holders until sellers are exhausted.
        </p>
        <p className="text-gray-700 leading-relaxed">
          As the coil tightens, <strong>volume dries up</strong> — the tell that supply has been
          absorbed. The setup completes when price breaks out above the <strong>pivot</strong> (the
          high of the final contraction) on expanding volume. Minervini counts the number of
          contractions as the <strong>&ldquo;T&rdquo; count</strong> (e.g. &ldquo;3T&rdquo;).
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Pattern Structure</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Price
  │        ╭╮                          ╭──── Breakout over pivot
  │       ╱  ╲      ╭╮                ╱       (volume expands)
  │      ╱    ╲    ╱  ╲    ╭╮  ╭─╮  ╱   ← Pivot (final contraction high)
  │     ╱      ╲  ╱    ╲  ╱  ╲╱   ╲╱
  │    ╱        ╲╱      ╲╱
  │   ╱      ↑25%    ↑12%   ↑6%  ← contractions tighten
  │  ╱       (T1)    (T2)   (T3)
  └─────────────────────────────────────────── Time
        Volume:  high → fading → dry  (dry-up into the apex)
`}</pre>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            { label: "Prior uptrend", detail: "Stock must be advancing — our detector requires price above a rising 50-day SMA. A VCP is a continuation pattern, not a bottom-fishing tool." },
            { label: "Progressive contractions", detail: "At least 2 pullbacks, each tighter than the last. More contractions (3–5T) that tighten cleanly = higher conviction." },
            { label: "Tight final contraction", detail: "The last pullback must be tight (≤15%, ideally <8%). This is the coil that's about to release." },
            { label: "Volume dry-up", detail: "Volume should fade from the first contraction to the last — proof that selling pressure is exhausted." },
            { label: "Pivot proximity", detail: "Price must be coiling just under the pivot (the final contraction's high) or breaking out just above it — not already extended." },
            { label: "Breakout trigger", detail: "Buy as price clears the pivot on expanding volume." },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-fuchsia-50 border border-fuchsia-200 rounded-lg p-4">
              <span className="text-fuchsia-600 font-bold mt-0.5">✓</span>
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
            Place the stop just below the <strong>low of the final contraction</strong>. Because the
            last pullback is tight, the stop is close — that&apos;s the whole point of the VCP: a
            low-risk entry right as the coil releases.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> 2× the entry risk.<br />
            <strong>T2:</strong> 4× the entry risk. Trail the stop up as the post-breakout advance
            extends — Minervini lets winners run while protecting the base.
          </p>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Minervini&apos;s Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>Tightness over time.</strong> What matters isn&apos;t the absolute depth but that each contraction is shallower than the one before — volatility is contracting.</p>
          <p>💡 <strong>Volume is the confirmation.</strong> A VCP without volume dry-up is suspect. The drying volume is what tells you supply is gone.</p>
          <p>💡 <strong>Buy the pivot, not the base.</strong> Don&apos;t anticipate inside the contractions — wait for the breakout above the final pivot on volume.</p>
          <p>💡 <strong>The best VCPs are in the strongest stocks.</strong> Combine a clean VCP with a high RS rank and a full Minervini Trend Template for the highest-probability entries.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/pp" className="flex-1 border border-fuchsia-300 text-fuchsia-700 rounded-lg p-4 text-center hover:bg-fuchsia-50 transition-colors font-medium text-sm">
          Next: Pocket Pivot →
        </Link>
        <Link href="/?setup=vcp" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run VCP Scan →
        </Link>
      </div>
    </div>
  );
}
