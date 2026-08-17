"""CLI to send or dry-run email digests manually (local testing / debugging).

Examples:
  python -m src.digest_cli --send weekday_arxiv --dry-run
  python -m src.digest_cli --all-due --dry-run
  python -m src.digest_cli --all-due --dry-run --today 2026-08-16   # 周日
  python -m src.digest_cli --send weekly_journals                    # 真实发送
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from . import history
from .config_loader import load_config, load_digest_configs, load_feeds, load_sources
from .digest_engine import (
    build_digest_email_html,
    build_digest_email_text,
    should_send_today,
)
from .email_sender import _send_smtp


def main():
    parser = argparse.ArgumentParser(description="Quantum RSS Radar digest sender")
    parser.add_argument("--send", help="Digest id to send (e.g. weekday_arxiv)")
    parser.add_argument(
        "--all-due", action="store_true", help="Handle all digests due today"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build emails but do NOT send; print subject and save HTML/TXT",
    )
    parser.add_argument("--today", help="Override today's date (YYYY-MM-DD)")
    parser.add_argument("--config-dir", default="config", help="Config directory")
    parser.add_argument(
        "--archive-dir",
        default=None,
        help="JSONL archive directory (default: config.archive_dir)",
    )
    parser.add_argument(
        "--out", default="digest_preview", help="Output dir for --dry-run files"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    config = load_config()
    feeds = load_feeds(args.config_dir)
    sources = load_sources(args.config_dir)
    feed_configs = {f.name: f for f in feeds}
    digests = load_digest_configs(args.config_dir)

    if not digests:
        print("No config/digests.yaml found — nothing to do.")
        sys.exit(1)

    archive_dir = args.archive_dir or config.archive_dir
    records = history.load_jsonl_archive(archive_dir)
    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date()
        if args.today
        else datetime.now().date()
    )

    if args.send:
        targets = [d for d in digests if d.id == args.send]
    elif args.all_due:
        targets = [d for d in digests if d.enabled and should_send_today(d, today)]
    else:
        targets = []

    if not targets:
        print(f"No digests selected (today={today}). Use --send <id> or --all-due.")
        # Still list what would fire today for convenience
        due = [d.id for d in digests if d.enabled and should_send_today(d, today)]
        print(f"Digests due today: {due or 'none'}")
        sys.exit(0)

    out_dir = Path(args.out)
    for digest in targets:
        selected = history.filter_by_digest(records, digest, today)
        pairs = history.records_to_pairs(selected)
        subject = digest.subject_template.format(
            name=digest.name, date=today.strftime("%Y-%m-%d")
        )

        print(
            f"\n=== {digest.name} [{digest.id}] — due {today}, {len(pairs)} papers ==="
        )
        for i, (p, a) in enumerate(pairs, 1):
            print(f"  {i}. [{a.relevance_score:.1f}] {p.title}  ({p.feed_name})")

        html = build_digest_email_html(digest, pairs, sources, config, feed_configs)
        text = build_digest_email_text(digest, pairs, sources, feed_configs)

        if args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / f"{digest.id}.html"
            txt_path = out_dir / f"{digest.id}.txt"
            html_path.write_text(html, encoding="utf-8")
            txt_path.write_text(text, encoding="utf-8")
            print(f"  [dry-run] subject: {subject}")
            print(f"  [dry-run] saved: {html_path}  /  {txt_path}")
        else:
            ok = _send_smtp(subject, html, text, config)
            print(f"  [sent] {'OK' if ok else 'FAILED'} — {subject}")


if __name__ == "__main__":
    main()
