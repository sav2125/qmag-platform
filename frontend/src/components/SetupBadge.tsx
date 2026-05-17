const COLORS: Record<string, string> = {
  EP:   "bg-purple-600 text-white",
  TB:   "bg-green-600 text-white",
  PP:   "bg-cyan-600 text-white",
  PULL: "bg-amber-500 text-white",
  FBD:  "bg-rose-600 text-white",
  WYS:  "bg-violet-700 text-white",
  FLAG: "bg-blue-600 text-white",
};

export function SetupBadge({ type }: { type: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold tracking-wide ${COLORS[type] ?? "bg-gray-500 text-white"}`}>
      {type}
    </span>
  );
}

export function GradeBadge({ grade }: { grade: string }) {
  const c = { A: "text-green-600", B: "text-blue-600", C: "text-amber-600", D: "text-gray-400" }[grade] ?? "text-gray-400";
  return <span className={`font-bold text-sm ${c}`}>{grade}</span>;
}

export function RRBadge({ rr }: { rr: number }) {
  const c = rr >= 2 ? "text-green-600 font-bold" : rr >= 1.5 ? "text-amber-600 font-semibold" : "text-gray-400";
  return <span className={c}>{rr.toFixed(1)}x</span>;
}

const STAGE_CONFIG: Record<number, { label: string; color: string; tip: string }> = {
  1: { label: "S1", color: "bg-gray-100 text-gray-500 border border-gray-200", tip: "Stage 1 — Basing. Stock is flat/below its 30-week MA. Not yet actionable." },
  2: { label: "S2", color: "bg-green-100 text-green-700 border border-green-300", tip: "Stage 2 — Advancing. Rising 30-week MA, price above it. The only stage Qullamaggie trades." },
  3: { label: "S3", color: "bg-amber-100 text-amber-700 border border-amber-300", tip: "Stage 3 — Topping. MA rolling over. Avoid new longs." },
  4: { label: "S4", color: "bg-red-100 text-red-600 border border-red-200", tip: "Stage 4 — Declining. Price below falling MA. Short only." },
};

export function StageBadge({ stage }: { stage: number }) {
  if (!stage) return <span className="text-gray-300 text-xs">—</span>;
  const cfg = STAGE_CONFIG[stage] ?? { label: `S${stage}`, color: "bg-gray-100 text-gray-500", tip: "" };
  return (
    <span className={`group relative inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-bold cursor-help ${cfg.color}`}>
      {cfg.label}
      {cfg.tip && (
        <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-56 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl">
          {cfg.tip}
        </span>
      )}
    </span>
  );
}

export function ADNetBadge({ net }: { net: number }) {
  if (net === 0) return <span className="text-gray-400 text-xs font-mono">0</span>;
  const positive = net > 0;
  return (
    <span className={`text-xs font-mono font-semibold ${positive ? "text-green-600" : "text-red-500"}`}>
      {positive ? "+" : ""}{net}
    </span>
  );
}

// ICS — Institutional Composite Score (0-100)
// Green ≥75 (accumulation), Amber 40-74 (neutral), Red <40 (distribution)
export function ICSBadge({ score }: { score: number }) {
  const color =
    score >= 75 ? "text-green-600 font-semibold" :
    score >= 40 ? "text-amber-600" :
    "text-red-500";
  return (
    <span
      className={`group relative text-[10px] font-mono cursor-help ${color}`}
      title="ICS: Institutional Composite Score (OBV + CMF + A/D line + MFI)"
    >
      ICS {score.toFixed(0)}
      <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-60 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal">
        Institutional Composite Score (0–100). Combines OBV trend, Chaikin Money Flow, A/D line trend, and MFI. ≥75 = clear accumulation. &lt;40 = distribution.
      </span>
    </span>
  );
}

// WeeklyDir — Weekly timeframe direction badge (resampled from daily bars)
// Shown as a compact pill under the Grade in the scan table.
export function WeeklyDirBadge({ dir }: { dir: "bullish" | "neutral" | "bearish" }) {
  const cfg = {
    bullish: { label: "W ▲", cls: "bg-green-100 text-green-700 border-green-300", tip: "Weekly timeframe is bullish (RSI>50, MACD+, above EMAs, SMA30 rising)" },
    neutral: { label: "W —", cls: "bg-amber-50  text-amber-600 border-amber-300",  tip: "Weekly timeframe is neutral — mixed signals" },
    bearish: { label: "W ▼", cls: "bg-red-50    text-red-600   border-red-200",    tip: "Weekly timeframe is bearish — consider staying out" },
  }[dir] ?? { label: "W ?", cls: "bg-gray-100 text-gray-500 border-gray-200", tip: "" };

  return (
    <span className={`group relative inline-block text-[9px] font-bold px-1.5 py-0.5 rounded border cursor-help ${cfg.cls}`}>
      {cfg.label}
      <span className="pointer-events-none absolute left-0 top-full mt-1 z-50 w-56 rounded-lg bg-gray-900 text-white text-xs p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-normal">
        {cfg.tip}
      </span>
    </span>
  );
}

// RVOL — Relative Volume (today vs 20-day avg)
// Purple ≥2× (surge), normal otherwise
export function RVOLLabel({ rvol }: { rvol: number }) {
  const color = rvol >= 2.0 ? "text-violet-600 font-semibold" : rvol >= 1.3 ? "text-gray-500" : "text-gray-400";
  return (
    <span className={`text-[10px] font-mono ${color}`}>
      {rvol.toFixed(1)}×vol
    </span>
  );
}
