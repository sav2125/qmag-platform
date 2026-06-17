"use client";

import { useEffect, useState } from "react";
import { api, MacroQuad, MarketRegime, FundamentalQuadRead } from "@/lib/api";

/* Fundamental GIP Quad — the macro DATA read (FRED GDP/CPI/IP rate-of-change),
   shown next to the price-implied Quad (the tape). When tape and data disagree, the
   market is pricing one regime while the fundamentals turn toward another — Hedgeye's
   "bullish until it isn't." */

const QUAD_CLS: Record<number, string> = {
  1: "text-green-700", 2: "text-lime-700", 3: "text-amber-700", 4: "text-red-700",
};
const QUAD_NAME: Record<number, string> = { 1: "Goldilocks", 2: "Reflation", 3: "Stagflation", 4: "Deflation" };

function FundCard({ title, sub, q }: { title: string; sub: string; q: FundamentalQuadRead | null }) {
  if (!q) return (
    <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-300">{title}: unavailable</div>
  );
  return (
    <div className="flex-1 rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-500">{title}<span className="normal-case font-normal text-gray-400"> · {sub}</span></div>
      <div className={`font-bold text-sm mt-0.5 ${QUAD_CLS[q.quad]}`}>Quad {q.quad} · {q.quad_name}</div>
      <div className="text-[10px] text-gray-400 mb-2">{q.quad_tag}</div>
      <div className="text-[11px] text-gray-600 space-y-0.5">
        <div>
          <span className="text-gray-400">{q.growth_metric}:</span>{" "}
          <strong className={q.growth === "accelerating" ? "text-green-700" : "text-red-600"}>{q.growth}</strong>{" "}
          <span className="font-mono">{q.growth_yoy_prev}%→{q.growth_yoy}% ({q.growth_delta_bps >= 0 ? "+" : ""}{q.growth_delta_bps}bps)</span>
        </div>
        <div>
          <span className="text-gray-400">CPI YoY:</span>{" "}
          <strong className={q.inflation === "accelerating" ? "text-amber-700" : "text-green-700"}>{q.inflation}</strong>{" "}
          <span className="font-mono">{q.cpi_yoy_prev}%→{q.cpi_yoy}% ({q.inflation_delta_bps >= 0 ? "+" : ""}{q.inflation_delta_bps}bps)</span>
        </div>
      </div>
    </div>
  );
}

function tapeQuads(r: MarketRegime | null) {
  return { c: r?.quarterly?.quad ?? null, w: r?.monthly?.quad ?? null };
}

export default function FundamentalQuadPanel() {
  const [gip, setGip] = useState<MacroQuad | null>(null);
  const [tape, setTape] = useState<MarketRegime | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.gip().then(setGip).catch(() => setError(true));
    api.regime().then(setTape).catch(() => { /* tape optional for this panel */ });
  }, []);

  if (error) return null;
  if (!gip) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-sm text-gray-400">
        Loading fundamental (data) regime…
      </div>
    );
  }

  const t = tapeQuads(tape);
  const dq = gip.quarterly?.quad ?? null;
  const dw = gip.monthly?.quad ?? null;
  const haveCompare = t.c != null && t.w != null && dq != null && dw != null;
  const diverge = haveCompare && (t.c !== dq || t.w !== dw);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-800">
          Fundamental Quad <span className="text-gray-400 font-normal">(the data)</span>
          <span className="ml-2 text-[10px] font-normal text-gray-400">FRED GDP/CPI/IP rate-of-change · {gip.as_of}</span>
        </h2>
        <a href="/scoring#gip" className="text-[11px] text-indigo-400 hover:underline">How this works →</a>
      </div>

      {/* Tape vs Data verdict — the headline */}
      {haveCompare && (
        <div className={`rounded-lg border px-3 py-2 mb-3 ${diverge ? "bg-amber-50 border-amber-300" : "bg-green-50 border-green-300"}`}>
          <div className="text-[11px] font-semibold mb-1 flex items-center gap-2">
            <span className={diverge ? "text-amber-800" : "text-green-800"}>
              {diverge ? "⚠ Tape and data diverge" : "Tape and data agree"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div className="text-gray-600">
              <span className="text-gray-400 uppercase text-[9px]">Tape (price-implied)</span><br />
              climate <span className={`font-semibold ${QUAD_CLS[t.c!]}`}>Q{t.c} {QUAD_NAME[t.c!]}</span> · weather <span className={`font-semibold ${QUAD_CLS[t.w!]}`}>Q{t.w} {QUAD_NAME[t.w!]}</span>
            </div>
            <div className="text-gray-600">
              <span className="text-gray-400 uppercase text-[9px]">Data (GDP/CPI)</span><br />
              climate <span className={`font-semibold ${QUAD_CLS[dq!]}`}>Q{dq} {QUAD_NAME[dq!]}</span> · weather <span className={`font-semibold ${QUAD_CLS[dw!]}`}>Q{dw} {QUAD_NAME[dw!]}</span>
            </div>
          </div>
          {diverge && (
            <div className="text-[11px] text-amber-900 mt-1.5">
              The market is still pricing its regime while the data has turned — the early-warning split (&quot;bullish until it isn&apos;t&quot;).
            </div>
          )}
        </div>
      )}

      {/* Fundamental dual-horizon cards */}
      <div className="flex flex-col sm:flex-row gap-2 mb-3">
        <FundCard title="Climate" sub="Quarterly · Real GDP" q={gip.quarterly} />
        <FundCard title="Weather" sub="Monthly · Industrial Prod." q={gip.monthly} />
      </div>

      <div className="bg-indigo-50/60 border border-indigo-100 rounded-lg px-3 py-2.5">
        <div className="font-semibold text-indigo-700 text-[12px] mb-1.5">What this is saying</div>
        <ul className="space-y-1.5">
          {gip.interpretation_points.map((p) => (
            <li key={p.label} className="text-[12px] text-gray-700 leading-relaxed flex gap-2">
              <span className="text-indigo-400 select-none mt-px">•</span>
              <span><span className="font-semibold text-gray-800">{p.label}:</span> {p.detail}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
        The <strong>data</strong> read (FRED, free) — Hedgeye-style GIP rate-of-change. Climate = Real GDP YoY (quarterly);
        weather = Industrial Production YoY (monthly), both vs Headline CPI. Trailing (latest released data), not a forward
        nowcast. Pair it with the price-implied Quad above; divergence is the signal. Not a P Score input.
      </p>
    </div>
  );
}
