const BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? "https://qmag-platform.onrender.com"
    : "http://localhost:8000");

export interface Setup {
  symbol: string;
  setup_type: "EP" | "TB" | "VCP" | "PP" | "PULL" | "FBD" | "WYS";
  state: string;
  entry: number;
  stop: number;
  t1: number;
  t2: number;
  rr: number;
  confidence: number;
  rs_score: number;
  rs_label: string;
  price: number;
  pct_change: number;
  notes: string;
  meta: Record<string, unknown>;
  weinstein_stage: number;    // 1-4; 0 = insufficient data
  ad_net: number;             // O'Neill A/D net days (+ = accumulation)
  prob_score: number;         // P Score (probability-weighted signal voting, 0–100) — the single score
  prob_grade: "A" | "B" | "C" | "D";  // P grade: A≥75 / B≥60 / C≥45 / D<45
  rvol: number;               // Relative Volume: today / 20-day avg
  isc_score: number;          // Institutional Composite Score: OBV+CMF+A/D+MFI → 0-100
  weekly_dir: "bullish" | "neutral" | "bearish"; // Weekly TF direction (free resample)
  regime_verdict?: "tailwind" | "neutral" | "headwind" | ""; // macro fit (top-N)
  regime_sector?: string;     // the stock's sector (regime fit)
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
  cached?: boolean;  // serve from today's snapshot (instant); ignored for watchlist/all
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
    if (p.cached) q.set("cached", "true");
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

  refreshSnapshot: (universe: string) =>
    req<{ universe: string; results: number; path: string }>("/scan/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ universe }),
    }),

  positioning: () => req<MarketPositioning>("/market/positioning"),
  breadth: () => req<MarketBreadth>("/market/breadth"),
  sectors: () => req<SectorRotation>("/market/sectors"),
  factors: () => req<FactorLeadership>("/market/factors"),
  regime: () => req<MarketRegime>("/market/regime"),
  gip: () => req<MacroQuad>("/market/gip"),
  gamma: () => req<MarketGamma>("/market/gamma"),
  themes: () => req<ThemeRotation>("/market/themes"),
  shortVolume: (symbol: string) => req<ShortVolume>(`/short-volume/${symbol}`),
  insider: (symbol: string) => req<Insider>(`/insider/${symbol}`),
  bars: (symbol: string, days = 180) => req<{ symbol: string; bars: Bar[] }>(`/bars/${symbol}?days=${days}`),
};

export interface Bar {
  time: string;   // yyyy-mm-dd
  open: number; high: number; low: number; close: number; volume: number;
}

// ── Short-volume pressure (FINRA Reg SHO) ─────────────────────────────────────

export interface ShortVolume {
  symbol:        string;
  latest_pct:    number;
  avg_pct:       number;
  trend:         number;   // recent-half avg − earlier-half avg (pp)
  level:         "very_high" | "elevated" | "normal" | "low";
  days:          number;
  series:        { date: string; short_pct: number }[];
  price_chg_5d:  number | null;
  price_chg_20d: number | null;
  interpretation_points: { label: string; detail: string }[];
}

// ── Insider activity (SEC EDGAR Form 4) ───────────────────────────────────────

export interface Insider {
  symbol:        string;
  signal:        "cluster_buying" | "buying" | "selling" | "none";
  buy_value:     number;
  sell_value:    number;
  net_value:     number;
  buyers:        number;
  sellers:       number;
  lookback_days: number;
  top_buys:      { owner: string; title: string; shares: number; value: number; date: string }[];
  interpretation_points: { label: string; detail: string }[];
}

// ── Sector RS rotation ────────────────────────────────────────────────────────

export interface SectorPerf {
  d1: number | null; w1: number | null; m1: number | null; m3: number | null; ytd: number | null;
}

export interface SectorRow {
  symbol:      string;
  name:        string;
  rs_strength: number;   // 3-mo relative perf vs SPY (%)
  rs_momentum: number;   // RS acceleration (recent month − prior month, %)
  quadrant:    "leading" | "weakening" | "improving" | "lagging";
  abs:         SectorPerf;   // absolute returns by horizon
  rel:         SectorPerf;   // relative-to-SPY returns by horizon
}

export interface SectorRotation {
  as_of:   string;
  sectors: SectorRow[];
  interpretation_points: { label: string; detail: string }[];
}

// ── Style-factor leadership ───────────────────────────────────────────────────

export interface FactorRow {
  factor:      string;
  high_label:  string;
  low_label:   string;
  spread:      SectorPerf;       // High − Low return spread by horizon
  leader:      "high" | "low";
  basket_size: number;
}

export interface FactorLeadership {
  as_of:    string;
  universe: number;
  factors:  FactorRow[];
  interpretation_points: { label: string; detail: string }[];
}

// ── Market-implied Quad regime ────────────────────────────────────────────────

export interface QuadRead {
  quad:            number;
  quad_name:       string;
  quad_tag:        string;
  growth:          string;
  growth_score:    number;
  inflation:       string;
  inflation_score: number;
  conviction:      string;
  playbook: {
    best_sectors: string[]; best_factors: string[]; best_assets: string[]; momentum_note: string;
  };
  evidence: { axis: string; label: string; detail: string; vote: number }[];
}

export interface MarketRegime {
  as_of:     string;
  monthly:   QuadRead | null;   // weather — intermediate-term (~1mo) tactical overlay
  quarterly: QuadRead | null;   // climate — longer-term (~3mo) dominant regime
  aligned:   boolean;
  interpretation_points: { label: string; detail: string }[];
}

// ── Fundamental GIP Quad (FRED GDP/CPI/IP rate-of-change — the DATA read) ──────

export interface FundamentalQuadRead {
  quad:               number;
  quad_name:          string;
  quad_tag:           string;
  growth:             string;   // accelerating / decelerating
  growth_delta_bps:   number;
  growth_metric:      string;   // "Real GDP YoY" / "Industrial Production YoY"
  growth_yoy:         number;
  growth_yoy_prev:    number;
  growth_date:        string;
  inflation:          string;
  inflation_delta_bps: number;
  cpi_yoy:            number;
  cpi_yoy_prev:       number;
  cpi_date:           string;
}

export interface MacroQuad {
  as_of:     string;
  quarterly: FundamentalQuadRead | null;   // climate — Real GDP
  monthly:   FundamentalQuadRead | null;   // weather — Industrial Production
  aligned:   boolean;
  interpretation_points: { label: string; detail: string }[];
}

// ── Theme rotation ────────────────────────────────────────────────────────────

export interface ThemeLeader {
  symbol: string;
  rel_m3: number | null;
  rel_m1: number | null;
}

export interface ThemeRow {
  key:         string;
  name:        string;
  source:      string;
  count:       number;
  rs_strength: number | null;
  rs_momentum: number | null;
  quadrant:    "leading" | "weakening" | "improving" | "lagging";
  rel:         SectorPerf;
  leaders:     ThemeLeader[];
}

export interface ThemeRotation {
  as_of:  string;
  themes: ThemeRow[];
  interpretation_points: { label: string; detail: string }[];
}

// ── Market gamma (index dealer-gamma regime: SPY + QQQ) ───────────────────────

export interface GammaIndex {
  symbol:     string;
  name:       string;
  spot:       number;
  gex_musd:   number;
  regime:     "positive" | "negative";
  flip:       number | null;
  above_flip: boolean;
  call_wall:  number | null;
  put_wall:   number | null;
  source:     string | null;
}

export interface MarketGamma {
  as_of:   string;
  indices: GammaIndex[];
  interpretation_points: { label: string; detail: string }[];
}

// ── Market breadth ────────────────────────────────────────────────────────────

export interface MarketBreadth {
  pct_above_50dma:  number;
  pct_above_200dma: number;
  new_highs:        number;
  new_lows:         number;
  net_highs_lows:   number;
  advancers:        number;
  decliners:        number;
  net_advancers:    number;
  universe_size:    number;
  breadth_score:    number;   // 0–100
  state:            "strong" | "healthy" | "mixed" | "weak" | "risk-off";
  divergent:        boolean;
  interpretation_points: { label: string; detail: string }[];
}

// ── Market positioning types ──────────────────────────────────────────────────

export interface COTContract {
  net_pct_oi: number;   // leveraged-funds net position as % of open interest
  z: number;            // z-score vs ~3y of weekly history
  date: string;
}

export interface MarketPositioning {
  as_of: string;
  cot: {
    es: COTContract | null;
    nq: COTContract | null;
    avg_z: number;
    state: "crowded_short" | "neutral" | "crowded_long";
    vote: number;
  } | null;
  put_call: {
    ratio: number;        // SPY put/call volume ratio (near-dated)
    put_vol: number;
    call_vol: number;
    state: "fear" | "neutral" | "complacent";
    vote: number;
  } | null;
  naaim: {
    value: number;        // 0–200 average manager exposure
    z: number;
    date: string | null;
    state: "washed_out" | "neutral" | "fully_invested";
    vote: number;
  } | null;
  credit: {
    oas: number;          // ICE BofA US HY OAS, %
    change_1m: number;    // change vs ~1 month ago, pts
    z: number;            // z-score vs ~3y
    date: string;
    state: "widening" | "tightening" | "neutral";
    vote: number;
  } | null;
  cta?: {
    symbol: string;
    price: number;
    levels: { ma: number; value: number; dist_pct: number; above: boolean }[];
    above_count: number;
    state: "trend_long" | "long" | "de_grossing" | "short";
    flip_ma: number;
    flip_value: number;
    interpretation: string;
  } | null;
  sources_available: number;
  dial: { score: number; label: string; detail: string };
}

// ── Analyze types ─────────────────────────────────────────────────────────────

export interface ProbComponent {
  source:       string;    // "RSI" | "MACD" | "EMA" | "Stage" | "ICS" | "ADNet" | "EP" | "TB" | ...
  direction:    "bullish" | "bearish";
  strength:     number;    // 0.0–1.0
  weight:       number;    // base weight from config
  accuracy:     number;    // backtested accuracy factor
  regime_mult:  number;    // regime multiplier applied
  contribution: number;    // strength × weight × accuracy × regime_mult
  detail?:      string;    // optional human-readable note (e.g. "7/8 criteria met")
}

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
  setup_type:  string;
  state:       string;
  entry:       number;
  stop:        number;
  t1:          number;
  t2:          number;
  rr:          number;
  risk_pct:    number;
  confidence:  number;
  notes:       string;
}

export interface MAStack {
  stack:               string;
  detail:              string;
  price_vs_ema21_pct:  number;
  price_vs_ema50_pct:  number;
  ema21_rising:        boolean;
  ema50_rising:        boolean;
  ema21_state:         "rising" | "turning_up" | "flat" | "falling";
  ema50_state:         "rising" | "turning_up" | "flat" | "falling";
  ema21:               number;
  ema50:               number;
  sma150:              number | null;
}

export interface RiskRange {
  price: number;
  immediate: {
    low: number; high: number; center: number;
    position_pct: number; width_pct: number; horizon_days: number;
  };
  durations: {
    name: string; label: string; level: number | null;
    above: boolean | null; slope: string | null; insufficient?: boolean;
  }[];
  ttt_state: "bullish_all" | "bullish_trade_trend" | "mixed" | "rolling_over" | "bearish_all";
  interpretation_points: { label: string; detail: string }[];
}

export interface TrendTemplateCriterion {
  label:  string;
  met:    boolean;
  detail: string;
}

export interface TrendTemplate {
  passed:   number;
  total:    number;
  criteria: TrendTemplateCriterion[];
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

export interface FibLevel {
  ratio: number;    // e.g. 0.382, 1.618
  pct:   number;    // e.g. 38.2, 161.8
  price: number;
}

export interface FibGrid {
  direction:         "uptrend" | "downtrend";
  lookback_bars:     number;
  swing_low:         number;
  swing_high:        number;
  swing_low_date:    string;
  swing_high_date:   string;
  range:             number;
  retracements:      FibLevel[];   // 23.6 / 38.2 / 50 / 61.8 / 78.6 (pullback levels)
  extensions:        FibLevel[];   // 127.2 / 161.8 / 200 / 261.8 (targets)
  golden_pocket:     { low: number; high: number };   // 61.8–65% band
  in_golden_pocket:  boolean;
  retrace_depth_pct: number;       // how far price has retraced the active leg
  nearest_level:     { name: string; price: number };
  price:             number;
}

export interface OptionsSnapshot {
  source:            string;
  nearest_expiry:    string;
  dte:               number;
  expiries_used:     number;
  atm_iv:            number | null;   // % implied volatility (ATM)
  hv:                number | null;   // 30d realised (historical) vol, %
  iv_hv:             number | null;   // IBKR IV Rank = IV ÷ HV
  iv_state:          "rich" | "fair" | "cheap" | null;
  expected_move_pct: number | null;   // ± % of spot by nearest expiry
  expected_move_abs: number | null;   // ± $ (ATM straddle)
  skew:              number | null;   // OTM put IV − OTM call IV (IV points)
  put_call_vol:      number | null;
  put_call_oi:       number | null;
  call_volume:       number;
  put_volume:        number;
  call_oi:           number;
  put_oi:            number;
  vol_oi_ratio:      number | null;
  unusual_activity:  boolean;
  max_pain:          number | null;   // OI-weighted pin price
  max_pain_dist_pct: number | null;   // % from spot
  aci_score:         number | null;   // delta-adjusted-OI sentiment −1..+1 (level)
  aci_label:         "bullish" | "neutral" | "bearish";
  bull_daoi:         number;          // call delta-adjusted OI
  bear_daoi:         number;          // put delta-adjusted OI
  oi_resistance:     OILevel[];       // call walls above price
  oi_support:        OILevel[];       // put walls below price
  lean:              "bullish" | "neutral" | "bearish";
  tell:              string;
  interpretation:    string;   // per-stock plain-English read (flat paragraph)
  interpretation_points: { label: string; detail: string }[];   // per-metric bullets
  gex:               GammaExposure | null;       // dealer gamma (CBOE path only)
  term_structure:    IVTermStructure | null;     // front vs ~45d ATM IV
}

export interface GammaExposure {
  gex_musd:  number;                       // $ per 1% move, in $M (signed)
  regime:    "positive" | "negative";      // positive = pinning; negative = amplifying
  flip:      number | null;                // zero-gamma flip price
  call_wall: number | null;                // strongest call-gamma strike above spot
  put_wall:  number | null;                // strongest put-gamma strike below spot
}

export interface IVTermStructure {
  front_dte: number;
  front_iv:  number;   // %
  back_dte:  number;
  back_iv:   number;   // %
  ratio:     number;   // front_iv / back_iv
  state:     "backwardation" | "contango" | "flat";
}

export interface OILevel {
  strike: number;
  oi:     number;
}

export interface SymbolAnalysis {
  symbol:         string;
  price:          number;
  pct_change:     number;
  rvol:           number;
  vol_ratio_50d:  number;

  direction:    "long" | "neutral" | "avoid";
  rs_score:     number;
  rs_label:     string;
  weinstein_stage: number;

  // P Score — probability-weighted signal voting — the single score
  prob_score:         number;   // 0–100
  prob_grade:         "A" | "B" | "C" | "D";   // A≥75 / B≥60 / C≥45 / D<45
  prob_direction:     string;   // "long" | "short" | "neutral"
  prob_agreement:     number;   // fraction of signals agreeing (0–1)
  prob_regime:        string;   // "trend" | "range" | "transition"
  prob_penalty:       number;   // overextension penalty applied
  prob_penalty_notes: string[];
  prob_components:    ProbComponent[];
  prob_interpretation_points?: { label: string; detail: string }[];   // per-driver plain-English read

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

  checklist:           ChecklistItem[];
  warnings:            Warning[];
  trend_template:      TrendTemplate;
  timeframe_alignment: MTFAlignment;
  fibonacci:           FibGrid | null;
  options:             OptionsSnapshot | null;
  risk_range:          RiskRange | null;
  regime_fit:          RegimeFit | null;
}

export interface RegimeFit {
  symbol:          string;
  verdict:         "tailwind" | "neutral" | "headwind";
  score:           number;
  sector:          string | null;
  sector_etf:      string | null;
  sector_quadrant: string | null;
  sector_rs:       number | null;
  quad:            number | null;
  quad_name:       string | null;
  posture:         string | null;
  momentum_on:     boolean | null;
  interpretation_points: { label: string; detail: string }[];
}
