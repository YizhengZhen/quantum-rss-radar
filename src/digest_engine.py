"""
Feed-digest email engine.

The project runs solely off config/rss_sources.yaml.  Each feed declares an
`update_frequency`; feeds sharing the same frequency are merged into ONE email
(e.g. all `weekday` feeds → one Mon–Fri email, all `weekly` feeds → one weekend
email).  On a given day:

  * feed_is_due(feed, today)  — does this feed fire today?
  * select_feed_records(...)  — which papers to recommend:
        per-feed window (derived from its frequency)
        + score >= feed.min_score
        + capped at feed.max_items (top by score)

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import logging
from datetime import datetime
from typing import Any

from . import history
from .email_sender import _resolve_feed_config, _send_smtp, format_single_paper_html
from .models import Config, FeedConfig, SourceConfig, UpdateFrequency

logger = logging.getLogger(__name__)


# ── Calendar ─────────────────────────────────────────────────

_FREQUENCY_LABEL = {
    UpdateFrequency.DAILY: "Daily",
    UpdateFrequency.WEEKDAY: "Weekday",
    UpdateFrequency.WEEKLY: "Weekly",
    UpdateFrequency.MONTHLY: "Monthly",
    UpdateFrequency.SEASON: "Seasonal",
}


def feed_is_due(feed: FeedConfig, today=None) -> bool:
    """Whether a feed's update_frequency fires on `today`."""
    today = today or datetime.now().date()
    freq = feed.update_frequency
    if freq == UpdateFrequency.DAILY:
        return True
    if freq == UpdateFrequency.WEEKDAY:
        return today.weekday() < 5  # Mon–Fri
    if freq == UpdateFrequency.WEEKLY:
        return today.weekday() == 6  # Sunday (weekend roundup)
    if freq == UpdateFrequency.MONTHLY:
        return today.day == 1
    if freq == UpdateFrequency.SEASON:
        return today.month % 3 == 1 and today.day == 1  # quarter start
    return False


def resolve_feed_window_days(feed: FeedConfig, today=None) -> int:
    """Window (days) from which to collect a feed's papers.

    * weekday: Monday covers Fri–Sun (3d), other weekdays 1d
    * weekly → 7d, monthly → 30d, season → 90d, daily → 1d
    """
    today = today or datetime.now().date()
    freq = feed.update_frequency
    if freq == UpdateFrequency.WEEKDAY:
        return 3 if today.weekday() == 0 else 1
    if freq == UpdateFrequency.WEEKLY:
        return 7
    if freq == UpdateFrequency.MONTHLY:
        return 30
    if freq == UpdateFrequency.SEASON:
        return 90
    return 1


def select_feed_records(
    records: list[dict[str, Any]], feed: FeedConfig, today=None
) -> list[dict[str, Any]]:
    """Papers from this feed's window, score >= feed.min_score, top feed.max_items."""
    today = today or datetime.now().date()
    window = resolve_feed_window_days(feed, today)

    feed_recs = [r for r in records if (r.get("feed_name") or "") == feed.name]
    in_window = history.filter_by_window(feed_recs, window, today)
    scored = [r for r in in_window if r.get("score", 0) >= feed.min_score]
    scored.sort(key=lambda r: r.get("score", 0), reverse=True)
    return scored[: feed.max_items] if feed.max_items > 0 else scored


# ── Email building ───────────────────────────────────────────


def _feed_header_html(feed: FeedConfig, count: int) -> str:
    color = feed.color or "#757575"
    # Section title uses the unique feed name (arXiv Physics / Math / CS share
    # display_name "arXiv" but must be distinguishable).  The per-card tag
    # still shows display_name via _resolve_feed_config.
    label = feed.name
    return (
        f'<div style="margin:24px 0 12px; padding:10px 16px; border-left:4px solid {color};'
        f' background:#f8f9fa; border-radius:4px;">'
        f'<h3 style="margin:0; font-size:16px; color:{color};">{label}</h3>'
        f'<span style="color:#6C757D; font-size:12px;">{count} papers · '
        f'min score {feed.min_score:g} · top {feed.max_items}</span>'
        f"</div>"
    )


def build_feed_email_html(
    group_label: str,
    sections: list[tuple[FeedConfig, list[tuple]]],
    sources: dict[str, SourceConfig],
    feed_configs: dict[str, FeedConfig],
    config: Config,
    today=None,
) -> str:
    today = today or datetime.now().date()
    date_str = today.strftime("%B %d, %Y")
    total = sum(len(pairs) for _, pairs in sections)

    body = ""
    for feed, pairs in sections:
        body += _feed_header_html(feed, len(pairs))
        body += "".join(
            format_single_paper_html(p, a, sources or {}, feed_configs, rank=i + 1)
            for i, (p, a) in enumerate(pairs)
        )

    website = (
        config.public_website_url or "https://yizhengzhen.github.io/quantum-rss-radar/"
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{group_label} Digest — {date_str}</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
         line-height:1.6; color:#212529; margin:0; padding:0; background:#f5f7fa; }}
  .container {{ max-width:620px; margin:0 auto; padding:20px; }}
  .header {{ background:linear-gradient(135deg,#4A90E2,#2C6FB7); color:#fff;
             padding:26px 30px; text-align:center; border-radius:8px 8px 0 0; }}
  .content {{ background:#fff; padding:28px 30px; border-radius:0 0 8px 8px;
              box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .footer {{ text-align:center; margin-top:28px; padding-top:18px;
             border-top:1px solid #E9ECEF; color:#6C757D; font-size:0.85em; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1 style="margin:0; font-size:24px;">🔬 Quantum RSS Radar</h1>
    <p style="margin:8px 0 0; opacity:0.9; font-size:15px;">{group_label} Digest — {date_str}</p>
  </div>

  <div class="content">

    <h2 style="margin:0 0 4px; font-size:20px;">{group_label} Digest</h2>
    <p style="color:#6C757D; margin:0 0 20px; font-size:14px;">
      AI-ranked by relevance to your research interests ({total} papers).
    </p>

    {body}

    <div style="text-align:center; margin-top:24px;">
      <a href="{website}"
         style="display:inline-block; background:#4A90E2; color:#fff; padding:12px 28px;
                text-decoration:none; border-radius:4px; font-weight:700; font-size:14px;">
        View Full Website &rarr;
      </a>
    </div>

  </div>

  <div class="footer">
    <p>Auto-generated by Quantum RSS Radar.</p>
    <p style="font-size:0.8em;">&copy; {datetime.now().year} — AI-powered research tracking</p>
  </div>

</div>
</body>
</html>"""


def build_feed_email_text(
    group_label: str,
    sections: list[tuple[FeedConfig, list[tuple]]],
    sources: dict[str, SourceConfig],
    feed_configs: dict[str, FeedConfig],
    today=None,
) -> str:
    today = today or datetime.now().date()
    date_str = today.strftime("%Y-%m-%d")
    total = sum(len(pairs) for _, pairs in sections)
    lines = [
        "=" * 60,
        f"QUANTUM RSS RADAR — {group_label.upper()} DIGEST",
        date_str,
        "=" * 60,
        "",
        f"Total papers: {total}",
        "",
    ]

    for feed, pairs in sections:
        lines += [f"── {feed.name} ({len(pairs)} papers) ──", ""]
        for i, (paper, analysis) in enumerate(pairs, 1):
            src_display, _ = _resolve_feed_config(paper, sources or {}, feed_configs)
            authors = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " et al."
            lines += [
                f"{i}. {paper.title}",
                f"   Score: {analysis.relevance_score:.1f}/10",
                f"   Source: {src_display}  |  Direction: {analysis.direction or 'General / Other'}",
                f"   Authors: {authors}",
                f"   TL;DR: {analysis.tldr}",
                f"   Link: {paper.link}",
                "",
            ]
        lines.append("")

    lines += [
        "-" * 40,
        "Auto-generated by Quantum RSS Radar.",
        f"(c) {datetime.now().year}",
        "",
    ]
    return "\n".join(lines)


# ── Orchestrated sending ─────────────────────────────────────


def send_feed_digests(
    config_dir: str = "config",
    config: Config | None = None,
    sources: dict[str, SourceConfig] | None = None,
    feed_configs: dict[str, FeedConfig] | None = None,
    archive_dir: str | None = None,
    today=None,
) -> dict[str, bool]:
    """Send one merged email per frequency group due today.

    Feeds sharing an `update_frequency` are merged into one email; feeds that
    are due but have no qualifying papers are omitted from the email.

    Returns:
        {update_frequency_value: sent_ok}
    """
    if config is None:
        from .config_loader import load_config

        config = load_config()

    if not config.email_enabled:
        logger.info("Email sending disabled — skipping feed digests")
        return {}

    feeds = list((feed_configs or {}).values())
    if not feeds:
        from .config_loader import load_feeds

        feeds = load_feeds(config_dir)

    groups: dict[UpdateFrequency, list[FeedConfig]] = {}
    for f in feeds:
        groups.setdefault(f.update_frequency, []).append(f)

    archive_dir = archive_dir or config.archive_dir
    records = history.load_jsonl_archive(archive_dir)
    today = today or datetime.now().date()

    results: dict[str, bool] = {}
    for freq, group_feeds in groups.items():
        if not feed_is_due(group_feeds[0], today):
            logger.info(f"[{freq.value}] not scheduled for {today} — skipping")
            continue

        sections: list[tuple[FeedConfig, list[tuple]]] = []
        for feed in group_feeds:
            selected = select_feed_records(records, feed, today)
            pairs = history.records_to_pairs(selected)
            if pairs:
                sections.append((feed, pairs))

        if not sections:
            logger.warning(f"[{freq.value}] due but no papers matched — skipping")
            results[freq.value] = False
            continue

        label = _FREQUENCY_LABEL[freq]
        subject = f"Quantum RSS Radar — {label} Digest ({today:%Y-%m-%d})"
        html = build_feed_email_html(
            label, sections, sources or {}, feed_configs or {}, config, today
        )
        text = build_feed_email_text(
            label, sections, sources or {}, feed_configs or {}, today
        )

        ok = _send_smtp(subject, html, text, config)
        n = sum(len(pairs) for _, pairs in sections)
        logger.info(f"[{freq.value}] '{label} Digest' sent: {ok} ({n} papers)")
        results[freq.value] = ok

    return results
