"""Preview the JSONL archive: window counts, preprint/publication split, and
which digests are due on a given date — for verifying the digest engine.

Usage:
  python scripts/archive_preview.py
  python scripts/archive_preview.py --today 2026-08-16
  python scripts/archive_preview.py --archive-dir data/all
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import load_config, load_digest_configs
from src import history
from src.digest_engine import should_send_today


def main():
    parser = argparse.ArgumentParser(description="Preview archive & digest scheduling")
    parser.add_argument("--archive-dir", default=None, help="JSONL archive directory")
    parser.add_argument("--today", default=None, help="Reference date YYYY-MM-DD")
    parser.add_argument("--config-dir", default="config", help="Config directory")
    args = parser.parse_args()

    config = load_config()
    archive_dir = args.archive_dir or config.archive_dir
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else datetime.now().date()

    records = history.load_jsonl_archive(archive_dir)
    print(f"\nArchive: {len(records)} merged records (dir={archive_dir})")

    pre = sum(1 for r in records if history.classify_preprint_publication(r) == "preprint")
    pub = len(records) - pre
    print(f"  preprints: {pre}   publications: {pub}")

    for window in (1, 7, 30, 90):
        n = len(history.filter_by_window(records, window, today))
        print(f"  last {window:>3}d window: {n}")

    digests = load_digest_configs(args.config_dir)
    print(f"\nDigests (today={today}):")
    for d in digests:
        due = should_send_today(d, today)
        sel = history.filter_by_digest(records, d, today)
        flag = "✔ due" if due else "  -"
        print(f"  [{flag}] {d.id:16s} → {len(sel)} papers")


if __name__ == "__main__":
    main()
