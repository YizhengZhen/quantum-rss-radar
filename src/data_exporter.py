"""
Data exporter for the Quantum RSS Radar system.
Supports multiple output formats: JSONL, Markdown, and Jekyll data files.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .models import Paper, PaperAnalysis, CategoryConfig

logger = logging.getLogger(__name__)


class DataExporter:
    """Exports paper data to multiple formats for different use cases."""
    
    def __init__(self, base_output_dir: str = "data"):
        """
        Initialize data exporter.
        
        Args:
            base_output_dir: Base directory for all output files
        """
        self.base_output_dir = Path(base_output_dir)
        
        # Create directory structure
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "jsonl").mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "markdown").mkdir(parents=True, exist_ok=True)
        (self.base_output_dir / "jekyll").mkdir(parents=True, exist_ok=True)
    
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
        
        # 1. Export to JSONL (single file with all papers)
        jsonl_path = self.export_jsonl(papers_with_analyses, date_str)
        results["jsonl"] = jsonl_path
        
        # 2. Export to Markdown (human-readable report)
        markdown_path = self.export_markdown(papers_with_analyses, categories, date_str)
        results["markdown"] = markdown_path
        
        # 3. Export to Jekyll data format (for static website)
        jekyll_path = self.export_jekyll_data(papers_with_analyses, categories, date_str)
        results["jekyll"] = jekyll_path
        
        logger.info(f"Exported data to all formats: {list(results.keys())}")
        return results
    
    def export_jsonl(self, 
                    papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                    date_str: str) -> Path:
        """
        Export papers to JSONL format (one object per line).
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            date_str: Date string for filename
            
        Returns:
            Path to the created JSONL file
        """
        output_dir = self.base_output_dir / "jsonl"
        output_path = output_dir / f"{date_str}_all.jsonl"
        
        records = []
        for paper, analysis in papers_with_analyses:
            # Combine paper and analysis into a single record
            record = {
                "id": paper.id,
                "date": date_str,
                "paper": paper.dict(),
                "analysis": analysis.dict(),
                "processed_at": datetime.now().isoformat()
            }
            records.append(record)
        
        # Write as JSONL (one JSON object per line)
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")
        
        logger.info(f"Exported {len(records)} papers to JSONL: {output_path}")
        return output_path
    
    def export_markdown(self,
                       papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                       categories: Dict[str, CategoryConfig],
                       date_str: str) -> Path:
        """
        Export papers to Markdown format for human reading.
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            date_str: Date string for filename
            
        Returns:
            Path to the created Markdown file
        """
        output_dir = self.base_output_dir / "markdown"
        output_path = output_dir / f"{date_str}_report.md"
        
        # Group papers by category
        papers_by_category: Dict[str, List[tuple[Paper, PaperAnalysis]]] = {}
        for paper, analysis in papers_with_analyses:
            category = paper.category
            if category not in papers_by_category:
                papers_by_category[category] = []
            papers_by_category[category].append((paper, analysis))
        
        # Sort categories by priority
        sorted_categories = sorted(
            papers_by_category.keys(),
            key=lambda cat: categories.get(cat, CategoryConfig(display_name=cat, color="#000000", priority=999)).priority
        )
        
        # Generate markdown content
        lines = []
        
        # Header
        lines.append(f"# Daily Research Report - {datetime.now().strftime('%B %d, %Y')}")
        lines.append("")
        lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Summary statistics
        total_papers = sum(len(papers) for papers in papers_by_category.values())
        recommended_papers = sum(
            1 for papers in papers_by_category.values()
            for _, analysis in papers
            if analysis.recommendation
        )
        
        lines.append("## 📊 Summary")
        lines.append("")
        lines.append(f"- **Total papers analyzed**: {total_papers}")
        lines.append(f"- **Recommended papers**: {recommended_papers}")
        lines.append(f"- **Categories covered**: {len(papers_by_category)}")
        lines.append("")
        
        # Table of contents
        lines.append("## 📑 Table of Contents")
        lines.append("")
        for category in sorted_categories:
            cat_config = categories.get(category, CategoryConfig(display_name=category, color="#000000", priority=999))
            papers = papers_by_category[category]
            recommended = sum(1 for _, analysis in papers if analysis.recommendation)
            lines.append(f"- [{cat_config.display_name}](#{category.lower().replace('_', '-')}) ({len(papers)} papers, {recommended} recommended)")
        lines.append("")
        
        # Papers by category
        for category in sorted_categories:
            cat_config = categories.get(category, CategoryConfig(display_name=category, color="#000000", priority=999))
            papers = papers_by_category[category]
            
            lines.append(f"## {cat_config.display_name}")
            lines.append("")
            
            # Sort papers by relevance score (descending)
            papers_sorted = sorted(papers, key=lambda x: x[1].relevance_score, reverse=True)
            
            for i, (paper, analysis) in enumerate(papers_sorted, 1):
                lines.append(self._generate_paper_markdown(paper, analysis, i))
                lines.append("")
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Generated Markdown report: {output_path}")
        return output_path
    
    def _generate_paper_markdown(self, paper: Paper, analysis: PaperAnalysis, index: int) -> str:
        """Generate markdown section for a single paper."""
        lines = []
        
        lines.append(f"### {index}. {paper.title}")
        lines.append("")
        lines.append(f"**Authors**: {', '.join(paper.authors)}")
        lines.append("")
        lines.append(f"**Score**: {analysis.relevance_score:.1f}/10 | **Recommended**: {'✅ Yes' if analysis.recommendation else '❌ No'}")
        lines.append("")
        lines.append(f"**Source**: {paper.source.value} | **Category**: {paper.category} | **Date**: {paper.published.strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append(f"**Link**: [{paper.link}]({paper.link})")
        lines.append("")
        
        if analysis.tldr:
            lines.append("#### TL;DR")
            lines.append("")
            lines.append(f"{analysis.tldr}")
            lines.append("")
        
        if paper.abstract:
            lines.append("#### Abstract")
            lines.append("")
            lines.append(f"{paper.abstract}")
            lines.append("")
        
        if analysis.motivation:
            lines.append("#### Motivation")
            lines.append("")
            lines.append(f"{analysis.motivation}")
            lines.append("")
        
        if analysis.method:
            lines.append("#### Method")
            lines.append("")
            lines.append(f"{analysis.method}")
            lines.append("")
        
        if analysis.result:
            lines.append("#### Result")
            lines.append("")
            lines.append(f"{analysis.result}")
            lines.append("")
        
        if analysis.conclusion:
            lines.append("#### Conclusion")
            lines.append("")
            lines.append(f"{analysis.conclusion}")
            lines.append("")
        
        if analysis.keywords:
            lines.append("#### Keywords")
            lines.append("")
            lines.append(f"{', '.join(analysis.keywords)}")
        
        return "\n".join(lines)
    
    def export_jekyll_data(self,
                          papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                          categories: Dict[str, CategoryConfig],
                          date_str: str) -> Path:
        """
        Export papers to Jekyll-compatible JSON format.
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            date_str: Date string for filename
            
        Returns:
            Path to the created Jekyll data file
        """
        output_dir = self.base_output_dir / "jekyll"
        output_path = output_dir / "papers.json"
        
        # Prepare data for Jekyll
        jekyll_data = self._prepare_jekyll_data(papers_with_analyses, categories, date_str)
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(jekyll_data, f, default=str, indent=2, ensure_ascii=False)
        
        # Also create a daily data file for history
        daily_dir = output_dir / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        daily_path = daily_dir / f"{date_str}.json"
        
        with open(daily_path, "w", encoding="utf-8") as f:
            json.dump(jekyll_data, f, default=str, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(papers_with_analyses)} papers to Jekyll data: {output_path}")
        logger.info(f"Daily snapshot saved to: {daily_path}")
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
    
    def copy_to_jekyll_site(self, jekyll_site_dir: str = "../jekyll_site"):
        """
        Copy Jekyll data files to the Jekyll site directory.
        
        Args:
            jekyll_site_dir: Path to Jekyll site directory
        """
        jekyll_site_path = Path(jekyll_site_dir)
        if not jekyll_site_path.exists():
            logger.warning(f"Jekyll site directory not found: {jekyll_site_path}")
            return
        
        source_data = self.base_output_dir / "jekyll"
        target_data = jekyll_site_path / "_data"
        
        # Ensure target directory exists
        target_data.mkdir(parents=True, exist_ok=True)
        (target_data / "daily").mkdir(parents=True, exist_ok=True)
        
        # Copy papers.json
        source_papers = source_data / "papers.json"
        target_papers = target_data / "papers.json"
        
        if source_papers.exists():
            import shutil
            shutil.copy2(source_papers, target_papers)
            logger.info(f"Copied papers.json to Jekyll site: {target_papers}")
        
        # Copy daily files
        source_daily = source_data / "daily"
        target_daily = target_data / "daily"
        
        if source_daily.exists():
            import shutil
            for daily_file in source_daily.glob("*.json"):
                shutil.copy2(daily_file, target_daily / daily_file.name)
            logger.info(f"Copied {len(list(source_daily.glob('*.json')))} daily files to Jekyll site")
    
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
        
        # Create daily notes directory
        daily_notes_dir = obsidian_path / "Daily Notes"
        daily_notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy Markdown report
        markdown_file = self.base_output_dir / "markdown" / f"{date_str}_report.md"
        if markdown_file.exists():
            import shutil
            target_file = daily_notes_dir / f"Research Report {date_str}.md"
            shutil.copy2(markdown_file, target_file)
            logger.info(f"Copied Markdown report to Obsidian: {target_file}")


# Helper function for backward compatibility
def export_papers_to_jekyll(papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                           categories: Dict[str, CategoryConfig],
                           output_dir: str = "data"):
    """
    Legacy function for exporting papers to Jekyll format.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        categories: Category configurations
        output_dir: Base output directory
    """
    exporter = DataExporter(output_dir)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Export to all formats
    results = exporter.export_all_formats(papers_with_analyses, categories, date_str)
    
    # Copy to Jekyll site
    exporter.copy_to_jekyll_site()
    
    return results