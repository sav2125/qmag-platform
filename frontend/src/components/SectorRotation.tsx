"use client";

import { useEffect, useState } from "react";
import { api, SectorRotation as Rotation, SectorRow, SectorPerf } from "@/lib/api";

/* Sector RS Rotation panel — the leading "where is leadership?" gauge.
   Each of the 11 SPDR sectors is scored on relative strength vs SPY (3-mo RS level)
   and whether that RS is accelerating (RRG-style momentum), then placed in one of
   four quadrants. Tells a momentum trader which groups to hunt in. */

const QUAD_CFG: Record<string, { label: string; cls: string; dot: string }> = {
  leading:   { label: "Leading",   cls: "text-green-700",  dot: "bg-green-500"  },
  weakening: { label: "Weakening", cls: "text-amber-700",  dot: "bg-amber-400"  },
  improving: { label: "Improving", cls: "text-sky-700",    dot: "bg-sky-400"    },
  lagging:   { label: "Lagging",   cls: "text-red-600",    dot: "bg-red-400"    },
};

const QUAD_ORDER = ["leading", "improving", "weakening", "lagging"];

const HORIZONS: { key: keyof SectorPerf; label: string }[] = [
  { key: "d1", label: "1D" }, { key: "w1", label: "1W" }, { key: "m1", label: "1M" },
  { key: "m3", label: "3M" }, { key: "ytd", label: "YTD" },
];

// green/red heat cell for a relative or absolute return
function heatCell(v: number | null) {
  if (v == null) return { bg: "transparent", fg: "#9ca3af" };
  const mag = Math.min(Math.abs(v) / 15, 1);                  // saturate at ±15%
  const a = 0.12 + mag * 0.5;
  return v >= 0
    ? { bg: `rgba(34,197,94,${a})`, fg: "#14532d" }
    : { bg: `rgba(239,68,68,${a})`, fg: "#7f1d1d" };
}

export default function SectorRotationPanel() {
  const [data, setData] = useState<Rotation | null>(null);
  const [error, setError] = useState(false);
  const [mode, setMode] = useState<"rel" | "abs">("rel");

  useEffect(() => {
    api.sectors().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;             // backend cold-start / unreachable — hide quietly
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading sector rotation…
      </div>
    );
  }

  // group by quadrant for a compact RRG-style read
  const byQuad: Record<string, SectorRow[]> = {};
  for (const r of data.sectors) (byQuad[r.quadrant] ??= []).push(r);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Sector Rotation
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            relative strength vs SPY · {data.as_of}
          </span>
        </h2>
        <a href="/scoring#sectors" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      {/* Ranked bars — RS strength left-to-right */}
      <div className="space-y-1 mb-3">
        {data.sectors.map((r) => {
          const cfg = QUAD_CFG[r.quadrant] ?? QUAD_CFG.lagging;
          const max = Math.max(...data.sectors.map((s) => Math.abs(s.rs_strength)), 1);
          const w = Math.round((Math.abs(r.rs_strength) / max) * 100);
          return (
            <div key={r.symbol} className="flex items-center gap-2 text-xs">
              <span className="w-12 font-mono font-semibold text-gray-700">{r.symbol}</span>
              <span className="w-28 text-gray-500 truncate hidden sm:inline">{r.name}</span>
              <div className="flex-1 h-3 bg-gray-100 rounded relative overflow-hidden">
                <div className={`h-full ${cfg.dot} opacity-70`} style={{ width: `${w}%` }} />
              </div>
              <span className={`w-14 text-right font-mono ${r.rs_strength >= 0 ? "text-green-700" : "text-red-500"}`}>
                {r.rs_strength >= 0 ? "+" : ""}{r.rs_strength}%
              </span>
              <span className={`w-20 text-right text-[10px] font-semibold ${cfg.cls}`}>
                {cfg.label} {r.rs_momentum >= 0 ? "↗" : "↘"}
              </span>
            </div>
          );
        })}
      </div>

      {/* Quadrant legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-[10px] text-gray-500">
        {QUAD_ORDER.map((q) => (
          <span key={q} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${QUAD_CFG[q].dot}`} />
            {QUAD_CFG[q].label} ({(byQuad[q] ?? []).length})
          </span>
        ))}
        <span className="text-gray-400">↗ RS accelerating · ↘ decelerating</span>
      </div>

      {/* Multi-horizon performance heatmap (abs / relative-to-SPY) */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">
            Performance by horizon ({mode === "rel" ? "relative to SPY" : "absolute"})
          </span>
          <div className="flex text-[10px] rounded-md overflow-hidden border border-gray-200">
            {(["rel", "abs"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)}
                className={`px-2 py-0.5 ${mode === m ? "bg-indigo-500 text-white" : "bg-white text-gray-500 hover:bg-gray-50"}`}>
                {m === "rel" ? "vs SPY" : "abs"}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="text-gray-400">
                <th className="text-left font-medium py-1 pr-2">Sector</th>
                {HORIZONS.map((h) => <th key={h.key} className="text-right font-medium py-1 px-1.5 w-12">{h.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.sectors.map((r) => {
                const row = mode === "rel" ? r.rel : r.abs;
                return (
                  <tr key={r.symbol}>
                    <td className="py-0.5 pr-2 font-mono font-semibold text-gray-700">
                      {r.symbol}<span className="hidden md:inline text-gray-400 font-sans font-normal"> {r.name}</span>
                    </td>
                    {HORIZONS.map((h) => {
                      const v = row[h.key];
                      const c = heatCell(v);
                      return (
                        <td key={h.key} className="text-right py-0.5 px-1.5 font-mono rounded"
                            style={{ backgroundColor: c.bg, color: c.fg }}>
                          {v == null ? "—" : `${v >= 0 ? "+" : ""}${v}`}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
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
