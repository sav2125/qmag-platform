"use client";

import { useEffect, useState } from "react";
import { api, MarketRegime as Regime } from "@/lib/api";

/* Market-Implied Quad — Growth/Inflation regime inferred from price action
   (sector leadership + style factors + credit + breadth), with Hedgeye's matching
   playbook. A heuristic mirror of the GIP Quads, NOT a GDP/CPI nowcast. */

// Hedgeye quad-grid layout: x = inflation (left low / right high), y = growth (top high / bottom low)
const GRID = [1, 2, 4, 3];
const QUAD_META: Record<number, { name: string; tag: string; cls: string; active: string }> = {
  1: { name: "Goldilocks",  tag: "Growth ↑ · Infl ↓", cls: "text-green-700",  active: "bg-green-50 border-green-400" },
  2: { name: "Reflation",   tag: "Growth ↑ · Infl ↑", cls: "text-lime-700",   active: "bg-lime-50 border-lime-400" },
  3: { name: "Stagflation", tag: "Growth ↓ · Infl ↑", cls: "text-amber-700",  active: "bg-amber-50 border-amber-400" },
  4: { name: "Deflation",   tag: "Growth ↓ · Infl ↓", cls: "text-red-700",    active: "bg-red-50 border-red-400" },
};

export default function MarketRegimePanel() {
  const [data, setData] = useState<Regime | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.regime().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading market regime…
      </div>
    );
  }

  const active = QUAD_META[data.quad];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Market-Implied Quad
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            regime inferred from price action · {data.as_of}
          </span>
        </h2>
        <a href="/scoring#regime" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Quad grid */}
        <div className="lg:w-64 shrink-0">
          <div className="grid grid-cols-2 gap-1.5">
            {GRID.map((q) => {
              const m = QUAD_META[q];
              const on = q === data.quad;
              return (
                <div key={q} className={`rounded-lg border p-2 text-center ${on ? m.active : "bg-gray-50 border-gray-200 opacity-50"}`}>
                  <div className={`text-[10px] font-bold ${m.cls}`}>QUAD {q}{on ? " ◀" : ""}</div>
                  <div className={`text-xs font-semibold ${on ? "text-gray-800" : "text-gray-400"}`}>{m.name}</div>
                  <div className="text-[9px] text-gray-400">{m.tag}</div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[9px] text-gray-400 mt-1 px-1">
            <span>← lower inflation</span><span>higher inflation →</span>
          </div>
        </div>

        {/* Active read + playbook */}
        <div className="flex-1">
          <div className={`rounded-lg border px-3 py-2 mb-2 ${active.active}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`font-bold text-sm ${active.cls}`}>Quad {data.quad} · {data.quad_name}</span>
              <span className="text-[10px] text-gray-500">{data.quad_tag}</span>
              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-white/70 text-gray-600">{data.conviction} conviction</span>
            </div>
            <div className="text-[11px] text-gray-600 mt-1">
              Growth <strong className={data.growth === "accelerating" ? "text-green-700" : "text-red-600"}>{data.growth}</strong> ({data.growth_score >= 0 ? "+" : ""}{data.growth_score})
              {" · "}Inflation <strong>{data.inflation}</strong> ({data.inflation_score >= 0 ? "+" : ""}{data.inflation_score})
            </div>
          </div>

          {/* Playbook chips */}
          <div className="space-y-1 text-[11px] mb-2">
            <PlaybookRow label="Favor sectors" items={data.playbook.best_sectors} />
            <PlaybookRow label="Favor factors" items={data.playbook.best_factors} />
            <PlaybookRow label="Best assets" items={data.playbook.best_assets} />
          </div>
        </div>
      </div>

      <div className="mt-3 bg-indigo-50/60 border border-indigo-100 rounded-lg px-3 py-2.5">
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

      {/* Evidence (transparency) */}
      <details className="mt-2">
        <summary className="text-[11px] text-gray-500 cursor-pointer hover:text-gray-700">Show the signals that voted ({data.evidence.length})</summary>
        <ul className="mt-1.5 space-y-1">
          {data.evidence.map((e, i) => (
            <li key={i} className="text-[11px] text-gray-600 flex gap-2">
              <span className={`font-mono font-semibold ${e.vote > 0 ? "text-green-600" : "text-red-500"}`}>{e.vote > 0 ? "+" : ""}{e.vote}</span>
              <span className="text-gray-400 uppercase text-[9px] mt-0.5 w-12 shrink-0">{e.axis}</span>
              <span><span className="font-semibold text-gray-700">{e.label}:</span> {e.detail}</span>
            </li>
          ))}
        </ul>
      </details>

      <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
        Heuristic <strong>market-implied</strong> regime — what the tape is trading like, not Hedgeye&apos;s GDP/CPI nowcast.
        The inflation axis is the weaker-inferred one on free data. Context for sizing &amp; where to hunt — not a P Score input.
      </p>
    </div>
  );
}

function PlaybookRow({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="flex gap-2 items-start">
      <span className="text-gray-400 w-20 shrink-0">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.map((it) => (
          <span key={it} className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-[10px]">{it}</span>
        ))}
      </div>
    </div>
  );
}
