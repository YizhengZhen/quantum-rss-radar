"""
Email sender for the Quantum RSS Radar system.

Generates rich HTML email with source colours, direction labels,
and structured paper summaries.  Integrated directly into the
pipeline — called by orchestrator_jekyll.py after data export.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict
import logging

from .models import Paper, PaperAnalysis, PaperSource, Config, SourceConfig

logger = logging.getLogger(__name__)


# ── Source priority for email sorting ───────────────────────
# Primary sort: source priority (ascending = most important first)
# Secondary sort: relevance score (descending = highest first)
# See docs/email_sorting.md for full rationale.
_SOURCE_PRIORITY: Dict[str, int] = {
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
        f'{source_display}</span>'
    )


def _direction_badge_html(direction: str) -> str:
    return (
        f'<span style="display:inline-block; padding:2px 10px; border-radius:12px;'
        f' font-size:0.85em; font-weight:500; color:#495057; background:#e9ecef;">'
        f'{direction}</span>'
    )


# ── Single paper card ───────────────────────────────────────

def format_single_paper_html(
    paper: Paper,
    analysis: PaperAnalysis,
    sources: Optional[Dict[str, SourceConfig]] = None,
    rank: Optional[int] = None,
) -> str:
    src_cfg = sources.get(paper.source.value) if sources else None
    src_display = src_cfg.display_name if src_cfg else paper.source.value.upper()
    src_color = src_cfg.color if src_cfg else ("#7ED321" if analysis.recommendation else "#F5A623")

    src_tag = _source_tag_html(paper.source.value, src_display, src_color)
    dir_badge = _direction_badge_html(analysis.direction or "General / Other")
    rank_str = f"<strong>{rank}.</strong> " if rank else ""

    authors_str = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors_str += " et al."
    pub_str = paper.published.strftime("%b %d, %Y") if paper.published else "Unknown"

    rec_badge = (
        '<span style="background:#7ED321; color:#fff; padding:2px 10px;'
        ' border-radius:12px; font-size:0.85em; font-weight:700; margin-left:8px;">'
        "RECOMMENDED</span>"
    ) if analysis.recommendation else ""

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


# ── Full HTML email ────────────────────────────────────────

def build_email_html(
    papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
    sources: Dict[str, SourceConfig],
    config: Config,
) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    total = len(papers_with_analyses)
    recommended = sum(1 for _, a in papers_with_analyses if a.recommendation)

    # Filter by minimum score for email — send ALL papers scoring >= email_min_score
    email_min = config.email_min_score
    scored_pairs = sorted(papers_with_analyses, key=lambda x: x[1].relevance_score, reverse=True)
    top_papers = [(p, a) for p, a in scored_pairs if a.relevance_score >= email_min]
    if not top_papers:
        logger.info(f"No papers score >= {email_min} for email — falling back to top {config.top_n_recommendations}")
        top_papers = scored_pairs[:min(config.top_n_recommendations, total)]
    # Two-level sort: source priority first, then score descending
    top_papers = sorted(top_papers, key=_email_sort_key)

    # Direction stats
    direction_counts: Dict[str, int] = {}
    for _, a in papers_with_analyses:
        d = a.direction or "General / Other"
        direction_counts[d] = direction_counts.get(d, 0) + 1
    dir_stats_html = "".join(
        f"<div style='text-align:center; min-width:80px;'>"
        f"<span style='font-size:1.1em; font-weight:700; color:#4A90E2;'>{cnt}</span><br>"
        f"<span style='font-size:0.75em; color:#6C757D;'>{d}</span></div>"
        for d, cnt in sorted(direction_counts.items(), key=lambda x: -x[1])
    )

    papers_html = "".join(
        format_single_paper_html(p, a, sources, rank=i + 1)
        for i, (p, a) in enumerate(top_papers)
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Research Digest — {date_str}</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
         line-height:1.6; color:#212529; margin:0; padding:0; background:#f5f7fa; }}
  .container {{ max-width:620px; margin:0 auto; padding:20px; }}
  .header {{ background:linear-gradient(135deg,#4A90E2,#2C6FB7); color:#fff;
             padding:28px 30px; text-align:center; border-radius:8px 8px 0 0; }}
  .content {{ background:#fff; padding:28px 30px; border-radius:0 0 8px 8px;
              box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .stats {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:28px; }}
  .stat-card {{ flex:1; min-width:100px; background:#f8f9fa; padding:14px;
               border-radius:8px; text-align:center; }}
  .stat-number {{ font-size:1.8em; font-weight:700; color:#4A90E2; }}
  .stat-label {{ font-size:0.8em; color:#6C757D; text-transform:uppercase;
                letter-spacing:1px; margin-top:2px; }}
  .footer {{ text-align:center; margin-top:28px; padding-top:18px;
             border-top:1px solid #E9ECEF; color:#6C757D; font-size:0.85em; }}
  @media (max-width:620px) {{ .stats {{ flex-direction:column; }} }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1 style="margin:0; font-size:26px;">🔬 Quantum RSS Radar</h1>
    <p style="margin:8px 0 0; opacity:0.9; font-size:15px;">
      Daily Research Digest — {date_str}
    </p>
  </div>

  <div class="content">

    <h2 style="margin:0 0 4px; font-size:20px;">Today's Top Research Papers</h2>
    <p style="color:#6C757D; margin:0 0 20px; font-size:14px;">
      AI-ranked by relevance to your research interests.
    </p>

    <div class="stats">
      <div class="stat-card">
        <div class="stat-number">{total}</div>
        <div class="stat-label">Total Papers</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{recommended}</div>
        <div class="stat-label">Recommended</div>
      </div>
      <div class="stat-card" style="flex-basis:100%;">
        <div style="display:flex; flex-wrap:wrap; gap:8px; justify-content:center;">
          {dir_stats_html}
        </div>
        <div class="stat-label" style="margin-top:6px;">Research Directions</div>
      </div>
    </div>

    <h3 style="color:#4A90E2; border-bottom:2px solid #E9ECEF; padding-bottom:10px;
               font-size:17px; margin-top:0;">
      Top {len(top_papers)} Papers by Score
    </h3>

    {papers_html}

    <div style="margin-top:28px; padding:16px; background:#f0f7ff; border-radius:8px; font-size:13px;">
      <h4 style="color:#4A90E2; margin:0 0 6px;">💡 How to use this digest</h4>
      <ul style="color:#6C757D; margin:0; padding-left:18px;">
        <li>Papers scored 0–10 by AI relevance to your research directions.</li>
        <li>Papers scoring ≥ {config.min_relevance_score}/10 are <strong>recommended</strong>.</li>
        <li>Click <strong>"Read Paper"</strong> to open the full abstract online.</li>
        <li>Visit the full website for filters, search, and history.</li>
      </ul>
    </div>

    <div style="text-align:center; margin-top:24px;">
      <a href="{config.public_website_url if config.public_website_url else 'https://yizhengzhen.github.io/quantum-rss-radar/'}"
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


# ── Plain-text fallback ─────────────────────────────────────

def build_email_text(
    papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
    sources: Dict[str, SourceConfig],
    config: Config,
) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    total = len(papers_with_analyses)
    recommended = sum(1 for _, a in papers_with_analyses if a.recommendation)

    # Filter by minimum score for email — send ALL papers scoring >= email_min_score
    email_min = config.email_min_score
    scored_pairs = sorted(papers_with_analyses, key=lambda x: x[1].relevance_score, reverse=True)
    top_papers = [(p, a) for p, a in scored_pairs if a.relevance_score >= email_min]
    if not top_papers:
        logger.info(f"No papers score >= {email_min} for email — falling back to top {config.top_n_recommendations}")
        top_papers = scored_pairs[:min(config.top_n_recommendations, total)]
    # Two-level sort: source priority first, then score descending
    top_papers = sorted(top_papers, key=_email_sort_key)

    lines = [
        "=" * 60,
        "QUANTUM RSS RADAR — Daily Research Digest",
        date_str,
        "=" * 60,
        "",
        f"Total papers: {total}  |  Recommended: {recommended}",
        "",
        f"TOP {len(top_papers)} PAPERS BY SCORE (min: {email_min})",
        "-" * 40,
        "",
    ]

    for i, (paper, analysis) in enumerate(top_papers, 1):
        src_cfg = sources.get(paper.source.value)
        src_display = src_cfg.display_name if src_cfg else paper.source.value.upper()
        rec = "[RECOMMENDED]" if analysis.recommendation else ""
        authors = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors += " et al."
        lines += [
            f"{i}. {paper.title}",
            f"   Score: {analysis.relevance_score:.1f}/10 {rec}",
            f"   Source: {src_display}  |  Direction: {analysis.direction or 'General / Other'}",
            f"   Authors: {authors}",
            f"   Published: {paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown'}",
            f"   TL;DR: {analysis.tldr}",
            f"   Link: {paper.link}",
            "",
        ]

    lines += [
        "-" * 40,
        "Full website: " + (config.public_website_url if config.public_website_url else "https://github.com/YizhengZhen/quantum-rss-radar") + "",
        "-" * 40,
        "",
        "Auto-generated by Quantum RSS Radar.",
        f"(c) {datetime.now().year}",
    ]

    return "\n".join(lines)


# ── Sending ─────────────────────────────────────────────────

def send_daily_email(
    papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
    sources: Dict[str, SourceConfig],
    config: Config,
) -> bool:
    if not config.email_enabled:
        logger.info("Email sending is disabled in configuration")
        return False
    if not papers_with_analyses:
        logger.warning("No papers to send in email")
        return False

    required = [
        config.email_sender, config.email_recipient,
        config.email_smtp_server, config.email_smtp_port,
        config.email_smtp_username, config.email_smtp_password,
    ]
    if not all(required):
        logger.error("Email configuration incomplete — check .env or GitHub Secrets")
        return False

    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"Quantum RSS Radar — Daily Research Digest ({date_str})"

        html = build_email_html(papers_with_analyses, sources, config)
        text = build_email_text(papers_with_analyses, sources, config)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.email_sender
        msg["To"] = config.email_recipient
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        port = config.email_smtp_port
        logger.info(f"Sending email via {config.email_smtp_server}:{port} -> {config.email_recipient}")

        # Port 465 → SMTP_SSL (immediate TLS)
        # Port 587 / others → SMTP + STARTTLS
        if port == 465:
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            with smtplib.SMTP_SSL(config.email_smtp_server, port, context=ctx) as server:
                server.login(config.email_smtp_username, config.email_smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(config.email_smtp_server, port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config.email_smtp_username, config.email_smtp_password)
                server.send_message(msg)

        logger.info(f"Daily email sent successfully to {config.email_recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


# ── Test helper ─────────────────────────────────────────────

def test_email_config(
    sources: Dict[str, SourceConfig],
    config: Config,
) -> bool:
    if not config.email_enabled:
        logger.info("Email sending is disabled in configuration")
        return False

    test_paper = Paper(
        id="test_001",
        title="Test Paper: Quantum Network Bell Nonlocality",
        authors=["Alice Researcher", "Bob Scientist", "Carol Chen"],
        abstract="Test abstract for email functionality.",
        link="https://arxiv.org/abs/1234.56789",
        published=datetime.now(),
        source=PaperSource.ARXIV,
        feed_name="Test Feed",
        raw_data={},
    )
    test_analysis = PaperAnalysis(
        paper_id="test_001",
        relevance_score=8.5,
        recommendation=True,
        summary={
            "tldr": "Demonstrates email delivery for Quantum RSS Radar.",
            "motivation": "Verify SMTP configuration.",
            "method": "Constructs test Paper + PaperAnalysis and calls send_daily_email.",
            "result": "Email sent successfully.",
            "conclusion": "Email module is operational.",
        },
        keywords=["test", "email", "quantum"],
        direction="Quantum Communication",
    )

    logger.info("Sending test email...")
    success = send_daily_email([(test_paper, test_analysis)], sources, config)
    if success:
        logger.info("Test email sent successfully!")
    else:
        logger.error("Failed to send test email")
    return success
