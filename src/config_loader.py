"""
Configuration loader for the Quantum RSS Radar system.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import os
from pathlib import Path
from typing import Dict, List
import dotenv

from .models import Config, FeedConfig, SourceConfig, PaperSource


def load_config() -> Config:
    """
    Load system configuration from environment variables.

    Returns:
        Config object with loaded settings
    """
    # Load environment variables from .env file if present
    dotenv.load_dotenv()

    # Get LLM configuration from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL")
    llm_model = os.getenv("LLM_MODEL", "deepseek-chat")

    # Determine provider based on base_url
    llm_provider = "generic"
    if llm_base_url:
        if "deepseek" in llm_base_url:
            llm_provider = "deepseek"
        elif "openai" in llm_base_url:
            llm_provider = "openai"
        elif "azure" in llm_base_url:
            llm_provider = "azure"
        elif "localhost" in llm_base_url or "127.0.0.1" in llm_base_url:
            llm_provider = "local"

    # Get email configuration from environment variables
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    email_sender = os.getenv("EMAIL_SENDER")
    email_recipient = os.getenv("EMAIL_RECIPIENT")
    email_smtp_server = os.getenv("EMAIL_SMTP_SERVER")
    email_smtp_port_str = os.getenv("EMAIL_SMTP_PORT", "587")
    email_smtp_username = os.getenv("EMAIL_SMTP_USERNAME")
    email_smtp_password = os.getenv("EMAIL_SMTP_PASSWORD")

    # Convert email port
    try:
        email_smtp_port = int(email_smtp_port_str)
    except ValueError:
        email_smtp_port = 587

    # Get processing settings from environment variables
    max_papers_per_feed = int(os.getenv("MAX_PAPERS_PER_FEED", "50"))
    min_relevance_score = float(os.getenv("MIN_RELEVANCE_SCORE", "5.0"))
    top_n_recommendations = int(os.getenv("TOP_N_RECOMMENDATIONS", "10"))

    # Get output directories
    output_dir = os.getenv("OUTPUT_DIR", "data")
    web_dir = os.getenv("WEB_DIR", "web_output")

    # Get advanced settings
    rss_timeout = int(os.getenv("RSS_TIMEOUT", "30"))
    llm_timeout = int(os.getenv("LLM_TIMEOUT", "60"))
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    config = Config(
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,

        email_enabled=email_enabled,
        email_sender=email_sender,
        email_recipient=email_recipient,
        email_smtp_server=email_smtp_server,
        email_smtp_port=email_smtp_port,
        email_smtp_username=email_smtp_username,
        email_smtp_password=email_smtp_password,

        max_papers_per_feed=max_papers_per_feed,
        min_relevance_score=min_relevance_score,
        top_n_recommendations=top_n_recommendations,

        output_dir=output_dir,
        web_dir=web_dir,
    )

    # Store additional config as dynamic attributes
    config._rss_timeout = rss_timeout
    config._llm_timeout = llm_timeout
    config._llm_temperature = llm_temperature
    config._debug = debug
    config._jekyll_site_dir = "jekyll_site/_site"
    config._deep_read_enabled = os.getenv("DEEP_READ_ENABLED", "true").lower() == "true"
    config._llm_cache_enabled = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
    config._public_website_url = os.getenv("PUBLIC_WEBSITE_URL", "")

    return config


def load_feeds(config_dir: str = "config") -> List[FeedConfig]:
    """
    Load RSS feed configurations from YAML file.

    Args:
        config_dir: Path to configuration directory

    Returns:
        List of FeedConfig objects (no 'category' field — LLM assigns direction)
    """
    feeds_path = Path(config_dir) / "rss_sources.yaml"
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feeds configuration not found at {feeds_path}")

    import yaml
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
            source=source,
            max_items=feed_data.get("max_items", -1),
            update_frequency=feed_data.get("update_frequency", {}),
        )
        feeds.append(feed)

    return feeds


def load_sources(config_dir: str = "config") -> Dict[str, SourceConfig]:
    """
    Load source (publisher) colour configuration from YAML file.

    Returns:
        Dict mapping source keys (e.g. 'arxiv', 'nature') to SourceConfig
        containing display_name and color for website tags.
    """
    feeds_path = Path(config_dir) / "rss_sources.yaml"
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feeds configuration not found at {feeds_path}")

    import yaml
    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds_data = yaml.safe_load(f) or {}

    sources = {}
    for source_key, source_data in feeds_data.get("sources", {}).items():
        sources[source_key] = SourceConfig(
            display_name=source_data.get("display_name", source_key),
            color=source_data.get("color", "#757575"),
        )

    return sources


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
