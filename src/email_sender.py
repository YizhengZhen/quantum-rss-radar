"""
Email sender for the Quantum RSS Radar system.

Generates rich HTML email with source colours, direction labels,
and structured paper summaries.  Integrated directly into the
pipeline — called by orchestrator_jekyll.py after data export.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import Config, FeedConfig, Paper, PaperAnalysis, PaperSource, SourceConfig

logger = logging.getLogger(__name__)


# ── Source priority for email sorting ───────────────────────
# Primary sort: source priority (ascending = most important first)
# Secondary sort: relevance score (descending = highest first)
# See docs/email_sorting.md for full rationale.
_SOURCE_PRIORITY: dict[str, int] = {
    "arxiv": 1,
    # Nature & sub-journals
    "nature": 2,
    # Science & Science Advances
    "science": 3,
    # APS journals (PRL, PRX, PRA, PRB, PRE, RMP, …)
    "aps": 4,
    # Other known publishers
    "ieee": 5,
    "springer": 5,
    "acm": 5,
}


def _resolve_feed_config(
    paper: Paper,
    sources: dict[str, SourceConfig],
    feed_configs: dict[str, FeedConfig],
) -> tuple[str, str]:
    """Resolve display name and colour for a paper.

    Priority:
      1. Feed-level display_name/color (from feed_configs, keyed by feed_name)
      2. Source-level display_name/color (from sources, keyed by source value)
      3. Hard-coded fallback

    Returns:
        (display_name, color) tuple
    """
    # Try feed-level config first
    feed_cfg = feed_configs.get(paper.feed_name) if feed_configs else None
    if feed_cfg and feed_cfg.display_name and feed_cfg.color:
        return feed_cfg.display_name, feed_cfg.color

    # Fall back to source-level config
    src_cfg = sources.get(paper.source.value) if sources else None
    if src_cfg:
        return src_cfg.display_name, src_cfg.color

    # Hard fallback
    return paper.source.value.upper(), "#757575"


def _email_sort_key(pair: tuple) -> tuple:
    """Two-level sort key: (source_priority asc, relevance_score desc)."""
    paper, analysis = pair
    priority = _SOURCE_PRIORITY.get(paper.source.value.lower(), 9)
    return (priority, -analysis.relevance_score)


# ── Helpers ─────────────────────────────────────────────────


def _source_tag_html(source_key: str, source_display: str, source_color: str) -> str:
    return (
        f'<span style="display:inline-block; padding:2px 10px; border-radius:12px;'
        f' font-size:0.85em; font-weight:600; color:#fff; background:{source_color};">'
        f"{source_display}</span>"
    )


def _direction_badge_html(direction: str) -> str:
    return (
        f'<span style="display:inline-block; padding:2px 10px; border-radius:12px;'
        f' font-size:0.85em; font-weight:500; color:#495057; background:#e9ecef;">'
        f"{direction}</span>"
    )


# ── Single paper card ───────────────────────────────────────


def format_single_paper_html(
    paper: Paper,
    analysis: PaperAnalysis,
    sources: dict[str, SourceConfig] | None = None,
    feed_configs: dict[str, FeedConfig] | None = None,
    rank: int | None = None,
) -> str:
    src_display, src_color = _resolve_feed_config(
        paper, sources or {}, feed_configs or {}
    )

    src_tag = _source_tag_html(paper.source.value, src_display, src_color)
    dir_badge = _direction_badge_html(analysis.direction or "General / Other")
    rank_str = f"<strong>{rank}.</strong> " if rank else ""

    authors_str = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors_str += " et al."
    pub_str = paper.published.strftime("%b %d, %Y") if paper.published else "Unknown"

    rec_badge = (
        (
            '<span style="background:#7ED321; color:#fff; padding:2px 10px;'
            ' border-radius:12px; font-size:0.85em; font-weight:700; margin-left:8px;">'
            "RECOMMENDED</span>"
        )
        if analysis.recommendation
        else ""
    )

    score_color = "#7ED321" if analysis.recommendation else "#F5A623"

    return f"""
    <div style="margin-bottom:20px; padding:18px; border-left:4px solid {src_color};
                background:#f8f9fa; border-radius:6px; box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <h3 style="margin:0 0 6px; color:#212529; font-size:16px;">
            {rank_str}{paper.title}
        </h3>
        <div style="margin:6px 0; display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
            {src_tag} {dir_badge}
        </div>
        <p style="margin:4px 0; color:#6C757D; font-size:13px;">
            <strong>Authors:</strong> {authors_str} &nbsp;|&nbsp;
            <strong>Published:</strong> {pub_str}
        </p>
        <p style="margin:6px 0;">
            <strong>Score:</strong>
            <span style="color:{score_color}; font-weight:700; font-size:15px;">
                {analysis.relevance_score:.1f}/10
            </span>
            {rec_badge}
        </p>
        <div style="margin:8px 0 0; font-size:13px; color:#212529;">
            <p style="margin:4px 0;"><strong>TL;DR:</strong> {analysis.tldr}</p>
            <p style="margin:4px 0;"><strong>Key Finding:</strong> {analysis.result}</p>
        </div>
        <a href="{paper.link}" target="_blank"
           style="display:inline-block; background:#4A90E2; color:#fff;
                  padding:8px 16px; text-decoration:none; border-radius:4px;
                  margin-top:8px; font-size:13px; font-weight:600;">
            Read Paper &rarr;
        </a>
    </div>
    """


# ── Sending ─────────────────────────────────────────────────


def _send_smtp(subject: str, html: str, text: str, config: Config) -> bool:
    """Send an HTML + plain-text email via SMTP using the given config.

    Shared by the feed-digest engine.
    Port 465 → SMTP_SSL (immediate TLS); other ports → SMTP + STARTTLS.
    """
    required = [
        config.email_sender,
        config.email_recipient,
        config.email_smtp_server,
        config.email_smtp_port,
        config.email_smtp_username,
        config.email_smtp_password,
    ]
    if not all(required):
        logger.error("Email configuration incomplete — check .env or GitHub Secrets")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.email_sender
        msg["To"] = config.email_recipient
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        port = config.email_smtp_port
        logger.info(
            f"Sending email via {config.email_smtp_server}:{port} -> {config.email_recipient}"
        )

        if port == 465:
            import ssl as _ssl

            ctx = _ssl.create_default_context()
            with smtplib.SMTP_SSL(
                config.email_smtp_server, port, context=ctx
            ) as server:
                server.login(config.email_smtp_username, config.email_smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(config.email_smtp_server, port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config.email_smtp_username, config.email_smtp_password)
                server.send_message(msg)

        logger.info(f"Email sent successfully to {config.email_recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
