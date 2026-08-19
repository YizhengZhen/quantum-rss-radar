#!/usr/bin/env python3
"""A/B test: re-analyze historical papers with a NEW research_directions.md.

Compares old scores (from JSONL) with new scores (fresh LLM call)
to evaluate whether the tier-based direction writing improves scoring quality.

Usage:
    # Run on a sample of 20 papers (default):
    uv run python scripts/rerun_analysis.py

    # Run on a specific JSONL file with 50 papers:
    uv run python scripts/rerun_analysis.py data/all/data_2026-06-05_084953.jsonl --sample 50

    # Run on the latest JSONL with all papers (will cost API calls):
    uv run python scripts/rerun_analysis.py --sample all

    # Only show stats of what would be analyzed (no API call):
    uv run python scripts/rerun_analysis.py --dry-run
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# ── Add src to path so we can import project modules ─────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import load_config, load_research_directions
from src.models import Paper, PaperSource
from src.semantic_analyzer import SemanticAnalyzer

DATA_DIR = Path("data/all")


def load_latest_jsonl() -> Path:
    # data/all is per-source now (data/all/<source>/data_*.jsonl) — recurse.
    import re

    files = list(DATA_DIR.glob("**/*.jsonl"))
    if not files:
        print(f"  No JSONL files in {DATA_DIR}")
        sys.exit(1)

    def _ts(p: Path) -> str:
        m = re.search(r"data_(\d{4}-\d{2}-\d{2}_\d{6})", p.name)
        return m.group(1) if m else p.name

    return max(files, key=_ts)


def load_papers_from_jsonl(path: Path, sample: int = 0):
    """Load papers from a JSONL file. Each line has one paper as a flat dict."""
    papers_raw = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                papers_raw.append(json.loads(line))

    # Skip papers without abstract
    papers_with_abstract = [
        p for p in papers_raw if p.get("abstract") and len(p["abstract"]) > 50
    ]
    skipped = len(papers_raw) - len(papers_with_abstract)

    if sample and sample < len(papers_with_abstract):
        # Take a balanced sample: mix of low/med/high scores
        papers_with_abstract.sort(key=lambda p: p.get("score") or 0)
        n = sample
        step = max(1, len(papers_with_abstract) // n)
        sampled = [
            papers_with_abstract[i] for i in range(0, len(papers_with_abstract), step)
        ][:n]
    else:
        sampled = papers_with_abstract

    print(f"  Total lines:        {len(papers_raw)}")
    print(f"  With abstract:      {len(papers_with_abstract)}")
    print(f"  Skipped (no abs):   {skipped}")
    print(f"  Sample:             {len(sampled)}")

    return sampled


def dict_to_paper(d: dict) -> Paper:
    """Convert a flat JSONL dict to a Paper model."""
    pub_str = d.get("published_date")
    if pub_str:
        try:
            published = datetime.fromisoformat(pub_str)
        except (ValueError, TypeError):
            published = datetime(2026, 1, 1)
    else:
        published = datetime(2026, 1, 1)
    return Paper(
        id=d.get("id", ""),
        title=d.get("title", ""),
        authors=d.get("authors", []),
        abstract=d.get("abstract", ""),
        link=d.get("link", ""),
        source=PaperSource[d.get("source", "arxiv").upper()]
        if d.get("source", "").upper() in PaperSource.__members__
        else PaperSource.ARXIV,
        published=published,
        feed_name=d.get("feed_name", ""),
    )


def format_comparison(old_score, old_dir, new_score, new_dir, title):
    """Format a single paper comparison line."""
    delta = (
        new_score - old_score if old_score is not None and new_score is not None else 0
    )
    old_str = f"{old_score:>4.1f}" if old_score is not None else " N/A"
    new_str = f"{new_score:>4.1f}" if new_score is not None else " N/A"
    delta_str = (
        f"{delta:+4.1f}" if old_score is not None and new_score is not None else "  N/A"
    )
    dir_change = " ✓" if old_dir != new_dir and new_dir != "General / Other" else ""
    return f"  {old_str} → {new_str} ({delta_str})  [{old_dir} → {new_dir}]{dir_change}  {title[:70]}"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A/B test new research_directions.md")
    parser.add_argument("jsonl", nargs="?", help="Path to JSONL file (default: latest)")
    parser.add_argument(
        "--sample",
        default="20",
        help="Number of papers to analyze. 'all' for all. (default: 20)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show stats, no API calls"
    )
    args = parser.parse_args()

    # ── 1. Load papers ──────────────────────────────────────────
    jsonl_path = Path(args.jsonl) if args.jsonl else load_latest_jsonl()
    if not jsonl_path.exists():
        print(f"  File not found: {jsonl_path}")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"📄  Loading data from: {jsonl_path.name}")
    print(f"{'=' * 60}")

    sample = 0 if args.sample == "all" else int(args.sample)
    papers_raw = load_papers_from_jsonl(jsonl_path, sample=sample)

    if args.dry_run:
        # Just show stats
        old_scores = [p.get("score") for p in papers_raw if p.get("score") is not None]
        old_directions = Counter(
            p.get("direction") or "General / Other" for p in papers_raw
        )

        print(f"\n📊  Old Score Stats ({len(old_scores)} papers with scores):")
        print(f"    Mean:   {sum(old_scores) / len(old_scores):.2f}")
        print(f"    Median: {sorted(old_scores)[len(old_scores) // 2]}")
        print(f"    Range:  {min(old_scores):.1f} - {max(old_scores):.1f}")

        print("\n📊  Old Direction Distribution:")
        for d, c in old_directions.most_common():
            print(f"    {d:<40} {c:>4}")

        print("\n📊  Estimated cost (if run with --sample all):")
        print(f"    Papers to analyze: {len(papers_raw)}")
        print(f"    ~{len(papers_raw) * 800} input tokens")
        print(f"    ~{len(papers_raw) * 300} output tokens")
        print("    (actual cost depends on your LLM provider)")

        print("\n📊  To actually run the comparison, omit --dry-run:")
        print(
            f"    uv run python scripts/rerun_analysis.py {jsonl_path.name} --sample 20"
        )
        return

    # ── 2. Initialize analyzer with NEW research_directions ──────
    print(f"\n{'=' * 60}")
    print("🤖  Initializing LLM analyzer with NEW research_directions.md...")
    print(f"{'=' * 60}")

    config = load_config()
    new_directions = load_research_directions()
    print(f"  New directions: {len(new_directions)} chars")

    analyzer = SemanticAnalyzer(config)
    analyzer.load_research_directions(new_directions)

    # ── 3. Re-analyze each paper ─────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"🔄  Re-analyzing {len(papers_raw)} papers (this calls the LLM)...")
    print(f"{'=' * 60}")

    old_scores = []
    new_scores = []
    comparisons = []

    old_dir_counter = Counter()
    new_dir_counter = Counter()

    for i, p_raw in enumerate(papers_raw, 1):
        paper = dict_to_paper(p_raw)
        old_score = p_raw.get("score")
        old_dir = p_raw.get("direction") or "General / Other"
        old_dir_counter[old_dir] += 1

        try:
            analysis = analyzer.analyze_paper(paper, new_directions)
            new_score = analysis.relevance_score
            new_dir = analysis.direction or "General / Other"
            new_dir_counter[new_dir] += 1

            print(
                f"\n  [{i}/{len(papers_raw)}] "
                f"old={old_score or 'N/A':>4} → new={new_score:>4.1f}  "
                f"[{old_dir[:20]:<20} → {new_dir[:20]:<20}]"
            )
            print(f"         {paper.title[:80]}")

            comparisons.append((paper, p_raw, analysis))
            old_scores.append(old_score)
            new_scores.append(new_score)

        except Exception as e:
            print(f"\n  [{i}/{len(papers_raw)}] ⚠️  FAILED: {e}")
            print(f"         {paper.title[:80]}")

    # ── 4. Summary comparison ────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("📊  COMPARISON SUMMARY")
    print(f"{'=' * 60}")

    # Score stats
    old_clean = [s for s in old_scores if s is not None]
    print("\n  Score Stats:")
    print(f"    {'':>20} {'Old':>8} {'New':>8} {'Δ':>8}")
    print(f"    {'─' * 44}")
    print(f"    {'Count':>20} {len(old_clean):>8} {len(new_scores):>8} {'':>8}")
    if old_clean and new_scores:
        old_mean = sum(old_clean) / len(old_clean)
        new_mean = sum(new_scores) / len(new_scores)
        print(
            f"    {'Mean':>20} {old_mean:>8.2f} {new_mean:>8.2f} {new_mean - old_mean:>+8.2f}"
        )
        old_med = sorted(old_clean)[len(old_clean) // 2]
        new_med = sorted(new_scores)[len(new_scores) // 2]
        print(
            f"    {'Median':>20} {old_med:>8.1f} {new_med:>8.1f} {new_med - old_med:>+8.1f}"
        )
        print(
            f"    {'Min':>20} {min(old_clean):>8.1f} {min(new_scores):>8.1f} {min(new_scores) - min(old_clean):>+8.1f}"
        )
        print(
            f"    {'Max':>20} {max(old_clean):>8.1f} {max(new_scores):>8.1f} {max(new_scores) - max(old_clean):>+8.1f}"
        )

        # Score distribution comparison
        print("\n  Score Distribution (Old vs New):")
        print(f"    {'Range':>8} {'Old':>6} {'New':>6}")
        for lo in range(0, 10):
            old_c = sum(1 for s in old_clean if lo <= s < lo + 1)
            new_c = sum(1 for s in new_scores if lo <= s < lo + 1)
            bar_old = "█" * max(1, old_c * 20 // max(1, len(old_clean)))
            bar_new = "█" * max(1, new_c * 20 // max(1, len(new_scores)))
            print(
                f"    [{lo}-{lo + 1}) {old_c:>4}/{new_c:>4}  old:{bar_old:<20} new:{bar_new}"
            )
        old_10 = sum(1 for s in old_clean if s >= 10)
        new_10 = sum(1 for s in new_scores if s >= 10)
        print(f"    [10]     {old_10:>4}/{new_10:>4}")

    # Direction distribution comparison
    print("\n  Direction Distribution (Old → New):")
    all_dirs = sorted(set(list(old_dir_counter.keys()) + list(new_dir_counter.keys())))
    for d in all_dirs:
        old_c = old_dir_counter.get(d, 0)
        new_c = new_dir_counter.get(d, 0)
        arrow = " → " if old_c != new_c else "    "
        print(f"    {d:<40} {old_c:>4}{arrow}{new_c:>4}")

    # Show interesting examples
    print(f"\n{'=' * 60}")
    print("🔍  INTERESTING CHANGES")
    print(f"{'=' * 60}")

    # Biggest increases
    def delta_key(x):
        p_raw, score = x[1], x[2].relevance_score
        old_s = p_raw.get("score")
        if old_s is not None and score is not None:
            return score - old_s
        return -999

    sorted_by_delta = sorted(comparisons, key=delta_key, reverse=True)
    print("\n  📈  Biggest Score INCREASES (Top 5):")
    for paper, p_raw, analysis in sorted_by_delta[:5]:
        old_s = p_raw.get("score") or 0
        print(
            f"    {old_s:>4.1f} → {analysis.relevance_score:>4.1f} ({analysis.relevance_score - old_s:+>4.1f})  [{p_raw.get('direction', '?')} → {analysis.direction}]"
        )
        print(f"           {paper.title[:80]}")

    # Biggest decreases
    sorted_by_delta_desc = sorted(comparisons, key=delta_key)
    print("\n  📉  Biggest Score DECREASES (Top 5):")
    for paper, p_raw, analysis in sorted_by_delta_desc[:5]:
        old_s = p_raw.get("score") or 0
        print(
            f"    {old_s:>4.1f} → {analysis.relevance_score:>4.1f} ({analysis.relevance_score - old_s:+>4.1f})  [{p_raw.get('direction', '?')} → {analysis.direction}]"
        )
        print(f"           {paper.title[:80]}")

    # Direction change summary
    dir_changes = []
    for paper, p_raw, analysis in comparisons:
        old_dir = p_raw.get("direction") or "General / Other"
        new_dir = analysis.direction or "General / Other"
        if (
            old_dir != new_dir
            and new_dir != "General / Other"
            and p_raw.get("score", 0) < 5
        ):
            dir_changes.append((p_raw, paper, analysis))
    if dir_changes:
        print(
            "\n  🔄  Papers that moved FROM Other/Other TO a meaningful direction (show up to 5):"
        )
        for p_raw, paper, analysis in dir_changes[:5]:
            old_s = p_raw.get("score") or 0
            print(
                f"    {old_s:>4.1f} → {analysis.relevance_score:>4.1f}  [{p_raw.get('direction', '?')} → {analysis.direction}]"
            )
            print(f"           {paper.title[:80]}")

    print(f"\n{'=' * 60}")
    print("✅  Comparison complete!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
