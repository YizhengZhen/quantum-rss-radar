"""
SQLite database module for the Quantum RSS Radar system.

Provides persistent storage for:
  - Papers & their AI analysis results (historical queries, cross-day stats)
  - Pipeline run metadata

Data is stored in data/radar.db (or as configured via .env).
JSONL export is preserved as the primary data source for the Jekyll website.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .models import Paper, PaperAnalysis, DeepReadResult, SourceConfig

logger = logging.getLogger(__name__)

# Default database path (relative to project root)
DEFAULT_DB_PATH = Path("data") / "radar.db"


class RadarDatabase:
    """SQLite database for Quantum RSS Radar persistent storage."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection and ensure schema exists.

        Args:
            db_path: Path to SQLite database file. Defaults to data/radar.db.
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Schema ──────────────────────────────────────────────

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent performance
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        """Create tables if they don't exist."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL DEFAULT '[]',
                    abstract TEXT NOT NULL DEFAULT '',
                    link TEXT NOT NULL DEFAULT '',
                    published_date TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'other',
                    source_display_name TEXT NOT NULL DEFAULT '',
                    source_color TEXT NOT NULL DEFAULT '#757575',
                    feed_name TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    rss_fetch_date TEXT NOT NULL DEFAULT '',

                    -- AI analysis
                    score REAL NOT NULL DEFAULT 0.0,
                    recommended INTEGER NOT NULL DEFAULT 0,
                    direction TEXT NOT NULL DEFAULT '',
                    tldr TEXT NOT NULL DEFAULT '',
                    motivation TEXT NOT NULL DEFAULT '',
                    method TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    conclusion TEXT NOT NULL DEFAULT '',
                    keywords TEXT NOT NULL DEFAULT '[]',
                    analysis_timestamp TEXT NOT NULL DEFAULT '',

                    -- Deep reading (optional)
                    deep_read TEXT,

                    -- Pipeline metadata
                    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                    pipeline_run TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(score DESC);
                CREATE INDEX IF NOT EXISTS idx_papers_direction ON papers(direction);
                CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
                CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_date);
                CREATE INDEX IF NOT EXISTS idx_papers_last_updated ON papers(last_updated);

                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL,
                    total_papers INTEGER NOT NULL DEFAULT 0,
                    analyzed_papers INTEGER NOT NULL DEFAULT 0,
                    deep_read_papers INTEGER NOT NULL DEFAULT 0,
                    duration_seconds REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'completed'
                );
            """)
            conn.commit()
            logger.debug(f"Database schema initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
        finally:
            conn.close()

    # ── Paper CRUD ──────────────────────────────────────────

    def save_papers(self,
                    papers_with_analyses: List[Tuple[Paper, PaperAnalysis]],
                    sources: Dict[str, SourceConfig],
                    pipeline_run_timestamp: str) -> int:
        """
        Insert or update papers in the database.

        Uses INSERT OR REPLACE so that re-analyzing the same paper
        (e.g., same arxiv ID appearing on different days) updates
        the existing record rather than creating duplicates.

        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            sources: Source configs (for display name + colour)
            pipeline_run_timestamp: ISO timestamp of this pipeline run

        Returns:
            Number of papers saved
        """
        conn = self._get_connection()
        saved = 0
        try:
            for paper, analysis in papers_with_analyses:
                src_cfg = sources.get(paper.source.value)
                src_display = src_cfg.display_name if src_cfg else paper.source.value
                src_color = src_cfg.color if src_cfg else "#757575"

                deep_read_json = None
                if analysis.deep_read:
                    deep_read_json = json.dumps(analysis.deep_read.model_dump(), ensure_ascii=False)

                conn.execute("""
                    INSERT OR REPLACE INTO papers (
                        id, title, authors, abstract, link,
                        published_date, source, source_display_name, source_color,
                        feed_name, tags, rss_fetch_date,
                        score, recommended, direction,
                        tldr, motivation, method, result, conclusion,
                        keywords, analysis_timestamp, deep_read,
                        last_updated, pipeline_run
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        datetime('now'), ?
                    )
                """, (
                    paper.id,
                    paper.title,
                    json.dumps(paper.authors, ensure_ascii=False),
                    paper.abstract,
                    paper.link,
                    paper.published.isoformat() if paper.published else "",
                    paper.source.value,
                    src_display,
                    src_color,
                    paper.feed_name,
                    json.dumps(paper.tags, ensure_ascii=False),
                    paper.rss_fetch_date.isoformat(),

                    analysis.relevance_score,
                    1 if analysis.recommendation else 0,
                    analysis.direction or "",
                    analysis.tldr or "",
                    analysis.motivation or "",
                    analysis.method or "",
                    analysis.result or "",
                    analysis.conclusion or "",
                    json.dumps(analysis.keywords, ensure_ascii=False),
                    analysis.processing_time.isoformat(),
                    deep_read_json,

                    pipeline_run_timestamp,
                ))
                saved += 1

            conn.commit()
            logger.info(f"Saved {saved} papers to SQLite database")
        except Exception as e:
            logger.error(f"Failed to save papers to database: {e}")
            conn.rollback()
        finally:
            conn.close()

        return saved

    def get_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get a single paper by its ID."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM papers WHERE id = ?", (paper_id,)
            ).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_latest_papers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the most recently updated papers.

        Args:
            limit: Maximum number of papers to return

        Returns:
            List of paper dicts, sorted by last_updated DESC
        """
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM papers
                ORDER BY last_updated DESC, score DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_papers_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get papers from a specific pipeline run date.

        Args:
            date_str: Date string in format 'YYYY-MM-DD'

        Returns:
            List of paper dicts from that pipeline run
        """
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM papers
                WHERE pipeline_run LIKE ?
                ORDER BY score DESC
            """, (f"{date_str}%",)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_papers_by_direction(self, direction: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get papers in a specific research direction."""
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM papers
                WHERE direction = ?
                ORDER BY score DESC
                LIMIT ?
            """, (direction, limit)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_direction_stats(self) -> List[Dict[str, Any]]:
        """Get statistics per research direction across all time."""
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT
                    direction,
                    COUNT(*) as total_papers,
                    SUM(recommended) as recommended_papers,
                    ROUND(AVG(score), 2) as avg_score
                FROM papers
                WHERE direction != ''
                GROUP BY direction
                ORDER BY total_papers DESC
            """).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ── Pipeline Run Tracking ───────────────────────────────

    def save_pipeline_run(self,
                          run_timestamp: str,
                          total_papers: int,
                          analyzed_papers: int,
                          deep_read_papers: int,
                          duration_seconds: float,
                          status: str = "completed"):
        """Record a pipeline run."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO pipeline_runs (
                    run_timestamp, total_papers, analyzed_papers,
                    deep_read_papers, duration_seconds, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (run_timestamp, total_papers, analyzed_papers,
                  deep_read_papers, duration_seconds, status))
            conn.commit()
        finally:
            conn.close()

    def get_latest_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent pipeline runs."""
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM pipeline_runs
                ORDER BY run_timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    # ── History and Statistics ───────────────────────────────

    def get_paper_history(self, paper_title: str) -> List[Dict[str, Any]]:
        """
        Search for papers by title (for checking if a paper was
        previously analyzed, even from a different source).

        Uses LIKE for fuzzy matching.
        """
        conn = self._get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM papers
                WHERE title LIKE ?
                ORDER BY last_updated DESC
                LIMIT 20
            """, (f"%{paper_title[:80]}%",)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        conn = self._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM papers").fetchone()["c"]
            recommended = conn.execute(
                "SELECT COUNT(*) as c FROM papers WHERE recommended = 1"
            ).fetchone()["c"]
            unique_directions = conn.execute(
                "SELECT COUNT(DISTINCT direction) as c FROM papers WHERE direction != ''"
            ).fetchone()["c"]
            unique_sources = conn.execute(
                "SELECT COUNT(DISTINCT source) as c FROM papers"
            ).fetchone()["c"]
            first_paper = conn.execute(
                "SELECT MIN(first_seen) as d FROM papers"
            ).fetchone()["d"]
            latest_run = conn.execute(
                "SELECT MAX(run_timestamp) as d FROM pipeline_runs"
            ).fetchone()["d"]

            return {
                "total_papers": total,
                "recommended_papers": recommended,
                "unique_directions": unique_directions,
                "unique_sources": unique_sources,
                "first_paper_date": first_paper,
                "latest_pipeline_run": latest_run,
            }
        finally:
            conn.close()
