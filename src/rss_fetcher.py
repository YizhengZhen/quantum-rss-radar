"""
RSS feed fetcher for the Quantum RSS Radar system.
"""

import feedparser
import requests
from datetime import datetime
from typing import List, Optional
import hashlib
import time
from pathlib import Path
import logging

from .models import Paper, PaperSource, FeedConfig

logger = logging.getLogger(__name__)


def generate_paper_id(title: str, authors: List[str], published: datetime) -> str:
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
    content = f"{title.lower()}|{','.join(sorted(authors)).lower()}|{published.isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def parse_arxiv_entry(entry, feed_name: str) -> Optional[Paper]:
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
        
        # Parse publication date
        published_str = entry.get("published", entry.get("updated", ""))
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            published = datetime.now()
        
        # Generate ID
        paper_id = generate_paper_id(title, authors, published)
        
        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            link=link,
            published=published,
            source=PaperSource.ARXIV,
            category="quantum",  # Will be updated from feed config
            feed_name=feed_name,
            rss_fetch_date=datetime.now(),  # Record fetch time
            raw_data={
                "arxiv_id": entry.get("id", ""),
                "categories": entry.get("tags", []),
            }
        )
    except Exception as e:
        logger.warning(f"Failed to parse arXiv entry: {e}")
        return None


def parse_generic_entry(entry, feed_name: str, source: PaperSource, category: str) -> Optional[Paper]:
    """
    Parse a generic RSS entry from journals.
    
    Args:
        entry: feedparser entry
        feed_name: Name of the RSS feed
        source: Paper source
        category: Paper category
        
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
        
        abstract = entry.get("summary", "").strip() or entry.get("description", "").strip()
        link = entry.get("link", "").strip()
        
        # Parse publication date
        published_str = entry.get("published", entry.get("updated", entry.get("dc_date", "")))
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # Try other date formats
            try:
                published = datetime.strptime(published_str, "%a, %d %b %Y %H:%M:%S %z")
            except (ValueError, TypeError):
                published = datetime.now()
        
        # Generate ID
        paper_id = generate_paper_id(title, authors, published)
        
        return Paper(
            id=paper_id,
            title=title,
            authors=authors,
            abstract=abstract,
            link=link,
            published=published,
            source=source,
            category=category,
            feed_name=feed_name,
            rss_fetch_date=datetime.now(),  # Record fetch time
            raw_data={
                "guid": entry.get("id", ""),
                "tags": entry.get("tags", []),
            }
        )
    except Exception as e:
        logger.warning(f"Failed to parse generic entry: {e}")
        return None


def fetch_feed(feed: FeedConfig, max_items: int = 50) -> List[Paper]:
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
        entries = parsed.entries[:max_items]
        
        for entry in entries:
            if feed.source == PaperSource.ARXIV:
                paper = parse_arxiv_entry(entry, feed.name)
            else:
                paper = parse_generic_entry(entry, feed.name, feed.source, feed.category)
            
            if paper:
                # Update category from feed config
                paper.category = feed.category
                papers.append(paper)
        
        logger.info(f"Fetched {len(papers)} papers from {feed.name}")
        return papers
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch feed {feed.name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching feed {feed.name}: {e}")
        return []


def save_raw_feed(papers: List[Paper], output_dir: str, feed_name: str):
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
    safe_name = re.sub(r'[^\w\-_]', '_', feed_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = raw_dir / f"{safe_name}_{timestamp}.json"
    
    # Save papers as JSON
    import json
    with open(filename, "w", encoding="utf-8") as f:
        json_data = [paper.dict() for paper in papers]
        json.dump(json_data, f, indent=2, default=str)
    
    logger.debug(f"Saved raw feed data to {filename}")


def fetch_all_feeds(feeds: List[FeedConfig], config, use_scheduler: bool = True) -> List[Paper]:
    """
    Fetch papers from all configured RSS feeds with optional scheduling.
    
    Args:
        feeds: List of FeedConfig objects
        config: System configuration
        use_scheduler: Whether to use feed scheduler (default: True)
        
    Returns:
        List of all Paper objects from all feeds
    """
    from .scheduler import get_scheduler
    
    all_papers = []
    
    # Filter feeds using scheduler if enabled
    feeds_to_fetch = feeds
    if use_scheduler:
        scheduler = get_scheduler()
        feeds_to_fetch = scheduler.filter_feeds_to_fetch(feeds)
        logger.info(f"Using scheduler: {len(feeds_to_fetch)} of {len(feeds)} feeds to fetch today")
    
    for feed in feeds_to_fetch:
        papers = fetch_feed(feed, config.max_papers_per_feed)
        
        # Save raw data
        save_raw_feed(papers, config.output_dir, feed.name)
        
        # Record fetch in scheduler
        if use_scheduler:
            scheduler.record_fetch(feed.name, len(papers))
        
        all_papers.extend(papers)
        
        # Delay between requests to be polite
        time.sleep(1)
    
    logger.info(f"Total papers fetched: {len(all_papers)}")
    
    # Log scheduler stats
    if use_scheduler and feeds_to_fetch:
        scheduler = get_scheduler()
        stats = scheduler.get_stats()
        logger.info(f"Scheduler stats: {stats['total_fetches']} total fetches, {stats['total_papers']} total papers")
    
    return all_papers
