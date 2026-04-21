"""
Main orchestrator for the Quantum RSS Radar system.

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
from .md_generator import (
    save_jsonl_output, 
    generate_markdown_report
)
from .data_exporter import DataExporter, export_papers_to_jekyll
from .website_builder import WebsiteBuilder
from .models import Paper, PaperAnalysis

logger = logging.getLogger(__name__)


class QuantumRSSRadar:
    """Main orchestrator for the Quantum RSS Radar system."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the Quantum RSS Radar system.
        
        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = config_dir
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
                logging.FileHandler('quantum_rss_radar.log')
            ]
        )
    
    def load_configuration(self):
        """Load all system configurations."""
        logger.info("Loading system configuration...")
        
        try:
            self.config = load_config(self.config_dir)
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
    
    def run_pipeline(self, test_mode: bool = False):
        """
        Run the complete Quantum RSS Radar pipeline.
        
        Args:
            test_mode: If True, run in test mode with limited papers
            
        Returns:
            True if pipeline completed successfully, False otherwise
        """
        logger.info("Starting Quantum RSS Radar pipeline...")
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
                # Limit papers for testing (increased from 5 to 20 for better coverage)
                papers = papers[:20]
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
            
            # Step 7: Combine all papers with analyses (unfiltered)
            logger.info("Combining papers with analyses...")
            all_papers_with_analyses = []
            paper_dict = {paper.id: paper for paper in papers}
            for analysis in analyses:
                paper = paper_dict.get(analysis.paper_id)
                if paper:
                    all_papers_with_analyses.append((paper, analysis))
            
            # Step 8: Filter and rank papers (for recommendations)
            logger.info("Filtering and ranking papers...")
            filtered_papers_with_analyses = self.analyzer.filter_and_rank_papers(papers, analyses)
            
            if not filtered_papers_with_analyses:
                logger.warning("No papers passed the relevance filter")
                # Continue anyway to show all papers on website
            
            logger.info(f"Analyzed {len(all_papers_with_analyses)} papers, {len(filtered_papers_with_analyses)} with score >= {self.config.min_relevance_score}")
            
            # Step 9: Save outputs
            logger.info("Saving outputs...")
            
            # Save JSONL output (save all papers, not just filtered)
            save_jsonl_output(all_papers_with_analyses, self.config.output_dir)
            
            # Generate Markdown report (use filtered papers for recommendations)
            generate_markdown_report(filtered_papers_with_analyses, self.categories, self.config.output_dir)
            
            # Step 10: Build website
            logger.info("Building website...")
            website_builder = WebsiteBuilder(self.config.web_dir)
            website_builder.build_website(
                all_papers_with_analyses=all_papers_with_analyses,
                filtered_papers_with_analyses=filtered_papers_with_analyses,
                categories=self.categories
            )
            
            # Step 11: Send email (if enabled)
            if self.config.email_enabled:
                logger.info("Sending daily email...")
                self._send_daily_email(filtered_papers_with_analyses)
            
            # Calculate execution time
            execution_time = datetime.now() - start_time
            logger.info(f"Pipeline completed in {execution_time.total_seconds():.2f} seconds")
            
            # Print summary
            self._print_summary(filtered_papers_with_analyses)
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _send_daily_email(self, papers_with_analyses: List[tuple[Paper, PaperAnalysis]]):
        """
        Send daily email with top recommendations.
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
        """
        try:
            from .email_sender import send_daily_email
            send_daily_email(papers_with_analyses, self.config)
            logger.info("Daily email sent successfully")
        except ImportError:
            logger.warning("Email sender module not available")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def _print_summary(self, papers_with_analyses: List[tuple[Paper, PaperAnalysis]]):
        """Print summary of pipeline execution."""
        total_papers = len(papers_with_analyses)
        recommended_papers = sum(1 for _, analysis in papers_with_analyses if analysis.recommendation)
        
        print("\n" + "="*60)
        print("QUANTUM RSS RADAR - EXECUTION SUMMARY")
        print("="*60)
        print(f"Total papers analyzed: {total_papers}")
        print(f"Recommended papers: {recommended_papers}")
        
        # Top 3 papers by score
        if papers_with_analyses:
            print("\nTop 3 recommended papers:")
            top_papers = sorted(papers_with_analyses, key=lambda x: x[1].relevance_score, reverse=True)[:3]
            for i, (paper, analysis) in enumerate(top_papers, 1):
                print(f"{i}. {paper.title[:60]}...")
                print(f"   Score: {analysis.relevance_score:.1f}/10 | Source: {paper.source.value}")
        
        # Output locations
        print(f"\nOutputs saved to:")
        print(f"  - JSONL: {self.config.output_dir}/processed/papers_analyzed.jsonl")
        print(f"  - Markdown: {self.config.output_dir}/markdown/")
        print(f"  - Website: {self.config.web_dir}/")
        
        print("="*60)
    
    def run_test_pipeline(self):
        """Run a test pipeline with limited data."""
        logger.info("Running test pipeline...")
        return self.run_pipeline(test_mode=True)


def main():
    """Main entry point for the Quantum RSS Radar system."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Quantum RSS Radar - AI-assisted daily academic research tracking system"
    )
    parser.add_argument(
        "--config-dir", 
        default="config",
        help="Path to configuration directory (default: config)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with limited papers"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="Skip email sending even if configured"
    )
    
    args = parser.parse_args()
    
    # Initialize and run the system
    radar = QuantumRSSRadar(args.config_dir)
    
    if args.test:
        success = radar.run_test_pipeline()
    else:
        success = radar.run_pipeline()
    
    if success:
        logger.info("Quantum RSS Radar pipeline completed successfully")
        sys.exit(0)
    else:
        logger.error("Quantum RSS Radar pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()