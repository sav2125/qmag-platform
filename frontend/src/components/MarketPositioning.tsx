"use client";

import { useEffect, useState } from "react";
import { api, MarketPositioning as Positioning } from "@/lib/api";

/* Market Positioning panel — the forward-looking "who's exposed" layer.
   Three free positioning sources combined into a contrarian regime dial:
   CFTC COT leveraged funds (CTA proxy), SPY put/call ratio, NAAIM exposure.
   Extremes are contrarian: fear = fuel for breakouts, crowding = air-pocket risk. */

const DIAL_STYLE: Record<string, string> = {
  pos: "bg-green-50 border-green-300 text-green-800",
  neu: "bg-gray-50 border-gray-200 text-gray-600",
  neg: "bg-amber-50 border-amber-300 text-amber-800",
};

function dialTone(score: number): string {
  if (score > 0) return "pos";
  if (score < 0) return "neg";
  return "neu";
}

function StatePill({ state }: { state: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    crowded_short:  { label: "Crowded short — squeeze fuel", cls: "bg-green-100 text-green-700" },
    washed_out:     { label: "Washed out — contrarian +",    cls: "bg-green-100 text-green-700" },
    fear:           { label: "Fear — contrarian +",          cls: "bg-green-100 text-green-700" },
    neutral:        { label: "Neutral",                      cls: "bg-gray-100 text-gray-500" },
    crowded_long:   { label: "Crowded long — caution",       cls: "bg-amber-100 text-amber-700" },
    fully_invested: { label: "Fully invested — caution",     cls: "bg-amber-100 text-amber-700" },
    complacent:     { label: "Complacent — caution",         cls: "bg-amber-100 text-amber-700" },
  };
  const c = cfg[state] ?? cfg.neutral;
  return <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${c.cls}`}>{c.label}</span>;
}

function SourceCard({
  title, tip, children, state, unavailable,
}: {
  title: string; tip: string; children?: React.ReactNode; state?: string; unavailable?: boolean;
}) {
  return (
    <div className="flex-1 min-w-[180px] bg-white border border-gray-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="group relative text-[11px] font-semibold text-gray-600 uppercase tracking-wide cursor-help">
          {title}
          <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-64 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal normal-case tracking-normal">
            {tip}
          </span>
        </span>
        {state && <StatePill state={state} />}
      </div>
      {unavailable
        ? <div className="text-sm text-gray-300">unavailable</div>
        : children}
    </div>
  );
}

export default function MarketPositioningPanel() {
  const [data, setData] = useState<Positioning | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.positioning().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;            // backend cold-start / unreachable — hide quietly
  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading market positioning…
      </div>
    );
  }

  const tone = dialTone(data.dial.score);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Market Positioning
          <span className="ml-2 text-[10px] font-normal text-gray-400">
            forward-looking regime · {data.as_of}
          </span>
        </h2>
        <a href="/scoring#positioning" className="text-[11px] text-indigo-400 hover:underline">
          How this works →
        </a>
      </div>

      {/* Regime dial */}
      <div className={`rounded-lg border px-4 py-2.5 mb-3 ${DIAL_STYLE[tone]}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold font-mono">
            {data.dial.score > 0 ? `+${data.dial.score}` : data.dial.score}
          </span>
          <span className="font-semibold text-sm">{data.dial.label}</span>
        </div>
        <p className="text-xs opacity-80 mt-0.5">{data.dial.detail}</p>
      </div>

      {/* Source cards */}
      <div className="flex flex-wrap gap-3">
        <SourceCard
          title="CTA / Lev. funds (COT)"
          tip="CFTC Commitment of Traders — leveraged-funds net position in E-mini S&P 500 + Nasdaq futures, z-scored vs ~3 years. The closest free proxy to CTA positioning. Crowded shorts = squeeze fuel (contrarian bullish); crowded longs = no marginal buyer left. Updates weekly (Fri, data as of Tue)."
          state={data.cot?.state}
          unavailable={!data.cot}
        >
          {data.cot && (
            <div className="text-xs text-gray-600 space-y-0.5">
              <div className="font-mono text-base font-bold text-gray-800">
                z {data.cot.avg_z > 0 ? "+" : ""}{data.cot.avg_z.toFixed(2)}
              </div>
              <div className="font-mono text-[11px] text-gray-400">
                ES {data.cot.es ? `${data.cot.es.net_pct_oi}% OI (z ${data.cot.es.z})` : "—"}
              </div>
              <div className="font-mono text-[11px] text-gray-400">
                NQ {data.cot.nq ? `${data.cot.nq.net_pct_oi}% OI (z ${data.cot.nq.z})` : "—"}
              </div>
            </div>
          )}
        </SourceCard>

        <SourceCard
          title="SPY Put/Call"
          tip="SPY put/call volume ratio across near-dated expirations (computed from Alpaca options data). SPY options skew put-heavy (hedging), so thresholds are calibrated: ≥2.0 = fear extreme (contrarian bullish), ≤1.1 = call-chasing complacency. Updates daily."
          state={data.put_call?.state}
          unavailable={!data.put_call}
        >
          {data.put_call && (
            <div className="text-xs text-gray-600 space-y-0.5">
              <div className="font-mono text-base font-bold text-gray-800">
                {data.put_call.ratio.toFixed(2)}
              </div>
              <div className="font-mono text-[11px] text-gray-400">
                P {Math.round(data.put_call.put_vol / 1000)}k / C {Math.round(data.put_call.call_vol / 1000)}k
              </div>
            </div>
          )}
        </SourceCard>

        <SourceCard
          title="NAAIM Exposure"
          tip="NAAIM Exposure Index — average equity exposure of active money managers (0 = flat, 200 = leveraged long). <30 = washed out (contrarian bullish), >90 = fully invested (no dry powder). Updates weekly (Wed)."
          state={data.naaim?.state}
          unavailable={!data.naaim}
        >
          {data.naaim && (
            <div className="text-xs text-gray-600 space-y-0.5">
              <div className="font-mono text-base font-bold text-gray-800">
                {data.naaim.value.toFixed(0)}
                <span className="text-[11px] font-normal text-gray-400"> / 200</span>
              </div>
              <div className="font-mono text-[11px] text-gray-400">
                z {data.naaim.z > 0 ? "+" : ""}{data.naaim.z.toFixed(2)}{data.naaim.date ? ` · ${data.naaim.date}` : ""}
              </div>
            </div>
          )}
        </SourceCard>
      </div>
    </div>
  );
}
