"use client";

import { useState, useCallback } from "react";
import { api, type Setup, type ScanParams } from "@/lib/api";
import { SetupTable } from "@/components/SetupTable";

const UNIVERSES = ["sp500", "tech", "watchlist"];
const SETUPS = [
  { value: "", label: "All Setups" },
  { value: "ep", label: "EP — Episodic Pivot" },
  { value: "tb", label: "TB — Tight Base" },
  { value: "pp", label: "PP — Pocket Pivot" },
  { value: "pull", label: "PULL — EMA Pullback" },
];

const LEGEND = [
  { type: "EP", color: "bg-purple-600", desc: "Catalyst surge ≥5% on ≥2× volume, tight base" },
  { type: "TB", color: "bg-green-600", desc: "Flat base ≤8% range, resistance tested ≥2×" },
  { type: "PP", color: "bg-cyan-600", desc: "Up-day volume > 10-day down-day high" },
  { type: "PULL", color: "bg-amber-500", desc: "Pullback to rising EMA21 in uptrend" },
];

export default function Dashboard() {
  const [setups, setSetups] = useState<Setup[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scanned, setScanned] = useState(false);

  const [universe, setUniverse] = useState("sp500");
  const [setupFilter, setSetupFilter] = useState("");
  const [minRs, setMinRs] = useState(50);
  const [minScore, setMinScore] = useState(0);
  const [top, setTop] = useState(20);

  const runScan = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: ScanParams = {
        universe,
        setup: setupFilter || null,
        min_rs: minRs,
        min_score: minScore,
        top,
      };
      const results = await api.scan(params);
      setSetups(results);
      setScanned(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }, [universe, setupFilter, minRs, minScore, top]);

  const counts = {
    A: setups.filter((s) => s.grade === "A").length,
    B: setups.filter((s) => s.grade === "B").length,
    ep: setups.filter((s) => s.setup_type === "EP").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Scan for Qullamaggie setups with actionable entry, stop, and targets.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Universe</label>
            <select value={universe} onChange={(e) => setUniverse(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none">
              {UNIVERSES.map((u) => <option key={u}>{u}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Setup Filter</label>
            <select value={setupFilter} onChange={(e) => setSetupFilter(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none">
              {SETUPS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Min RS ({minRs})</label>
            <input type="range" min={0} max={90} step={5} value={minRs}
              onChange={(e) => setMinRs(Number(e.target.value))}
              className="w-full accent-indigo-600 mt-1" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Top N</label>
            <input type="number" min={5} max={50} value={top}
              onChange={(e) => setTop(Number(e.target.value))}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div className="flex items-end">
            <button onClick={runScan} disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-lg px-4 py-2 text-sm transition-colors">
              {loading ? "Scanning…" : "Run Scan"}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
          ⚠ {error} — make sure the backend is running on port 8000.
        </div>
      )}

      {/* Stats bar */}
      {scanned && !loading && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total Setups", value: setups.length, color: "text-indigo-600" },
            { label: "Grade A", value: counts.A, color: "text-green-600" },
            { label: "Episodic Pivots", value: counts.ep, color: "text-purple-600" },
          ].map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <p className="text-xs text-gray-500">{stat.label}</p>
              <p className={`text-3xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Results table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">
            {scanned ? `${setups.length} Setup${setups.length !== 1 ? "s" : ""}` : "Results"}
          </h2>
          {!scanned && (
            <span className="text-sm text-gray-400">Configure filters above and press Run Scan</span>
          )}
        </div>
        <SetupTable setups={setups} loading={loading} />
      </div>

      {/* Legend */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Setup Legend</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {LEGEND.map((l) => (
            <div key={l.type} className="flex items-start gap-2">
              <span className={`${l.color} text-white text-xs font-bold px-2 py-0.5 rounded mt-0.5 shrink-0`}>{l.type}</span>
              <span className="text-xs text-gray-500">{l.desc}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-3">
          Entry/Stop/T1/T2 are computed levels. Always confirm on your own chart before trading.
          R:R is based on entry to T2. RS = Relative Strength vs SPY (0–100).
        </p>
      </div>
    </div>
  );
}
