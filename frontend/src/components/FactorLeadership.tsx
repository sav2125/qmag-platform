"use client";

import { useEffect, useState } from "react";
import { api, FactorLeadership as FL, SectorPerf } from "@/lib/api";

/* Style-factor leadership — "what is the market paying for right now?"
   High vs Low quartile return spread for Momentum, Beta, Volatility, Short-Interest
   across 1D→YTD. Positive = that factor is in gear. The Momentum + Beta rows tell a
   Qullamaggie trader whether the regime supports breakouts or fights them. */

const HORIZONS: { key: keyof SectorPerf; label: string }[] = [
  { key: "d1", label: "1D" }, { key: "w1", label: "1W" }, { key: "m1", label: "1M" },
  { key: "m3", label: "3M" }, { key: "ytd", label: "YTD" },
];

function heat(v: number | null) {
  if (v == null) return { bg: "transparent", fg: "#9ca3af" };
  const mag = Math.min(Math.abs(v) / 20, 1);
  const a = 0.12 + mag * 0.5;
  return v >= 0
    ? { bg: `rgba(34,197,94,${a})`, fg: "#14532d" }
    : { bg: `rgba(239,68,68,${a})`, fg: "#7f1d1d" };
}

export default function FactorLeadershipPanel() {
  const [data, setData] = useState<FL | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.factors().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading factor leadership…
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Style-Factor Leadership
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            High − Low quartile spread · {data.universe} large caps · {data.as_of}
          </span>
        </h2>
        <a href="/scoring#factors" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      <div className="overflow-x-auto mb-3">
        <table className="w-full text-[11px] border-collapse">
          <thead>
            <tr className="text-gray-400">
              <th className="text-left font-medium py-1 pr-2">Factor (High vs Low)</th>
              <th className="text-center font-medium py-1 px-1">Leader</th>
              {HORIZONS.map((h) => <th key={h.key} className="text-right font-medium py-1 px-1.5 w-12">{h.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.factors.map((f) => (
              <tr key={f.factor}>
                <td className="py-0.5 pr-2 font-semibold text-gray-700">{f.factor}</td>
                <td className="text-center py-0.5 px-1">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                    f.leader === "high" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                    {f.leader === "high" ? f.high_label : f.low_label}
                  </span>
                </td>
                {HORIZONS.map((h) => {
                  const v = f.spread[h.key];
                  const c = heat(v);
                  return (
                    <td key={h.key} className="text-right py-0.5 px-1.5 font-mono rounded"
                        style={{ backgroundColor: c.bg, color: c.fg }}>
                      {v == null ? "—" : `${v >= 0 ? "+" : ""}${v}`}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
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
