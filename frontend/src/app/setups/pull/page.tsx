import Link from "next/link";

export default function PullPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/setups" className="text-sm text-indigo-600 hover:underline mb-6 inline-block">
        ← All Setups
      </Link>

      <div className="flex items-center gap-3 mb-2">
        <span className="bg-orange-500 text-white text-sm font-bold px-3 py-1 rounded">PULL</span>
        <h1 className="text-3xl font-bold text-gray-900">EMA Pullback</h1>
        <span className="text-2xl">↩️</span>
      </div>
      <p className="text-lg text-gray-500 mb-8 italic">
        &ldquo;Buy the dip in a confirmed uptrend&rdquo;
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">What is an EMA Pullback?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          Strong stocks in uptrends rarely go straight up — they make a move, pull back to
          their rising moving averages, and then resume the trend. The EMA Pullback setup
          identifies the safest point to enter an existing trend: right as the stock touches
          its 21-day EMA and shows signs of resuming upward.
        </p>
        <p className="text-gray-700 leading-relaxed">
          This is a lower-risk, trend-continuation trade. The stock has already proven itself
          as a leader — you&apos;re simply catching it at a natural reset point.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Pattern Structure</h2>
        <div className="bg-gray-950 text-green-400 rounded-xl p-6 font-mono text-sm leading-relaxed">
          <pre>{`
Price
  │                              ╭──── Resume uptrend
  │           ╭──────╮          │
  │      ╭────╯       ╰─────────╯ ← Touch EMA21 (entry)
  │ ─────╯
  │ ·  ·  ·  ·  ·  ·  ·  ·  ·  · ← EMA21 (rising)
  │   ──  ──  ──  ──  ──  ──  ── ← EMA50 (below EMA21)
  │
  └─────────────────────────────────────────── Time
    EMA21 > EMA50 throughout = confirmed uptrend
    RSI 38–68 at the touch point
`}</pre>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Entry Criteria</h2>
        <div className="space-y-3">
          {[
            { label: "EMA alignment", detail: "EMA21 must be above EMA50 — this confirms the stock is in a defined uptrend, not just bouncing" },
            { label: "Rising EMAs", detail: "Both EMA21 and EMA50 must be sloping upward — flat or declining EMAs mean the trend is weakening" },
            { label: "EMA21 touch", detail: "Price touched or came within 1–2% of the EMA21 within the last 1–5 trading days" },
            { label: "RSI range", detail: "RSI between 38–68 — not overbought (>70) or oversold (<30). Midrange RSI on pullback = healthy reset" },
            { label: "Low pullback volume", detail: "Volume should dry up on the pullback days — light selling means institutions aren't distributing" },
          ].map((c) => (
            <div key={c.label} className="flex gap-3 bg-orange-50 border border-orange-200 rounded-lg p-4">
              <span className="text-orange-500 font-bold mt-0.5">✓</span>
              <div>
                <span className="font-semibold text-gray-800">{c.label}: </span>
                <span className="text-gray-600">{c.detail}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* EMA cheat sheet */}
      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">EMA Reference</h2>
        <div className="bg-gray-50 border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="text-left p-3 font-semibold text-gray-700">EMA</th>
                <th className="text-left p-3 font-semibold text-gray-700">Period</th>
                <th className="text-left p-3 font-semibold text-gray-700">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td className="p-3 font-bold text-orange-600">EMA21</td>
                <td className="p-3 text-gray-600">~1 month</td>
                <td className="p-3 text-gray-600">Primary support in a healthy uptrend. Pullback entry zone.</td>
              </tr>
              <tr>
                <td className="p-3 font-bold text-gray-600">EMA50</td>
                <td className="p-3 text-gray-600">~2.5 months</td>
                <td className="p-3 text-gray-600">Must stay below EMA21. If price falls through EMA50, trend is broken.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <h3 className="font-bold text-red-700 mb-2">🛑 Stop Loss</h3>
          <p className="text-sm text-gray-700">
            Place stop below the <strong>EMA50</strong> or the recent swing low of the
            pullback — whichever gives a tighter risk. A close below the EMA50 means
            the uptrend structure is broken; exit immediately.
          </p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <h3 className="font-bold text-green-700 mb-2">🎯 Targets</h3>
          <p className="text-sm text-gray-700">
            <strong>T1:</strong> Prior high or recent swing high.<br />
            <strong>T2:</strong> 2–3× risk in a strong trend. Trail stop to the rising
            EMA21 — exit only when price decisively closes below it.
          </p>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Qullamaggie&apos;s Key Tips</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p>💡 <strong>Only trade pullbacks in leaders.</strong> EMA pullbacks in RS ≥75 stocks in bull markets are the safest version of this setup.</p>
          <p>💡 <strong>Watch for the first touch.</strong> The first pullback to the EMA21 after a breakout is usually the most powerful — subsequent touches lose reliability.</p>
          <p>💡 <strong>Volume on resumption matters.</strong> You want to see volume expand as the stock bounces off the EMA21. Weak volume on the bounce = weak signal.</p>
          <p>💡 <strong>Market conditions matter most.</strong> EMA pullbacks work best in confirmed bull markets. In choppy or bear markets, stocks slice through EMAs easily — reduce size or avoid entirely.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <Link href="/setups/ep" className="flex-1 border border-purple-300 text-purple-700 rounded-lg p-4 text-center hover:bg-purple-50 transition-colors font-medium text-sm">
          ← Back to EP
        </Link>
        <Link href="/" className="flex-1 bg-indigo-600 text-white rounded-lg p-4 text-center hover:bg-indigo-700 transition-colors font-medium text-sm">
          Run PULL Scan →
        </Link>
      </div>
    </div>
  );
}
