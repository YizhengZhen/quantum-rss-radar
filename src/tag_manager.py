"""
Tag manager for the Quantum RSS Radar system.
Manages keyword tags extracted from research papers.
"""

import json
from pathlib import Path
from typing import List, Dict, Set, Optional
from datetime import datetime
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class TagManager:
    """Manages a library of tags with frequency tracking."""
    
    def __init__(self, tag_file: str = "data/tags.json"):
        """
        Initialize the tag manager.
        
        Args:
            tag_file: Path to the tag database file
        """
        self.tag_file = Path(tag_file)
        self.tags: Dict[str, Dict[str, any]] = {}
        self._load_tags()
        
    def _load_tags(self):
        """Load tags from the JSON file."""
        try:
            if self.tag_file.exists():
                with open(self.tag_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tags = data.get("tags", {})
                logger.info(f"Loaded {len(self.tags)} tags from {self.tag_file}")
            else:
                self.tags = {}
                logger.info(f"Created new tag database at {self.tag_file}")
        except Exception as e:
            logger.error(f"Failed to load tags from {self.tag_file}: {e}")
            self.tags = {}
    
    def _save_tags(self):
        """Save tags to the JSON file."""
        try:
            self.tag_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tags": self.tags,
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_tags": len(self.tags)
                }
            }
            with open(self.tag_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.tags)} tags to {self.tag_file}")
        except Exception as e:
            logger.error(f"Failed to save tags to {self.tag_file}: {e}")
    
    def get_existing_tags(self, limit: int = 100) -> List[str]:
        """
        Get existing tags sorted by frequency.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of tag names sorted by frequency (descending)
        """
        sorted_tags = sorted(
            self.tags.items(), 
            key=lambda x: x[1].get("count", 0), 
            reverse=True
        )
        return [tag for tag, _ in sorted_tags[:limit]]
    
    def match_existing_tags(self, text: str, limit: int = 5) -> List[str]:
        """
        Match existing tags against text content.
        
        Args:
            text: Text to match against (title + abstract)
            limit: Maximum number of tags to return
            
        Returns:
            List of matching tags sorted by relevance
        """
        text_lower = text.lower()
        matches = []
        
        for tag_name, tag_data in self.tags.items():
            if tag_name.lower() in text_lower:
                # Score based on frequency and exact match
                frequency = tag_data.get("count", 0)
                # Check for exact word boundary matches
                pattern = r'\b' + re.escape(tag_name.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    score = frequency * 2  # Bonus for exact match
                else:
                    score = frequency
                matches.append((tag_name, score))
        
        # Sort by score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in matches[:limit]]
    
    def add_tag(self, tag: str):
        """
        Add or update a tag in the database.
        
        Args:
            tag: Tag name (will be normalized)
        """
        # Normalize tag: lowercase, replace spaces with hyphens
        normalized_tag = tag.lower().strip()
        normalized_tag = re.sub(r'\s+', '-', normalized_tag)
        # Remove special characters (keep hyphens and alphanumeric)
        normalized_tag = re.sub(r'[^a-z0-9\-]', '', normalized_tag)
        
        if not normalized_tag:
            return
        
        if normalized_tag in self.tags:
            # Update existing tag
            self.tags[normalized_tag]["count"] += 1
            self.tags[normalized_tag]["last_seen"] = datetime.now().isoformat()
        else:
            # Add new tag
            self.tags[normalized_tag] = {
                "count": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
        
        self._save_tags()
    
    def add_tags(self, tags: List[str]):
        """
        Add multiple tags at once.
        
        Args:
            tags: List of tag names
        """
        for tag in tags:
            self.add_tag(tag)
    
    def extract_and_assign_tags(self, 
                               paper_title: str, 
                               abstract: str,
                               llm_tags: List[str]) -> List[str]:
        """
        Extract and assign tags for a paper.
        Prioritizes existing tags, then adds LLM-generated tags.
        
        Args:
            paper_title: Paper title
            abstract: Paper abstract
            llm_tags: Tags extracted by LLM
            
        Returns:
            List of assigned tags (max 5)
        """
        text = f"{paper_title} {abstract}"
        
        # 1. Match existing tags
        existing_matches = self.match_existing_tags(text, limit=5)
        
        # 2. Add LLM tags (if we need more)
        assigned_tags = existing_matches.copy()
        
        for llm_tag in llm_tags:
            if len(assigned_tags) >= 5:
                break
            if llm_tag not in assigned_tags:
                assigned_tags.append(llm_tag)
        
        # 3. Update tag database with all tags
        for tag in assigned_tags:
            self.add_tag(tag)
        
        return assigned_tags[:5]
    
    def get_tag_stats(self) -> Dict[str, any]:
        """
        Get statistics about the tag database.
        
        Returns:
            Dictionary with tag statistics
        """
        total_tags = len(self.tags)
        total_uses = sum(tag_data.get("count", 0) for tag_data in self.tags.values())
        
        # Most used tags
        most_used = sorted(
            self.tags.items(), 
            key=lambda x: x[1].get("count", 0), 
            reverse=True
        )[:10]
        
        # Newest tags
        newest = sorted(
            self.tags.items(),
            key=lambda x: x[1].get("first_seen", ""),
            reverse=True
        )[:10]
        
        return {
            "total_tags": total_tags,
            "total_uses": total_uses,
            "most_used": [(tag, data["count"]) for tag, data in most_used],
            "newest_tags": [(tag, data["first_seen"]) for tag, data in newest]
        }
    
    def cleanup_tags(self, min_count: int = 2):
        """
        Remove rarely used tags.
        
        Args:
            min_count: Minimum usage count to keep tag
        """
        initial_count = len(self.tags)
        self.tags = {
            tag: data 
            for tag, data in self.tags.items() 
            if data.get("count", 0) >= min_count
        }
        removed = initial_count - len(self.tags)
        if removed > 0:
            self._save_tags()
            logger.info(f"Removed {removed} tags with count < {min_count}")
        return removed


def normalize_tag(tag: str) -> str:
    """
    Normalize a tag string.
    
    Args:
        tag: Raw tag string
        
    Returns:
        Normalized tag
    """
    # Lowercase
    tag = tag.lower().strip()
    # Replace spaces and underscores with hyphens
    tag = re.sub(r'[\s_]+', '-', tag)
    # Remove special characters
    tag = re.sub(r'[^a-z0-9\-]', '', tag)
    # Remove multiple hyphens
    tag = re.sub(r'\-+', '-', tag)
    # Remove leading/trailing hyphens
    tag = tag.strip('-')
    return tag


def extract_keywords_from_text(text: str, max_keywords: int = 10) -> List[str]:
    """
    Simple keyword extraction (fallback if LLM is not available).
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of extracted keywords
    """
    # Common stopwords to ignore
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'down', 'out', 'over', 'under',
        'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall'
    }
    
    # Extract words (alphanumeric with hyphens)
    words = re.findall(r'[a-zA-Z0-9\-]+', text.lower())
    
    # Filter stopwords and short words
    filtered_words = [
        word for word in words 
        if word not in stopwords and len(word) > 3 and not word.isdigit()
    ]
    
    # Count frequencies
    word_counts = Counter(filtered_words)
    
    # Get most common keywords
    keywords = [word for word, _ in word_counts.most_common(max_keywords)]
    
    # Normalize keywords
    normalized_keywords = [normalize_tag(kw) for kw in keywords]
    
    return normalized_keywords


# Global tag manager instance
_global_tag_manager: Optional[TagManager] = None


def get_tag_manager() -> TagManager:
    """
    Get the global tag manager instance.
    
    Returns:
        TagManager instance
    """
    global _global_tag_manager
    if _global_tag_manager is None:
        _global_tag_manager = TagManager()
    return _global_tag_manager