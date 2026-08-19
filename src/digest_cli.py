"""CLI to preview or send feed-digest emails manually (local testing / debugging).

The email schedule is driven entirely by config/rss_sources.yaml: each feed's
`update_frequency` decides whether it fires today, and feeds sharing the same
frequency are merged into ONE email.

Examples:
  python -m src.digest_cli --dry-run                        # 预览今天各频率组
  python -m src.digest_cli --dry-run --today 2026-08-23     # 模拟周日 (weekly 组)
  python -m src.digest_cli --freq weekly --dry-run          # 只看 weekly 组
  python -m src.digest_cli                                  # 真实发送今天到期的邮件
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from . import history
from .config_loader import load_config, load_feeds, load_sources
from .digest_engine import (
    _FREQUENCY_LABEL,
    build_feed_email_html,
    build_feed_email_text,
    feed_is_due,
    select_feed_records,
)
from .email_sender import _send_smtp
from .models import UpdateFrequency


def main():
    parser = argparse.ArgumentParser(description="Quantum RSS Radar feed digest sender")
    parser.add_argument(
        "--freq",
        help="Only handle this frequency: daily|weekday|weekly|monthly|season",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build emails but do NOT send; save HTML/TXT to --out",
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

    config = load_config()
    feeds = load_feeds(args.config_dir)
    sources = load_sources(args.config_dir)
    feed_configs = {f.name: f for f in feeds}

    archive_dir = args.archive_dir or config.archive_dir
    records = history.load_jsonl_archive(archive_dir)
    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date()
        if args.today
        else datetime.now().date()
    )

    # Group feeds by update_frequency (feeds sharing a frequency merge into one email)
    groups: dict[UpdateFrequency, list] = {}
    for f in feeds:
        groups.setdefault(f.update_frequency, []).append(f)

    if args.freq:
        try:
            only = UpdateFrequency(args.freq.lower())
        except ValueError:
            print(
                f"Invalid --freq '{args.freq}'. "
                "Valid: daily|weekday|weekly|monthly|season"
            )
            sys.exit(2)
        groups = {freq: fs for freq, fs in groups.items() if freq == only}

    out_dir = Path(args.out)
    for freq, group_feeds in sorted(groups.items(), key=lambda x: x[0].value):
        if not feed_is_due(group_feeds[0], today):
            print(f"[{freq.value:8s}] not scheduled for {today} — skipped")
            continue

        sections = []
        for feed in group_feeds:
            selected = select_feed_records(records, feed, today)
            pairs = history.records_to_pairs(selected)
            print(
                f"[{freq.value:8s}] {feed.name:36s} min={feed.min_score:4g} "
                f"top={feed.max_items:>3} → {len(pairs)}"
            )
            if pairs:
                sections.append((feed, pairs))

        if not sections:
            print(f"[{freq.value:8s}] due but no papers matched — skipped")
            continue

        label = _FREQUENCY_LABEL[freq]
        subject = f"Quantum RSS Radar — {label} Digest ({today:%Y-%m-%d})"
        html = build_feed_email_html(
            label, sections, sources, feed_configs, config, today
        )
        text = build_feed_email_text(label, sections, sources, feed_configs, today)
        total = sum(len(pairs) for _, pairs in sections)
        print(f"  → {label} Digest: {total} papers | subject: {subject}")

        if args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / f"{freq.value}.html"
            txt_path = out_dir / f"{freq.value}.txt"
            html_path.write_text(html, encoding="utf-8")
            txt_path.write_text(text, encoding="utf-8")
            print(f"  [dry-run] saved: {html_path}  /  {txt_path}")
        else:
            ok = _send_smtp(subject, html, text, config)
            print(f"  [sent] {'OK' if ok else 'FAILED'} — {subject}")


if __name__ == "__main__":
    main()
