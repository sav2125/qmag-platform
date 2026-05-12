"""Daily digest runner — called by the scheduled routine.

Usage:
    python daily_digest.py [--universe sp500] [--min-rs 50] [--top 20]
"""
import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send Qullamaggie daily digest email")
    parser.add_argument("--universe", default="sp500")
    parser.add_argument("--min-rs", type=float, default=50.0, dest="min_rs")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--setup", default=None, help="ep | tb | pp | pull")
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
