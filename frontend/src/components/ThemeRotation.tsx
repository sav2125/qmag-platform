"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ThemeRotation as Rotation, ThemeRow } from "@/lib/api";

/* Theme rotation — which investable themes are leading + the names to focus on.
   Curated baskets (cyber, agentic AI, AI infra, quantum, space, robotics, power, biotech)
   scored by RS vs SPY + RS acceleration into RRG quadrants, each expandable to its top-RS
   constituents. Answers "when is a theme rotating" and "what to focus on". */

const QUAD_CFG: Record<string, { label: string; cls: string; dot: string }> = {
  leading:   { label: "Leading",   cls: "text-green-700", dot: "bg-green-500" },
  weakening: { label: "Weakening", cls: "text-amber-700", dot: "bg-amber-400" },
  improving: { label: "Improving", cls: "text-sky-700",   dot: "bg-sky-400" },
  lagging:   { label: "Lagging",   cls: "text-red-600",   dot: "bg-red-400" },
};

function ThemeBar({ t, max }: { t: ThemeRow; max: number }) {
  const cfg = QUAD_CFG[t.quadrant] ?? QUAD_CFG.lagging;
  const [open, setOpen] = useState(false);
  const rs = t.rs_strength ?? 0;
  const w = Math.round((Math.abs(rs) / max) * 100);
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 text-xs py-1.5 hover:bg-gray-50 text-left">
        <span className="w-3 text-gray-300">{open ? "▾" : "▸"}</span>
        <span className="w-40 font-semibold text-gray-700 truncate">{t.name}</span>
        <div className="flex-1 h-3 bg-gray-100 rounded relative overflow-hidden min-w-[40px]">
          <div className={`h-full ${cfg.dot} opacity-70`} style={{ width: `${w}%` }} />
        </div>
        <span className={`w-14 text-right font-mono ${rs >= 0 ? "text-green-700" : "text-red-500"}`}>
          {rs >= 0 ? "+" : ""}{rs}%
        </span>
        <span className={`w-20 text-right text-[10px] font-semibold ${cfg.cls}`}>
          {cfg.label} {(t.rs_momentum ?? 0) >= 0 ? "↗" : "↘"}
        </span>
      </button>
      {open && (
        <div className="pl-5 pb-2 flex flex-wrap gap-1.5">
          {t.leaders.map((l) => (
            <Link key={l.symbol} href={`/analyze?symbol=${l.symbol}`}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-gray-50 border border-gray-200 hover:border-indigo-300">
              {l.symbol}{" "}
              <span className={(l.rel_m3 ?? 0) >= 0 ? "text-green-600" : "text-red-500"}>
                {(l.rel_m3 ?? 0) >= 0 ? "+" : ""}{l.rel_m3}%
              </span>
            </Link>
          ))}
          <span className="text-[10px] text-gray-400 self-center">{t.count} names · {t.source} · RS vs SPY (3-mo)</span>
        </div>
      )}
    </div>
  );
}

export default function ThemeRotationPanel() {
  const [data, setData] = useState<Rotation | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.themes().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading theme rotation…
      </div>
    );
  }
  const max = Math.max(...data.themes.map((t) => Math.abs(t.rs_strength ?? 0)), 1);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-bold text-gray-800">
          Theme Rotation
          <span className="ml-2 text-[10px] font-normal text-gray-400">where leadership is concentrated · {data.as_of}</span>
        </h2>
        <a href="/scoring#themes" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>
      <p className="text-[11px] text-gray-400 mb-2">Click a theme to see the top-RS names to focus on.</p>

      <div className="mb-3">
        {data.themes.map((t) => <ThemeBar key={t.key} t={t} max={max} />)}
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
