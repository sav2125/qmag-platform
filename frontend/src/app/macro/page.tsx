import MarketRegimePanel from "@/components/MarketRegime";
import FundamentalQuadPanel from "@/components/FundamentalQuad";
import MarketGammaPanel from "@/components/MarketGamma";
import MarketPositioningPanel from "@/components/MarketPositioning";
import MarketBreadthPanel from "@/components/MarketBreadth";
import SectorRotationPanel from "@/components/SectorRotation";
import FactorLeadershipPanel from "@/components/FactorLeadership";

export const metadata = { title: "Macro · Qullamaggie Platform" };

export default function MacroPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Macro Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1 max-w-3xl">
          The market-context layer — the regime a momentum trader is operating inside. Everything here is{" "}
          <strong>context for sizing and where to hunt</strong>, not a per-stock signal: it tells you whether to be
          aggressive or defensive, and which groups and factors are leading. Inspired by Hedgeye&apos;s GIP process,
          built entirely on free data. The regime is shown two ways — the <strong>price-implied Quad</strong> (what the
          tape is trading) and the <strong>fundamental Quad</strong> (what the GDP/CPI data say); when they
          <strong> diverge</strong>, the market is pricing one regime while the data turns toward another. See{" "}
          <a href="/scoring#regime" className="text-indigo-500 hover:underline">Scoring → Market-Implied Quad</a>{" "}
          for the methodology.
        </p>
      </div>

      {/* Capstone: dual-horizon Quad regime (climate + weather) — the TAPE */}
      <MarketRegimePanel />

      {/* Fundamental Quad — the DATA (GDP/CPI), with tape-vs-data divergence */}
      <FundamentalQuadPanel />

      {/* Market gamma — index dealer-gamma regime (SPY/QQQ) */}
      <MarketGammaPanel />

      {/* Supporting context, finest → coarsest */}
      <MarketPositioningPanel />
      <MarketBreadthPanel />
      <SectorRotationPanel />
      <FactorLeadershipPanel />

      <p className="text-[11px] text-gray-400 leading-relaxed">
        The Quad synthesizes the panels below it (sector leadership + style factors + credit + breadth). None of these
        feed the per-stock P&nbsp;Score — they are a separate, top-down regime read. All sources are free and cached
        (6–12h); see each panel&apos;s &quot;How this works&quot; link for the exact methodology.
      </p>
    </div>
  );
}
