"use client";

import type { Setup } from "@/lib/api";
import { SetupBadge, GradeBadge, RRBadge } from "./SetupBadge";

interface Props {
  setups: Setup[];
  loading: boolean;
}

export function SetupTable({ setups, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400">
        <svg className="animate-spin h-8 w-8 mr-3" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
        Scanning universe…
      </div>
    );
  }

  if (!setups.length) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-400">
        <p className="text-lg font-medium">No setups found</p>
        <p className="text-sm mt-1">Try lowering Min RS or Min Score, or choose a different universe.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-gray-500 border-b border-gray-200">
            <th className="text-left py-3 px-3">Symbol</th>
            <th className="text-left py-3 px-3">Setup</th>
            <th className="text-left py-3 px-3">State</th>
            <th className="text-right py-3 px-3">Price</th>
            <th className="text-right py-3 px-3">Entry</th>
            <th className="text-right py-3 px-3 text-red-500">Stop</th>
            <th className="text-right py-3 px-3">T1</th>
            <th className="text-right py-3 px-3 text-green-600">T2</th>
            <th className="text-right py-3 px-3">R:R</th>
            <th className="text-right py-3 px-3">RS</th>
            <th className="text-center py-3 px-3">Grd</th>
            <th className="text-left py-3 px-3">Notes</th>
          </tr>
        </thead>
        <tbody>
          {setups.map((s) => (
            <tr key={s.symbol} className="border-b border-gray-100 hover:bg-indigo-50/30 transition-colors">
              <td className="py-3 px-3 font-bold text-gray-900">{s.symbol}</td>
              <td className="py-3 px-3"><SetupBadge type={s.setup_type} /></td>
              <td className="py-3 px-3 capitalize text-gray-500 text-xs">{s.state}</td>
              <td className="py-3 px-3 text-right font-mono text-gray-700">
                ${s.price.toFixed(2)}
                <span className={`ml-1 text-xs ${s.pct_change >= 0 ? "text-green-600" : "text-red-500"}`}>
                  {s.pct_change >= 0 ? "+" : ""}{s.pct_change.toFixed(1)}%
                </span>
              </td>
              <td className="py-3 px-3 text-right font-mono">${s.entry.toFixed(2)}</td>
              <td className="py-3 px-3 text-right font-mono text-red-500">${s.stop.toFixed(2)}</td>
              <td className="py-3 px-3 text-right font-mono text-gray-700">${s.t1.toFixed(2)}</td>
              <td className="py-3 px-3 text-right font-mono text-green-600 font-semibold">${s.t2.toFixed(2)}</td>
              <td className="py-3 px-3 text-right"><RRBadge rr={s.rr} /></td>
              <td className="py-3 px-3 text-right text-gray-700">{s.rs_score.toFixed(0)}</td>
              <td className="py-3 px-3 text-center"><GradeBadge grade={s.grade} /></td>
              <td className="py-3 px-3 text-gray-400 text-xs max-w-[200px] truncate">{s.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
