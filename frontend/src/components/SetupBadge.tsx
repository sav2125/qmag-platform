const COLORS: Record<string, string> = {
  EP:   "bg-purple-600 text-white",
  TB:   "bg-green-600 text-white",
  PP:   "bg-cyan-600 text-white",
  PULL: "bg-amber-500 text-white",
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
