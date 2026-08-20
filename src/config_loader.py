"""
Configuration loader for the Quantum RSS Radar system.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import logging
import os
from pathlib import Path

import dotenv

from .models import Config, FeedConfig, PaperSource, SourceConfig, UpdateFrequency

logger = logging.getLogger(__name__)


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
    email_smtp_port_str = os.getenv("EMAIL_SMTP_PORT") or "587"
    email_smtp_username = os.getenv("EMAIL_SMTP_USERNAME")
    email_smtp_password = os.getenv("EMAIL_SMTP_PASSWORD")

    # Convert email port
    try:
        email_smtp_port = int(email_smtp_port_str)
    except ValueError:
        email_smtp_port = 587

    # Get processing settings from environment variables
    # NB: use `os.getenv("X") or default` so an env var that is PRESENT but
    # EMPTY (e.g. an unset GitHub secret expands to "") still falls back to
    # the default instead of crashing int()/float() on ''. This bit CI in
    # run #160: 'invalid literal for int() with base 10: \'\''.
    max_papers_per_feed = int(os.getenv("MAX_PAPERS_PER_FEED") or "50")
    min_relevance_score = float(os.getenv("MIN_RELEVANCE_SCORE") or "5.0")

    # Get output directories
    output_dir = os.getenv("OUTPUT_DIR") or "data"
    web_dir = os.getenv("WEB_DIR") or "web_output"

    # Get quarterly / archive settings
    archive_dir = os.getenv("ARCHIVE_DIR") or "data/all"
    quarter_window_days = int(os.getenv("QUARTER_WINDOW_DAYS") or "90")
    quarterly_top_n = int(os.getenv("QUARTERLY_TOP_N") or "50")

    # Get advanced settings
    rss_timeout = int(os.getenv("RSS_TIMEOUT") or "30")
    llm_timeout = int(os.getenv("LLM_TIMEOUT") or "60")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE") or "0.1")
    llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS") or "2500")
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
        archive_dir=archive_dir,
        quarter_window_days=quarter_window_days,
        quarterly_top_n=quarterly_top_n,
        output_dir=output_dir,
        web_dir=web_dir,
    )

    # Store additional config as dynamic attributes
    config._rss_timeout = rss_timeout
    config._llm_timeout = llm_timeout
    config._llm_temperature = llm_temperature
    config._llm_max_tokens = llm_max_tokens
    config._debug = debug
    config._jekyll_site_dir = "jekyll_site/_site"
    config._deep_read_enabled = os.getenv("DEEP_READ_ENABLED", "true").lower() == "true"
    config._llm_cache_enabled = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
    config._arxiv_doi_enrich = os.getenv("ARXIV_DOI_ENRICH", "false").lower() == "true"
    config._public_website_url = os.getenv("PUBLIC_WEBSITE_URL", "")

    return config


def load_feeds(config_dir: str = "config") -> list[FeedConfig]:
    """
    Load RSS feed configurations from config/rss_sources.yaml.

    Flat schema — each feed independently declares every field:
      name / url / source / display_name / color /
      max_items (recommendation cap) / min_score / update_frequency.
    FeedConfig objects carry no 'category' field — LLM assigns direction.

    Args:
        config_dir: Path to configuration directory

    Returns:
        List of FeedConfig objects
    """
    feeds_path = Path(config_dir) / "rss_sources.yaml"
    if not feeds_path.exists():
        raise FileNotFoundError(f"Feeds configuration not found at {feeds_path}")

    import yaml

    with open(feeds_path, "r", encoding="utf-8") as f:
        feeds_data = yaml.safe_load(f) or {}

    feeds: list[FeedConfig] = []
    for feed_data in feeds_data.get("feeds", []):
        freq_raw = str(feed_data.get("update_frequency", "daily")).lower()
        try:
            freq = UpdateFrequency(freq_raw)
        except ValueError:
            logger.warning(
                f"Invalid update_frequency '{freq_raw}' for '{feed_data.get('name')}' "
                f"— using daily"
            )
            freq = UpdateFrequency.DAILY

        feeds.append(
            FeedConfig(
                name=feed_data["name"],
                url=feed_data["url"],
                source=_parse_source(feed_data.get("source", "")),
                display_name=feed_data.get("display_name"),
                color=feed_data.get("color"),
                max_items=feed_data.get("max_items", -1),
                min_score=float(feed_data.get("min_score", 7.0)),
                update_frequency=freq,
            )
        )

    return feeds


def _parse_source(source_str: str) -> PaperSource:
    """Parse a source key into a PaperSource, falling back to OTHER."""
    try:
        return PaperSource(source_str.lower())
    except ValueError:
        return PaperSource.OTHER


def load_sources(config_dir: str = "config") -> dict[str, SourceConfig]:
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

    sources: dict[str, SourceConfig] = {}

    # Prefer an explicit sources: block (legacy), else derive from feeds.
    if feeds_data.get("sources"):
        for source_key, source_data in feeds_data["sources"].items():
            sources[source_key] = SourceConfig(
                display_name=source_data.get("display_name", source_key),
                color=source_data.get("color", "#757575"),
            )
    else:
        for feed in feeds_data.get("feeds", []):
            src = (feed.get("source") or "").lower()
            if not src:
                continue
            sources.setdefault(
                src,
                SourceConfig(
                    display_name=feed.get("display_name") or src,
                    color=feed.get("color") or "#757575",
                ),
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
