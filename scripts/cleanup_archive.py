"""Clean up & deduplicate the historical JSONL archive (checklist item D).

Background
----------
The archive predates DOI-first dedup: historical records use old title-hash ids
(e.g. ``3a346624521a1757``) and carry no ``doi`` field.  After the pipeline
switched to ``doi:/arx:/title:`` ids, those old records no longer merge with new
runs, so the same paper can appear twice.  This script re-keys every historical
record to the new id scheme (DOI from link → arXiv id from link → title hash),
extracts DOIs into the ``doi`` field, merges duplicates, remaps the LLM cache,
and rebuilds the SQLite database.

Usage
-----
  python scripts/cleanup_archive.py --dry-run                 # inventory only
  python scripts/cleanup_archive.py --rewrite                 # re-key + dedup (backup kept)
  python scripts/cleanup_archive.py --rewrite --remap-cache --rebuild-db
  python scripts/cleanup_archive.py --rebuild-site            # regen papers.json + quarterly.json
"""

import argparse
import json
import logging
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import history
from src.history import compute_record_key, canonical_record

logger = logging.getLogger(__name__)


def iter_records(archive_dir: Path):
    """Yield (filename, record) for every line of every data_*.jsonl."""
    for f in sorted(archive_dir.glob("data_*.jsonl")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield f, json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.warning(f"Failed to read {f}: {e}")


def load_file_records(f: Path):
    recs = []
    with open(f, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return recs


def write_file_records(f: Path, recs):
    recs = sorted(recs, key=lambda r: r.get("score", 0), reverse=True)
    with open(f, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def dry_run(archive_dir: Path):
    print(f"\n===== DRY RUN (no writes) — archive: {archive_dir} =====")
    total = 0
    with_doi = 0
    per_file_dup = 0
    global_groups = defaultdict(int)
    files = set()
    for f, rec in iter_records(archive_dir):
        files.add(f)
        total += 1
        if rec.get("doi"):
            with_doi += 1
        global_groups[compute_record_key(rec)] += 1

    for f in sorted(files):
        recs = load_file_records(f)
        keys = defaultdict(int)
        for r in recs:
            keys[compute_record_key(r)] += 1
        dup = sum(c - 1 for c in keys.values() if c > 1)
        per_file_dup += dup
        if dup:
            print(f"  {f.name}: {len(recs)} records, {len(keys)} unique keys, {dup} within-file duplicates")

    doi_from_link = sum(
        1 for _, r in iter_records(archive_dir)
        if r.get("doi") or history._doi_from_link(r.get("link", ""))  # noqa: SLF001
    )
    global_dups = sum(c - 1 for c in global_groups.values() if c > 1)
    merged_estimate = len(global_groups)

    print(f"\n  files            : {len(files)}")
    print(f"  records          : {total}")
    print(f"  with DOI (field) : {with_doi}")
    print(f"  with DOI (link)  : {doi_from_link}")
    print(f"  within-file dups : {per_file_dup}")
    print(f"  archive-unique   : {merged_estimate} (dedup across files by key)")
    print(f"  cross-file dups  : {total - merged_estimate}")
    print(f"\n  → rewrite re-keys all records to the new id scheme (doi:/arx:/title:) and removes "
          f"{per_file_dup} within-file duplicates. Cross-file duplicates ({total - merged_estimate}) "
          f"are resolved at load time by history.load_jsonl_archive (id + DOI merge), so after "
          f"re-keying future runs merge cleanly.")


def rewrite(archive_dir: Path, backup_dir: Path, remap_cache: bool, rebuild_db: bool):
    print(f"\n===== REWRITE — archive: {archive_dir} =====")
    backup_dir.mkdir(parents=True, exist_ok=True)
    id_map = {}
    total_before = 0
    total_after = 0

    for f in sorted(archive_dir.glob("data_*.jsonl")):
        if f.name.startswith("data_clean_"):
            continue
        recs = load_file_records(f)
        if not recs:
            continue
        total_before += len(recs)

        # backup original
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, backup_dir / f.name)

        # re-key + dedup within file
        groups = defaultdict(list)
        for r in recs:
            new_key = compute_record_key(r)
            id_map[r.get("id")] = new_key
            groups[new_key].append(r)
        deduped = [canonical_record(g) for g in groups.values()]
        write_file_records(f, deduped)
        total_after += len(deduped)
        print(f"  {f.name}: {len(recs)} → {len(deduped)} records (removed {len(recs) - len(deduped)})")

    print(f"\n  Total: {total_before} → {total_after} records (removed {total_before - total_after})")
    print(f"  Originals backed up to: {backup_dir}")

    if remap_cache:
        remap_llm_cache(id_map, ROOT / "data" / "llm_cache.json")
    if rebuild_db:
        rebuild_database(archive_dir, ROOT / "data" / "radar.db")


def remap_llm_cache(id_map, cache_path: Path):
    if not cache_path.exists():
        print("  [cache] llm_cache.json not found — skipped")
        return
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("  [cache] llm_cache.json is not a dict — skipped")
        return
    new_data = {}
    remapped = 0
    for old_id, value in data.items():
        new_id = id_map.get(old_id, old_id)
        if new_id != old_id:
            remapped += 1
        new_data[new_id] = value
    cache_path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [cache] remapped {remapped}/{len(data)} entries to new ids in llm_cache.json")


def rebuild_database(archive_dir: Path, db_path: Path):
    import sqlite3

    # merge full archive (id + doi) to get canonical records
    records = history.load_jsonl_archive(str(archive_dir))
    if not records:
        print("  [db] no records to seed — skipped")
        return

    con = sqlite3.connect(str(db_path))
    con.execute("DROP TABLE IF EXISTS papers")
    con.execute("DROP TABLE IF EXISTS pipeline_runs")
    con.commit()
    con.close()
    # remove stale indexes file via fresh init
    from src.database import RadarDatabase

    db = RadarDatabase(db_path)
    from src.config_loader import load_sources

    sources = load_sources("config")
    from src import history as _h
    pairs = _h.records_to_pairs(records)
    import logging as _l

    # save_papers needs SourceConfig dict; build a mapping keyed by source value
    feed_configs = None
    from src.models import SourceConfig

    src_map = {}
    for k, cfg in sources.items():
        src_map[k] = cfg
    # source value keys in records may be 'aps' etc. — matches sources keys
    saved = db.save_papers(pairs, src_map, datetime.now().isoformat(), feed_configs)
    print(f"  [db] rebuilt radar.db: seeded {saved} canonical papers from cleaned archive")


def rebuild_site(archive_dir: Path, config_dir: str):
    from src.config_loader import load_config
    from src.data_exporter import DataExporter

    config = load_config()
    exporter = DataExporter(config.output_dir if config.output_dir else "data")
    records = history.load_jsonl_archive(str(archive_dir))
    exporter.export_quarterly_jekyll(
        records,
        window_days=config.quarter_window_days,
        top_n=config.quarterly_top_n,
    )
    exporter.copy_to_jekyll_site()
    print(f"  [site] regenerated jekyll_site/_data/papers.json + quarterly.json "
          f"({len(records)} archive records)")


def main():
    parser = argparse.ArgumentParser(description="Clean up & dedup historical JSONL archive")
    parser.add_argument("--archive-dir", default="data/all", help="JSONL archive directory")
    parser.add_argument("--backup-dir", default="data/archive_pre_clean", help="Backup dir for originals")
    parser.add_argument("--dry-run", action="store_true", help="Inventory only (default behaviour without --rewrite)")
    parser.add_argument("--rewrite", action="store_true", help="Re-key + dedup archive (backup kept)")
    parser.add_argument("--remap-cache", action="store_true", help="Remap llm_cache.json ids")
    parser.add_argument("--rebuild-db", action="store_true", help="Rebuild radar.db from cleaned archive")
    parser.add_argument("--rebuild-site", action="store_true", help="Regenerate papers.json + quarterly.json")
    parser.add_argument("--config-dir", default="config", help="Config directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    archive_dir = Path(args.archive_dir)

    if args.rewrite:
        rewrite(archive_dir, Path(args.backup_dir), args.remap_cache, args.rebuild_db)
    elif args.dry_run:
        dry_run(archive_dir)
    else:
        dry_run(archive_dir)

    if args.rebuild_site:
        rebuild_site(archive_dir, args.config_dir)


if __name__ == "__main__":
    main()
