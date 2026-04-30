"""
Jekyll-compatible orchestrator for the Quantum RSS Radar system.
This version exports data to Jekyll format instead of building the website directly.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys

from .config_loader import (
    load_config, 
    load_feeds, 
    load_categories, 
    load_research_directions
)
from .rss_fetcher import fetch_all_feeds
from .normalizer import normalize_papers, enrich_paper_metadata
from .deduplicate import deduplicate_papers
from .semantic_analyzer import SemanticAnalyzer
from .data_exporter import DataExporter
from .models import Paper, PaperAnalysis

logger = logging.getLogger(__name__)


class QuantumRSSRadarJekyll:
    """Main orchestrator for Jekyll-compatible Quantum RSS Radar system."""
    
    def __init__(self, config_dir: str = "config", output_format: str = "all"):
        """
        Initialize the Quantum RSS Radar system for Jekyll.
        
        Args:
            config_dir: Path to configuration directory
            output_format: Output format ("all", "jsonl", "markdown", "jekyll")
        """
        self.config_dir = config_dir
        self.output_format = output_format
        self.config = None
        self.feeds = None
        self.categories = None
        self.research_directions = None
        self.analyzer = None
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('quantum_rss_radar_jekyll.log')
            ]
        )
    
    def load_configuration(self):
        """Load all system configurations."""
        logger.info("Loading system configuration...")
        
        try:
            self.config = load_config()
            self.feeds = load_feeds(self.config_dir)
            self.categories = load_categories(self.config_dir)
            self.research_directions = load_research_directions(self.config_dir)
            
            logger.info(f"Loaded {len(self.feeds)} RSS feeds")
            logger.info(f"Loaded {len(self.categories)} categories")
            logger.info(f"Research directions loaded: {len(self.research_directions)} characters")
            
            # Initialize semantic analyzer
            self.analyzer = SemanticAnalyzer(self.config)
            self.analyzer.load_research_directions(self.research_directions)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def run_pipeline(self, test_mode: bool = False, date_str: str = None):
        """
        Run the complete Quantum RSS Radar pipeline for Jekyll.
        
        Args:
            test_mode: If True, run in test mode with limited papers
            date_str: Date string for output files (YYYY-MM-DD). If None, uses today.
            
        Returns:
            True if pipeline completed successfully, False otherwise
        """
        logger.info(f"Starting Quantum RSS Radar Jekyll pipeline (output: {self.output_format})...")
        start_time = datetime.now()
        
        try:
            # Step 1: Load configuration
            if not self.load_configuration():
                logger.error("Failed to load configuration")
                return False
            
            # Step 2: Fetch RSS feeds
            logger.info("Fetching RSS feeds...")
            papers = fetch_all_feeds(self.feeds, self.config)
            
            if test_mode:
                # Limit papers for testing
                papers = papers[:10]
                logger.info(f"Test mode: Limiting to {len(papers)} papers")
            
            if not papers:
                logger.warning("No papers fetched from RSS feeds")
                return False
            
            logger.info(f"Fetched {len(papers)} papers from RSS feeds")
            
            # Step 3: Normalize paper metadata
            logger.info("Normalizing paper metadata...")
            papers = normalize_papers(papers)
            
            # Step 4: Enrich paper metadata
            logger.info("Enriching paper metadata...")
            enriched_papers = []
            for paper in papers:
                enriched_papers.append(enrich_paper_metadata(paper))
            papers = enriched_papers
            
            # Step 5: Deduplicate papers
            logger.info("Deduplicating papers...")
            papers = deduplicate_papers(papers)
            logger.info(f"After deduplication: {len(papers)} unique papers")
            
            # Step 6: Analyze papers with LLM
            logger.info("Analyzing papers with LLM...")
            analyses = self.analyzer.analyze_papers_batch(papers, self.research_directions)
            
            # Step 7: Combine all papers with analyses
            logger.info("Combining papers with analyses...")
            all_papers_with_analyses = []
            paper_dict = {paper.id: paper for paper in papers}
            for analysis in analyses:
                paper = paper_dict.get(analysis.paper_id)
                if paper:
                    all_papers_with_analyses.append((paper, analysis))
            
            if not all_papers_with_analyses:
                logger.warning("No papers with analyses")
                return False
            
            logger.info(f"Analyzed {len(all_papers_with_analyses)} papers")
            
            # Step 8: Export data to requested format(s)
            logger.info("Exporting data...")
            results = self._export_data(all_papers_with_analyses, date_str)
            
            # Step 9: Copy to Jekyll site if applicable
            if self.output_format in ["all", "jekyll"]:
                logger.info("Copying data to Jekyll site...")
                self._copy_to_jekyll_site(results)
            
            # Calculate execution time
            execution_time = datetime.now() - start_time
            logger.info(f"Pipeline completed in {execution_time.total_seconds():.2f} seconds")
            
            # Print summary
            self._print_summary(results)
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _export_data(self, papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                    date_str: str = None) -> Dict[str, Any]:
        """
        Export data to requested format(s).
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            date_str: Date string for output files
            
        Returns:
            Dictionary with export results
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        exporter = DataExporter(self.config.output_dir if self.config else "data")
        results = {}
        
        if self.output_format in ["all", "jsonl", "jekyll"]:
            json_path = exporter.export_json(papers_with_analyses, self.categories, date_str)
            results["json"] = str(json_path)
        
        if self.output_format in ["all", "markdown"]:
            md_path = exporter.export_markdown(papers_with_analyses, self.categories, date_str)
            results["markdown"] = str(md_path)
        
        return results
    
    def _copy_to_jekyll_site(self, results: Dict[str, Any]):
        """Copy exported data to Jekyll site directory."""
        try:
            exporter = DataExporter(self.config.output_dir if self.config else "data")
            exporter.copy_to_jekyll_site()
            logger.info("Copied latest papers data to Jekyll site")
                
        except Exception as e:
            logger.error(f"Failed to copy data to Jekyll site: {e}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print summary of pipeline execution."""
        print("\n" + "="*60)
        print("QUANTUM RSS RADAR JEKYLL - EXECUTION SUMMARY")
        print("="*60)
        print(f"Output format: {self.output_format}")
        
        if results:
            print("\nOutput files created:")
            for format_name, file_path in results.items():
                if file_path:
                    print(f"  - {format_name.upper()}: {file_path}")
        
        # Copy to Jekyll site info
        if self.output_format in ["all", "jekyll"]:
            jekyll_site_dir = Path("jekyll_site")
            if jekyll_site_dir.exists():
                print(f"\nJekyll site data directory: {jekyll_site_dir / '_data'}")
                print(f"To build Jekyll site, run:")
                print(f"  cd jekyll_site")
                print(f"  bundle exec jekyll serve")
        
        print("="*60)
    
    def run_test_pipeline(self):
        """Run a test pipeline with limited data."""
        logger.info("Running test pipeline...")
        return self.run_pipeline(test_mode=True)


def main():
    """Main entry point for the Jekyll-compatible Quantum RSS Radar system."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Quantum RSS Radar Jekyll - Export data for Jekyll static site"
    )
    parser.add_argument(
        "--config-dir", 
        default="config",
        help="Path to configuration directory (default: config)"
    )
    parser.add_argument(
        "--format",
        default="all",
        choices=["all", "json", "markdown", "jekyll"],
        help="Output format (default: all)"
    )
    parser.add_argument(
        "--date",
        help="Date for output files (YYYY-MM-DD). If not provided, uses today."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with limited papers"
    )
    parser.add_argument(
        "--skip-jekyll-copy",
        action="store_true",
        help="Skip copying to Jekyll site directory"
    )
    
    args = parser.parse_args()
    
    # Initialize and run the system
    radar = QuantumRSSRadarJekyll(args.config_dir, args.format)
    
    if args.test:
        success = radar.run_test_pipeline()
    else:
        success = radar.run_pipeline(date_str=args.date)
    
    if success:
        logger.info("Quantum RSS Radar Jekyll pipeline completed successfully")
        sys.exit(0)
    else:
        logger.error("Quantum RSS Radar Jekyll pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()