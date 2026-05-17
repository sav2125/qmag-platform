"""Snapshot cache for scan results.

Design
------
The scan is expensive (30 s for S&P 500, minutes for larger universes).
Because all signals are based on *daily* bars that don't update until
~5 PM ET, recomputing the same result multiple times per day is wasteful.

One snapshot is stored per universe per calendar day:
    data/snapshots/{universe}_YYYY-MM-DD.json

Each snapshot captures *all* detected setups (min_rs=0, no setup filter,
top_n=500) so that any combination of downstream filters can be applied
in-memory in microseconds.

Filters that require the raw DataFrame (min_adr, above_ema21/50) cannot
be applied from a snapshot and are silently skipped when cached=True.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = Path(__file__).parent.parent / "data" / "snapshots"

# Universes we build snapshots for — excludes watchlist (user-specific)
# and all_us (~7 000 stocks, 15–30 min — too slow for a nightly routine).
SNAPSHOT_UNIVERSES: list[str] = [
    "sp500",
    "nasdaq100",
    "largecap",
    "midcap",
    "smallcap",
    "tech",
]


# ── Serialisation ─────────────────────────────────────────────────────────────

def setup_to_dict(s: Any) -> dict[str, Any]:
    """Convert a Setup object to a JSON-serialisable dict.

    This is the single source of truth for Setup serialisation — used by
    both the FastAPI /scan endpoint and the snapshot writer.

    Field naming:
      q_score / q_grade  — Qullamaggie composite score (existing formula)
      prob_score / prob_grade — Probability scorer (tech-analysis port)
    """
    return {
        "symbol":          s.symbol,
        "setup_type":      s.setup_type,
        "state":           s.state,
        "entry":           s.entry,
        "stop":            s.stop,
        "t1":              s.t1,
        "t2":              s.t2,
        "rr":              s.rr,
        "confidence":      s.confidence,
        # Q Score (Qullamaggie formula: quality×60 + RS×25 + stage×10 + A/D×5)
        "q_score":         s.composite_score,
        "grade":           s.grade,           # Q grade (A≥72 / B≥58 / C≥44 / D<44)
        # P Score (probability-weighted signal voting)
        "prob_score":      getattr(s, "prob_score", 0.0),
        "prob_grade":      getattr(s, "prob_grade", "D"),
        "rs_score":        s.rs_score,
        "rs_label":        s.rs_label,
        "price":           s.price,
        "pct_change":      s.pct_change,
        "notes":           s.notes,
        "meta":            s.meta,
        "weinstein_stage": s.weinstein_stage,
        "ad_net":          s.ad_net,
        "rvol":            s.rvol,
        "isc_score":       s.isc_score,
        "weekly_dir":      getattr(s, "weekly_dir", "neutral"),
    }


# ── Path helpers ──────────────────────────────────────────────────────────────

def snapshot_path(universe: str, day: date | None = None) -> Path:
    d = day or date.today()
    return SNAPSHOT_DIR / f"{universe}_{d.isoformat()}.json"


def has_snapshot(universe: str, day: date | None = None) -> bool:
    return snapshot_path(universe, day).exists()


# ── Save / load ───────────────────────────────────────────────────────────────

def save_snapshot(universe: str, rows: list[dict[str, Any]]) -> Path:
    """Persist a list of serialised setup dicts as today's snapshot."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    p = snapshot_path(universe)
    p.write_text(json.dumps(rows, default=str))
    logger.info("Snapshot saved: %s  (%d results)", p.name, len(rows))
    return p


def load_snapshot(universe: str, day: date | None = None) -> list[dict[str, Any]] | None:
    """Load today's (or a given day's) snapshot. Returns None if not found or corrupt."""
    p = snapshot_path(universe, day)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        logger.warning("Snapshot %s is corrupt (%s) — will recompute.", p.name, exc)
        return None


# ── In-memory filtering ───────────────────────────────────────────────────────

def apply_filters(
    rows: list[dict[str, Any]],
    setup_filter: str | None = None,
    min_rs: float = 0.0,
    min_score: float = 0.0,
    top_n: int = 50,
) -> list[dict[str, Any]]:
    """Apply scan-style filters in-memory to snapshot rows.

    Filters that require the raw DataFrame (min_adr, above_ema21/50) are
    not applied here — they're silently ignored when reading from cache.
    """
    out = rows
    if setup_filter:
        sf = setup_filter.upper()
        out = [r for r in out if r.get("setup_type", "").upper() == sf]
    if min_rs > 0:
        out = [r for r in out if r.get("rs_score", 0) >= min_rs]
    if min_score > 0:
        out = [r for r in out if r.get("q_score", r.get("composite_score", 0)) >= min_score]
    # Already sorted by composite_score desc when saved; preserve that order.
    return out[:top_n]


# ── Housekeeping ──────────────────────────────────────────────────────────────

def cleanup_old(keep_days: int = 7) -> int:
    """Delete snapshots older than keep_days. Returns count of deleted files."""
    if not SNAPSHOT_DIR.exists():
        return 0
    cutoff_ord = date.today().toordinal() - keep_days
    deleted = 0
    for p in SNAPSHOT_DIR.glob("*.json"):
        # Filename format: {universe}_YYYY-MM-DD.json
        # The date part is always the last '_'-separated segment.
        try:
            date_str = p.stem.rsplit("_", 1)[-1]
            if date.fromisoformat(date_str).toordinal() < cutoff_ord:
                p.unlink()
                deleted += 1
                logger.debug("Deleted old snapshot: %s", p.name)
        except Exception:
            pass  # non-standard filenames — ignore
    if deleted:
        logger.info("Snapshot cleanup: removed %d old file(s)", deleted)
    return deleted
