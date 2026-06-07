#!/usr/bin/env python3
"""Analyze historical AI analysis results from JSONL data.

Usage:
    uv run python scripts/inspect_results.py [--feed PRA] [--source arXiv] [--after 2026-06-05]
"""

import json, sys, re
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path("data/all")

def load_all_papers():
    files = sorted(DATA_DIR.glob("*.jsonl"))
    if not files:
        print(f"NO JSONL files in {DATA_DIR}")
        sys.exit(1)
    papers = []
    for f in files:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    papers.append((f.name, json.loads(line)))
    return papers

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Filter by source_display_name (e.g. arXiv, APS, Nature)")
    parser.add_argument("--feed", help="Filter by feed_name (e.g. PRA, PRX, Quantum)")
    parser.add_argument("--after", help="Only include data after YYYY-MM-DD")
    args = parser.parse_args()

    print("Loading data...")
    all_papers = load_all_papers()
    print(f"  {len(all_papers)} papers from {len(set(f for f,_ in all_papers))} JSONL files")

    papers = all_papers
    if args.source:
        papers = [(f, p) for f, p in papers if (p.get("source_display_name") or p.get("source") or "").lower() == args.source.lower()]
    if args.feed:
        papers = [(f, p) for f, p in papers if args.feed.lower() in (p.get("feed_name") or "").lower()]
    if args.after:
        papers = [(f, p) for f, p in papers if (p.get("analysis_timestamp") or p.get("published_date") or "")[:10] >= args.after]

    label_parts = []
    if args.source: label_parts.append(f"source={args.source}")
    if args.feed: label_parts.append(f"feed={args.feed}")
    if args.after: label_parts.append(f"after={args.after}")
    label = " | ".join(label_parts) if label_parts else "All Papers"

    total = len(papers)
    if total == 0:
        print(f"\n  No papers match: {label}")
        return

    scored = [(f, p) for f, p in papers if p.get("score") is not None]
    recommended = [(f, p) for f, p in papers if p.get("recommended") is True]

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Total papers:              {total}")
    print(f"  With AI analysis:          {len(scored)} ({len(scored)/total*100:.0f}%)")
    print(f"  Recommended (>=7.0):       {len(recommended)} ({len(recommended)/total*100:.0f}%)")

    if scored:
        scores = [p["score"] for _, p in scored]
        print(f"\n  Score Distribution:")
        print(f"    Mean:   {sum(scores)/len(scores):.2f}")
        print(f"    Median: {sorted(scores)[len(scores)//2]}")
        print(f"    Range:  {min(scores):.1f} - {max(scores):.1f}")

        buckets = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10.1)]
        for lo, hi in buckets:
            count = sum(1 for s in scores if lo <= s < hi)
            bar = "#" * max(1, count // max(1, len(scores)//60))
            print(f"    [{lo:>2}-{hi:<4.0f}) {count:>4}  {bar}")

    # Source / Feed / Direction distribution
    src_c = Counter()
    feed_c = Counter()
    dir_c = Counter()
    for _, p in papers:
        src_c[p.get("source_display_name") or p.get("source") or "?"] += 1
        feed_c[p.get("feed_name") or "?"] += 1
        dir_c[p.get("direction") or "No Direction"] += 1

    print(f"\n  Sources:")
    for s, c in src_c.most_common():
        print(f"    {s:<35} {c:>4}")

    print(f"\n  Feeds:")
    for s, c in feed_c.most_common():
        print(f"    {s:<35} {c:>4}")

    print(f"\n  Research Direction Distribution:")
    for d, c in dir_c.most_common(20):
        print(f"    {d:<40} {c:>4}")

    # Per-feed score stats
    if scored:
        feed_scores = defaultdict(list)
        for _, p in scored:
            feed_scores[p.get("feed_name") or "?"].append(p["score"])
        print(f"\n  Per-Feed Score Stats:")
        print(f"    {'Feed':<35} {'Cnt':>4} {'Avg':>4} {'>=7':>4}")
        for feed in sorted(feed_scores, key=lambda s: len(feed_scores[s]), reverse=True):
            ss = feed_scores[feed]
            avg = sum(ss)/len(ss)
            hi7 = sum(1 for s in ss if s >= 7.0)
            print(f"    {feed:<35} {len(ss):>4} {avg:>4.1f} {hi7:>4}")

    # Daily trend
    if scored:
        daily = defaultdict(list)
        for fname, p in scored:
            m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
            if m:
                daily[m.group(1)].append(p["score"])
        print(f"\n  Score Trend Over Time:")
        for date in sorted(daily):
            ss = daily[date]
            avg = sum(ss)/len(ss)
            hi7 = sum(1 for s in ss if s >= 7.0)
            bar = "#" * min(50, int(avg * 5))
            print(f"    {date}  avg={avg:>4.1f}  >=7={hi7:>3}/{len(ss):<3}  {bar}")

    # Top-5
    if scored:
        print(f"\n{'='*60}")
        print("  TOP-5 HIGHEST SCORED PAPERS")
        print(f"{'='*60}")
        top5 = sorted(scored, key=lambda x: x[1]["score"], reverse=True)[:5]
        for i, (_, p) in enumerate(top5, 1):
            score = p["score"]
            rec = " RECOMMENDED" if p.get("recommended") else ""
            direction = p.get("direction") or "?"
            feed = p.get("feed_name") or p.get("source") or "?"
            title = (p.get("title") or "?")[:90]
            tldr = (p.get("tldr") or "N/A")[:100]
            print(f"\n  #{i} [{direction}] {title}")
            print(f"     Score: {score}/10{rec}  |  {feed}")
            print(f"     TL;DR: {tldr}")

        # Bottom-5 (score > 0)
        low = [(f, p) for f, p in scored if 0 < p["score"] < 4]
        low = sorted(low, key=lambda x: x[1]["score"])[:5]
        if low:
            print(f"\n{'─'*60}")
            print("  BOTTOM-5 LOWEST (non-zero)")
            print(f"{'─'*60}")
            for i, (_, p) in enumerate(low, 1):
                print(f"  #{i} [score={p['score']}] [{p.get('direction','?')}] {(p.get('title') or '?')[:80]}")
                print(f"     Feed: {p.get('feed_name') or p.get('source') or '?'}")

        # Zero scores
        zero = [(f, p) for f, p in scored if p["score"] == 0]
        if zero:
            print(f"\n{'─'*60}")
            print(f"  SCORE = 0: {len(zero)} papers")
            print(f"{'─'*60}")
            for i, (_, p) in enumerate(zero[:5], 1):
                title = (p.get("title") or "?")[:80]
                feed = p.get("feed_name") or p.get("source") or "?"
                print(f"  #{i} [{feed}] {title}")

    print()

if __name__ == "__main__":
    main()
