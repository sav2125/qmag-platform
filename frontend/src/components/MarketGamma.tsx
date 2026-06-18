"use client";

import { useEffect, useState } from "react";
import { api, MarketGamma as Gamma, GammaIndex } from "@/lib/api";

/* Market Gamma — index dealer-gamma regime (SPY + QQQ) at a glance.
   Positive/long gamma = dealers dampen moves (calm, mean-reverting); negative/short
   gamma = dealers amplify moves (breakouts & breakdowns run). The flip is the switch. */

function IndexCell({ g }: { g: GammaIndex }) {
  const pos = g.regime === "positive";
  const cfg = pos
    ? { tag: "long gamma · calm", cls: "bg-sky-100 text-sky-700" }
    : { tag: "short gamma · amplifying", cls: "bg-amber-100 text-amber-700" };
  return (
    <div className="flex-1 min-w-[200px] rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-semibold text-gray-800">{g.name} <span className="text-gray-400 font-normal">{g.symbol}</span></span>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${cfg.cls}`}>{cfg.tag}</span>
      </div>
      <div className="text-xs text-gray-600 space-y-0.5">
        <div className="font-mono">
          spot <span className="font-semibold text-gray-800">${g.spot}</span>
          <span className="text-gray-300"> · </span>
          GEX <span className={pos ? "text-sky-700" : "text-amber-700"}>{g.gex_musd >= 0 ? "+" : ""}{g.gex_musd}M</span>
        </div>
        <div className="font-mono text-[11px] text-gray-500">
          flip ${g.flip ?? "—"}{" "}
          <span className={g.above_flip ? "text-green-600" : "text-red-500"}>
            ({g.above_flip ? "▲ above — stabilizing" : "▼ below — accelerant"})
          </span>
        </div>
        <div className="font-mono text-[11px] text-gray-400">
          walls {g.call_wall ? `C $${g.call_wall}` : "—"} / {g.put_wall ? `P $${g.put_wall}` : "—"}
        </div>
      </div>
    </div>
  );
}

export default function MarketGammaPanel() {
  const [data, setData] = useState<Gamma | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.gamma().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading market gamma…
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Market Gamma
          <span className="ml-2 text-[10px] font-normal text-gray-400">index dealer-gamma regime · {data.as_of}</span>
        </h2>
        <a href="/scoring#options" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        {data.indices.map((g) => <IndexCell key={g.symbol} g={g} />)}
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
      <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
        Free per-index GEX from the CBOE chain (SPY/QQQ as the index proxy). Snapshot — walls shift with open interest and
        reset around monthly OPEX; a probabilistic tendency, not a guarantee. Context, not a P Score input.
      </p>
    </div>
  );
}
