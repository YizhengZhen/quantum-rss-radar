"""
Data exporter for the Quantum RSS Radar system.
Outputs:
  1. data/all/data_YYYY-MM-DD_HHMMSS.jsonl  ← each line = 1 paper with ALL fields
  2. data/reports/report_YYYY-MM-DD_HHMMSS.md             ← all papers sorted by score desc, human‑readable
  3. jekyll_site/_data/papers.json                        ← latest data for Jekyll compilation

Note: 'category' has been removed.  Research direction is assigned by LLM
(analysis.direction).  Source colour tags come from SourceConfig.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .models import Paper, PaperAnalysis, SourceConfig, FeedConfig

logger = logging.getLogger(__name__)


class DataExporter:
    """Exports paper data to structured directories."""

    def __init__(self, base_output_dir: str = "data"):
        """
        Initialize data exporter.

        Args:
            base_output_dir: Base directory for all output files
        """
        self.base_output_dir = Path(base_output_dir)

        # Create directory structure
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "all").mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "reports").mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────
    #  1. JSONL  — one file per run, one paper per line
    # ──────────────────────────────────────────────

    def export_jsonl(self,
                     papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                     sources: Dict[str, SourceConfig],
                     timestamp: Optional[datetime] = None,
                     feed_configs: Optional[Dict[str, FeedConfig]] = None) -> Path:
        """
        Export **all** papers to a JSONL file under data/all/.

        Every line is a complete JSON object containing the original paper
        metadata *and* the AI analysis fields (score, recommendation, tldr, …).

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            sources: Source configs (for display name + colour)
            timestamp: Datetime used for the filename.  Defaults to now.

        Returns:
            Path to the created JSONL file
        """
        if timestamp is None:
            timestamp = datetime.now()
        ts = timestamp.strftime("%Y-%m-%d_%H%M%S")
        output_dir = self.base_output_dir / "all"
        output_path = output_dir / f"data_{ts}.jsonl"

        # Sort by score descending first
        sorted_pairs = sorted(
            papers_with_analyses,
            key=lambda x: x[1].relevance_score,
            reverse=True,
        )

        written = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for paper, analysis in sorted_pairs:
                record = self._paper_to_flat_dict(paper, analysis, sources, timestamp, feed_configs)
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                written += 1

        logger.info(f"Exported {written} papers to JSONL: {output_path}")
        return output_path

    # ──────────────────────────────────────────────
    #  2. Markdown — all papers, score‑sorted, human‑readable
    # ──────────────────────────────────────────────

    def export_markdown(self,
                        papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                        sources: Dict[str, SourceConfig],
                        timestamp: Optional[datetime] = None,
                        feed_configs: Optional[Dict[str, FeedConfig]] = None) -> Path:
        """
        Export **all** papers as a single Markdown file under data/reports/.

        Papers are sorted by score (descending).  Each paper gets a section
        with all metadata, AI analysis fields, and the RSS source.
        """
        if timestamp is None:
            timestamp = datetime.now()
        ts = timestamp.strftime("%Y-%m-%d_%H%M%S")
        date_only = timestamp.strftime("%Y-%m-%d")
        output_dir = self.base_output_dir / "reports"
        output_path = output_dir / f"report_{ts}.md"

        # Sort by score descending
        sorted_pairs = sorted(
            papers_with_analyses,
            key=lambda x: x[1].relevance_score,
            reverse=True,
        )

        lines: List[str] = []
        lines.append("# Quantum RSS Radar — Daily Report")
        lines.append("")
        lines.append(f"**Date**: {date_only}  |  **Generated**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"**Total papers**: {len(sorted_pairs)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for idx, (paper, analysis) in enumerate(sorted_pairs, 1):
            # Resolve display name: feed-level first, then source-level
            feed_cfg = feed_configs.get(paper.feed_name) if feed_configs else None
            if feed_cfg and feed_cfg.display_name:
                src_display = feed_cfg.display_name
            else:
                src_cfg = sources.get(paper.source.value)
                src_display = src_cfg.display_name if src_cfg else paper.source.value

            lines.append(f"## {idx}. {paper.title}")
            lines.append("")
            lines.append(f"- **Score**: {analysis.relevance_score:.1f} / 10  |  "
                         f"**Recommended**: {'✅ Yes' if analysis.recommendation else '❌ No'}")
            lines.append(f"- **Source**: {src_display}  |  **Feed**: {paper.feed_name}")
            lines.append(f"- **Direction**: {analysis.direction}")
            lines.append(f"- **Published**: {paper.published.strftime('%Y-%m-%d')}")
            lines.append(f"- **Authors**: {', '.join(paper.authors)}")
            lines.append(f"- **Link**: [{paper.link}]({paper.link})")
            if paper.tags:
                lines.append(f"- **Tags**: `{'`  `'.join(paper.tags)}`")
            lines.append("")
            lines.append("### TL;DR")
            lines.append("")
            lines.append(analysis.tldr or "*Not provided*")
            lines.append("")
            if analysis.motivation:
                lines.append("### Motivation")
                lines.append("")
                lines.append(analysis.motivation)
                lines.append("")
            if analysis.method:
                lines.append("### Method")
                lines.append("")
                lines.append(analysis.method)
                lines.append("")
            if analysis.result:
                lines.append("### Result")
                lines.append("")
                lines.append(analysis.result)
                lines.append("")
            if analysis.conclusion:
                lines.append("### Conclusion")
                lines.append("")
                lines.append(analysis.conclusion)
                lines.append("")
            if analysis.keywords:
                lines.append(f"*Keywords: {', '.join(analysis.keywords)}*")
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Exported report with {len(sorted_pairs)} papers: {output_path}")
        return output_path

    # ──────────────────────────────────────────────
    #  3.  Jekyll copy — reads latest JSONL → _data/papers.json
    # ──────────────────────────────────────────────

    def copy_to_jekyll_site(self, jekyll_site_dir: str = "jekyll_site"):
        """
        Read the most recent JSONL file under data/all/ and write a
        Jekyll‑compatible **papers.json** into jekyll_site/_data/.
        """
        jekyll_site_path = Path(jekyll_site_dir)
        if not jekyll_site_path.exists():
            logger.warning(f"Jekyll site directory not found: {jekyll_site_path}")
            return

        # Find the latest JSONL
        all_dir = self.base_output_dir / "all"
        jsonl_files = sorted(all_dir.glob("data_*.jsonl"), reverse=True)
        if not jsonl_files:
            logger.warning("No JSONL files found under data/all/, cannot copy to Jekyll")
            return

        latest_jsonl = jsonl_files[0]

        # Read all lines
        records: List[Dict[str, Any]] = []
        with open(latest_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        # Build Jekyll data structure
        jekyll_data = self._records_to_jekyll_data(records)

        # Write
        target_dir = jekyll_site_path / "_data"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "papers.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(jekyll_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Copied {len(records)} papers to Jekyll site: {target_file}")

    # ──────────────────────────────────────────────
    #  Internal helpers
    # ──────────────────────────────────────────────

    @staticmethod
    def _paper_to_flat_dict(paper: Paper,
                            analysis: PaperAnalysis,
                            sources: Dict[str, SourceConfig],
                            run_timestamp: datetime,
                            feed_configs: Optional[Dict[str, FeedConfig]] = None) -> Dict[str, Any]:
        """Flatten a Paper + PaperAnalysis into a single dict for JSONL."""
        # Resolve display name and colour: feed-level first, then source-level
        feed_cfg = feed_configs.get(paper.feed_name) if feed_configs else None
        if feed_cfg and feed_cfg.display_name and feed_cfg.color:
            src_display = feed_cfg.display_name
            src_color = feed_cfg.color
        else:
            src_cfg = sources.get(paper.source.value)
            src_display = src_cfg.display_name if src_cfg else paper.source.value
            src_color = src_cfg.color if src_cfg else "#757575"

        return {
            # — paper metadata —
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "link": paper.link,
            "published_date": paper.published.isoformat(),
            "source": paper.source.value,
            "source_display_name": src_display,
            "source_color": src_color,
            "feed_name": paper.feed_name,
            "tags": paper.tags,
            "rss_fetch_date": paper.rss_fetch_date.isoformat(),

            # — AI analysis —
            "score": analysis.relevance_score,
            "recommended": analysis.recommendation,
            "direction": analysis.direction,
            "tldr": analysis.tldr,
            "motivation": analysis.motivation,
            "method": analysis.method,
            "result": analysis.result,
            "conclusion": analysis.conclusion,
            "keywords": analysis.keywords,
            "analysis_timestamp": analysis.processing_time.isoformat(),

            # — deep reading (optional) —
            "deep_read": analysis.deep_read.model_dump() if analysis.deep_read else None,

            # — pipeline metadata —
            "pipeline_run": run_timestamp.isoformat(),
        }

    @staticmethod
    def _records_to_jekyll_data(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert a list of flat dicts (from JSONL) into Jekyll‑compatible structure."""
        papers = []
        sources_data: Dict[str, Dict[str, Any]] = {}
        directions_data: Dict[str, Dict[str, Any]] = {}

        for rec in records:
            src_id = rec.get("source", "other")
            if src_id not in sources_data:
                sources_data[src_id] = {
                    "name": rec.get("source_display_name", src_id),
                    "color": rec.get("source_color", "#757575"),
                    "count": 0,
                    "recommended_count": 0,
                }

            direction = rec.get("direction", "General / Other") or "General / Other"
            if direction not in directions_data:
                directions_data[direction] = {
                    "name": direction,
                    "count": 0,
                    "recommended_count": 0,
                }

            paper_entry = {
                "id": rec["id"],
                "title": rec["title"],
                "authors": rec.get("authors", []),
                "abstract": rec.get("abstract", ""),
                "link": rec.get("link", ""),
                "date": rec.get("published_date", ""),
                "published_date": rec.get("published_date", "")[:10] if rec.get("published_date") else "",
                "source": src_id,
                "source_display_name": rec.get("source_display_name", src_id),
                "source_color": rec.get("source_color", "#757575"),
                "direction": direction,
                "feed_name": rec.get("feed_name", ""),
                "tags": rec.get("tags", []),
                "score": rec.get("score", 0),
                "recommended": rec.get("recommended", False),
                "analysis": {
                    "tldr": rec.get("tldr", ""),
                    "motivation": rec.get("motivation", ""),
                    "method": rec.get("method", ""),
                    "result": rec.get("result", ""),
                    "conclusion": rec.get("conclusion", ""),
                    "keywords": rec.get("keywords", []),
                    "direction": direction,
                    "processing_time": rec.get("analysis_timestamp", ""),
                },
                "deep_read": rec.get("deep_read"),
            }
            papers.append(paper_entry)
            sources_data[src_id]["count"] += 1
            directions_data[direction]["count"] += 1
            if rec.get("recommended"):
                sources_data[src_id]["recommended_count"] += 1
                directions_data[direction]["recommended_count"] += 1

        all_dates = sorted(
            set(p["published_date"] for p in papers if p["published_date"]),
            reverse=True,
        )
        recommended_count = sum(1 for p in papers if p["recommended"])

        return {
            "papers": papers,
            "sources": sources_data,
            "directions": directions_data,
            "dates": all_dates,
            "stats": {
                "total_papers": len(papers),
                "recommended_papers": recommended_count,
                "total_sources": len(sources_data),
                "total_directions": len(directions_data),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    # ──────────────────────────────────────────────
    #  Convenience: run both exports + Jekyll copy
    # ──────────────────────────────────────────────

    def export_all(self,
                   papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                   sources: Dict[str, SourceConfig],
                   timestamp: Optional[datetime] = None,
                   feed_configs: Optional[Dict[str, FeedConfig]] = None) -> Dict[str, str]:
        """
        Run JSONL export + Markdown export + Jekyll copy in one call.

        Returns:
            Dict with keys "jsonl" and "markdown" mapping to file paths.
        """
        if timestamp is None:
            timestamp = datetime.now()

        jsonl_path = self.export_jsonl(papers_with_analyses, sources, timestamp, feed_configs)
        md_path = self.export_markdown(papers_with_analyses, sources, timestamp, feed_configs)
        self.copy_to_jekyll_site()

        return {"jsonl": str(jsonl_path), "markdown": str(md_path)}
