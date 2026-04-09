"""
Paper deduplication for the Quantum RSS Radar system.
"""

import hashlib
from typing import List, Dict, Set, Tuple
import logging
from collections import defaultdict

from .models import Paper

logger = logging.getLogger(__name__)


def compute_title_similarity(title1: str, title2: str) -> float:
    """
    Compute similarity between two paper titles.
    
    Args:
        title1: First title
        title2: Second title
        
    Returns:
        Similarity score between 0 and 1
    """
    # Convert to lowercase and split into words
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def compute_author_similarity(authors1: List[str], authors2: List[str]) -> float:
    """
    Compute similarity between author lists.
    
    Args:
        authors1: First author list
        authors2: Second author list
        
    Returns:
        Similarity score between 0 and 1
    """
    if not authors1 or not authors2:
        return 0.0
    
    # Extract last names (simple heuristic)
    def extract_last_name(author: str) -> str:
        parts = author.split()
        if not parts:
            return ""
        # Last part is usually last name
        return parts[-1].lower()
    
    last_names1 = {extract_last_name(a) for a in authors1 if extract_last_name(a)}
    last_names2 = {extract_last_name(a) for a in authors2 if extract_last_name(a)}
    
    if not last_names1 or not last_names2:
        return 0.0
    
    intersection = len(last_names1.intersection(last_names2))
    union = len(last_names1.union(last_names2))
    
    return intersection / union if union > 0 else 0.0


def are_papers_duplicate(paper1: Paper, paper2: Paper, 
                         title_threshold: float = 0.7,
                         author_threshold: float = 0.5) -> bool:
    """
    Determine if two papers are duplicates.
    
    Args:
        paper1: First paper
        paper2: Second paper
        title_threshold: Title similarity threshold
        author_threshold: Author similarity threshold
        
    Returns:
        True if papers are likely duplicates
    """
    # Check if same source and same ID (for arXiv)
    if paper1.source == paper2.source:
        if paper1.source.value == "arxiv":
            # Extract arXiv IDs
            arxiv_id1 = paper1.raw_data.get("arxiv_id", "")
            arxiv_id2 = paper2.raw_data.get("arxiv_id", "")
            if arxiv_id1 and arxiv_id2 and arxiv_id1 == arxiv_id2:
                return True
    
    # Check title similarity
    title_sim = compute_title_similarity(paper1.title, paper2.title)
    if title_sim < title_threshold:
        return False
    
    # Check author similarity
    author_sim = compute_author_similarity(paper1.authors, paper2.authors)
    if author_sim < author_threshold:
        return False
    
    # Additional checks
    # Check publication date (within 7 days)
    date_diff = abs((paper1.published - paper2.published).days)
    if date_diff > 7:
        return False
    
    # Check abstract similarity (simple length-based)
    len1 = len(paper1.abstract)
    len2 = len(paper2.abstract)
    if min(len1, len2) > 0:
        length_ratio = max(len1, len2) / min(len1, len2)
        if length_ratio > 3:  # Abstracts very different in length
            return False
    
    logger.debug(f"Found duplicate: {paper1.title[:50]}... and {paper2.title[:50]}...")
    logger.debug(f"  Title similarity: {title_sim:.2f}, Author similarity: {author_sim:.2f}")
    
    return True


def find_duplicate_groups(papers: List[Paper]) -> List[List[int]]:
    """
    Find groups of duplicate papers.
    
    Args:
        papers: List of papers
        
    Returns:
        List of groups, each group is a list of indices of duplicate papers
    """
    logger.info(f"Looking for duplicates among {len(papers)} papers")
    
    n = len(papers)
    visited = [False] * n
    groups = []
    
    for i in range(n):
        if visited[i]:
            continue
        
        group = [i]
        visited[i] = True
        
        for j in range(i + 1, n):
            if visited[j]:
                continue
            
            if are_papers_duplicate(papers[i], papers[j]):
                group.append(j)
                visited[j] = True
        
        if len(group) > 1:
            groups.append(group)
            logger.info(f"Found duplicate group of size {len(group)}")
    
    logger.info(f"Found {len(groups)} duplicate groups")
    return groups


def select_best_paper_from_group(papers: List[Paper], indices: List[int]) -> Tuple[int, Paper]:
    """
    Select the best paper from a group of duplicates.
    
    Args:
        papers: Full list of papers
        indices: Indices of duplicate papers in the group
        
    Returns:
        Tuple of (selected_index, selected_paper)
    """
    if len(indices) == 1:
        return indices[0], papers[indices[0]]
    
    group_papers = [papers[i] for i in indices]
    
    # Score each paper based on quality metrics
    scores = []
    for idx, paper in zip(indices, group_papers):
        score = 0
        
        # Prefer arXiv (usually has full abstract)
        if paper.source.value == "arxiv":
            score += 3
        
        # Prefer papers with longer abstracts (more information)
        score += min(len(paper.abstract) / 1000, 2)  # Up to 2 points
        
        # Prefer papers with more authors (might be more significant)
        score += min(len(paper.authors) / 5, 1)  # Up to 1 point
        
        # Prefer newer papers (within reason)
        # This is already handled by RSS recency
        
        scores.append((score, idx, paper))
    
    # Sort by score (descending), then by index (ascending for tie-breaking)
    scores.sort(key=lambda x: (-x[0], x[1]))
    
    best_score, best_idx, best_paper = scores[0]
    
    logger.debug(f"Selected paper {best_idx} from duplicate group (score: {best_score:.2f})")
    
    return best_idx, best_paper


def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
    """
    Remove duplicate papers from the list.
    
    Args:
        papers: List of papers (may contain duplicates)
        
    Returns:
        List of unique papers
    """
    if len(papers) <= 1:
        return papers
    
    logger.info(f"Deduplicating {len(papers)} papers")
    
    # Find duplicate groups
    duplicate_groups = find_duplicate_groups(papers)
    
    if not duplicate_groups:
        logger.info("No duplicates found")
        return papers
    
    # Mark which papers to keep
    keep = [True] * len(papers)
    kept_from_group = {}
    
    for group in duplicate_groups:
        # Select best paper from group
        best_idx, best_paper = select_best_paper_from_group(papers, group)
        
        # Mark others for removal
        for idx in group:
            if idx != best_idx:
                keep[idx] = False
        
        # Update the kept paper with merged information if needed
        kept_from_group[best_idx] = group
    
    # Create deduplicated list
    deduplicated = [paper for i, paper in enumerate(papers) if keep[i]]
    
    # Log duplicates found
    total_duplicates = len(papers) - len(deduplicated)
    logger.info(f"Removed {total_duplicates} duplicate papers, kept {len(deduplicated)} unique papers")
    
    # Log details about removed duplicates
    for group in duplicate_groups:
        if len(group) > 1:
            kept_idx = next(i for i in group if keep[i])
            removed_indices = [i for i in group if i != kept_idx]
            logger.debug(f"Kept paper {kept_idx}, removed duplicates: {removed_indices}")
    
    return deduplicated


def merge_paper_sources(papers: List[Paper]) -> Dict[str, List[str]]:
    """
    Create a mapping from paper IDs to their sources (for debugging).
    
    Args:
        papers: List of papers
        
    Returns:
        Dict mapping paper title to list of sources
    """
    source_map = defaultdict(list)
    
    for paper in papers:
        # Use a simplified title as key
        simple_title = paper.title.lower()[:100]
        source_map[simple_title].append(paper.source.value)
    
    # Find papers with multiple sources
    multi_source = {title: sources for title, sources in source_map.items() if len(sources) > 1}
    
    if multi_source:
        logger.info(f"Found {len(multi_source)} papers from multiple sources")
        for title, sources in list(multi_source.items())[:5]:  # Show first 5
            logger.debug(f"  {title[:50]}...: {sources}")
    
    return dict(source_map)