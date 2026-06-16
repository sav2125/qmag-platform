"use client";

import { useEffect, useState } from "react";
import { api, MarketBreadth as Breadth } from "@/lib/api";

/* Market Breadth panel — the leading "momentum environment" gauge.
   How many stocks participate (above their 50/200-DMA, new highs vs lows). Breadth
   narrows before the index tops, so it answers "should I be aggressive right now?" */

const STATE_CFG: Record<string, { label: string; cls: string }> = {
  "strong":   { label: "Strong — be aggressive",   cls: "bg-green-100 text-green-700" },
  "healthy":  { label: "Healthy",                   cls: "bg-green-100 text-green-700" },
  "mixed":    { label: "Mixed — be selective",      cls: "bg-amber-100 text-amber-700" },
  "weak":     { label: "Weak — reduce size",        cls: "bg-orange-100 text-orange-700" },
  "risk-off": { label: "Risk-off — stand aside",    cls: "bg-red-100 text-red-700" },
};

export default function MarketBreadthPanel() {
  const [data, setData] = useState<Breadth | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.breadth().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;             // backend cold-start / unreachable — hide quietly
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading market breadth…
      </div>
    );
  }

  const cfg = STATE_CFG[data.state] ?? STATE_CFG.mixed;
  const stat = (label: string, value: string, sub: string, tone?: string) => (
    <div key={label} className="flex-1 min-w-[140px] bg-gray-50 rounded-lg px-3 py-2">
      <div className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</div>
      <div className={`text-sm font-mono font-semibold ${tone ?? "text-gray-800"}`}>{value}</div>
      <div className="text-[10px] text-gray-400">{sub}</div>
    </div>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Market Breadth
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            momentum environment · {data.universe_size} large caps
          </span>
        </h2>
        <a href="/scoring#breadth" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${cfg.cls}`}>{cfg.label}</span>
        <span className="text-[11px] text-gray-500">breadth score <strong className="font-mono text-gray-700">{data.breadth_score}</strong>/100</span>
        {data.divergent && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">⚠ narrowing vs SPY</span>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {stat("% > 50-DMA", `${data.pct_above_50dma}%`, "above 50-day MA",
              data.pct_above_50dma >= 60 ? "text-green-700" : data.pct_above_50dma < 40 ? "text-red-600" : "text-gray-800")}
        {stat("% > 200-DMA", `${data.pct_above_200dma}%`, "above 200-day MA",
              data.pct_above_200dma >= 60 ? "text-green-700" : data.pct_above_200dma < 40 ? "text-red-600" : "text-gray-800")}
        {stat("New H − L", `${data.net_highs_lows > 0 ? "+" : ""}${data.net_highs_lows}`, `${data.new_highs} hi / ${data.new_lows} lo`,
              data.net_highs_lows > 0 ? "text-green-700" : data.net_highs_lows < 0 ? "text-red-600" : "text-gray-800")}
        {stat("Advancers", `${data.net_advancers > 0 ? "+" : ""}${data.net_advancers}`, `${data.advancers} up / ${data.decliners} dn`,
              data.net_advancers > 0 ? "text-green-700" : data.net_advancers < 0 ? "text-red-600" : "text-gray-800")}
      </div>

      <div className="bg-indigo-50/60 border border-indigo-100 rounded-lg px-3 py-2.5">
        <div className="font-semibold text-indigo-700 text-[12px] mb-1.5">What this is saying</div>
        <ul className="space-y-1.5">
          {data.interpretation_points.map((p) => (
            <li key={p.label} className="text-[12px] text-gray-700 leading-relaxed flex gap-2">
              <span className="text-indigo-400 select-none mt-px">•</span>
              <span><span className="font-semibold text-gray-800">{p.label}:</span> {p.detail}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
