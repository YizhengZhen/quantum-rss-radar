"""Preview the JSONL archive: window counts, preprint/publication split, and
per-feed digest scheduling — which feeds are due today and how many papers
each would contribute (per-feed update_frequency / min_score / max_items).

Usage:
  python scripts/archive_preview.py
  python scripts/archive_preview.py --today 2026-08-23
  python scripts/archive_preview.py --archive-dir data/all
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import history
from src.config_loader import load_config, load_feeds
from src.digest_engine import feed_is_due, select_feed_records


def main():
    parser = argparse.ArgumentParser(
        description="Preview archive & feed-digest scheduling"
    )
    parser.add_argument("--archive-dir", default=None, help="JSONL archive directory")
    parser.add_argument("--today", default=None, help="Reference date YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config", help="Config directory")
    args = parser.parse_args()

    config = load_config()
    archive_dir = args.archive_dir or config.archive_dir
    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date()
        if args.today
        else datetime.now().date()
    )

    records = history.load_jsonl_archive(archive_dir)
    print(f"\nArchive: {len(records)} merged records (dir={archive_dir})")

    pre = sum(
        1 for r in records if history.classify_preprint_publication(r) == "preprint"
    )
    pub = len(records) - pre
    print(f"  preprints: {pre}   publications: {pub}")

    for window in (1, 7, 30, 90):
        n = len(history.filter_by_window(records, window, today))
        print(f"  last {window:>3}d window: {n}")

    feeds = load_feeds(args.config_dir)
    print(f"\nFeeds due today ({today}):")
    for f in feeds:
        due = feed_is_due(f, today)
        sel = select_feed_records(records, f, today)
        flag = "✔ due" if due else "  -"
        print(
            f"  [{flag}] {f.name:36s} {f.update_frequency.value:8s} "
            f"min={f.min_score:4g} top={f.max_items:>3} → {len(sel)}"
        )


if __name__ == "__main__":
    main()
