"""
Jekyll-compatible orchestrator for the Quantum RSS Radar system.
This version exports data to Jekyll format instead of building the website directly.

'category' has been removed — LLM assigns 'direction' during analysis.
Source colour tags come from SourceConfig (config/rss_sources.yaml → sources).

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
    load_sources,
    load_research_directions,
)
from .rss_fetcher import fetch_all_feeds
from .normalizer import normalize_papers, enrich_paper_metadata
from .deduplicate import deduplicate_papers
from .semantic_analyzer import SemanticAnalyzer
from .arxiv_deep_reader import deep_read_high_score_papers
from .reference_paper_analyzer import run_reference_paper_analysis, generate_research_directions_from_papers
from .data_exporter import DataExporter
from .database import RadarDatabase
from .email_sender import send_daily_email
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
                          Note: "all" now exports JSONL (data/all/) + MD report (data/reports/) + Jekyll copy.
        """
        self.config_dir = config_dir
        self.output_format = output_format
        self.config = None
        self.feeds = None
        self.sources = None
        self.research_directions = None
        self.analyzer = None
        self.db = None

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
            self.sources = load_sources(self.config_dir)
            self.research_directions = load_research_directions(self.config_dir)

            # Auto-generate research_directions.md from PDFs if it doesn't exist
            # but config/papers/ has PDFs
            rd_path = Path(self.config_dir) / "research_directions.md"
            if not rd_path.exists() or rd_path.stat().st_size < 50:
                papers_dir = Path(self.config_dir) / "papers"
                if papers_dir.exists() and any(papers_dir.rglob("*.pdf")):
                    logger.info("research_directions.md missing or empty — auto-generating from PDFs...")
                    generated = generate_research_directions_from_papers(self.config_dir, self.config)
                    if generated:
                        self.research_directions = generated
                        logger.info(f"Auto-generated research_directions.md ({len(generated)} chars)")
                    else:
                        logger.warning("Could not auto-generate research_directions.md — pipeline may produce poor results")

            logger.info(f"Loaded {len(self.feeds)} RSS feeds")
            logger.info(f"Loaded {len(self.sources)} source configurations")
            logger.info(f"Research directions loaded: {len(self.research_directions)} characters")

            # Initialize semantic analyzer (pass config_dir for prompt template loading)
            self.analyzer = SemanticAnalyzer(self.config, config_dir=self.config_dir)
            self.analyzer.load_research_directions(self.research_directions)
            self.analyzer.load_curated_papers(self.config_dir)

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

            # Step 1.5: Analyze any new reference PDFs (config/papers/{tier}/)
            logger.info("Checking for new reference PDFs...")
            new_refs = run_reference_paper_analysis(
                self.config_dir,
                self.config,
                self.research_directions,
            )
            if new_refs:
                logger.info(f"Generated {new_refs} new reference YAML(s) — reloading analyzer")
                # Reload so the new YAMLs are included in the few-shot prompt
                self.analyzer.load_research_directions(self.research_directions)

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

            # Step 8: Deep reading for high-score papers (arXiv PDF + LLM analysis)
            logger.info("Running deep reading for high-score papers...")
            all_papers_with_analyses = deep_read_high_score_papers(
                all_papers_with_analyses,
                self.config,
                self.analyzer.llm_client if hasattr(self.analyzer, 'llm_client') else None,
            )
            logger.info(f"Deep reading completed for {len(all_papers_with_analyses)} papers")

            # Step 9: Export data to requested format(s)
            logger.info("Exporting data...")
            results = self._export_data(all_papers_with_analyses, date_str)

            # Step 10: Copy to Jekyll site if applicable
            if self.output_format in ["all", "jekyll"]:
                if self.output_format != "all":  # export_all() already did this
                    logger.info("Copying data to Jekyll site...")
                    self._copy_to_jekyll_site(results)

            # Step 11: Save to SQLite database
            logger.info("Saving to SQLite database...")
            pipeline_ts = datetime.now().isoformat()
            try:
                self.db = RadarDatabase()
                feed_configs = {feed.name: feed for feed in self.feeds} if self.feeds else None
                db_saved = self.db.save_papers(
                    all_papers_with_analyses, self.sources, pipeline_ts, feed_configs,
                )
                logger.info(f"Saved {db_saved} papers to database")
            except Exception as e:
                logger.warning(f"Failed to save to database: {e}")

            # Step 12: Send daily email (if enabled)
            if self.config.email_enabled:
                logger.info("Sending daily email digest...")
                # Build feed-level config lookup (feed_name → FeedConfig)
                feed_configs = {feed.name: feed for feed in self.feeds}
                email_success = send_daily_email(
                    all_papers_with_analyses, self.sources, self.config, feed_configs,
                )
                if email_success:
                    logger.info("Daily email sent successfully")
                    if results:
                        results["email_sent"] = "sent"
                else:
                    logger.warning("Daily email failed to send")
                    if results:
                        results["email_sent"] = "failed"
            else:
                logger.info("Email sending disabled, skipping")

            # Calculate execution time and record pipeline run
            execution_time = datetime.now() - start_time
            logger.info(f"Pipeline completed in {execution_time.total_seconds():.2f} seconds")
            if self.db is not None:
                try:
                    deep_read_count = sum(1 for _, a in all_papers_with_analyses if a.deep_read is not None)
                    self.db.save_pipeline_run(
                        run_timestamp=pipeline_ts,
                        total_papers=len(all_papers_with_analyses),
                        analyzed_papers=len(all_papers_with_analyses),
                        deep_read_papers=deep_read_count,
                        duration_seconds=execution_time.total_seconds(),
                    )
                except Exception as e:
                    logger.warning(f"Failed to record pipeline run: {e}")

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

        Outputs:
          - data/all/quantum_rss_radar_YYYY-MM-DD_HHMMSS.jsonl  (all papers, one JSON per line)
          - data/reports/report_YYYY-MM-DD_HHMMSS.md             (all papers, sorted by score)
          - jekyll_site/_data/papers.json                        (latest data for Jekyll)

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            date_str: Date string for output files (unused, timestamp is used for filenames)

        Returns:
            Dictionary with export results
        """
        exporter = DataExporter(self.config.output_dir if self.config else "data")
        feed_configs = {feed.name: feed for feed in self.feeds} if self.feeds else None
        results = exporter.export_all(papers_with_analyses, self.sources, feed_configs=feed_configs)
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
        print("QUANTUM RSS RADAR - EXECUTION SUMMARY")
        print("="*60)
        print(f"Output format: {self.output_format}")

        if results:
            print("\n📄 Output files created:")
            for format_name, file_path in results.items():
                if file_path:
                    label = {"jsonl": "JSONL (all papers)", "markdown": "MD report (all papers)"}.get(format_name, format_name.upper())
                    print(f"  • {label}: {file_path}")

        # Jekyll site info
        jekyll_site_dir = Path("jekyll_site")
        if jekyll_site_dir.exists():
            print(f"\n🌐 Jekyll site data: {jekyll_site_dir / '_data' / 'papers.json'}")
            print(f"   To preview: cd jekyll_site && bundle exec jekyll serve")

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
