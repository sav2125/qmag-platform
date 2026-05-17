const BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "https://qmag-platform.onrender.com"
    : "http://localhost:8000");

export interface Setup {
  symbol: string;
  setup_type: "EP" | "TB" | "PP" | "PULL" | "FBD" | "WYS";
  state: string;
  entry: number;
  stop: number;
  t1: number;
  t2: number;
  rr: number;
  confidence: number;
  grade: "A" | "B" | "C" | "D";
  rs_score: number;
  rs_label: string;
  price: number;
  pct_change: number;
  notes: string;
  meta: Record<string, unknown>;
  weinstein_stage: number;    // 1-4; 0 = insufficient data
  ad_net: number;             // O'Neill A/D net days (+ = accumulation)
  composite_score: number;    // Unified 0-100: pattern quality + RS + stage + A/D
  rvol: number;               // Relative Volume: today / 20-day avg
  isc_score: number;          // Institutional Composite Score: OBV+CMF+A/D+MFI → 0-100
}

export interface ScanParams {
  universe?: string;
  setup?: string | null;
  min_rs?: number;
  min_score?: number;
  top?: number;
  min_adr?: number;
  min_pct_change?: number;
  above_ema21?: boolean;
  above_ema50?: boolean;
  max_base_bars?: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  scan: (p: ScanParams = {}) => {
    const q = new URLSearchParams();
    if (p.universe) q.set("universe", p.universe);
    if (p.setup) q.set("setup", p.setup);
    if (p.min_rs != null) q.set("min_rs", String(p.min_rs));
    if (p.min_score != null) q.set("min_score", String(p.min_score));
    if (p.top != null) q.set("top", String(p.top));
    if (p.min_adr != null && p.min_adr > 0) q.set("min_adr", String(p.min_adr));
    if (p.min_pct_change != null && p.min_pct_change > 0) q.set("min_pct_change", String(p.min_pct_change));
    if (p.above_ema21) q.set("above_ema21", "true");
    if (p.above_ema50) q.set("above_ema50", "true");
    if (p.max_base_bars != null) q.set("max_base_bars", String(p.max_base_bars));
    return req<Setup[]>(`/scan?${q}`);
  },

  getWatchlist: () => req<{ symbols: string[] }>("/watchlist"),
  addToWatchlist: (symbol: string) =>
    req<{ symbols: string[] }>("/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol }),
    }),
  removeFromWatchlist: (symbol: string) =>
    req<{ symbols: string[] }>(`/watchlist/${symbol}`, { method: "DELETE" }),

  sendDigest: (params: { universe?: string; setup?: string | null; min_rs?: number; top?: number }) =>
    req<{ sent: boolean; setups: number; to: string }>("/notify/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }),

  testEmail: () =>
    req<{ sent: boolean; to: string }>("/notify/test", { method: "POST" }),

  analyze: (symbol: string) =>
    req<SymbolAnalysis>(`/analyze/${encodeURIComponent(symbol.toUpperCase())}`),
};

// ── Analyze types ─────────────────────────────────────────────────────────────

export interface ChecklistItem {
  label:  string;
  status: "pass" | "warn" | "fail" | "neutral";
  detail: string;
}

export interface Warning {
  name:     string;
  severity: "info" | "warning" | "critical";
  detail:   string;
}

export interface ActiveSetup {
  setup_type:      string;
  state:           string;
  entry:           number;
  stop:            number;
  t1:              number;
  t2:              number;
  rr:              number;
  risk_pct:        number;
  confidence:      number;
  composite_score: number;
  grade:           string;
  notes:           string;
}

export interface MAStack {
  stack:               string;
  detail:              string;
  price_vs_ema21_pct:  number;
  price_vs_ema50_pct:  number;
  ema21_rising:        boolean;
  ema50_rising:        boolean;
  ema21:               number;
  ema50:               number;
  sma150:              number | null;
}

export interface ScoreBreakdown {
  pattern: { pts: number; max: number; label: string };
  rs:      { pts: number; max: number; label: string };
  stage:   { pts: number; max: number; label: string };
  ad:      { pts: number; max: number; label: string };
  total:   number;
}

// ── Multi-timeframe types ──────────────────────────────────────────────────────

export interface TimeframeSignal {
  label:            "Daily" | "Weekly" | "Monthly";
  bars:             number;
  direction:        "bullish" | "neutral" | "bearish";
  stage:            number;           // 0 = insufficient data
  rsi:              number;
  macd:             "bullish" | "bearish";
  ema_fast:         number;
  ema_slow:         number;
  price_vs_ema_pct: number;
  key_ma:           number | null;    // SMA150 / SMA30 / SMA12
  key_ma_label:     string;           // "SMA150" | "SMA30" | "SMA12"
  insufficient?:    true;
}

export interface MTFAlignment {
  alignment: "full_bull" | "mostly_bull" | "mixed" | "mostly_bear" | "full_bear";
  score:     number;    // -3 … +3
  label:     string;
  daily:     TimeframeSignal;
  weekly:    TimeframeSignal;
  monthly:   TimeframeSignal;
}

export interface SymbolAnalysis {
  symbol:         string;
  price:          number;
  pct_change:     number;
  rvol:           number;
  vol_ratio_50d:  number;

  composite_score:  number;
  grade:            string;
  direction:        "long" | "neutral" | "avoid";
  rs_score:         number;
  rs_label:         string;
  weinstein_stage:  number;

  rsi:            number;
  adx:            number;
  macd_histogram: number;
  macd_direction: "bullish" | "bearish";
  macd_expanding: boolean;

  ma_stack: MAStack;

  ad_net:    number;
  isc_score: number;

  overextension_penalty: number;

  best_setup:    ActiveSetup | null;
  active_setups: ActiveSetup[];

  checklist:          ChecklistItem[];
  warnings:           Warning[];
  score_breakdown:    ScoreBreakdown;
  timeframe_alignment: MTFAlignment;
}
