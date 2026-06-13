---
name: dual-ta
description: Use when the user wants a full DUAL-LENS technical analysis of a ticker — both Japanese candlestick (Nison) AND Western/classical charting, reconciled via convergence — ending in a risk-first trade plan. Triggers on phrases like "dual TA", "Japanese and Western analysis", "full TA on <TICKER>", "candlestick + classical read", "analyze <TICKER> both styles", "do TA on <TICKER>", or any request for a complete technical read that should exercise candlesticks, classical patterns, indicators/volume, market regime, and a trade plan together. Delegates to the `ta-expert` subagent (the knowledge base) and enforces the section structure, data-verification discipline, and convergence step below.
---

# Dual-Lens Technical Analysis (Japanese + Western)

Produce a complete technical read that gives the **Japanese candlestick** lens and the
**Western/classical** lens each a full, clearly-labeled treatment, then reconciles them via
**convergence** (Nison's principle: independent signals clustering at the same price = the
trade). This is the workflow validated on NVTS/HOOD reads.

## How to run it

1. **Get the ticker.** If the user named one, use it. If not, ask which symbol (one short
   question) — never run on a guessed ticker.

2. **Delegate to the `ta-expert` subagent** via the Agent tool (`subagent_type: ta-expert`).
   The agent holds the full Nison + Cheds + Edwards-&-Magee/Bulkowski/Wyckoff/Minervini/
   O'Neil/Qullamaggie knowledge base and the data tools. Pass it the prompt template below,
   substituting the ticker. Do NOT re-derive TA knowledge in the main thread — the agent is
   the brain; this skill is the recipe.

3. **Relay the agent's analysis** to the user. Preserve the A–E section structure and the
   specific prices/levels; tighten prose but lose no substance. If the agent flags a
   platform/detector bug (e.g. nonsensical setup targets), surface it.

## Non-negotiables (the agent enforces these; verify they're present before relaying)

- **Data before opinion** — the agent must fetch live data first; if data is unavailable it
  says so and stops. No blind reads.
- **Verify every pattern against the raw OHLC** — named candle lines and classical patterns
  must be checked against the actual open/high/low/close and swing points, with "qualifies"
  vs "only approximates" called explicitly. No shape-matching.
- **Risk first** — the read is incomplete without entry, structural stop, T1/T2 (method),
  R:R, size tied to the positioning dial, and explicit invalidation.
- **Probabilities, not certainties.** Loyalty to the chart, not the position.
- **Tested behavior beats the textbook label** (e.g. three-line-strike, hanging man).

## Prompt template to pass to the ta-expert subagent

> Produce a COMPREHENSIVE dual-lens technical analysis of **{TICKER}** that exercises your
> full knowledge base — the Japanese candlestick (Nison) side AND the Western/classical side —
> then synthesizes them. Give each lens a full, clearly-labeled treatment; don't footnote one.
>
> STEP 1 — Fetch live data first (never analyze blind):
> - `curl -s "https://qmag-platform.onrender.com/analyze/{TICKER}"`
> - `curl -s "https://qmag-platform.onrender.com/market/positioning"`
> (Render free tier may cold-start ~30s; retry once.)
> STEP 2 — Pull raw daily OHLCV to verify every candle/pattern claim:
> `cd ~/Documents/qmag-platform/backend && python3 -c "from scanner.fetcher import fetch_ohlcv; df=fetch_ohlcv('{TICKER}', period_days=200); print(df.tail(60).to_string())"`
>
> Then write the analysis in these explicit sections:
>
> **A) JAPANESE CANDLESTICK READ (Nison)** — construction (real body vs shadows, shaven
> head/bottom, marubozu/spinning top/doji), every named single/two/three-candle pattern with
> Nison's criteria verified against the OHLC (qualifies vs approximates), trend/location +
> close-based + OB/OS weighting + tested-behavior-vs-label, windows/gaps, blended-candle
> momentum, wick clusters, candle-completion caveat, and the candle-native trigger + invalidation.
>
> **B) WESTERN / CLASSICAL READ** — trend & swing structure, Weinstein stage, S/R map incl.
> 52-week position + polarity + local-vs-long-term, classical patterns forming/in-play
> (double/triple bottoms incl. Adam/Eve, rising-three-valleys, H&S/complex + neckline slope,
> rounding, wedge/triangle/flag/pennant, springs/upthrusts/two-level-filter, BARR, dead-cat-
> bounce) verified with swing data + confirmation/invalidation/measured-move (mind obstacles),
> plus quick-drop-vs-slow-bleed, level-importance rules, length-of-advance↔consolidation.
>
> **C) INDICATOR & VOLUME LAYER** (confirmation, not trigger) — MAs (10/21 EMA, 50/150/200),
> momentum family (RSI, MACD, ADX/DI; CCI/StochRSI/MFI/TSI if useful) with divergences
> (regular vs hidden, strength); volume forensics (climax/churn/dry-up, A/D, ICS) and
> market-profile thinking (value/POC/volume nodes & vacuums) if inferable.
>
> **D) CONVERGENCE / SYNTHESIS** — where the Japanese signals, Western levels, and indicators
> CLUSTER at the same price (that confluence is the trade); plus the platform read (P Score +
> grade, setups firing, Minervini Trend Template n/8) and where you AGREE/DISAGREE and why
> (weight leading triggers over lagging filters per the leading-vs-lagging rule).
>
> **E) VERDICT + TRADE PLAN** — long/short/stand-aside + conviction; entry (level + trigger),
> structural stop, T1/T2 (method), R:R (reject < 2:1 for swing entries), size tied to the
> positioning dial, explicit invalidation, and what would change your mind.
>
> Cite specific prices/dates from the fetched data only. If a detector/setup looks broken
> (e.g. targets below entry), flag it rather than relaying it as a signal.

## Notes

- For a quick read the user can still ask the `ta-expert` agent directly; this skill is for
  the **full both-styles treatment with the convergence step**.
- If the user cites a specific pattern someone called ("X says this is a Y"), the agent's
  pattern-claim-verification routine applies — verify it against the numbers, report
  confirmed vs unconfirmed with the exact trigger/target/failure levels.
