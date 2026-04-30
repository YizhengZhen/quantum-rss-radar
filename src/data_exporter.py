"""
Data exporter for the Quantum RSS Radar system.
Supports multiple output formats: JSON (papers/), Markdown (reports/), and Jekyll site copy.

Directory structure:
  data/
  ├── raw/                           ← RSS raw fetch archives (unchanged)
  ├── papers/
  │   ├── papers_2026-04-09.json     ← Daily: all papers + AI analysis
  │   ├── papers_2026-04-10.json
  │   └── latest.json                ← Copy of the latest for Jekyll reference
  ├── reports/
  │   └── recommendations_2026-04-09.md  ← Daily: recommended papers summary
  └── fetch_history.json             ← Fetch metadata (unchanged)

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .models import Paper, PaperAnalysis, CategoryConfig

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
        (self.base_output_dir / "papers").mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "reports").mkdir(parents=True, exist_ok=True)

    def export_all_formats(self,
                          papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                          categories: Dict[str, CategoryConfig],
                          date_str: Optional[str] = None) -> Dict[str, Path]:
        """
        Export data to all supported formats.

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            date_str: Date string for output files (YYYY-MM-DD). If None, uses today.

        Returns:
            Dictionary with format names as keys and file paths as values
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        results = {}

        # 1. Export to JSON (single file with all papers + analysis)
        json_path = self.export_json(papers_with_analyses, categories, date_str)
        results["json"] = str(json_path)

        # 2. Export to Markdown (recommendations summary only)
        md_path = self.export_markdown(papers_with_analyses, categories, date_str)
        results["markdown"] = str(md_path)

        logger.info(f"Exported data: JSON={json_path.name}, MD={md_path.name}")
        return results

    def export_json(self,
                   papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                   categories: Dict[str, CategoryConfig],
                   date_str: str) -> Path:
        """
        Export papers to a single daily JSON file (Jekyll-compatible format).

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            date_str: Date string for filename

        Returns:
            Path to the created JSON file
        """
        output_dir = self.base_output_dir / "papers"
        output_path = output_dir / f"papers_{date_str}.json"

        # Prepare data (Jekyll-compatible structure)
        jekyll_data = self._prepare_jekyll_data(papers_with_analyses, categories, date_str)

        # Write daily file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(jekyll_data, f, default=str, indent=2, ensure_ascii=False)

        # Also write/overwrite latest.json for easy reference
        latest_path = output_dir / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(jekyll_data, f, default=str, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(papers_with_analyses)} papers to: {output_path}")
        return output_path

    def export_markdown(self,
                       papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                       categories: Dict[str, CategoryConfig],
                       date_str: str) -> Path:
        """
        Export recommended papers to Markdown summary.

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            date_str: Date string for filename

        Returns:
            Path to the created Markdown file
        """
        output_dir = self.base_output_dir / "reports"
        output_path = output_dir / f"recommendations_{date_str}.md"

        # Filter only recommended papers
        recommended = [
            (p, a) for p, a in papers_with_analyses
            if a.recommendation
        ]
        # Sort by score descending
        recommended.sort(key=lambda x: x[1].relevance_score, reverse=True)

        lines = []

        # Header
        lines.append(f"# Daily Research Recommendations - {date_str}")
        lines.append("")
        lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")

        # Summary
        total_recommended = len(recommended)
        total = len(papers_with_analyses)
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Papers analyzed**: {total}")
        lines.append(f"- **Recommendations**: {total_recommended}")
        lines.append(f"- **Date**: {date_str}")
        lines.append("")

        if not recommended:
            lines.append("*No papers meet the recommendation threshold for this date.*")
            lines.append("")
        else:
            # Top picks
            lines.append("## Top Picks")
            lines.append("")
            for i, (paper, analysis) in enumerate(recommended, 1):
                lines.append(f"### {i}. {paper.title}")
                lines.append("")
                lines.append(f"**Score**: {analysis.relevance_score:.1f}/10")
                lines.append("")
                lines.append(f"**Authors**: {', '.join(paper.authors)}")
                lines.append("")
                lines.append(f"**Source**: {paper.source.value} | **Category**: {paper.category}")
                lines.append("")
                lines.append(f"**Link**: [{paper.link}]({paper.link})")
                lines.append("")

                if analysis.tldr:
                    lines.append(f"**TL;DR**: {analysis.tldr}")
                    lines.append("")
                if analysis.motivation:
                    lines.append(f"**Motivation**: {analysis.motivation}")
                    lines.append("")
                if analysis.method:
                    lines.append(f"**Method**: {analysis.method}")
                    lines.append("")
                if analysis.result:
                    lines.append(f"**Result**: {analysis.result}")
                    lines.append("")
                if analysis.conclusion:
                    lines.append(f"**Conclusion**: {analysis.conclusion}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Generated recommendations report: {output_path}")
        return output_path

    def _prepare_jekyll_data(self,
                            papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                            categories: Dict[str, CategoryConfig],
                            date_str: str) -> Dict[str, Any]:
        """
        Prepare data structure for Jekyll website.

        Returns:
            Dictionary with Jekyll-compatible data structure
        """
        # Convert papers to Jekyll format
        jekyll_papers = []
        for paper, analysis in papers_with_analyses:
            jekyll_paper = {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "link": paper.link,
                "date": paper.published.isoformat(),
                "published_date": paper.published.strftime("%Y-%m-%d"),
                "source": paper.source.value,
                "category": paper.category,
                "feed_name": paper.feed_name,
                "tags": paper.tags,

                # Analysis data
                "score": analysis.relevance_score,
                "recommended": analysis.recommendation,
                "analysis": {
                    "tldr": analysis.tldr,
                    "motivation": analysis.motivation,
                    "method": analysis.method,
                    "result": analysis.result,
                    "conclusion": analysis.conclusion,
                    "keywords": analysis.keywords,
                    "processing_time": analysis.processing_time.isoformat()
                }
            }
            jekyll_papers.append(jekyll_paper)

        # Calculate statistics
        total_papers = len(jekyll_papers)
        recommended_papers = sum(1 for paper in jekyll_papers if paper["recommended"])

        # Prepare categories data
        jekyll_categories = {}
        for cat_id, cat_config in categories.items():
            papers_in_category = [p for p in jekyll_papers if p["category"] == cat_id]
            jekyll_categories[cat_id] = {
                "name": cat_config.display_name,
                "color": cat_config.color,
                "priority": cat_config.priority,
                "count": len(papers_in_category),
                "recommended_count": sum(1 for p in papers_in_category if p["recommended"])
            }

        # Group dates (all unique publication dates)
        all_dates = sorted(set(p["published_date"] for p in jekyll_papers), reverse=True)

        # Final Jekyll data structure
        jekyll_data = {
            "papers": jekyll_papers,
            "categories": jekyll_categories,
            "dates": all_dates,
            "stats": {
                "total_papers": total_papers,
                "recommended_papers": recommended_papers,
                "total_categories": len(jekyll_categories),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "export_date": date_str
            }
        }

        return jekyll_data

    def copy_to_jekyll_site(self, jekyll_site_dir: str = "jekyll_site"):
        """
        Copy the latest papers data to the Jekyll site directory.

        Args:
            jekyll_site_dir: Path to Jekyll site directory (relative to CWD)
        """
        jekyll_site_path = Path(jekyll_site_dir)
        if not jekyll_site_path.exists():
            logger.warning(f"Jekyll site directory not found: {jekyll_site_path}")
            return

        source_file = self.base_output_dir / "papers" / "latest.json"
        target_dir = jekyll_site_path / "_data"
        target_file = target_dir / "papers.json"

        if not source_file.exists():
            logger.warning(f"No latest.json found at {source_file}, cannot copy to Jekyll")
            return

        # Ensure target directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy
        shutil.copy2(source_file, target_file)
        logger.info(f"Copied latest papers data to Jekyll site: {target_file}")

    def export_to_obsidian(self, obsidian_vault_dir: str, date_str: Optional[str] = None):
        """
        Export data to Obsidian vault for note-taking.

        Args:
            obsidian_vault_dir: Path to Obsidian vault directory
            date_str: Date string for filename (YYYY-MM-DD). If None, uses today.
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        obsidian_path = Path(obsidian_vault_dir)
        if not obsidian_path.exists():
            logger.warning(f"Obsidian vault directory not found: {obsidian_path}")
            return

        daily_notes_dir = obsidian_path / "Daily Notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)

        # Copy recommendations report
        report_file = self.base_output_dir / "reports" / f"recommendations_{date_str}.md"
        if report_file.exists():
            target_file = daily_notes_dir / f"Research Recommendations {date_str}.md"
            shutil.copy2(report_file, target_file)
            logger.info(f"Copied report to Obsidian: {target_file}")


# Legacy helper function
def export_papers_to_jekyll(papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                           categories: Dict[str, CategoryConfig],
                           output_dir: str = "data"):
    """
    Export papers and copy to Jekyll site.

    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        categories: Category configurations
        output_dir: Base output directory
    """
    exporter = DataExporter(output_dir)
    date_str = datetime.now().strftime("%Y-%m-%d")

    results = exporter.export_all_formats(papers_with_analyses, categories, date_str)
    exporter.copy_to_jekyll_site()

    return results
