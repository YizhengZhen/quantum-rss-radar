"""Migrate the flat JSONL archive to the per-source layout.

Old layout:  data/all/data_YYYY-MM-DD_HHMMSS.jsonl    (all sources in one file)
New layout:  data/all/<source>/data_YYYY-MM-DD_HHMMSS.jsonl

Splits each flat file by the record's `source` field into per-source files that
keep the SAME timestamp name.  Idempotent: if no top-level flat files exist the
script reports the layout is already migrated.

Usage:
  python scripts/migrate_archive_layout.py                     # migrate data/all
  python scripts/migrate_archive_layout.py --archive-dir <dir> # other dir
  python scripts/migrate_archive_layout.py --dry-run           # preview only
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)


def migrate(archive_dir: Path, dry_run: bool) -> None:
    flat_files = sorted(archive_dir.glob("data_*.jsonl"))
    if not flat_files:
        print(f"No flat data_*.jsonl found in {archive_dir} — layout already migrated?")
        return

    total_files = 0
    total_records = 0
    for f in flat_files:
        groups: dict[str, list] = defaultdict(list)
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                src = (rec.get("source") or "other").lower()
                groups[src].append(rec)

        if dry_run:
            for src in sorted(groups):
                print(f"  [dry] {f.name} → {src}/{f.name} ({len(groups[src])} records)")
            continue

        for src in sorted(groups):
            out_dir = archive_dir / src
            out_path = out_dir / f.name
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                for rec in groups[src]:
                    fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            total_records += len(groups[src])
            total_files += 1

        # Original flat file is superseded by its per-source splits
        f.unlink()
        print(f"  migrated {f.name} → {len(groups)} per-source files")

    print(f"\nDone: {total_files} per-source files, {total_records} records")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate flat JSONL archive to per-source layout"
    )
    parser.add_argument(
        "--archive-dir",
        default="data/all",
        help="Archive directory (default: data/all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview only, no writes"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    migrate(Path(args.archive_dir), args.dry_run)


if __name__ == "__main__":
    main()
