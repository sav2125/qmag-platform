"use client";

import { useEffect, useState } from "react";
import { api, MarketRegime as Regime, QuadRead } from "@/lib/api";

/* Market-Implied Quad — Growth/Inflation regime inferred from price action
   (sector leadership + style factors + credit + breadth), with Hedgeye's matching
   playbook. Dual horizon: QUARTERLY = climate (longer-term, ~3mo) · MONTHLY = weather
   (intermediate, ~1mo). A heuristic mirror of the GIP Quads, NOT a GDP/CPI nowcast. */

// Hedgeye quad-grid layout: x = inflation (left low / right high), y = growth (top high / bottom low)
const GRID = [1, 2, 4, 3];
const QUAD_META: Record<number, { name: string; tag: string; cls: string; active: string }> = {
  1: { name: "Goldilocks",  tag: "Growth ↑ · Infl ↓", cls: "text-green-700", active: "bg-green-50 border-green-400" },
  2: { name: "Reflation",   tag: "Growth ↑ · Infl ↑", cls: "text-lime-700",  active: "bg-lime-50 border-lime-400" },
  3: { name: "Stagflation", tag: "Growth ↓ · Infl ↑", cls: "text-amber-700", active: "bg-amber-50 border-amber-400" },
  4: { name: "Deflation",   tag: "Growth ↓ · Infl ↓", cls: "text-red-700",   active: "bg-red-50 border-red-400" },
};

function QuadCard({ title, sub, q }: { title: string; sub: string; q: QuadRead | null }) {
  if (!q) return (
    <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-300">
      {title}: unavailable
    </div>
  );
  const m = QUAD_META[q.quad];
  return (
    <div className={`flex-1 rounded-lg border p-3 ${m.active}`}>
      <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">{title}<span className="normal-case font-normal text-gray-400"> · {sub}</span></div>
      <div className="flex items-baseline gap-2 mt-0.5">
        <span className={`font-bold text-sm ${m.cls}`}>Quad {q.quad} · {q.quad_name}</span>
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-white/70 text-gray-600">{q.conviction}</span>
      </div>
      <div className="text-[10px] text-gray-500 mb-2">{q.quad_tag}</div>
      {/* mini 2x2 grid */}
      <div className="grid grid-cols-2 gap-1">
        {GRID.map((n) => {
          const mm = QUAD_META[n];
          const on = n === q.quad;
          return (
            <div key={n} className={`rounded px-1 py-0.5 text-center border ${on ? mm.active : "bg-white/40 border-gray-100 opacity-50"}`}>
              <div className={`text-[9px] font-bold ${mm.cls}`}>Q{n}{on ? " ◀" : ""}</div>
              <div className={`text-[9px] ${on ? "text-gray-700" : "text-gray-400"}`}>{mm.name}</div>
            </div>
          );
        })}
      </div>
      <div className="text-[10px] text-gray-500 mt-1.5">
        Growth <strong className={q.growth === "accelerating" ? "text-green-700" : "text-red-600"}>{q.growth}</strong> ({q.growth_score >= 0 ? "+" : ""}{q.growth_score})
        {" · "}Infl <strong>{q.inflation}</strong> ({q.inflation_score >= 0 ? "+" : ""}{q.inflation_score})
      </div>
    </div>
  );
}

function PlaybookRow({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="flex gap-2 items-start">
      <span className="text-gray-400 w-20 shrink-0">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.map((it) => <span key={it} className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 text-[10px]">{it}</span>)}
      </div>
    </div>
  );
}

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

  const drive = data.monthly ?? data.quarterly;           // tactical playbook source
  const allEvidence = [
    ...(data.quarterly?.evidence ?? []).map((e) => ({ ...e, hz: "Q" })),
    ...(data.monthly?.evidence ?? []).map((e) => ({ ...e, hz: "M" })),
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Market-Implied Quad
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            regime inferred from price action · {data.as_of}
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${data.aligned ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
            {data.aligned ? "climate & weather aligned" : "in transition"}
          </span>
          <a href="/scoring#regime" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
        </div>
      </div>

      {/* Dual-horizon quad cards: climate (quarterly) + weather (monthly) */}
      <div className="flex flex-col sm:flex-row gap-2 mb-3">
        <QuadCard title="Climate" sub="Quarterly · ~3mo" q={data.quarterly} />
        <QuadCard title="Weather" sub="Monthly · ~1mo" q={data.monthly} />
      </div>

      {/* Tactical playbook (from the monthly/weather read) */}
      {drive && (
        <div className="space-y-1 text-[11px] mb-3">
          <PlaybookRow label="Favor sectors" items={drive.playbook.best_sectors} />
          <PlaybookRow label="Favor factors" items={drive.playbook.best_factors} />
          <PlaybookRow label="Best assets" items={drive.playbook.best_assets} />
        </div>
      )}

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

      <details className="mt-2">
        <summary className="text-[11px] text-gray-500 cursor-pointer hover:text-gray-700">Show the signals that voted ({allEvidence.length})</summary>
        <ul className="mt-1.5 space-y-1">
          {allEvidence.map((e, i) => (
            <li key={i} className="text-[11px] text-gray-600 flex gap-2">
              <span className="text-gray-300 font-mono w-4 shrink-0">{e.hz}</span>
              <span className={`font-mono font-semibold ${e.vote > 0 ? "text-green-600" : "text-red-500"}`}>{e.vote > 0 ? "+" : ""}{e.vote}</span>
              <span className="text-gray-400 uppercase text-[9px] mt-0.5 w-12 shrink-0">{e.axis}</span>
              <span><span className="font-semibold text-gray-700">{e.label}:</span> {e.detail}</span>
            </li>
          ))}
        </ul>
      </details>

      <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
        <strong>Climate vs weather:</strong> the quarterly Quad is the dominant regime (your default posture); the monthly
        Quad is the faster tactical overlay for timing. Heuristic <strong>market-implied</strong> read — what the tape is
        trading like, not a GDP/CPI nowcast; the inflation axis is the weaker-inferred one. Context, not a P Score input.
      </p>
    </div>
  );
}
