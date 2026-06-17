"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, MarketRegime as Regime } from "@/lib/api";

/* Compact macro strip for the Dashboard — the full panels live on /macro.
   Shows the dual-horizon Quad (climate + weather) at a glance with a link through. */

const QUAD_CLS: Record<number, string> = {
  1: "text-green-700", 2: "text-lime-700", 3: "text-amber-700", 4: "text-red-700",
};

export default function MacroSnapshot() {
  const [data, setData] = useState<Regime | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.regime().then(setData).catch(() => setError(true));
  }, []);

  if (error) return null;

  return (
    <Link href="/macro" className="block">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-3 hover:border-indigo-300 transition-colors">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs font-bold text-gray-800 uppercase tracking-wide">Macro</span>
            {!data ? (
              <span className="text-xs text-gray-400">loading regime…</span>
            ) : (
              <div className="flex items-center gap-3 text-xs">
                {data.quarterly && (
                  <span className="text-gray-600">
                    Climate <span className={`font-semibold ${QUAD_CLS[data.quarterly.quad]}`}>Q{data.quarterly.quad} {data.quarterly.quad_name}</span>
                  </span>
                )}
                <span className="text-gray-300">·</span>
                {data.monthly && (
                  <span className="text-gray-600">
                    Weather <span className={`font-semibold ${QUAD_CLS[data.monthly.quad]}`}>Q{data.monthly.quad} {data.monthly.quad_name}</span>
                  </span>
                )}
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${data.aligned ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                  {data.aligned ? "aligned" : "in transition"}
                </span>
              </div>
            )}
          </div>
          <span className="text-[11px] text-indigo-500 font-medium">Full macro dashboard →</span>
        </div>
      </div>
    </Link>
  );
}
