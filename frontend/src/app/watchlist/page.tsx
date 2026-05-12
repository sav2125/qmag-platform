"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export default function WatchlistPage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getWatchlist().then((r) => {
      setSymbols(r.symbols);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  async function add() {
    const sym = input.trim().toUpperCase();
    if (!sym) return;
    try {
      const res = await api.addToWatchlist(sym);
      setSymbols(res.symbols);
      setInput("");
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add");
    }
  }

  async function remove(sym: string) {
    try {
      const res = await api.removeFromWatchlist(sym);
      setSymbols(res.symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove");
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Watchlist</h1>
        <p className="text-sm text-gray-500 mt-1">
          Add symbols here then scan with <span className="font-mono bg-gray-100 px-1 rounded">universe: watchlist</span>.
        </p>
      </div>

      {/* Add form */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
        <label className="block text-xs font-medium text-gray-500 mb-2">Add Symbol</label>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && add()}
            placeholder="AAPL"
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none font-mono"
          />
          <button onClick={add}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg px-5 py-2 text-sm transition-colors">
            Add
          </button>
        </div>
        {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
      </div>

      {/* List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">{symbols.length} symbol{symbols.length !== 1 ? "s" : ""}</h2>
        </div>
        {loading ? (
          <p className="text-gray-400 text-sm text-center py-8">Loading…</p>
        ) : symbols.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-8">
            No symbols yet. Add some above.
          </p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {symbols.map((sym) => (
              <li key={sym} className="flex items-center justify-between px-5 py-3 hover:bg-gray-50">
                <span className="font-mono font-semibold text-gray-900">{sym}</span>
                <button onClick={() => remove(sym)}
                  className="text-xs text-red-400 hover:text-red-600 transition-colors">
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
