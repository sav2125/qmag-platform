const BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "https://qmag-platform.onrender.com"
    : "http://localhost:8000");

export interface Setup {
  symbol: string;
  setup_type: "EP" | "TB" | "PP" | "PULL" | "FBD";
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
};
