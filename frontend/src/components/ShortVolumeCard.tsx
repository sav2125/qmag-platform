"use client";

import { useEffect, useState } from "react";
import { api, ShortVolume } from "@/lib/api";

/* Short-volume pressure card (FINRA Reg SHO daily) — lazy per-symbol layer.
   % of daily volume sold short (level + trend), read against recent price so it's
   directional: elevated shorts into a rising stock = squeeze fuel; into a falling
   one = bearish confirmation. NOT classic short interest — read the deviation. */

const LEVEL_CFG: Record<string, { label: string; cls: string }> = {
  very_high: { label: "very high short %", cls: "bg-amber-100 text-amber-800" },
  elevated:  { label: "elevated short %",  cls: "bg-amber-100 text-amber-800" },
  normal:    { label: "normal short %",    cls: "bg-gray-100 text-gray-500"  },
  low:       { label: "low short %",       cls: "bg-gray-100 text-gray-500"  },
};

export default function ShortVolumeCard({ symbol }: { symbol: string }) {
  const [data, setData] = useState<ShortVolume | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "none">("loading");

  useEffect(() => {
    let live = true;
    setState("loading");
    api.shortVolume(symbol)
      .then((d) => { if (live) { setData(d); setState("ok"); } })
      .catch(() => { if (live) setState("none"); });
    return () => { live = false; };
  }, [symbol]);

  if (state === "none") return null;   // not covered / unreachable — hide quietly

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Short-Volume Pressure (leading)</h3>
        <a href="/scoring#shortvol" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      {state === "loading" || !data ? (
        <div className="text-sm text-gray-400">Loading short-volume…</div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600 mb-3">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${(LEVEL_CFG[data.level] ?? LEVEL_CFG.normal).cls}`}>
              {(LEVEL_CFG[data.level] ?? LEVEL_CFG.normal).label}
            </span>
            <span className="text-gray-400">{data.days} trading days · FINRA Reg SHO</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Most recent day's short-sale volume as a share of total volume.">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Latest short %</div>
              <div className="text-sm font-mono font-semibold text-gray-800">{data.latest_pct}%</div>
            </div>
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Average short-sale volume % over the lookback window. Baseline for liquid names is ~45-50% (market-maker hedging).">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Avg short %</div>
              <div className="text-sm font-mono font-semibold text-gray-800">{data.avg_pct}%</div>
            </div>
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Recent-half average minus earlier-half average (percentage points). Positive = short pressure rising.">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Trend</div>
              <div className={`text-sm font-mono font-semibold ${data.trend > 1.5 ? "text-amber-700" : data.trend < -1.5 ? "text-green-700" : "text-gray-800"}`}>
                {data.trend > 0 ? "+" : ""}{data.trend}pp
              </div>
            </div>
          </div>

          <div className="mt-3 bg-indigo-50/60 border border-indigo-100 rounded-lg px-3 py-2.5">
            <div className="font-semibold text-indigo-700 text-[12.5px] mb-1.5">What this is saying</div>
            <ul className="space-y-1.5">
              {data.interpretation_points.map((p) => (
                <li key={p.label} className="text-[12.5px] text-gray-700 leading-relaxed flex gap-2">
                  <span className="text-indigo-400 select-none mt-px">•</span>
                  <span><span className="font-semibold text-gray-800">{p.label}:</span> {p.detail}</span>
                </li>
              ))}
            </ul>
          </div>
          <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
            <strong>Why it&apos;s leading:</strong> short-sellers position <em>ahead</em> of moves. This is short-sale <em>volume</em>
            {" "}(a daily flow proxy), not bi-monthly short interest — read the deviation from the ~45-50% baseline and the trend, against price.
          </p>
        </>
      )}
    </div>
  );
}
