#!/usr/bin/env python3
"""
Generate RSS sources data for Jekyll footer from config/rss_sources.yaml
"""

import os
import yaml
import json
from pathlib import Path

# Source mapping to display names and URLs
SOURCE_DISPLAY_INFO = {
    "arxiv": {
        "name": "arXiv",
        "url": "https://arxiv.org/",
        "icon": "fas fa-archive"
    },
    "aps": {
        "name": "APS",
        "url": "https://journals.aps.org/",
        "icon": "fas fa-atom"
    },
    "nature": {
        "name": "Nature",
        "url": "https://www.nature.com/",
        "icon": "fas fa-leaf"
    },
    "science": {
        "name": "Science",
        "url": "https://www.science.org/",
        "icon": "fas fa-flask"
    },
    "springer": {
        "name": "Springer",
        "url": "https://link.springer.com/",
        "icon": "fas fa-book-open"
    },
    "ieee": {
        "name": "IEEE",
        "url": "https://ieeexplore.ieee.org/",
        "icon": "fas fa-bolt"
    },
    "acm": {
        "name": "ACM",
        "url": "https://dl.acm.org/",
        "icon": "fas fa-laptop-code"
    },
    "other": {
        "name": "Other Sources",
        "url": "#",
        "icon": "fas fa-rss"
    }
}

def generate_rss_sources_data():
    """Generate Jekyll data file for RSS sources."""
    config_dir = Path("config")
    jekyll_data_dir = Path("jekyll_site/_data")
    
    # Ensure directories exist
    jekyll_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Load RSS sources from YAML
    sources_path = config_dir / "rss_sources.yaml"
    if not sources_path.exists():
        print(f"Error: RSS sources file not found at {sources_path}")
        return
    
    with open(sources_path, "r", encoding="utf-8") as f:
        sources_data = yaml.safe_load(f) or {}
    
    # Extract unique sources from feeds
    unique_sources = set()
    for feed in sources_data.get("feeds", []):
        source = feed.get("source", "").lower()
        if source and source in SOURCE_DISPLAY_INFO:
            unique_sources.add(source)
    
    # Create source objects with display info
    sources_list = []
    for source_id in sorted(unique_sources):
        if source_id in SOURCE_DISPLAY_INFO:
            source_info = SOURCE_DISPLAY_INFO[source_id].copy()
            source_info["id"] = source_id
            sources_list.append(source_info)
    
    # Add any missing sources that are in the default list but not in feeds
    for source_id, source_info in SOURCE_DISPLAY_INFO.items():
        if source_id not in unique_sources and source_id != "other":
            source_obj = source_info.copy()
            source_obj["id"] = source_id
            source_obj["enabled"] = False  # Mark as not currently in use
            sources_list.append(source_obj)
    
    # Sort by name
    sources_list.sort(key=lambda x: x["name"])
    
    # Prepare data for Jekyll
    output_data = {
        "sources": sources_list,
        "count": len([s for s in sources_list if s.get("enabled", True)]),
        "generated_at": str(datetime.now().isoformat())
    }
    
    # Write to Jekyll data file
    output_path = jekyll_data_dir / "rss_sources.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Generated RSS sources data: {len(sources_list)} sources")
    print(f"Output written to: {output_path}")
    
    # Also create a YAML version for Jekyll (optional)
    output_yaml_path = jekyll_data_dir / "rss_sources.yaml"
    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Also created YAML version: {output_yaml_path}")

if __name__ == "__main__":
    from datetime import datetime
    generate_rss_sources_data()