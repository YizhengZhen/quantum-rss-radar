#!/usr/bin/env python3
"""Analyze historical AI analysis results from JSONL data.

Usage:
    uv run python scripts/inspect_results.py
    uv run python scripts/inspect_results.py --source PRA       # filter by source
    uv run python scripts/inspect_results.py --after 2026-06-05  # only recent runs
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import re

DATA_DIR = Path("data/all")
SOURCES_ORDER = [
    "arXiv: Physics", "arXiv: Computer Science", "arXiv: Math",
    "Nature Physics", "Nature Photonics", "Nature Communications", "Nature Reviews Physics",
    "Physical Review A", "Physical Review B", "Physical Review E",
    "Physical Review Letters", "Physical Review X", "Physical Review Research",
    "PRX Quantum", "Quantum", "New Journal of Physics",
    "npj Quantum Information", "Reports on Progress in Physics",
    "Reviews of Modern Physics", "PNAS", "IEEE"
]

def load_all_papers(data_dir: Path = DATA_DIR):
    """Load all JSONL files into a list of dicts."""
    files = sorted(data_dir.glob("*.jsonl"))
    if not files:
        print(f"❌ No JSONL files found in {data_dir}")
        sys.exit(1)

    papers = []
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    papers.append((f.name, json.loads(line)))
    return papers

def filter_papers(papers, source_filter=None, after_date=None):
    result = []
    for fname, p in papers:
        if source_filter:
            src = (p.get("source_display_name") or p.get("source") or "").lower()
            if source_filter.lower() not in src:
                continue
        if after_date:
            ts = p.get("published_date") or p.get("analysis_timestamp") or ""
            if not ts or ts[:10] < after_date:
                continue
        result.append((fname, p))
    return result

def basic_stats(papers):
    """Print basic stats about the dataset."""
    total = len(papers)
    scored = [p for _, p in papers if p.get("score") is not None]
    recommended = [p for _, p in papers if p.get("recommended") is True]
    
    # Source distribution
    source_counter = Counter()
    for _, p in papers:
        src = p.get("source_display_name") or p.get("source") or "unknown"
        source_counter[src] += 1
    
    # Direction distribution
    dir_counter = Counter()
    for _, p in papers:
        d = p.get("direction") or "No Direction"
        dir_counter[d] += 1
    
    return total, scored, recommended, source_counter, dir_counter

def print_stats(papers, label="All Papers"):
    total, scored, recommended, source_counter, dir_counter = basic_stats(papers)
    
    print(f"\n{'='*60}")
    print(f"📊  {label}")
    print(f"{'='*60}")
    print(f"Total papers:         {total}")
    print(f"With AI analysis:     {len(scored)} ({len(scored)/total*100:.0f}%)" if total else "With AI analysis:     0")
    print(f"Recommended (≥EMAIL_MIN_SCORE=7.0): {len(recommended)} ({len(recommended)/total*100:.0f}%)" if total else "")
    
    if scored:
        scores = [p.get("score", 0) for _, p in scored]
        print(f"\n📈  Score Distribution:")
        print(f"   Mean:      {sum(scores)/len(scores):.2f}")
        print(f"   Median:    {sorted(scores)[len(scores)//2]}")
        print(f"   Range:     {min(scores):.1f} – {max(scores):.1f}")
        
        # Histogram
        buckets = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10)]
        print(f"\n   Histogram:")
        for lo, hi in buckets:
            count = sum(1 for s in scores if lo <= s < hi)
            bar = "█" * max(1, count // max(1, max(1, len(scores)//40)))
            print(f"   [{lo:>2}-{hi:<2}) {count:>4}  {bar}")
        print(f"   [10]       {sum(1 for s in scores if s == 10)}")
    else:
        print("\n⚠️  No scores found (papers may not have been analyzed by LLM yet)")
    
    # Top sources
    print(f"\n📡  Top Sources:")
    total_src = sum(source_counter.values())
    for src, count in source_counter.most_common(15):
        bar = "█" * max(1, count * 40 // total_src)
        print(f"   {src:<30} {count:>4}  {bar}")
    
    # Direction distribution
    print(f"\n🔬  Research Direction Distribution:")
    total_dir = sum(dir_counter.values())
    for d, count in dir_counter.most_common(20):
        bar = "█" * max(1, count * 40 // total_dir)
        print(f"   {d:<35} {count:>4}  {bar}")
    
    return scored

def print_samples(papers, n=5, min_score=None, max_score=None):
    """Print detailed samples."""
    filtered = [(f, p) for f, p in papers 
                if p.get("score") is not None]
    if min_score is not None:
        filtered = [(f, p) for f, p in filtered if p.get("score", 0) >= min_score]
    if max_score is not None:
        filtered = [(f, p) for f, p in filtered if p.get("score", 0) <= max_score]
    
    if not filtered:
        print("   (no matching papers)")
        return
    
    filtered = sorted(filtered, key=lambda x: x[1].get("score", 0), reverse=True)[:n]
    
    for i, (fname, p) in enumerate(filtered, 1):
        score = p.get("score", 0)
        rec = "⭐ RECOMMENDED" if p.get("recommended") else ""
        direction = p.get("direction") or "No Direction"
        source = p.get("source_display_name") or p.get("source") or "?"
        title = p.get("title", "?")[:100]
        tldr = (p.get("tldr") or "N/A")[:120]
        keywords = (p.get("keywords") or "")
        if isinstance(keywords, str):
            kw = keywords[:80]
        else:
            kw = ", ".join(keywords)[:80]
        
        print(f"\n  {'─'*55}")
        print(f"  #{i} [{direction}] {title}")
        print(f"  Score: {score}/10 {rec}  |  Source: {source}")
        print(f"  TL;DR: {tldr}")
        print(f"  Keywords: {kw}")

def analyze_source_scores(papers):
    """Print per-source score stats."""
    source_scores = defaultdict(list)
    for _, p in papers:
        src = p.get("source_display_name") or p.get("source") or "unknown"
        s = p.get("score")
        if s is not None:
            source_scores[src].append(s)
    
    print(f"\n{'='*60}")
    print("📊  Per-Source Score Stats")
    print(f"{'='*60}")
    print(f"   {'Source':<30} {'Count':>5} {'Avg':>5} {'Med':>5} {'≥7.0':>5} {'≥9.0':>5}")
    print(f"   {'─'*56}")
    
    # Sort by count desc
    for src in sorted(source_scores, key=lambda s: len(source_scores[s]), reverse=True):
        scores = source_scores[src]
        avg = sum(scores)/len(scores)
        med = sorted(scores)[len(scores)//2]
        hi7 = sum(1 for s in scores if s >= 7.0)
        hi9 = sum(1 for s in scores if s >= 9.0)
        print(f"   {src:<30} {len(scores):>5} {avg:>5.1f} {med:>5.1f} {hi7:>5} {hi9:>5}")

def analyze_score_trend(papers):
    """Show score trend over time."""
    daily = defaultdict(list)
    for fname, p in papers:
        # Get date from filename
        m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
        if m:
            date = m.group(1)
            s = p.get("score")
            if s is not None:
                daily[date].append(s)
    
    if not daily:
        return
    
    print(f"\n{'='*60}")
    print("📈  Score Trend Over Time")
    print(f"{'='*60}")
    for date in sorted(daily):
        scores = daily[date]
        avg = sum(scores)/len(scores)
        med = sorted(scores)[len(scores)//2]
        hi7 = sum(1 for s in scores if s >= 7.0)
        bar = "█" * min(40, int(avg * 4))
        print(f"   {date}  avg={avg:>4.1f}  med={med:>4.1f}  ≥7={hi7:>3}/{len(scores):<3} {bar}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze historical AI analysis results")
    parser.add_argument("--source", help="Filter by source (e.g. PRA, arXiv, Nature)")
    parser.add_argument("--after", help="Only include files after this date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    print("📡  Loading Quantum RSS Radar historical data...")
    papers = load_all_papers()
    print(f"   Loaded {len(papers)} papers from {len(set(f for f,_ in papers))} JSONL files")
    
    if args.source or args.after:
        papers = filter_papers(papers, source_filter=args.source, after_date=args.after)
        label_parts = []
        if args.source: label_parts.append(f"source={args.source}")
        if args.after: label_parts.append(f"after={args.after}")
        label = ", ".join(label_parts)
    else:
        label = "All Papers"
    
    scored = print_stats(papers, label)
    
    if scored:
        analyze_source_scores(papers)
        analyze_score_trend(papers)
        
        # Show samples
        print(f"\n{'='*60}")
        print("🏆  Top-5 Papers (Highest Score)")
        print(f"{'='*60}")
        print_samples(papers, n=5)
        
        print(f"\n{'='*60}")
        print("❌  Bottom-5 Papers (Lowest Score, non-zero)")
        print(f"{'='*60}")
        print_samples(papers, n=5, max_score=3.0)
        
        # Papers that scored 0
        zero_scored = [(f, p) for f, p in papers if p.get("score") == 0]
        if zero_scored:
            print(f"\n{'='*60}")
            print(f"⚠️  Papers with Score = 0: {len(zero_scored)} papers")
            print(f"{'='*60}")
            print_samples(zero_scored, n=3)

if __name__ == "__main__":
    main()
