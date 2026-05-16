"use client";

import type { Setup } from "@/lib/api";
import { SetupBadge, GradeBadge, RRBadge } from "./SetupBadge";

interface Props {
  setups: Setup[];
  loading: boolean;
}

// ── State badge ──────────────────────────────────────────────────────────────

const STATE_CONFIG: Record<string, { label: string; color: string; icon: string; tip: string }> = {
  breakout: {
    label: "Breakout",
    color: "bg-green-100 text-green-800 border border-green-300",
    icon: "🚀",
    tip: "Stock has broken above resistance on volume right now. This is the entry signal — act today.",
  },
  base: {
    label: "In Base",
    color: "bg-yellow-100 text-yellow-800 border border-yellow-300",
    icon: "⏳",
    tip: "Pattern is forming but not yet triggered. Stock is consolidating. Set an alert at the entry price and wait for the breakout.",
  },
  active: {
    label: "Active",
    color: "bg-blue-100 text-blue-800 border border-blue-300",
    icon: "📈",
    tip: "Pattern is in an active uptrend. Entry available near current price — the stock is already moving.",
  },
};

function StateBadge({ state }: { state: string }) {
  const cfg = STATE_CONFIG[state.toLowerCase()] ?? {
    label: state,
    color: "bg-gray-100 text-gray-600 border border-gray-200",
    icon: "•",
    tip: "",
  };
  return (
    <span
      className={`group relative inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold cursor-help ${cfg.color}`}
    >
      <span>{cfg.icon}</span>
      <span>{cfg.label}</span>
      {cfg.tip && (
        <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-56 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl">
          {cfg.tip}
        </span>
      )}
    </span>
  );
}

// ── Action hint ───────────────────────────────────────────────────────────────

function ActionHint({ state, entry, price }: { state: string; entry: number; price: number }) {
  const pctToEntry = ((entry - price) / price) * 100;

  if (state === "breakout") {
    return <span className="text-green-700 font-semibold text-xs">✅ Enter now</span>;
  }
  if (state === "active") {
    return <span className="text-blue-700 font-semibold text-xs">📌 Enter near mkt</span>;
  }
  // base — show how far to entry
  return (
    <span className="text-yellow-700 text-xs">
      🔔 Alert {pctToEntry > 0 ? `+${pctToEntry.toFixed(1)}%` : `${pctToEntry.toFixed(1)}%`} away
    </span>
  );
}

// ── Main table ────────────────────────────────────────────────────────────────

export function SetupTable({ setups, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
        Scanning universe…
      </div>
    );
  }

  if (!setups.length) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-400">
        <p className="text-lg font-medium">No setups found</p>
        <p className="text-sm mt-1">Try lowering Min RS or choosing a broader universe.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-gray-500 border-b border-gray-200 bg-gray-50">
            <th className="text-left py-3 px-3">Symbol</th>
            <th className="text-left py-3 px-3">Setup</th>
            <th className="text-left py-3 px-3">
              State
              <span className="ml-1 text-gray-400 normal-case font-normal">(hover for info)</span>
            </th>
            <th className="text-left py-3 px-3">Action</th>
            <th className="text-right py-3 px-3">Price</th>
            <th className="text-right py-3 px-3">Entry</th>
            <th className="text-right py-3 px-3 text-red-500">Stop</th>
            <th className="text-right py-3 px-3 text-red-400 text-[11px]">Risk%</th>
            <th className="text-right py-3 px-3">T1</th>
            <th className="text-right py-3 px-3 text-green-600">T2</th>
            <th className="text-right py-3 px-3">R:R</th>
            <th className="text-right py-3 px-3">RS</th>
            <th className="text-center py-3 px-3">Grd</th>
            <th className="text-left py-3 px-3">Notes</th>
          </tr>
        </thead>
        <tbody>
          {setups.map((s) => {
            const riskPct = ((s.entry - s.stop) / s.entry) * 100;
            return (
              <tr
                key={s.symbol}
                className="border-b border-gray-100 hover:bg-indigo-50/40 transition-colors"
              >
                {/* Symbol */}
                <td className="py-3 px-3">
                  <span className="font-bold text-gray-900">{s.symbol}</span>
                  <span className="block text-[10px] text-gray-400">{s.rs_label}</span>
                </td>

                {/* Setup badge */}
                <td className="py-3 px-3">
                  <SetupBadge type={s.setup_type} />
                </td>

                {/* State badge with tooltip */}
                <td className="py-3 px-3">
                  <StateBadge state={s.state} />
                </td>

                {/* Action hint */}
                <td className="py-3 px-3 whitespace-nowrap">
                  <ActionHint state={s.state} entry={s.entry} price={s.price} />
                </td>

                {/* Price + daily change */}
                <td className="py-3 px-3 text-right font-mono text-gray-700">
                  ${s.price.toFixed(2)}
                  <span className={`block text-[11px] ${s.pct_change >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {s.pct_change >= 0 ? "+" : ""}{s.pct_change.toFixed(1)}%
                  </span>
                </td>

                {/* Entry */}
                <td className="py-3 px-3 text-right font-mono font-semibold text-gray-800">
                  ${s.entry.toFixed(2)}
                </td>

                {/* Stop */}
                <td className="py-3 px-3 text-right font-mono text-red-500">
                  ${s.stop.toFixed(2)}
                </td>

                {/* Risk % */}
                <td className="py-3 px-3 text-right text-red-400 text-xs font-mono">
                  -{riskPct.toFixed(1)}%
                </td>

                {/* T1 */}
                <td className="py-3 px-3 text-right font-mono text-gray-600">
                  ${s.t1.toFixed(2)}
                </td>

                {/* T2 */}
                <td className="py-3 px-3 text-right font-mono text-green-600 font-semibold">
                  ${s.t2.toFixed(2)}
                </td>

                {/* R:R */}
                <td className="py-3 px-3 text-right">
                  <RRBadge rr={s.rr} />
                </td>

                {/* RS score */}
                <td className="py-3 px-3 text-right text-gray-700 font-mono">
                  {s.rs_score.toFixed(0)}
                </td>

                {/* Grade */}
                <td className="py-3 px-3 text-center">
                  <GradeBadge grade={s.grade} />
                </td>

                {/* Notes — full text, wraps */}
                <td className="py-3 px-3 text-gray-500 text-xs max-w-[220px] leading-relaxed">
                  {s.notes}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* State legend */}
      <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 flex flex-wrap gap-4 text-xs text-gray-500">
        <span className="font-semibold text-gray-600">State guide:</span>
        {Object.entries(STATE_CONFIG).map(([key, cfg]) => (
          <span key={key} className="flex items-center gap-1">
            <span className={`px-1.5 py-0.5 rounded ${cfg.color}`}>{cfg.icon} {cfg.label}</span>
            <span>— {cfg.tip.split(".")[0]}.</span>
          </span>
        ))}
      </div>
    </div>
  );
}
