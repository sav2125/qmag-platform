"""Daily digest runner — called by the scheduled routine.

Usage:
    # Send digest + build all snapshots (recommended nightly cron)
    python daily_digest.py --universe sp500 --min-rs 50 --top 20 --all-snapshots

    # Build snapshots only, skip email (useful for market-close cron)
    python daily_digest.py --snapshots-only

    # Legacy: send digest for one universe, no snapshots
    python daily_digest.py --universe sp500 --min-rs 50 --top 20
"""
import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_all_snapshots() -> None:
    """Run a full scan (min_rs=0, top_n=500) for every snapshotable universe
    and persist the results to disk. Called after the digest or standalone.

    Skips 'watchlist' and 'all_us' — the former is user-specific, the
    latter takes 15–30 minutes.
    """
    from scanner.engine import scan
    from scanner.snapshot import SNAPSHOT_UNIVERSES, save_snapshot, setup_to_dict, cleanup_old

    # Remove snapshots older than 7 days first
    deleted = cleanup_old(keep_days=7)
    if deleted:
        logger.info("Cleaned up %d old snapshot(s)", deleted)

    for univ in SNAPSHOT_UNIVERSES:
        logger.info("Building snapshot: universe=%s (min_rs=0, top_n=500)…", univ)
        try:
            results = scan(universe=univ, min_rs=0.0, top_n=500)
            rows = [setup_to_dict(r) for r in results]
            save_snapshot(univ, rows)
        except Exception as exc:
            logger.error("Snapshot failed for %s: %s", univ, exc)

    logger.info("All snapshots built.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send Qullamaggie daily digest email")
    parser.add_argument("--universe", default="sp500")
    parser.add_argument("--min-rs", type=float, default=50.0, dest="min_rs")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--setup", default=None, help="ep | tb | pp | pull | fbd | wys")
    parser.add_argument(
        "--all-snapshots", action="store_true", dest="all_snapshots",
        help="After sending the digest, build snapshots for all universes",
    )
    parser.add_argument(
        "--snapshots-only", action="store_true", dest="snapshots_only",
        help="Skip email; only build snapshots for all universes",
    )
    args = parser.parse_args()

    # ── Snapshots-only mode ───────────────────────────────────────────────────
    if args.snapshots_only:
        logger.info("Snapshots-only mode — skipping email")
        build_all_snapshots()
        return

    # ── Email digest ──────────────────────────────────────────────────────────
    to_email = os.getenv("NOTIFY_TO_EMAIL")
    from_email = os.getenv("NOTIFY_FROM_EMAIL")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not to_email or not from_email:
        logger.error("NOTIFY_TO_EMAIL and NOTIFY_FROM_EMAIL must be set in .env")
        sys.exit(1)

    logger.info("Running scan: universe=%s setup=%s min_rs=%.0f top=%d",
                args.universe, args.setup or "all", args.min_rs, args.top)

    from scanner.engine import scan
    results = scan(
        universe=args.universe,
        setup_filter=args.setup,
        min_rs=args.min_rs,
        top_n=args.top,
    )
    logger.info("Scan complete: %d setups found", len(results))

    from notifier.email_sender import send_digest
    send_digest(results, to_email, from_email, smtp_host, smtp_port, smtp_user, smtp_pass)
    logger.info("Digest sent to %s", to_email)

    # ── Optionally build all snapshots after digest ────────────────────────────
    if args.all_snapshots:
        logger.info("Building snapshots for all universes…")
        build_all_snapshots()


if __name__ == "__main__":
    main()
