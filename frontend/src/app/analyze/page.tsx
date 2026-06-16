"use client";

import { useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api, type SymbolAnalysis, type ActiveSetup, type ChecklistItem, type Warning, type TimeframeSignal } from "@/lib/api";
import { SetupBadge, ProbGradeBadge, RRBadge, StageBadge, ADNetBadge, ICSBadge, RVOLLabel } from "@/components/SetupBadge";

// ── Small reusable UI pieces ──────────────────────────────────────────────────

function Card({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-5 ${className}`}>
      {title && <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">{title}</h3>}
      {children}
    </div>
  );
}

function StatPill({ label, value, sub, color = "text-gray-800" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="flex flex-col items-center bg-gray-50 rounded-lg px-4 py-3 min-w-[80px]">
      <span className={`text-lg font-bold font-mono ${color}`}>{value}</span>
      {sub && <span className="text-[10px] text-gray-400 font-mono">{sub}</span>}
      <span className="text-[10px] text-gray-500 uppercase tracking-wide mt-0.5">{label}</span>
    </div>
  );
}

// ── Direction badge ───────────────────────────────────────────────────────────

function DirectionBadge({ direction }: { direction: string }) {
  const cfg = {
    long:    { label: "🟢 LONG BIAS",   bg: "bg-green-50  border-green-300 text-green-800" },
    neutral: { label: "⚪ NEUTRAL",     bg: "bg-gray-50   border-gray-300  text-gray-700"  },
    avoid:   { label: "🔴 AVOID LONGS", bg: "bg-red-50    border-red-300   text-red-700"   },
  }[direction] ?? { label: direction.toUpperCase(), bg: "bg-gray-50 border-gray-300 text-gray-700" };

  return (
    <span className={`inline-flex items-center px-4 py-1.5 rounded-full border font-semibold text-sm ${cfg.bg}`}>
      {cfg.label}
    </span>
  );
}

// ── Checklist row ─────────────────────────────────────────────────────────────

function CheckRow({ item }: { item: ChecklistItem }) {
  const icons = { pass: "✅", warn: "⚠️", fail: "❌", neutral: "⬜" };
  const colors = {
    pass:    "border-green-100 bg-green-50/40",
    warn:    "border-amber-100 bg-amber-50/40",
    fail:    "border-red-100   bg-red-50/40",
    neutral: "border-gray-100  bg-gray-50",
  };
  return (
    <div className={`flex items-start gap-3 px-4 py-2.5 rounded-lg border ${colors[item.status]}`}>
      <span className="text-base mt-0.5 shrink-0">{icons[item.status]}</span>
      <div>
        <span className="text-xs font-semibold text-gray-700">{item.label}</span>
        <span className="text-xs text-gray-500 ml-2">{item.detail}</span>
      </div>
    </div>
  );
}

// ── Warning row ───────────────────────────────────────────────────────────────

function WarningRow({ w }: { w: Warning }) {
  const cfg = {
    critical: { icon: "🚨", bg: "bg-red-50 border-red-200 text-red-800" },
    warning:  { icon: "⚠️", bg: "bg-amber-50 border-amber-200 text-amber-800" },
    info:     { icon: "💡", bg: "bg-blue-50 border-blue-200 text-blue-800" },
  }[w.severity] ?? { icon: "•", bg: "bg-gray-50 border-gray-200 text-gray-700" };

  return (
    <div className={`flex items-start gap-2 px-4 py-2.5 rounded-lg border text-sm ${cfg.bg}`}>
      <span className="shrink-0">{cfg.icon}</span>
      <div>
        <span className="font-semibold">{w.name}</span>
        <span className="ml-2 opacity-80">{w.detail}</span>
      </div>
    </div>
  );
}

// ── Setup card ────────────────────────────────────────────────────────────────

function SetupCard({ s, highlight = false }: { s: ActiveSetup; highlight?: boolean }) {
  const riskPct = ((s.entry - s.stop) / s.entry * 100).toFixed(1);
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-indigo-300 bg-indigo-50/50 shadow-sm" : "border-gray-200 bg-white"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <SetupBadge type={s.setup_type} />
          <span className={`text-xs px-2 py-0.5 rounded font-medium capitalize ${
            s.state === "breakout" ? "bg-green-100 text-green-700" :
            s.state === "active"   ? "bg-blue-100 text-blue-700"   :
                                     "bg-yellow-100 text-yellow-700"
          }`}>{s.state}</span>
          {highlight && <span className="text-[10px] bg-indigo-600 text-white px-2 py-0.5 rounded font-bold">BEST</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 font-mono">conf {(s.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-400 mb-0.5">Entry</div>
          <div className="font-mono font-semibold">${s.entry.toFixed(2)}</div>
        </div>
        <div className="bg-red-50 rounded p-2">
          <div className="text-gray-400 mb-0.5">Stop · Risk</div>
          <div className="font-mono text-red-600">${s.stop.toFixed(2)}</div>
          <div className="text-red-400 text-[10px]">-{riskPct}%</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-400 mb-0.5">T1</div>
          <div className="font-mono">${s.t1.toFixed(2)}</div>
        </div>
        <div className="bg-green-50 rounded p-2">
          <div className="text-gray-400 mb-0.5">T2 · R:R</div>
          <div className="font-mono text-green-700 font-semibold">${s.t2.toFixed(2)}</div>
          <div className="mt-0.5"><RRBadge rr={s.rr} /></div>
        </div>
      </div>
      {s.notes && (
        <p className="text-[11px] text-gray-500 mt-2 italic">{s.notes}</p>
      )}
    </div>
  );
}

// ── MACD indicator ────────────────────────────────────────────────────────────

function MACDIcon({ direction, expanding }: { direction: string; expanding: boolean }) {
  const bull = direction === "bullish";
  return (
    <span className={`font-semibold text-sm ${bull ? "text-green-600" : "text-red-500"}`}>
      {bull ? "▲" : "▼"} {bull ? "Bullish" : "Bearish"}{expanding ? " ↑" : " ↓"}
    </span>
  );
}

// ── RSI bar ───────────────────────────────────────────────────────────────────

function RSIBar({ rsi }: { rsi: number }) {
  const color = rsi > 70 ? "bg-red-500" : rsi > 55 ? "bg-amber-400" : rsi >= 40 ? "bg-green-500" : "bg-blue-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full relative">
        {/* Zone bands */}
        <div className="absolute h-full left-[40%] w-[25%] bg-green-100 rounded" />
        <div className="absolute h-full left-0 top-0 rounded-full overflow-hidden" style={{ width: `${rsi}%` }}>
          <div className={`h-full ${color}`} />
        </div>
      </div>
      <span className={`text-sm font-mono font-semibold w-10 text-right ${rsi > 70 ? "text-red-600" : rsi >= 40 ? "text-green-600" : "text-blue-500"}`}>
        {rsi.toFixed(0)}
      </span>
    </div>
  );
}

// ── Timeframe card ────────────────────────────────────────────────────────────

const TF_DIR_CFG = {
  bullish: { dot: "bg-green-500",  label: "Bullish",  text: "text-green-700" },
  neutral: { dot: "bg-amber-400",  label: "Neutral",  text: "text-amber-700" },
  bearish: { dot: "bg-red-500",    label: "Bearish",  text: "text-red-600"   },
};

const STAGE_LBL: Record<number, string> = {
  1: "S1 Basing", 2: "S2 Advancing", 3: "S3 Topping", 4: "S4 Declining",
};

function TFCard({ tf }: { tf: TimeframeSignal }) {
  if (tf.insufficient) {
    return (
      <div className="flex-1 bg-gray-50 rounded-xl border border-gray-200 p-4 text-center text-xs text-gray-400">
        <div className="font-semibold text-gray-500 mb-1">{tf.label}</div>
        Not enough bars ({tf.bars})
      </div>
    );
  }

  const dir = TF_DIR_CFG[tf.direction] ?? TF_DIR_CFG.neutral;
  const stageColor = { 2: "text-green-700 bg-green-50", 4: "text-red-700 bg-red-50", 1: "text-blue-700 bg-blue-50", 3: "text-amber-700 bg-amber-50" }[tf.stage] ?? "text-gray-600 bg-gray-50";

  return (
    <div className="flex-1 bg-gray-50 rounded-xl border border-gray-200 p-4 min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-gray-600 uppercase tracking-wide">{tf.label}</span>
        <span className="text-[10px] text-gray-400">{tf.bars} bars</span>
      </div>

      {/* Direction */}
      <div className={`flex items-center gap-1.5 mb-3 ${dir.text}`}>
        <span className={`inline-block w-2 h-2 rounded-full ${dir.dot}`} />
        <span className="font-semibold text-sm">{dir.label}</span>
      </div>

      {/* Stage */}
      <div className={`text-[10px] font-medium px-2 py-0.5 rounded inline-block mb-3 ${stageColor}`}>
        {tf.stage ? STAGE_LBL[tf.stage] ?? `Stage ${tf.stage}` : "Stage unknown"}
      </div>

      {/* Indicators grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <div>
          <span className="text-gray-400">RSI</span>
          <span className={`ml-1.5 font-mono font-semibold ${tf.rsi > 70 ? "text-red-600" : tf.rsi >= 50 ? "text-green-600" : "text-gray-600"}`}>
            {tf.rsi.toFixed(0)}
          </span>
        </div>
        <div>
          <span className="text-gray-400">MACD</span>
          <span className={`ml-1.5 font-semibold ${tf.macd === "bullish" ? "text-green-600" : "text-red-500"}`}>
            {tf.macd === "bullish" ? "▲" : "▼"}
          </span>
        </div>
        <div className="col-span-2">
          <span className="text-gray-400">{tf.key_ma_label}</span>
          <span className="ml-1.5 font-mono">{tf.key_ma !== null ? `$${tf.key_ma.toFixed(2)}` : "—"}</span>
          {tf.key_ma !== null && (
            <span className={`ml-1 text-[10px] font-semibold ${tf.price_vs_ema_pct >= 0 ? "text-green-600" : "text-red-500"}`}>
              ({tf.price_vs_ema_pct >= 0 ? "+" : ""}{tf.price_vs_ema_pct.toFixed(1)}% vs EMA)
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── The inner page (uses useSearchParams) ─────────────────────────────────────

function AnalyzeInner() {
  const searchParams = useSearchParams();
  const router       = useRouter();

  const [input,    setInput]    = useState(searchParams.get("symbol") ?? "");
  const [data,     setData]     = useState<SymbolAnalysis | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  const runAnalysis = useCallback(async (sym: string) => {
    if (!sym.trim()) return;
    const s = sym.trim().toUpperCase();
    setLoading(true);
    setError("");
    router.replace(`/analyze?symbol=${s}`, { scroll: false });
    try {
      const result = await api.analyze(s);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [router]);

  // Auto-run if symbol in URL on mount
  const [autoRan, setAutoRan] = useState(false);
  if (!autoRan) {
    const sym = searchParams.get("symbol");
    if (sym) { setAutoRan(true); runAnalysis(sym); }
    else setAutoRan(true);
  }

  const stageLabel: Record<number, string> = {
    1: "S1 — Basing", 2: "S2 — Advancing", 3: "S3 — Topping", 4: "S4 — Declining",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Stock Analyzer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Full technical analysis for any US stock — all 6 setups, signals, checklist, and score breakdown.
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <div className="flex gap-3 max-w-md">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && runAnalysis(input)}
            placeholder="Enter ticker — e.g. NVDA"
            className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm font-mono uppercase focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
          />
          <button
            onClick={() => runAnalysis(input)}
            disabled={loading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-lg px-5 py-2.5 text-sm transition-colors"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Analysis takes 3–5 s — fetching up to 2 years of daily bars.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="flex items-center justify-center h-48 text-gray-400">
          <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Fetching data and running all 6 detectors…
        </div>
      )}

      {/* ── Results ── */}
      {data && !loading && (
        <div className="space-y-5">

          {/* ── Row 1: Hero metrics ── */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* Price card */}
            <Card className="md:col-span-1">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-3xl font-bold font-mono text-gray-900">{data.symbol}</p>
                  <p className="text-2xl font-bold font-mono text-gray-800 mt-1">${data.price.toFixed(2)}</p>
                  <span className={`text-sm font-semibold ${data.pct_change >= 0 ? "text-green-600" : "text-red-500"}`}>
                    {data.pct_change >= 0 ? "+" : ""}{data.pct_change.toFixed(2)}% today
                  </span>
                </div>
                <div className="text-right space-y-1.5">
                  <RVOLLabel rvol={data.rvol} />
                  <div className="block text-[10px] text-gray-400 font-mono">{data.vol_ratio_50d.toFixed(1)}× 50d avg</div>
                </div>
              </div>
            </Card>

            {/* P Score card (the single score) */}
            <Card className="md:col-span-1">

              {/* ── Score header: P Score + Qullamaggie setup status ── */}
              <div className="flex gap-4 mb-3">

                {/* P Score — the single probability score */}
                <div className="flex-1 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2.5 text-center">
                  <div className="text-[9px] font-semibold text-teal-500 uppercase tracking-wide mb-0.5">P Score</div>
                  <div className="flex items-baseline justify-center gap-1.5">
                    <span className="text-2xl font-bold font-mono text-teal-700">{(data.prob_score ?? 0).toFixed(0)}</span>
                    <span className="text-xs text-teal-400">/100</span>
                  </div>
                  <div className="mt-1">
                    <ProbGradeBadge grade={data.prob_grade ?? "D"} />
                    <div className="text-[9px] text-teal-400 mt-0.5">Signal voting grade</div>
                  </div>
                </div>

                {/* Qullamaggie setup status — does a Q setup fire? */}
                <div className={`flex-1 rounded-lg px-3 py-2.5 text-center border ${
                  data.best_setup ? "bg-purple-50 border-purple-200" : "bg-gray-50 border-gray-200"
                }`}>
                  <div className="text-[9px] font-semibold text-gray-400 uppercase tracking-wide mb-0.5">Qullamaggie Setup</div>
                  {data.best_setup ? (
                    <>
                      <div className="flex items-center justify-center gap-1 mt-1">
                        <SetupBadge type={data.best_setup.setup_type} />
                        <span className="text-[10px] text-purple-600 font-semibold capitalize">{data.best_setup.state}</span>
                      </div>
                      <div className="text-[9px] text-gray-500 mt-1">
                        {data.active_setups.length > 1
                          ? `+${data.active_setups.length - 1} more firing`
                          : "fires now"}
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="text-base font-bold text-gray-400 mt-1">None</div>
                      <div className="text-[9px] text-gray-400 mt-0.5">no setup firing</div>
                    </>
                  )}
                </div>
              </div>

              {/* RS + Stage context pills */}
              <div className="flex items-center gap-2 mb-3">
                <div className="text-center bg-gray-50 rounded px-3 py-1.5 flex-1">
                  <div className="text-sm font-mono font-semibold text-gray-700">{data.rs_score.toFixed(0)}</div>
                  <div className="text-[10px] text-gray-400">{data.rs_label}</div>
                </div>
                <div className="text-center bg-gray-50 rounded px-3 py-1.5 flex-1">
                  <StageBadge stage={data.weinstein_stage} />
                  <div className="text-[10px] text-gray-400 mt-0.5">{stageLabel[data.weinstein_stage] ?? "Unknown"}</div>
                </div>
                {data.prob_regime && (
                  <div className="text-center bg-gray-50 rounded px-3 py-1.5 flex-1">
                    <div className="text-[10px] font-semibold text-gray-600 capitalize">{data.prob_regime}</div>
                    <div className="text-[9px] text-gray-400">regime</div>
                  </div>
                )}
              </div>

              {/* P Score breakdown — per-signal contribution bars */}
              {(data.prob_components ?? []).length > 0 && (() => {
                const comps = data.prob_components;
                const maxContrib = Math.max(...comps.map((c) => c.contribution), 0.01);
                return (
                  <div className="border-t border-gray-100 pt-2.5 space-y-1.5 mt-1">
                    <div className="text-[9px] font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      P Score breakdown
                    </div>
                    {comps.map((c) => {
                      const pct  = Math.min(100, (c.contribution / maxContrib) * 100);
                      const bull = c.direction === "bullish";
                      const fill = bull ? "bg-teal-400" : "bg-red-300";
                      // Compact source label
                      const shortSrc =
                        c.source === "ADNet"     ? "A/D"    :
                        c.source === "TrendTmpl" ? "Minv"   :
                        c.source === "WeeklyTF"  ? "Weekly" :
                        c.source;
                      return (
                        <div key={c.source} className="flex items-center gap-2 group relative cursor-help">
                          {/* Direction arrow + name */}
                          <div className="w-14 text-[10px] text-gray-500 shrink-0 flex items-center gap-0.5">
                            <span className={bull ? "text-teal-500" : "text-red-400"}>
                              {bull ? "▲" : "▼"}
                            </span>
                            <span>{shortSrc}</span>
                          </div>
                          {/* Bar */}
                          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full transition-all ${fill}`} style={{ width: `${pct}%` }} />
                          </div>
                          {/* Contribution number */}
                          <div className="w-10 text-right text-[10px] font-mono text-gray-500 shrink-0">
                            {c.contribution.toFixed(2)}
                          </div>
                          {/* Hover tooltip — full breakdown */}
                          <span className="pointer-events-none absolute left-0 bottom-full mb-1 z-50 w-64 rounded-lg bg-gray-900 text-white text-[10px] p-2 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity shadow-xl font-mono">
                            {(c.source === "TrendTmpl" ? "Minervini Trend Template"
                              : c.source === "WeeklyTF" ? "Weekly timeframe adjustment"
                              : c.source)} ({c.direction})<br />
                            str={c.strength.toFixed(2)} × w={c.weight} × acc={c.accuracy} × ×{c.regime_mult}<br />
                            = {c.contribution.toFixed(3)}
                            {c.detail && <><br />{c.detail}</>}
                          </span>
                        </div>
                      );
                    })}
                    {/* Agreement + regime meta */}
                    <div className="flex gap-3 pt-1 text-[9px] text-gray-400">
                      <span>Agreement: <span className="font-semibold text-gray-500">{((data.prob_agreement ?? 0) * 100).toFixed(0)}%</span></span>
                      <span>Regime: <span className="font-semibold text-gray-500 capitalize">{data.prob_regime ?? "—"}</span></span>
                      {(data.prob_penalty ?? 0) > 0 && (
                        <span className="text-orange-500">Penalty: −{data.prob_penalty.toFixed(1)}pts</span>
                      )}
                    </div>
                    {(data.prob_penalty_notes ?? []).length > 0 && (
                      <div className="text-[9px] text-orange-500 space-y-0.5">
                        {data.prob_penalty_notes.map((n, i) => <div key={i}>⚠ {n}</div>)}
                      </div>
                    )}
                  </div>
                );
              })()}
            </Card>

            {/* Direction + key technicals */}
            <Card className="md:col-span-1">
              <div className="space-y-2">
                <DirectionBadge direction={data.direction} />
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <div className="text-[10px] text-gray-400 uppercase">RSI 14</div>
                    <RSIBar rsi={data.rsi} />
                  </div>
                  <div>
                    <div className="text-[10px] text-gray-400 uppercase mb-0.5">MACD</div>
                    <MACDIcon direction={data.macd_direction} expanding={data.macd_expanding} />
                  </div>
                  <div>
                    <div className="text-[10px] text-gray-400 uppercase">ADX</div>
                    <span className={`text-sm font-mono font-semibold ${data.adx >= 30 ? "text-green-600" : data.adx >= 20 ? "text-amber-600" : "text-gray-500"}`}>
                      {data.adx.toFixed(0)} {data.adx >= 30 ? "— trending" : data.adx >= 20 ? "— developing" : "— weak"}
                    </span>
                  </div>
                  <div>
                    <div className="text-[10px] text-gray-400 uppercase">EMA21</div>
                    <span className={`text-sm font-mono font-semibold ${data.ma_stack.price_vs_ema21_pct >= 0 ? "text-green-600" : "text-red-500"}`}>
                      {data.ma_stack.price_vs_ema21_pct >= 0 ? "+" : ""}{data.ma_stack.price_vs_ema21_pct.toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-gray-400 ml-1">${data.ma_stack.ema21.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* ── Row 2: MA stack + Institutional ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* MA Stack */}
            <Card title="MA Stack">
              <div className="space-y-2">
                <div className={`text-sm font-semibold px-3 py-2 rounded-lg ${
                  data.ma_stack.stack === "full_bull"    ? "bg-green-50 text-green-800 border border-green-200" :
                  data.ma_stack.stack === "partial_bull" ? "bg-amber-50 text-amber-800 border border-amber-200" :
                  data.ma_stack.stack === "bear"         ? "bg-red-50   text-red-800   border border-red-200"   :
                                                           "bg-gray-50  text-gray-700  border border-gray-200"
                }`}>
                  {data.ma_stack.detail}
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs mt-2">
                  {[
                    { label: "EMA21", val: data.ma_stack.ema21, rising: data.ma_stack.ema21_rising },
                    { label: "EMA50", val: data.ma_stack.ema50, rising: data.ma_stack.ema50_rising },
                    { label: "SMA150", val: data.ma_stack.sma150, rising: null },
                  ].map(({ label, val, rising }) => (
                    <div key={label} className="bg-gray-50 rounded p-2">
                      <div className="text-gray-400">{label}</div>
                      <div className="font-mono font-semibold">{val ? `$${val.toFixed(2)}` : "—"}</div>
                      {rising !== null && (
                        <div className={`text-[10px] ${rising ? "text-green-600" : "text-red-400"}`}>
                          {rising ? "↑ rising" : "↓ flat/falling"}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            {/* Institutional Flow */}
            <Card title="Institutional Flow">
              <div className="flex items-center gap-6 mb-3">
                <div className="text-center">
                  <div className="text-xs text-gray-400 mb-1">A/D Net (25d)</div>
                  <ADNetBadge net={data.ad_net} />
                  <div className="text-[10px] text-gray-400 mt-1">
                    {data.ad_net > 0 ? "accumulation" : data.ad_net < 0 ? "distribution" : "neutral"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-gray-400 mb-1">ICS</div>
                  <ICSBadge score={data.isc_score} />
                  <div className="text-[10px] text-gray-400 mt-1">
                    {data.isc_score >= 75 ? "strong acc." : data.isc_score >= 40 ? "mixed" : "distribution"}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-xs text-gray-500 leading-relaxed">
                    ICS combines OBV trend, Chaikin Money Flow, A/D line slope, and MFI.
                    A/D Net counts discrete accumulation/distribution days (O&apos;Neill method).
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* ── Row 3: Timeframe Alignment ── */}
          <Card title="Timeframe Alignment">
            {/* Overall label + score */}
            {(() => {
              const mtf = data.timeframe_alignment;
              const alignCfg: Record<string, { bar: string; text: string; dot: string }> = {
                full_bull:   { bar: "bg-green-100 border-green-300 text-green-800",   text: "text-green-700",  dot: "bg-green-500"  },
                mostly_bull: { bar: "bg-emerald-50 border-emerald-300 text-emerald-800", text: "text-emerald-600", dot: "bg-emerald-400" },
                mixed:       { bar: "bg-amber-50 border-amber-300 text-amber-800",    text: "text-amber-700",  dot: "bg-amber-400"  },
                mostly_bear: { bar: "bg-orange-50 border-orange-300 text-orange-800", text: "text-orange-600", dot: "bg-orange-500"  },
                full_bear:   { bar: "bg-red-50 border-red-300 text-red-800",          text: "text-red-600",    dot: "bg-red-500"    },
              };
              const cfg = alignCfg[mtf.alignment] ?? alignCfg.mixed;
              const scoreEmoji = mtf.score >= 2 ? "🟢" : mtf.score <= -2 ? "🔴" : "🟡";

              return (
                <>
                  <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium mb-4 ${cfg.bar}`}>
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${cfg.dot} shrink-0`} />
                    <span>{scoreEmoji} {mtf.label}</span>
                    <span className="ml-auto text-[11px] opacity-70 font-mono">score {mtf.score > 0 ? "+" : ""}{mtf.score} / 3</span>
                  </div>
                  <div className="flex gap-3">
                    <TFCard tf={mtf.daily} />
                    <TFCard tf={mtf.weekly} />
                    <TFCard tf={mtf.monthly} />
                  </div>
                  <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
                    <strong>How:</strong> Daily uses EMA21/50 + SMA150. Weekly resamples daily bars → exact Weinstein 30-week SMA.
                    Monthly resamples to monthly bars → 12-month SMA. Direction per TF: bullish = 4+/5 signals; bearish = 1−/5.
                    No extra API calls — all derived from the same 2-year daily OHLCV fetch.
                  </p>
                </>
              );
            })()}
          </Card>

          {/* ── Row 3b: Fibonacci ── */}
          {data.fibonacci && (() => {
            const f = data.fibonacci!;
            const up = f.direction === "uptrend";
            return (
              <Card title="Fibonacci">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600 mb-3">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${up ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {up ? "Uptrend leg" : "Downtrend leg"}
                  </span>
                  <span className="font-mono">
                    ${f.swing_low.toFixed(2)} <span className="text-gray-400">({f.swing_low_date})</span>
                    {" → "}${f.swing_high.toFixed(2)} <span className="text-gray-400">({f.swing_high_date})</span>
                  </span>
                  <span className="text-gray-300">·</span>
                  <span>retraced <strong className="text-gray-700">{f.retrace_depth_pct.toFixed(1)}%</strong> of the leg</span>
                  {f.in_golden_pocket && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">in golden pocket</span>
                  )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Retracement ladder */}
                  <div>
                    <p className="text-[11px] font-semibold text-gray-500 mb-1.5">Retracement ladder (pullback support)</p>
                    <div className="space-y-0.5">
                      <div className="flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded bg-gray-50 text-gray-500">
                        <span>swing high · 0%</span><span>${f.swing_high.toFixed(2)}</span>
                      </div>
                      {f.retracements.map((r) => {
                        const isGolden  = r.pct === 61.8;
                        const isNearest = Math.abs(r.price - f.nearest_level.price) < 0.001;
                        return (
                          <div key={r.pct} className={`flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded border ${isGolden ? "bg-amber-50 border-amber-200" : "border-transparent"} ${isNearest ? "ring-1 ring-indigo-300" : ""}`}>
                            <span className={isGolden ? "text-amber-800 font-semibold" : "text-gray-600"}>
                              {r.pct.toFixed(1)}%{isGolden ? " · golden pocket" : ""}
                            </span>
                            <span className="flex items-center gap-2">
                              {isNearest && <span className="text-[9px] text-indigo-600 font-sans font-semibold">price ${f.price.toFixed(2)}</span>}
                              <span className={isGolden ? "text-amber-800 font-semibold" : "text-gray-800"}>${r.price.toFixed(2)}</span>
                            </span>
                          </div>
                        );
                      })}
                      <div className="flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded bg-gray-50 text-gray-500">
                        <span>swing low · 100%</span><span>${f.swing_low.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Extension targets */}
                  <div>
                    <p className="text-[11px] font-semibold text-gray-500 mb-1.5">Extension targets (beyond the swing)</p>
                    <div className="space-y-0.5">
                      {f.extensions.map((e) => (
                        <div key={e.pct} className="flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded">
                          <span className="text-gray-600">{e.pct.toFixed(1)}%</span>
                          <span className="text-green-700 font-semibold">${e.price.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 text-[11px] text-gray-600 bg-gray-50 rounded px-2 py-1.5 leading-relaxed">
                      Golden pocket: <strong className="text-amber-800">${f.golden_pocket.low.toFixed(2)}–${f.golden_pocket.high.toFixed(2)}</strong>
                      <span className="text-gray-400"> · nearest: {f.nearest_level.name} ${f.nearest_level.price.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
                  <strong>How:</strong> anchored to the dominant swing in the last {f.lookback_bars} bars (absolute high &amp; low, ordered by time).
                  Retracements = high − range × ratio; extensions project the leg beyond the swing. The <strong>golden pocket</strong> (61.8–65%) is
                  the highest-probability reaction band. A level is confluence, <strong>not a trigger</strong> — wait for a reversal candle or an
                  S/R / moving-average overlap before acting.
                </p>
              </Card>
            );
          })()}

          {/* ── Row 3c: Options (leading context) ── */}
          {data.options && (() => {
            const o = data.options!;
            const leanCfg = {
              bullish: { c: "bg-green-100 text-green-700", t: "Bullish positioning" },
              bearish: { c: "bg-red-100 text-red-700",     t: "Bearish positioning" },
              neutral: { c: "bg-gray-100 text-gray-600",   t: "Neutral positioning" },
            }[o.lean];
            const stat = (label: string, value: string, sub?: string, tone?: string, help?: string) => (
              <div key={label} title={help} className={`bg-gray-50 rounded-lg px-3 py-2 ${help ? "cursor-help" : ""}`}>
                <div className="text-[10px] text-gray-500 uppercase tracking-wide flex items-center gap-1">
                  {label}{help && <span className="text-gray-400 normal-case" aria-hidden="true">ⓘ</span>}
                </div>
                <div className={`text-sm font-mono font-semibold ${tone ?? "text-gray-800"}`}>{value}</div>
                {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
              </div>
            );
            return (
              <Card title="Options (leading)">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600 mb-3">
                  <span title="Overall options positioning lean, synthesized from skew + put/call flow (and ACI where available). Context & confluence — NOT a standalone trigger; contrarian at extremes. Confirm direction with price + the firing setup." className={`px-2 py-0.5 rounded-full text-[10px] font-semibold cursor-help ${leanCfg.c}`}>{leanCfg.t}</span>
                  <span title="Skips current-week weeklies (<7 DTE); anchored to the ~30-day monthly horizon for swing-relevant IV & expected move">expiry <strong className="font-mono">{o.nearest_expiry}</strong> · {o.dte}d (swing horizon)</span>
                  {o.unusual_activity && <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">unusual activity</span>}
                  <span className="text-gray-300">·</span>
                  <span className="text-gray-400">{o.expiries_used} expiries · {o.source}</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {stat("Expected move",
                        o.expected_move_pct != null ? `±${o.expected_move_pct}%` : "—",
                        o.expected_move_abs != null ? `±$${o.expected_move_abs} by expiry` : undefined,
                        "text-indigo-700",
                        "The ± range the options market prices in by the anchor expiry (the at-the-money straddle). A target or stop outside this band is unlikely to be reached by then — use it to size a swing trade realistically.")}
                  {stat("ATM IV", o.atm_iv != null ? `${o.atm_iv}%` : "—", o.hv != null ? `vs ${o.hv}% realised` : "implied volatility", undefined,
                        "Implied volatility: how big a move the market expects, annualised. A high number alone doesn't mean 'expensive' — judge rich vs cheap with IV Rank (next), which compares it to how the stock actually moves.")}
                  {stat("IV Rank (IV/HV)",
                        o.iv_hv != null ? `${o.iv_hv}×` : "—",
                        o.iv_state ? (o.iv_state === "rich" ? "options rich" : o.iv_state === "cheap" ? "options cheap" : "fair value") : undefined,
                        o.iv_state == null ? undefined : o.iv_state === "rich" ? "text-red-600" : o.iv_state === "cheap" ? "text-green-700" : "text-gray-800",
                        "Implied ÷ 30-day realised volatility (IBKR's IV-Rank definition). >1.2 = options rich (market pricing more than the stock actually moves — a fear / pre-catalyst premium); <0.8 = cheap / complacent; ~1 = fair value.")}
                  {stat("Skew (P−C IV)",
                        o.skew != null ? `${o.skew > 0 ? "+" : ""}${o.skew} pts` : "—",
                        o.skew == null ? undefined : o.skew < 0 ? "call demand" : o.skew > 3 ? "downside fear" : "balanced",
                        o.skew == null ? undefined : o.skew < 0 ? "text-green-700" : o.skew > 3 ? "text-red-600" : "text-gray-800",
                        "Out-of-the-money put IV minus call IV. Positive = traders paying up for downside protection (fear); negative = paying up for upside calls (bullish demand). The cleaner directional tell when the chain is liquid.")}
                  {stat("P/C volume", o.put_call_vol != null ? o.put_call_vol.toFixed(2) : "—",
                        `${o.call_volume.toLocaleString()}C / ${o.put_volume.toLocaleString()}P`, undefined,
                        "Put volume ÷ call volume (today's flow). <0.7 = call-heavy (bullish lean); >1.2 = put-heavy. Sentiment gauge — contrarian at extremes.")}
                  {stat("P/C open int.", o.put_call_oi != null ? o.put_call_oi.toFixed(2) : "—",
                        `${o.call_oi.toLocaleString()}C / ${o.put_oi.toLocaleString()}P`, undefined,
                        "Put ÷ call open interest — the resting positioning that's already on the book. Slower-moving and less noisy than the volume ratio. (Unavailable on the Alpaca live feed.)")}
                  {stat("Volume / OI", o.vol_oi_ratio != null ? o.vol_oi_ratio.toFixed(2) : "—",
                        o.unusual_activity ? "fresh positioning" : "normal",
                        o.unusual_activity ? "text-amber-700" : undefined,
                        "Today's total option volume ÷ open interest. ≥0.5 flags fresh positioning ('unusual activity') being put on today, rather than old resting bets. (Needs OI — unavailable on the Alpaca live feed.)")}
                  {stat("Max pain",
                        o.max_pain != null ? `$${o.max_pain.toFixed(2)}` : "—",
                        o.max_pain_dist_pct != null ? `${o.max_pain_dist_pct > 0 ? "+" : ""}${o.max_pain_dist_pct}% from price` : "pin price",
                        o.max_pain_dist_pct == null ? undefined : Math.abs(o.max_pain_dist_pct) <= 3 ? "text-amber-700" : "text-gray-800",
                        "The strike where option holders lose the most / writers pay the least — price tends to gravitate (pin) toward it into expiry. A short-horizon magnet; weak for multi-week swings. (Needs OI — unavailable on the Alpaca live feed.)")}
                  {stat("ACI (delta-adj OI)",
                        o.aci_score != null ? `${o.aci_score > 0 ? "+" : ""}${o.aci_score}` : "—",
                        o.aci_score == null ? undefined : `${o.aci_label} · ${o.bull_daoi.toLocaleString()}↑ / ${o.bear_daoi.toLocaleString()}↓`,
                        o.aci_label === "bullish" ? "text-green-700" : o.aci_label === "bearish" ? "text-red-600" : "text-gray-800",
                        "Accumulation lean: call-side minus put-side open interest, each weighted by Black-Scholes delta (so a far-OTM lottery strike counts far less than an at-the-money one). +1 = fully bullish positioning, −1 = bearish. (Needs OI — unavailable on the Alpaca live feed.)")}
                </div>

                {(o.oi_support.length > 0 || o.oi_resistance.length > 0) && (
                  <div className="mt-2 text-[11px] text-gray-600 bg-gray-50 rounded px-2 py-1.5 leading-relaxed cursor-help"
                       title="Strikes carrying the largest open interest: call walls above price tend to act as resistance, put walls below as support (where positioning — and dealer hedging — clusters).">
                    <span className="font-semibold text-gray-500">OI levels:</span>{" "}
                    {o.oi_resistance.length > 0 && (
                      <span>resistance (call walls) <span className="font-mono text-red-600">
                        {o.oi_resistance.map((l) => `$${l.strike}`).join(", ")}</span></span>
                    )}
                    {o.oi_resistance.length > 0 && o.oi_support.length > 0 && <span className="text-gray-300"> · </span>}
                    {o.oi_support.length > 0 && (
                      <span>support (put walls) <span className="font-mono text-green-700">
                        {o.oi_support.map((l) => `$${l.strike}`).join(", ")}</span></span>
                    )}
                  </div>
                )}

                <div className="mt-3 bg-indigo-50/60 border border-indigo-100 rounded-lg px-3 py-2.5 text-[12.5px] text-gray-700 leading-relaxed">
                  <span className="font-semibold text-indigo-700">What this is saying — </span>
                  {o.interpretation ?? o.tell}
                </div>
                <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
                  <strong>Why it&apos;s leading:</strong> options price future <em>expectations</em>, not past action. The <strong>expected move</strong>
                  sizes catalyst targets/stops; <strong>skew</strong> shows hedging (puts) vs demand (calls); <strong>P/C</strong> is sentiment
                  (contrarian at extremes); <strong>vol÷OI</strong> flags fresh positioning. Context &amp; confluence — <strong>not a P Score input</strong>.
                </p>
              </Card>
            );
          })()}

          {/* ── Row 4: Active setups ── */}
          <Card title={`Active Setups (${data.active_setups.length} firing)`}>
            {data.active_setups.length === 0 ? (
              <p className="text-sm text-gray-400">No setups currently detected for {data.symbol}. The stock may not meet any pattern criteria right now.</p>
            ) : (
              <div className="space-y-3">
                {data.active_setups
                  .sort((a, b) => b.confidence - a.confidence)
                  .map((s, i) => (
                    <SetupCard key={s.setup_type} s={s} highlight={i === 0 && data.active_setups.length > 1} />
                  ))}
              </div>
            )}
            {data.active_setups.length === 0 && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-500">
                <strong>Setup detector legend:</strong> EP (catalyst surge), TB (tight base breakout), VCP (volatility contraction), WYS (Wyckoff spring), PP (pocket pivot), PULL (EMA21 pullback), FBD (failed breakdown)
              </div>
            )}
          </Card>

          {/* ── Row 4b: Minervini Trend Template ── */}
          {data.trend_template && data.trend_template.total > 0 && (
            <Card title={`Minervini Trend Template (${data.trend_template.passed}/${data.trend_template.total})`}>
              <p className="text-xs text-gray-500 mb-3">
                Mark Minervini&apos;s 8-point SEPA leadership filter. A full pass = textbook market-leader structure.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {data.trend_template.criteria.map((c) => (
                  <div
                    key={c.label}
                    className={`flex items-start gap-2 rounded-lg border px-2.5 py-1.5 ${
                      c.met ? "border-green-200 bg-green-50/60" : "border-red-200 bg-red-50/50"
                    }`}
                  >
                    <span className={`text-sm leading-none mt-0.5 ${c.met ? "text-green-600" : "text-red-500"}`}>
                      {c.met ? "✓" : "✗"}
                    </span>
                    <div className="min-w-0">
                      <div className={`text-xs font-medium ${c.met ? "text-gray-700" : "text-gray-600"}`}>{c.label}</div>
                      <div className="text-[10px] text-gray-400 font-mono truncate">{c.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-gray-400 mt-3">
                Contributes to the P Score as the <span className="font-semibold text-teal-600">Minv</span> signal.{" "}
                <a href="/scoring#pscore-signals" className="text-indigo-400 hover:underline">Scoring docs →</a>
              </p>
            </Card>
          )}

          {/* ── Row 5: Checklist + Warnings ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <Card title="Signal Checklist">
              <div className="space-y-1.5">
                {data.checklist.map((item) => (
                  <CheckRow key={item.label} item={item} />
                ))}
              </div>
            </Card>

            <div className="space-y-4">

              {/* Warnings */}
              {data.warnings.length > 0 && (
                <Card title="Early Warnings">
                  <div className="space-y-1.5">
                    {data.warnings.map((w, i) => (
                      <WarningRow key={i} w={w} />
                    ))}
                  </div>
                </Card>
              )}

              {data.warnings.length === 0 && (
                <Card title="Early Warnings">
                  <p className="text-sm text-gray-400">✅ No early warnings — clean technical picture.</p>
                </Card>
              )}
            </div>
          </div>

          {/* ── Row 6: Key stats ── */}
          <Card title="Key Metrics">
            <div className="flex flex-wrap gap-3">
              <StatPill label="RSI" value={data.rsi.toFixed(0)}
                color={data.rsi > 70 ? "text-red-600" : data.rsi >= 40 ? "text-green-600" : "text-blue-500"} />
              <StatPill label="ADX" value={data.adx.toFixed(0)} sub={data.adx >= 30 ? "trending" : "weak"}
                color={data.adx >= 30 ? "text-green-600" : "text-gray-500"} />
              <StatPill label="RVOL" value={`${data.rvol.toFixed(1)}×`}
                color={data.rvol >= 2 ? "text-violet-600" : "text-gray-700"} />
              <StatPill label="50d Vol" value={`${data.vol_ratio_50d.toFixed(1)}×`} />
              <StatPill label="RS Score" value={data.rs_score.toFixed(0)} sub={data.rs_label}
                color={data.rs_score >= 75 ? "text-green-600" : data.rs_score >= 50 ? "text-amber-600" : "text-red-500"} />
              <StatPill label="ICS" value={data.isc_score.toFixed(0)}
                color={data.isc_score >= 75 ? "text-green-600" : data.isc_score >= 40 ? "text-amber-600" : "text-red-500"} />
              <StatPill label="A/D Net" value={data.ad_net > 0 ? `+${data.ad_net}` : String(data.ad_net)}
                color={data.ad_net > 0 ? "text-green-600" : data.ad_net < 0 ? "text-red-500" : "text-gray-500"} />
              {data.ma_stack.sma150 && (
                <StatPill label="SMA150" value={`$${data.ma_stack.sma150.toFixed(0)}`} />
              )}
            </div>
          </Card>

        </div>
      )}

      {/* Empty state */}
      {!data && !loading && !error && (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <p className="text-lg font-medium">Enter a ticker to begin</p>
          <p className="text-sm mt-1">Try NVDA, AAPL, META, or any US stock symbol.</p>
        </div>
      )}
    </div>
  );
}

// ── Page export (wraps inner in Suspense for useSearchParams) ─────────────────

export default function AnalyzePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-48 text-gray-400">Loading…</div>
    }>
      <AnalyzeInner />
    </Suspense>
  );
}
