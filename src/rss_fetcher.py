"""
RSS feed fetcher for the Quantum RSS Radar system.
'category' has been removed — the LLM assigns a research 'direction' during analysis.
"""

import hashlib
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import feedparser
import requests

from .models import FeedConfig, Paper, PaperSource

logger = logging.getLogger(__name__)


def normalize_doi(doi: str | None) -> str:
    """Normalize a DOI: lowercase, strip URL/prefix wrappers."""
    if not doi:
        return ""
    doi = str(doi).strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi = doi.replace("doi:", "")
    return doi.strip()


def normalize_arxiv_id(arxiv_id: str) -> str:
    """Extract a bare arXiv ID (no version suffix, no URL).  Returns '' if the
    input does not look like an arXiv ID."""
    if not arxiv_id:
        return ""
    # Modern arXiv IDs: 2301.00001, optionally with version suffix
    m = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", arxiv_id)
    if m:
        return m.group(1)
    # Old-style arXiv IDs: quant-ph/0501001
    m2 = re.search(r"([a-z\-]+(\.[A-Z]{2})?/\d{7})(?:v\d+)?", arxiv_id)
    if m2:
        return m2.group(1)
    return ""


def extract_arxiv_id(link: str) -> str:
    """Extract a normalized arXiv ID (version stripped) from a link/entry id."""
    return normalize_arxiv_id(link)


def extract_arxiv_id_keep_version(link: str) -> str:
    """Extract an arXiv ID KEEPING the version suffix, e.g. '2301.00001v2'.

    Product decision: different versions (v1, v2, …) are treated as different
    papers, so the version is part of the identity.  Returns '' if the input
    has no arXiv ID.
    """
    if not link:
        return ""
    m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", link)
    if m:
        return m.group(1)
    m2 = re.search(r"([a-z\-]+(\.[A-Z]{2})?/\d{7}(?:v\d+)?)", link)
    if m2:
        return m2.group(1)
    return ""


def extract_doi_from_entry(entry, link: str = "") -> str:
    """Extract a normalized DOI from an RSS entry.

    Priority: prism:doi → dc:identifier → regex from link.
    """
    doi = entry.get("prism_doi", "") or entry.get("dc_identifier", "")
    if not doi and link:
        m = re.search(r"(10\.\d{4,9}/[^\s&?#]+)", link, re.IGNORECASE)
        if m:
            doi = m.group(1)
    return normalize_doi(doi)


def generate_paper_id(title: str, authors: list[str], published: datetime) -> str:
    """
    Generate a unique ID for a paper based on title, authors, and publication date.

    Args:
        title: Paper title
        authors: List of authors
        published: Publication date

    Returns:
        Unique string ID
    """
    # Create a hash from key identifying information
    content = (
        f"{title.lower()}|{','.join(sorted(authors)).lower()}|{published.isoformat()}"
    )
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def parse_arxiv_entry(entry, feed_name: str) -> Paper | None:
    """
    Parse an arXiv RSS entry.

    Args:
        entry: feedparser entry
        feed_name: Name of the RSS feed

    Returns:
        Paper object or None if parsing fails
    """
    try:
        title = entry.get("title", "").strip()
        # arXiv titles often have format "Title [arXiv:1234.5678v1]"
        if "[arXiv:" in title:
            title = title.split("[arXiv:")[0].strip()

        # Extract authors
        authors = []
        if "authors" in entry:
            for author in entry.authors:
                authors.append(author.get("name", ""))
        elif "author" in entry:
            authors = [entry.author]

        abstract = entry.get("summary", "").strip()
        link = entry.get("link", "").strip()

        # Parse publication date. arXiv RSS 'published' is RFC-822 style
        # ("Tue, 18 Aug 2026 18:00:00 GMT"), which fromisoformat cannot parse;
        # feedparser also exposes the parsed struct via published_parsed.
        published = None
        published_str = entry.get("published", entry.get("updated", ""))
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass
        if published is None and entry.get("published_parsed"):
            import time as _time

            try:
                published = datetime.fromtimestamp(_time.mktime(entry.published_parsed))
            except (ValueError, TypeError, OverflowError):
                published = None
        if published is None:
            published = datetime.now()

        # arXiv ID WITH version suffix → stable dedup-friendly ID.
        # Product decision: different versions (v1, v2, …) are different papers,
        # so the version is part of the identity (arxiv:2301.00001v1).
        arxiv_id = extract_arxiv_id_keep_version(entry.get("id", "") or link)
        paper_id = (
            f"arx:{arxiv_id}"
            if arxiv_id
            else generate_paper_id(title, authors, published)
        )

        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            link=link,
            published=published,
            source=PaperSource.ARXIV,
            feed_name=feed_name,
            rss_fetch_date=datetime.now(),
            raw_data={
                "arxiv_id": arxiv_id,
                "categories": entry.get("tags", []),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to parse arXiv entry: {e}")
        return None


def parse_generic_entry(entry, feed_name: str, source: PaperSource) -> Paper | None:
    """
    Parse a generic RSS entry from journals.
    Note: 'category' parameter removed — LLM assigns direction later.

    Args:
        entry: feedparser entry
        feed_name: Name of the RSS feed
        source: Paper source

    Returns:
        Paper object or None if parsing fails
    """
    try:
        title = entry.get("title", "").strip()

        # Extract authors
        authors = []
        if "authors" in entry:
            for author in entry.authors:
                authors.append(author.get("name", ""))
        elif "author" in entry:
            authors = [entry.author]
        elif "dc_creator" in entry:
            authors = [entry.dc_creator]

        abstract = (
            entry.get("summary", "").strip() or entry.get("description", "").strip()
        )
        link = entry.get("link", "").strip()

        # Parse publication date
        published_str = entry.get(
            "published", entry.get("updated", entry.get("dc_date", ""))
        )
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # Try other date formats
            try:
                published = datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S %z")
            except (ValueError, TypeError):
                published = datetime.now()

        # Extract DOI → stable dedup-friendly ID (doi:10.xxxx/yyyy)
        doi = extract_doi_from_entry(entry, link)
        paper_id = f"doi:{doi}" if doi else generate_paper_id(title, authors, published)

        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            link=link,
            published=published,
            source=source,
            feed_name=feed_name,
            rss_fetch_date=datetime.now(),
            doi=doi or None,
            raw_data={
                "guid": entry.get("id", ""),
                "tags": entry.get("tags", []),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to parse generic entry: {e}")
        return None


def fetch_feed(feed: FeedConfig, max_items: int = 50) -> list[Paper]:
    """
    Fetch and parse papers from an RSS feed.

    Args:
        feed: Feed configuration
        max_items: Maximum number of items to fetch

    Returns:
        List of Paper objects
    """
    logger.info(f"Fetching feed: {feed.name} ({feed.url})")

    try:
        # Fetch RSS feed with timeout
        response = requests.get(feed.url, timeout=30)
        response.raise_for_status()

        # Parse feed
        parsed = feedparser.parse(response.content)

        if parsed.bozo and parsed.bozo_exception:
            logger.warning(f"Feed parsing warning: {parsed.bozo_exception}")

        papers = []
        # -1 / None = unlimited; otherwise take the first max_items entries.
        # (list[:-1] would silently DROP the last entry, not mean unlimited.)
        entries = (
            parsed.entries
            if max_items is None or max_items < 0
            else parsed.entries[:max_items]
        )

        for entry in entries:
            if feed.source == PaperSource.ARXIV:
                paper = parse_arxiv_entry(entry, feed.name)
            else:
                paper = parse_generic_entry(entry, feed.name, feed.source)

            if paper:
                papers.append(paper)

        logger.info(f"Fetched {len(papers)} papers from {feed.name}")
        return papers

    except requests.RequestException as e:
        logger.error(f"Failed to fetch feed {feed.name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching feed {feed.name}: {e}")
        return []


def save_raw_feed(papers: list[Paper], output_dir: str, feed_name: str):
    """
    Save raw feed data for debugging/archival purposes.

    Args:
        papers: List of Paper objects
        output_dir: Output directory
        feed_name: Name of the feed (sanitized for filename)
    """
    if not papers:
        return

    # Create output directory
    raw_dir = Path(output_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize feed name for filename
    import re

    safe_name = re.sub(r"[^\w\-_]", "_", feed_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = raw_dir / f"{safe_name}_{timestamp}.json"

    # Save papers as JSON
    import json

    with open(filename, "w", encoding="utf-8") as f:
        json_data = [paper.dict() for paper in papers]
        json.dump(json_data, f, indent=2, default=str)

    logger.debug(f"Saved raw feed data to {filename}")


def fetch_all_feeds(
    feeds: list[FeedConfig], config, use_schedule: bool = True, today=None
) -> list[Paper]:
    """
    Fetch papers from all configured RSS feeds, gated by each feed's own
    update_frequency (per-source scheduled fetching — only feeds due today).

    Args:
        feeds: List of FeedConfig objects
        config: System configuration
        use_schedule: Whether to apply per-source scheduled fetching (default: True)
        today: Override today's date (for testing)

    Returns:
        List of all Paper objects from the feeds fetched today
    """
    from datetime import datetime

    all_papers = []

    # Per-source schedule: fetch only feeds whose update_frequency fires today.
    feeds_to_fetch = feeds
    if use_schedule:
        today = today or datetime.now().date()
        if isinstance(today, datetime):
            today = today.date()
        feeds_to_fetch = [f for f in feeds if f.is_due(today)]
        logger.info(
            f"Per-source schedule: {len(feeds_to_fetch)} of {len(feeds)} feeds due today"
        )

    for feed in feeds_to_fetch:
        papers = fetch_feed(feed, config.max_papers_per_feed)

        # Save raw data (debugging / audit trail)
        save_raw_feed(papers, config.output_dir, feed.name)

        all_papers.extend(papers)

        # Delay between requests to be polite
        time.sleep(1)

    logger.info(f"Total papers fetched: {len(all_papers)}")
    return all_papers
