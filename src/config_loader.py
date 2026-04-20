"""
Configuration loader for the Quantum RSS Radar system.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import dotenv

from .models import Config, FeedConfig, CategoryConfig, PaperSource


def load_config(config_dir: str = "config") -> Config:
    """
    Load system configuration from YAML files and environment variables.
    
    Args:
        config_dir: Path to configuration directory
        
    Returns:
        Config object with loaded settings
    """
    # Load environment variables from .env file if present
    dotenv.load_dotenv()
    
    config_path = Path(config_dir) / "settings.yaml"
    if not config_path.exists():
        # Create default config
        config = Config()
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        
        # Helper function to resolve environment variables
        def resolve_env_var(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.getenv(env_var)
            return value
        
        # Get LLM configuration with env var resolution
        llm_config = config_data.get("llm", {})
        llm_api_key = resolve_env_var(llm_config.get("api_key"))
        llm_base_url = resolve_env_var(llm_config.get("base_url"))
        
        # Get email configuration with env var resolution
        email_config = config_data.get("email", {})
        
        config = Config(
            llm_provider=llm_config.get("provider", "openai"),
            llm_model=llm_config.get("model", "gpt-4-turbo-preview"),
            llm_api_key=llm_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
            llm_base_url=llm_base_url or os.getenv("LLM_BASE_URL"),
            
            email_enabled=email_config.get("enabled", False),
            email_sender=resolve_env_var(email_config.get("sender")),
            email_recipient=resolve_env_var(email_config.get("recipient")),
            email_smtp_server=resolve_env_var(email_config.get("smtp_server")),
            email_smtp_port=email_config.get("smtp_port", 587),
            email_smtp_username=resolve_env_var(email_config.get("smtp_username")),
            email_smtp_password=resolve_env_var(email_config.get("smtp_password")),
            
            max_papers_per_feed=config_data.get("processing", {}).get("max_papers_per_feed", 50),
            min_relevance_score=config_data.get("processing", {}).get("min_relevance_score", 5.0),
            top_n_recommendations=config_data.get("processing", {}).get("top_n_recommendations", 10),
            
            output_dir=config_data.get("output_dir", "data"),
            web_dir=config_data.get("web_dir", "web_output"),
        )
    
    return config


def load_feeds(config_dir: str = "config") -> List[FeedConfig]:
    """
    Load RSS feed configurations from YAML file.
    
    Args:
        config_dir: Path to configuration directory
        
    Returns:
        List of FeedConfig objects
    """
    feeds_path = Path(config_dir) / "rss_sources.yaml"
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feeds configuration not found at {feeds_path}")
    
    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds_data = yaml.safe_load(f) or {}
    
    feeds = []
    for feed_data in feeds_data.get("feeds", []):
        source_str = feed_data.get("source", "").lower()
        try:
            source = PaperSource(source_str)
        except ValueError:
            source = PaperSource.OTHER
        
        feed = FeedConfig(
            name=feed_data["name"],
            url=feed_data["url"],
            category=feed_data["category"],
            source=source,
            max_items=feed_data.get("max_items", -1),
            update_frequency=feed_data.get("update_frequency", {}),
        )
        feeds.append(feed)
    
    return feeds


def load_categories(config_dir: str = "config") -> Dict[str, CategoryConfig]:
    """
    Load category configurations from YAML file.
    
    Args:
        config_dir: Path to configuration directory
        
    Returns:
        Dict mapping category IDs to CategoryConfig objects
    """
    feeds_path = Path(config_dir) / "rss_sources.yaml"
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feeds configuration not found at {feeds_path}")
    
    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds_data = yaml.safe_load(f) or {}
    
    categories = {}
    for category_id, category_data in feeds_data.get("categories", {}).items():
        category = CategoryConfig(
            display_name=category_data["display_name"],
            color=category_data["color"],
            priority=category_data.get("priority", 1),
        )
        categories[category_id] = category
    
    return categories


def load_research_directions(config_dir: str = "config") -> str:
    """
    Load research directions from Markdown file.
    
    Args:
        config_dir: Path to configuration directory
        
    Returns:
        Research directions as a string
    """
    directions_path = Path(config_dir) / "research_directions.md"
    if not directions_path.exists():
        return "# Research Interests\n\nAdd your research interests here."
    
    with open(directions_path, "r", encoding="utf-8") as f:
        return f.read()