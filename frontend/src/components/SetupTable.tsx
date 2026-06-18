"use client";

import type { Setup } from "@/lib/api";
import { SetupBadge, ProbGradeBadge, RRBadge, StageBadge, ADNetBadge, ICSBadge, RVOLLabel, WeeklyDirBadge } from "./SetupBadge";

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
  // base — price is at or above entry: treat as "at the trigger"
  if (pctToEntry <= 0.5) {
    return <span className="text-orange-600 font-semibold text-xs">⚡ At entry — watch vol</span>;
  }
  // base — show how far price still needs to travel to reach entry
  return (
    <span className="text-yellow-700 text-xs">
      🔔 Alert at ${entry.toFixed(2)} (+{pctToEntry.toFixed(1)}%)
    </span>
  );
}

// ── Regime fit badge ───────────────────────────────────────────────────────────

function RegimeBadge({ verdict, sector }: { verdict?: string; sector?: string }) {
  if (!verdict) return <span className="text-gray-300 text-xs">—</span>;
  const cfg: Record<string, { t: string; c: string }> = {
    tailwind: { t: "↑ tail", c: "bg-green-100 text-green-700" },
    neutral:  { t: "– neut", c: "bg-gray-100 text-gray-500" },
    headwind: { t: "↓ head", c: "bg-amber-100 text-amber-700" },
  };
  const x = cfg[verdict] ?? cfg.neutral;
  return (
    <span className="inline-block">
      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${x.c}`}>{x.t}</span>
      {sector && <span className="block text-[9px] text-gray-400 mt-0.5 max-w-[72px] truncate mx-auto">{sector}</span>}
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
            <th className="text-center py-3 px-3">
              <span className="group relative cursor-help">
                Regime
                <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-64 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal normal-case tracking-normal">
                  <strong>Regime fit</strong> — does the macro wind back this setup? Combines the stock&apos;s sector leadership, the live Quad posture (1/2 = green light), and the momentum factor. Tailwind / neutral / headwind. Context only — <strong>not</strong> part of the P Score.
                </span>
              </span>
            </th>
            <th className="text-center py-3 px-3">
              <span className="group relative cursor-help">
                Score
                <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-72 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal normal-case tracking-normal">
                  <strong>P Score</strong> (teal) — probability-weighted signal voting across up to 20 signals (RSI, MACD, EMA stack, stage, Minervini Trend Template, OBV, CMF, ICS, A/D Net, setup pattern, …). A≥75 / B≥60 / C≥45 / D&lt;45.<br /><br />
                  <strong>W ▲ / W — / W ▼</strong> — weekly timeframe direction (SMA30 = Weinstein 30-week MA).
                </span>
              </span>
            </th>
            <th className="text-center py-3 px-3">
              <span className="group relative cursor-help">
                Stg
                <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-52 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal normal-case tracking-normal">
                  Weinstein Stage (30-week MA). S2 = advancing — the only stage to trade.
                </span>
              </span>
            </th>
            <th className="text-center py-3 px-3">
              <span className="group relative cursor-help">
                A/D
                <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-64 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal normal-case tracking-normal">
                  <strong>A/D Net</strong> — O&apos;Neill accumulation/distribution day count (last 25 bars). Positive = institutions buying.<br />
                  <strong>ICS</strong> — Institutional Composite Score (OBV + CMF + A/D line + MFI, 0–100). ≥75 = strong accumulation.
                </span>
              </span>
            </th>
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

                {/* Price + daily change + RVOL */}
                <td className="py-3 px-3 text-right font-mono text-gray-700">
                  ${s.price.toFixed(2)}
                  <span className={`block text-[11px] ${s.pct_change >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {s.pct_change >= 0 ? "+" : ""}{s.pct_change.toFixed(1)}%
                  </span>
                  <span className="block mt-0.5">
                    <RVOLLabel rvol={s.rvol ?? 1} />
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

                {/* Regime fit */}
                <td className="py-3 px-3 text-center">
                  <RegimeBadge verdict={s.regime_verdict} sector={s.regime_sector} />
                </td>

                {/* Score (P Score) + Weekly dir */}
                <td className="py-3 px-3 text-center">
                  <ProbGradeBadge grade={s.prob_grade ?? "D"} score={s.prob_score} />
                  {/* Weekly TF direction */}
                  <span className="block mt-1">
                    <WeeklyDirBadge dir={s.weekly_dir ?? "neutral"} />
                  </span>
                </td>

                {/* Weinstein Stage */}
                <td className="py-3 px-3 text-center">
                  <StageBadge stage={s.weinstein_stage} />
                </td>

                {/* A/D net days + ICS */}
                <td className="py-3 px-3 text-center">
                  <ADNetBadge net={s.ad_net} />
                  {s.isc_score != null && (
                    <span className="block mt-0.5">
                      <ICSBadge score={s.isc_score} />
                    </span>
                  )}
                </td>

                {/* Notes — full text, wraps */}
                <td className="py-3 px-3 text-gray-500 text-xs max-w-[220px] leading-relaxed">
                  {s.notes}
                  {(s.meta?.overextension_penalty as number) > 0 && (
                    <span className="block text-orange-500 mt-0.5">
                      ⚠ Overextended (−{Math.round((s.meta.overextension_penalty as number) * 100)}pts)
                    </span>
                  )}
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
