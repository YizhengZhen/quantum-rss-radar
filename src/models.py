"""
Data models for the Quantum RSS Radar system.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PaperSource(str, Enum):
    """Sources of research papers."""
    ARXIV = "arxiv"
    APS = "aps"
    NATURE = "nature"
    SCIENCE = "science"
    IEEE = "ieee"
    ACM = "acm"
    SPRINGER = "springer"
    OTHER = "other"


class Paper(BaseModel):
    """Represents a research paper from RSS feed.

    Note: 'category' is NOT stored here.  The LLM assigns a
    'direction' during semantic analysis based on the user's
    research interests (see PaperAnalysis.direction).
    """
    id: str = Field(..., description="Unique identifier for the paper")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    abstract: str = Field(..., description="Paper abstract")
    link: str = Field(..., description="URL to paper or arXiv page")
    published: datetime = Field(..., description="Publication date")
    source: PaperSource = Field(..., description="Source of the paper")
    feed_name: str = Field(..., description="Name of the RSS feed")
    rss_fetch_date: datetime = Field(default_factory=datetime.now, description="RSS feed fetch time")
    tags: List[str] = Field(default_factory=list, description="Keywords tags, max 5")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw RSS data")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PaperAnalysis(BaseModel):
    """AI analysis results for a paper."""
    paper_id: str = Field(..., description="ID of the analyzed paper")
    relevance_score: float = Field(..., ge=0, le=10, description="Relevance score 0-10")
    recommendation: bool = Field(..., description="Whether to recommend (yes/no)")
    summary: Dict[str, str] = Field(..., description="Structured summary")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    direction: str = Field("", description="Research direction classified by LLM based on user interests")
    processing_time: datetime = Field(default_factory=datetime.now, description="When analysis was performed")

    # Structured summary fields (also included in summary dict)
    @property
    def tldr(self) -> str:
        return self.summary.get("tldr", "")

    @property
    def motivation(self) -> str:
        return self.summary.get("motivation", "")

    @property
    def method(self) -> str:
        return self.summary.get("method", "")

    @property
    def result(self) -> str:
        return self.summary.get("result", "")

    @property
    def conclusion(self) -> str:
        return self.summary.get("conclusion", "")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Config(BaseModel):
    """System configuration."""
    llm_provider: str = Field("openai", description="LLM provider: openai, deepseek, or custom")
    llm_model: str = Field("gpt-4-turbo-preview", description="LLM model name")
    llm_api_key: Optional[str] = Field(None, description="LLM API key")
    llm_base_url: Optional[str] = Field(None, description="Custom API base URL for OpenAI-compatible providers")

    email_enabled: bool = Field(False, description="Whether to send emails")
    email_sender: Optional[str] = Field(None, description="Sender email address")
    email_recipient: Optional[str] = Field(None, description="Recipient email address")
    email_smtp_server: Optional[str] = Field(None, description="SMTP server")
    email_smtp_port: Optional[int] = Field(587, description="SMTP port")
    email_smtp_username: Optional[str] = Field(None, description="SMTP username")
    email_smtp_password: Optional[str] = Field(None, description="SMTP password")

    max_papers_per_feed: int = Field(50, description="Max papers to fetch per feed")
    min_relevance_score: float = Field(5.0, description="Minimum score for recommendation")
    top_n_recommendations: int = Field(10, description="Number of top papers for email")

    output_dir: str = Field("data", description="Base output directory")
    web_dir: str = Field("web_output", description="Website output directory")

    class Config:
        extra = "allow"  # Allow dynamic attributes

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize dynamic attributes
        self._raw_config = {}
        self._jekyll_site_dir = "jekyll_site/_site"
        self._rss_timeout = 30
        self._llm_timeout = 60
        self._llm_temperature = 0.1
        self._debug = False

    @property
    def jekyll_site_dir(self) -> str:
        """Get Jekyll site directory."""
        return getattr(self, "_jekyll_site_dir", "jekyll_site/_site")

    @property
    def rss_timeout(self) -> int:
        """Get RSS fetch timeout."""
        return getattr(self, "_rss_timeout", 30)

    @property
    def llm_timeout(self) -> int:
        """Get LLM API timeout."""
        return getattr(self, "_llm_timeout", 60)

    @property
    def llm_temperature(self) -> float:
        """Get LLM temperature."""
        return getattr(self, "_llm_temperature", 0.1)

    @property
    def debug(self) -> bool:
        """Get debug mode."""
        return getattr(self, "_debug", False)

    @property
    def raw_config(self) -> dict:
        """Get raw configuration data."""
        return getattr(self, "_raw_config", {})


class FeedConfig(BaseModel):
    """Configuration for an RSS feed.

    Note: 'category' has been removed.  The LLM assigns a
    research 'direction' during semantic analysis.
    """
    name: str = Field(..., description="Feed display name")
    url: str = Field(..., description="RSS feed URL")
    source: PaperSource = Field(..., description="Source type")
    max_items: int = Field(-1, description="Maximum items to fetch (-1 for unlimited)")
    update_frequency: Dict[str, Any] = Field(default_factory=dict, description="Update frequency configuration")


class SourceConfig(BaseModel):
    """Configuration for a paper source (displayed on website)."""
    display_name: str = Field(..., description="Display name for UI (e.g. 'arXiv')")
    color: str = Field(..., description="Hex color for the source tag")
