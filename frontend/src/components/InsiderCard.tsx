"use client";

import { useEffect, useState } from "react";
import { api, Insider } from "@/lib/api";

/* Insider activity card (SEC EDGAR Form 4) — lazy per-symbol layer.
   Open-market purchases (P) vs sales (S) over ~120 days. Buys are the leading
   signal (insiders buy for one reason); cluster buying is strongest. Sales are
   down-weighted (diversification/taxes/comp). Grants & exercises are excluded. */

const SIGNAL_CFG: Record<string, { label: string; cls: string }> = {
  cluster_buying: { label: "cluster buying", cls: "bg-green-100 text-green-700" },
  buying:         { label: "insider buying", cls: "bg-green-100 text-green-700" },
  selling:        { label: "selling only",   cls: "bg-amber-100 text-amber-700" },
  none:           { label: "quiet",          cls: "bg-gray-100 text-gray-500"  },
};

function money(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}k`;
  return `$${v}`;
}

export default function InsiderCard({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Insider | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "none">("loading");

  useEffect(() => {
    let live = true;
    setState("loading");
    api.insider(symbol)
      .then((d) => { if (live) { setData(d); setState("ok"); } })
      .catch(() => { if (live) setState("none"); });
    return () => { live = false; };
  }, [symbol]);

  if (state === "none") return null;   // not covered / unreachable — hide quietly

  const cfg = data ? (SIGNAL_CFG[data.signal] ?? SIGNAL_CFG.none) : SIGNAL_CFG.none;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Insider Activity (leading)</h3>
        <a href="/scoring#insider" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      {state === "loading" || !data ? (
        <div className="text-sm text-gray-400">Loading insider filings…</div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600 mb-3">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${cfg.cls}`}>{cfg.label}</span>
            <span className="text-gray-400">last {data.lookback_days}d · SEC Form 4 (open-market only)</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Open-market purchases (transaction code P). The bullish conviction signal.">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Bought</div>
              <div className="text-sm font-mono font-semibold text-green-700">{money(data.buy_value)}</div>
              <div className="text-[10px] text-gray-400">{data.buyers} buyer{data.buyers === 1 ? "" : "s"}</div>
            </div>
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Open-market sales (code S). A weak signal on its own — diversification, taxes, comp.">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Sold</div>
              <div className="text-sm font-mono font-semibold text-gray-700">{money(data.sell_value)}</div>
              <div className="text-[10px] text-gray-400">{data.sellers} seller{data.sellers === 1 ? "" : "s"}</div>
            </div>
            <div className="bg-gray-50 rounded-lg px-3 py-2" title="Net open-market flow (buys − sells).">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Net flow</div>
              <div className={`text-sm font-mono font-semibold ${data.net_value > 0 ? "text-green-700" : data.net_value < 0 ? "text-amber-700" : "text-gray-800"}`}>
                {data.net_value >= 0 ? "+" : "−"}{money(Math.abs(data.net_value))}
              </div>
            </div>
          </div>

          {data.top_buys.length > 0 && (
            <div className="mt-2 text-[11px] text-gray-600 bg-green-50/60 rounded px-2 py-1.5 leading-relaxed">
              <span className="font-semibold text-gray-500">Recent buys:</span>{" "}
              {data.top_buys.map((b, i) => (
                <span key={i}>
                  {i > 0 && <span className="text-gray-300"> · </span>}
                  <span className="font-mono text-green-700">{money(b.value)}</span> {b.title} {b.owner} ({b.date})
                </span>
              ))}
            </div>
          )}

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
            <strong>Why it&apos;s leading:</strong> insiders trade on private knowledge of the business. Open-market <em>buying</em> —
            especially a <em>cluster</em> of insiders — is one of the better-documented edges; selling is noisy and down-weighted here.
          </p>
        </>
      )}
    </div>
  );
}
