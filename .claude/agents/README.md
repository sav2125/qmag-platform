# Claude Code Agents

Project-scoped [Claude Code subagents](https://docs.claude.com/en/docs/claude-code/sub-agents).
Each `.md` file is a self-contained agent definition (YAML frontmatter + system prompt).
They are available automatically to anyone running Claude Code in this repo.

## ta-expert

A world-class technical-analysis agent operating at CMT + CFA-charterholder standards.

- **Knowledge base:** Steve Nison's *Japanese Candlestick Charting Techniques* (read in
  full), the Cheds Trading "Trading Encyclopedia" curriculum, Edwards & Magee, Bulkowski,
  Wyckoff, Weinstein, Minervini (SEPA), O'Neil (CANSLIM), Qullamaggie momentum.
- **Live data:** fetches this platform's API before opining — never analyzes blind:
  - `GET /analyze/{symbol}` — P Score, 7 setups, Trend Template, MTF, checklist
  - `GET /market/positioning` — COT / put-call / NAAIM regime dial
  - raw OHLCV via `backend/scanner.fetcher.fetch_ohlcv` for pattern-claim verification
- **Discipline:** probabilities not certainties; risk-first (every read ends with
  entry / stop / targets / R:R / invalidation); candles lead, Western tools confirm and
  set targets; verifies any claimed pattern against the actual OHLC numbers.

Invoke from Claude Code with the `ta-expert` subagent type, e.g. *"use ta-expert to
analyze NVTS."*
