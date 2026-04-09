"""
Markdown report generator for the Quantum RSS Radar system.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

from .models import Paper, PaperAnalysis, CategoryConfig

logger = logging.getLogger(__name__)


def save_jsonl_output(papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                     output_dir: str, 
                     filename: str = "papers_analyzed.jsonl"):
    """
    Save papers and analyses in JSONL format.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        output_dir: Output directory
        filename: Output filename
    """
    output_path = Path(output_dir) / "processed" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    records = []
    for paper, analysis in papers_with_analyses:
        record = {
            "paper": paper.dict(),
            "analysis": analysis.dict(),
            "processed_at": datetime.now().isoformat()
        }
        records.append(record)
    
    # Write as JSONL (one JSON object per line)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, default=str) + "\n")
    
    logger.info(f"Saved {len(records)} papers to JSONL: {output_path}")


def generate_markdown_report(papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                           categories: Dict[str, CategoryConfig],
                           output_dir: str):
    """
    Generate Markdown report with paper summaries.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        categories: Category configurations
        output_dir: Output directory
    """
    if not papers_with_analyses:
        logger.warning("No papers to generate report for")
        return
    
    # Create output directory
    markdown_dir = Path(output_dir) / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate daily report filename
    date_str = datetime.now().strftime("%Y%m%d")
    output_path = markdown_dir / f"research_report_{date_str}.md"
    
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
    content = generate_markdown_content(papers_by_category, sorted_categories, categories, date_str)
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"Generated Markdown report: {output_path}")
    
    # Also generate a summary file with just top recommendations
    generate_top_recommendations(papers_with_analyses, output_dir, date_str)


def generate_markdown_content(papers_by_category: Dict[str, List[tuple[Paper, PaperAnalysis]]],
                            sorted_categories: List[str],
                            categories: Dict[str, CategoryConfig],
                            date_str: str) -> str:
    """Generate the full markdown content."""
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
            lines.append(generate_paper_section(paper, analysis, i))
            lines.append("")
    
    # Appendix: All paper links
    lines.append("## 🔗 All Paper Links")
    lines.append("")
    all_papers = [(p, a) for papers in papers_by_category.values() for p, a in papers]
    for paper, analysis in sorted(all_papers, key=lambda x: x[1].relevance_score, reverse=True):
        score_str = f"⭐ {analysis.relevance_score:.1f}/10"
        if analysis.recommendation:
            score_str += " ✅"
        lines.append(f"- [{paper.title}]({paper.link}) - {score_str}")
    
    return "\n".join(lines)


def generate_paper_section(paper: Paper, analysis: PaperAnalysis, index: int) -> str:
    """Generate markdown section for a single paper."""
    lines = []
    
    # Header with score and recommendation
    score_str = f"⭐ {analysis.relevance_score:.1f}/10"
    if analysis.recommendation:
        score_str += " **✅ RECOMMENDED**"
    
    lines.append(f"### {index}. {paper.title}")
    lines.append("")
    lines.append(f"**{score_str}** | *{paper.source.value.upper()}* | *Published: {paper.published.strftime('%Y-%m-%d') if paper.published else 'Unknown'}*")
    lines.append("")
    
    # Authors
    if paper.authors:
        authors_str = ", ".join(paper.authors[:5])  # Show first 5 authors
        if len(paper.authors) > 5:
            authors_str += f" et al. ({len(paper.authors)} authors)"
        lines.append(f"**Authors**: {authors_str}")
        lines.append("")
    
    # Link
    lines.append(f"**Link**: [{paper.link}]({paper.link})")
    lines.append("")
    
    # Summary
    lines.append("#### Summary")
    lines.append("")
    lines.append(f"**TLDR**: {analysis.tldr}")
    lines.append("")
    lines.append(f"**Motivation**: {analysis.motivation}")
    lines.append("")
    lines.append(f"**Method**: {analysis.method}")
    lines.append("")
    lines.append(f"**Result**: {analysis.result}")
    lines.append("")
    lines.append(f"**Conclusion**: {analysis.conclusion}")
    lines.append("")
    
    # Keywords
    if analysis.keywords:
        keywords_str = ", ".join(f"`{k}`" for k in analysis.keywords[:5])
        lines.append(f"**Keywords**: {keywords_str}")
        lines.append("")
    
    # Abstract (collapsible)
    lines.append("<details>")
    lines.append("<summary>Show full abstract</summary>")
    lines.append("")
    lines.append(paper.abstract)
    lines.append("")
    lines.append("</details>")
    lines.append("")
    
    return "\n".join(lines)


def generate_top_recommendations(papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                               output_dir: str,
                               date_str: str):
    """
    Generate a separate markdown file with only top recommended papers.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        output_dir: Output directory
        date_str: Date string for filename
    """
    # Filter recommended papers
    recommended = [(p, a) for p, a in papers_with_analyses if a.recommendation]
    
    if not recommended:
        logger.info("No recommended papers to generate top recommendations")
        return
    
    # Sort by relevance score
    recommended.sort(key=lambda x: x[1].relevance_score, reverse=True)
    
    # Take top N (or all if less than N)
    top_n = min(10, len(recommended))
    top_papers = recommended[:top_n]
    
    # Create output directory
    markdown_dir = Path(output_dir) / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = markdown_dir / f"top_recommendations_{date_str}.md"
    
    # Generate content
    lines = []
    lines.append(f"# Top {top_n} Recommended Papers - {datetime.now().strftime('%B %d, %Y')}")
    lines.append("")
    lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    
    lines.append("## 📋 Executive Summary")
    lines.append("")
    lines.append(f"Today's analysis identified **{len(recommended)} recommended papers** out of {len(papers_with_analyses)} total papers.")
    lines.append(f"Here are the top {top_n} papers ranked by relevance score:")
    lines.append("")
    
    for i, (paper, analysis) in enumerate(top_papers, 1):
        lines.append(f"{i}. **[{paper.title}]({paper.link})**")
        lines.append(f"   - Score: {analysis.relevance_score:.1f}/10")
        lines.append(f"   - Authors: {', '.join(paper.authors[:3])}" + (" et al." if len(paper.authors) > 3 else ""))
        lines.append(f"   - TLDR: {analysis.tldr}")
        lines.append(f"   - Source: {paper.source.value}")
        lines.append("")
    
    lines.append("## 🔍 Detailed Analysis")
    lines.append("")
    
    for i, (paper, analysis) in enumerate(top_papers, 1):
        lines.append(f"### {i}. {paper.title}")
        lines.append("")
        lines.append(f"**Relevance Score**: {analysis.relevance_score:.1f}/10")
        lines.append("")
        lines.append(f"**Motivation**: {analysis.motivation}")
        lines.append("")
        lines.append(f"**Key Finding**: {analysis.result}")
        lines.append("")
        lines.append(f"**Why it matters**: {analysis.conclusion}")
        lines.append("")
        lines.append(f"[Read paper]({paper.link})")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    logger.info(f"Generated top recommendations: {output_path}")