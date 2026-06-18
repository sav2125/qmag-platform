"use client";

import { useEffect, useRef, useState } from "react";
import { api, type SymbolAnalysis, type Bar } from "@/lib/api";

/* Price chart for the Analyze page — candlesticks + EMA21/50 with the trade drawn on
   it: entry / stop / T1 / T2 and the Risk Range band. Uses TradingView's free
   lightweight-charts (client-side, no key), dynamically imported so it never runs at
   build/SSR time. */

function ema(vals: number[], span: number): number[] {
  const k = 2 / (span + 1);
  let prev = vals[0];
  const out = [prev];
  for (let i = 1; i < vals.length; i++) {
    prev = vals[i] * k + prev * (1 - k);
    out.push(prev);
  }
  return out;
}

export default function PriceChart({ data }: { data: SymbolAnalysis }) {
  const ref = useRef<HTMLDivElement>(null);
  const [bars, setBars] = useState<Bar[] | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let live = true;
    setBars(null); setErr(false);
    api.bars(data.symbol, 180)
      .then((r) => { if (live) setBars(r.bars); })
      .catch(() => { if (live) setErr(true); });
    return () => { live = false; };
  }, [data.symbol]);

  useEffect(() => {
    if (!ref.current || !bars || bars.length === 0) return;
    let chart: { remove: () => void } | null = null;
    let disposed = false;

    (async () => {
      const { createChart, LineStyle } = await import("lightweight-charts");
      if (disposed || !ref.current) return;
      const c = createChart(ref.current, {
        height: 360,
        layout: { background: { color: "#ffffff" }, textColor: "#374151", fontSize: 11 },
        grid: { vertLines: { color: "#f1f5f9" }, horzLines: { color: "#f1f5f9" } },
        rightPriceScale: { borderColor: "#e5e7eb" },
        timeScale: { borderColor: "#e5e7eb", rightOffset: 4 },
        crosshair: { mode: 1 },
        autoSize: true,
      });
      chart = c;

      const candle = c.addCandlestickSeries({
        upColor: "#16a34a", downColor: "#dc2626", borderVisible: false,
        wickUpColor: "#16a34a", wickDownColor: "#dc2626",
      });
      candle.setData(bars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));

      const times = bars.map((b) => b.time);
      const closes = bars.map((b) => b.close);
      const e21 = ema(closes, 21), e50 = ema(closes, 50);
      const e21s = c.addLineSeries({ color: "#2563eb", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
      e21s.setData(times.map((t, i) => ({ time: t, value: +e21[i].toFixed(2) })));
      const e50s = c.addLineSeries({ color: "#f59e0b", lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
      e50s.setData(times.map((t, i) => ({ time: t, value: +e50[i].toFixed(2) })));

      const pl = (price: number | null | undefined, color: string, title: string, dashed = true) => {
        if (price == null || !isFinite(price)) return;
        candle.createPriceLine({ price, color, lineWidth: 1, lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title });
      };
      const bs = data.best_setup;
      if (bs) {
        pl(bs.entry, "#2563eb", "Entry", false);
        pl(bs.stop, "#dc2626", "Stop", false);
        pl(bs.t1, "#16a34a", "T1");
        pl(bs.t2, "#15803d", "T2");
      }
      const rr = data.risk_range?.immediate;
      if (rr) {
        pl(rr.high, "#9ca3af", "RR hi");
        pl(rr.low, "#9ca3af", "RR lo");
      }
      c.timeScale().fitContent();
    })();

    return () => { disposed = true; if (chart) chart.remove(); };
  }, [bars, data]);

  if (err) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Price Chart — {data.symbol}</h3>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-gray-500">
          <span><span style={{ color: "#2563eb" }}>—</span> EMA21</span>
          <span><span style={{ color: "#f59e0b" }}>—</span> EMA50</span>
          <span><span style={{ color: "#2563eb" }}>│</span> Entry</span>
          <span><span style={{ color: "#dc2626" }}>│</span> Stop</span>
          <span><span style={{ color: "#16a34a" }}>┄</span> Targets</span>
          <span><span style={{ color: "#9ca3af" }}>┄</span> Risk Range</span>
        </div>
      </div>
      <div ref={ref} style={{ width: "100%", height: 360 }} />
      {!bars && <div className="text-sm text-gray-400 mt-2">Loading chart…</div>}
      <p className="text-[10px] text-gray-400 mt-2 leading-relaxed">
        Daily candles (~180 bars) with EMA21/50 and the active setup&apos;s entry/stop/targets + the Risk Range band drawn
        in. Computed levels — always confirm on your own chart before trading.
      </p>
    </div>
  );
}
