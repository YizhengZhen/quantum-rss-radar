"""
Paper metadata normalizer for the Quantum RSS Radar system.
"""

import re
from typing import List, Dict, Any
import logging

from .models import Paper

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """
    Normalize paper title.
    
    Args:
        title: Raw title
        
    Returns:
        Normalized title
    """
    # Remove extra whitespace
    title = title.strip()
    
    # Remove arXiv suffix if present
    if "[arXiv:" in title:
        title = title.split("[arXiv:")[0].strip()
    
    # Capitalize first letter of each word (but preserve acronyms)
    words = title.split()
    normalized_words = []
    for word in words:
        if word.isupper() or word.islower():
            # For all-uppercase or all-lowercase words, capitalize first letter
            normalized_words.append(word.capitalize())
        else:
            # Preserve existing capitalization (e.g., "PhD", "LLM")
            normalized_words.append(word)
    
    return " ".join(normalized_words)


def normalize_authors(authors: List[str]) -> List[str]:
    """
    Normalize author names.
    
    Args:
        authors: List of raw author names
        
    Returns:
        List of normalized author names
    """
    normalized = []
    
    for author in authors:
        if not author or author.strip() == "":
            continue
        
        # Remove extra whitespace
        author = author.strip()
        
        # Handle common patterns
        # Remove email addresses
        if "@" in author:
            author = author.split("<")[0].strip()
        
        # Remove affiliations in parentheses
        if "(" in author and ")" in author:
            # Try to remove institutional affiliations
            # e.g., "John Doe (Harvard University)" -> "John Doe"
            author = re.sub(r'\s*\([^)]*\)$', '', author)
        
        # Standardize name format
        # Handle "Doe, John" format
        if "," in author and author.count(",") == 1:
            last, first = author.split(",")
            author = f"{first.strip()} {last.strip()}"
        
        # Capitalize properly
        parts = author.split()
        capitalized_parts = []
        for part in parts:
            if "-" in part:
                # Handle hyphenated names
                subparts = part.split("-")
                capitalized_subparts = [s.capitalize() for s in subparts]
                capitalized_parts.append("-".join(capitalized_subparts))
            elif part.isupper() and len(part) > 1:
                # Preserve all-caps names (like "MIT")
                capitalized_parts.append(part)
            elif part.lower() in ["van", "von", "de", "der", "la"]:
                # Preserve lowercase particles
                capitalized_parts.append(part.lower())
            else:
                capitalized_parts.append(part.capitalize())
        
        author = " ".join(capitalized_parts)
        normalized.append(author)
    
    return normalized


def normalize_abstract(abstract: str) -> str:
    """
    Normalize paper abstract.
    
    Args:
        abstract: Raw abstract
        
    Returns:
        Normalized abstract
    """
    if not abstract:
        return ""
    
    # Remove HTML tags
    import html
    abstract = html.unescape(abstract)
    
    # Remove common LaTeX/math formatting
    abstract = re.sub(r'\$[^$]+\$', '[MATH]', abstract)  # Inline math
    abstract = re.sub(r'\\[a-zA-Z]+\{[^}]+\}', '', abstract)  # LaTeX commands
    
    # Remove URLs
    abstract = re.sub(r'https?://\S+', '[URL]', abstract)
    
    # Remove excessive whitespace
    abstract = re.sub(r'\s+', ' ', abstract)
    
    # Capitalize first letter
    abstract = abstract.strip()
    if abstract and not abstract[0].isupper():
        abstract = abstract[0].upper() + abstract[1:]
    
    # Ensure it ends with a period
    if abstract and not abstract.endswith(('.', '!', '?')):
        abstract = abstract + '.'
    
    return abstract


def normalize_paper(paper: Paper) -> Paper:
    """
    Normalize all metadata in a paper.
    
    Args:
        paper: Input paper
        
    Returns:
        Normalized paper (new instance)
    """
    logger.debug(f"Normalizing paper: {paper.title[:50]}...")
    
    # Create a copy of the paper
    normalized = paper.copy()
    
    # Normalize title
    normalized.title = normalize_title(paper.title)
    
    # Normalize authors
    normalized.authors = normalize_authors(paper.authors)
    
    # Normalize abstract
    normalized.abstract = normalize_abstract(paper.abstract)
    
    # Clean up link
    if paper.link:
        # Remove tracking parameters
        if "?" in paper.link:
            base = paper.link.split("?")[0]
            # Keep arXiv IDs
            if "arxiv.org" in base:
                normalized.link = base
    
    # Extract and clean categories
    if "categories" in paper.raw_data:
        categories = paper.raw_data["categories"]
        if isinstance(categories, list):
            # Flatten categories
            flat_categories = []
            for cat in categories:
                if isinstance(cat, dict) and "term" in cat:
                    flat_categories.append(cat["term"])
                elif isinstance(cat, str):
                    flat_categories.append(cat)
            paper.raw_data["categories"] = flat_categories
    
    return normalized


def normalize_papers(papers: List[Paper]) -> List[Paper]:
    """
    Normalize a list of papers.
    
    Args:
        papers: List of input papers
        
    Returns:
        List of normalized papers
    """
    logger.info(f"Normalizing {len(papers)} papers")
    
    normalized_papers = []
    for paper in papers:
        try:
            normalized = normalize_paper(paper)
            normalized_papers.append(normalized)
        except Exception as e:
            logger.warning(f"Failed to normalize paper {paper.id}: {e}")
            # Keep original paper if normalization fails
            normalized_papers.append(paper)
    
    logger.info(f"Normalized {len(normalized_papers)} papers")
    return normalized_papers


def extract_keywords_from_title(title: str) -> List[str]:
    """
    Extract potential keywords from paper title.
    
    Args:
        title: Paper title
        
    Returns:
        List of potential keywords
    """
    # Common stop words to remove
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after',
        'using', 'via', 'based', 'approach', 'method', 'model', 'system',
        'analysis', 'study', 'investigation', 'paper', 'article', 'review'
    }
    
    # Clean title
    title = title.lower()
    title = re.sub(r'[^\w\s-]', ' ', title)  # Remove punctuation
    
    # Split into words
    words = title.split()
    
    # Filter stop words and short words
    keywords = []
    for word in words:
        if (word not in stop_words and 
            len(word) > 3 and 
            not word.isnumeric() and
            word not in keywords):
            keywords.append(word)
    
    return keywords[:10]  # Return top 10 keywords


def enrich_paper_metadata(paper: Paper) -> Paper:
    """
    Enrich paper metadata with additional derived fields.
    
    Args:
        paper: Input paper
        
    Returns:
        Enriched paper
    """
    enriched = paper.copy()
    
    # Extract keywords from title
    keywords = extract_keywords_from_title(paper.title)
    
    # Add to raw data
    enriched.raw_data["derived_keywords"] = keywords
    
    # Determine if it's a review paper based on title
    title_lower = paper.title.lower()
    is_review = any(term in title_lower for term in [
        'review', 'survey', 'overview', 'perspective', 'tutorial',
        'introduction to', 'state of the art', 'comprehensive study'
    ])
    enriched.raw_data["is_review"] = is_review
    
    # Estimate reading time from abstract length
    word_count = len(paper.abstract.split())
    reading_time_minutes = max(1, word_count // 200)  # ~200 words per minute
    enriched.raw_data["estimated_reading_time_minutes"] = reading_time_minutes
    
    return enriched