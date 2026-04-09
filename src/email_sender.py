"""
Email sender for the Quantum RSS Radar system.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
import logging

from .models import Paper, PaperAnalysis, Config

logger = logging.getLogger(__name__)


def format_paper_for_email(paper: Paper, analysis: PaperAnalysis) -> str:
    """
    Format a paper for email display.
    
    Args:
        paper: Paper object
        analysis: PaperAnalysis object
        
    Returns:
        Formatted HTML string
    """
    return f"""
    <div style="margin-bottom: 20px; padding: 15px; border-left: 4px solid {'#7ED321' if analysis.recommendation else '#F5A623'}; background-color: #f8f9fa;">
        <h3 style="margin-top: 0; color: #212529;">
            {paper.title}
        </h3>
        
        <p style="margin: 5px 0; color: #6C757D;">
            <strong>Authors:</strong> {', '.join(paper.authors[:3])}{' et al.' if len(paper.authors) > 3 else ''}
        </p>
        
        <p style="margin: 5px 0;">
            <strong>Score:</strong> <span style="color: {'#7ED321' if analysis.recommendation else '#F5A623'}; font-weight: bold;">{analysis.relevance_score:.1f}/10</span>
            {'<span style="background-color: #7ED321; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.9em; margin-left: 10px;">RECOMMENDED</span>' if analysis.recommendation else ''}
        </p>
        
        <p style="margin: 5px 0; color: #6C757D;">
            <strong>Source:</strong> {paper.source.value.upper()} | 
            <strong>Published:</strong> {paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown'}
        </p>
        
        <div style="margin: 10px 0;">
            <p style="margin: 5px 0;"><strong>TL;DR:</strong> {analysis.tldr}</p>
            <p style="margin: 5px 0;"><strong>Key Finding:</strong> {analysis.result}</p>
        </div>
        
        <a href="{paper.link}" style="display: inline-block; background-color: #4A90E2; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; margin-top: 5px;">
            Read Paper →
        </a>
    </div>
    """


def generate_email_html(papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                       config: Config) -> str:
    """
    Generate HTML email content.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        config: System configuration
        
    Returns:
        HTML email content
    """
    date_str = datetime.now().strftime("%B %d, %Y")
    total_papers = len(papers_with_analyses)
    recommended_papers = sum(1 for _, analysis in papers_with_analyses if analysis.recommendation)
    
    # Sort by score (descending)
    sorted_papers = sorted(papers_with_analyses, key=lambda x: x[1].relevance_score, reverse=True)
    
    # Take top N recommendations
    top_n = min(config.top_n_recommendations, len(sorted_papers))
    top_papers = sorted_papers[:top_n]
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Research Digest - {date_str}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #212529; margin: 0; padding: 0; background-color: #f5f7fa; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #4A90E2, #2C6FB7); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: white; padding: 30px; border-radius: 0 0 8px 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
            .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 30px; }}
            .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
            .stat-number {{ font-size: 2em; font-weight: bold; color: #4A90E2; }}
            .stat-label {{ color: #6C757D; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #E9ECEF; color: #6C757D; font-size: 0.9em; }}
            @media (max-width: 600px) {{ .stats {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">🔬 Quantum RSS Radar</h1>
                <p style="margin: 10px 0 0; opacity: 0.9; font-size: 16px;">Daily Research Digest - {date_str}</p>
            </div>
            
            <div class="content">
                <h2 style="color: #212529; margin-top: 0;">Today's Top Research Papers</h2>
                <p style="color: #6C757D;">
                    Your personalized research recommendations based on your research interests.
                </p>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_papers}</div>
                        <div class="stat-label">Total Papers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{recommended_papers}</div>
                        <div class="stat-label">Recommended</div>
                    </div>
                </div>
                
                <h3 style="color: #4A90E2; border-bottom: 2px solid #E9ECEF; padding-bottom: 10px;">
                    Top {top_n} Recommended Papers
                </h3>
    """
    
    for i, (paper, analysis) in enumerate(top_papers, 1):
        html_content += format_paper_for_email(paper, analysis)
    
    html_content += f"""
                <div style="margin-top: 30px; padding: 15px; background-color: #f0f7ff; border-radius: 8px;">
                    <h4 style="color: #4A90E2; margin-top: 0;">💡 How to use this digest:</h4>
                    <ul style="color: #6C757D;">
                        <li>Papers are scored 0-10 based on relevance to your research interests</li>
                        <li>✅ RECOMMENDED papers scored {config.min_relevance_score}+/10</li>
                        <li>Review abstracts to identify papers worth reading in detail</li>
                        <li>Bookmark interesting papers using the website</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://your-website-url.com" style="display: inline-block; background-color: #4A90E2; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold; margin: 0 10px;">
                        View Full Website
                    </a>
                    <a href="https://your-website-url.com/recommended" style="display: inline-block; background-color: #7ED321; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold; margin: 0 10px;">
                        All Recommended Papers
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>
                    This email was automatically generated by Quantum RSS Radar.<br>
                    To update your research interests or unsubscribe, visit your account settings.
                </p>
                <p style="font-size: 0.8em;">
                    &copy; {datetime.now().year} Quantum RSS Radar | AI-powered research tracking
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def generate_email_text(papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                       config: Config) -> str:
    """
    Generate plain text email content.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        config: System configuration
        
    Returns:
        Plain text email content
    """
    date_str = datetime.now().strftime("%B %d, %Y")
    total_papers = len(papers_with_analyses)
    recommended_papers = sum(1 for _, analysis in papers_with_analyses if analysis.recommendation)
    
    # Sort by score (descending)
    sorted_papers = sorted(papers_with_analyses, key=lambda x: x[1].relevance_score, reverse=True)
    
    # Take top N recommendations
    top_n = min(config.top_n_recommendations, len(sorted_papers))
    top_papers = sorted_papers[:top_n]
    
    text_content = f"""
QUANTUM RSS RADAR - DAILY RESEARCH DIGEST
{date_str}
{'=' * 50}

Today's Analysis:
- Total papers analyzed: {total_papers}
- Recommended papers: {recommended_papers}

TOP {top_n} RECOMMENDED PAPERS:
{'=' * 50}

"""
    
    for i, (paper, analysis) in enumerate(top_papers, 1):
        text_content += f"""
{i}. {paper.title}
   Score: {analysis.relevance_score:.1f}/10 {'[RECOMMENDED]' if analysis.recommendation else ''}
   Authors: {', '.join(paper.authors[:3])}{' et al.' if len(paper.authors) > 3 else ''}
   Source: {paper.source.value.upper()} | Published: {paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown'}
   TL;DR: {analysis.tldr}
   Key Finding: {analysis.result}
   Link: {paper.link}
   
"""
    
    text_content += f"""
HOW TO USE THIS DIGEST:
- Papers are scored 0-10 based on relevance to your research interests
- RECOMMENDED papers scored {config.min_relevance_score}+/10
- Review abstracts to identify papers worth reading in detail

VIEW ONLINE:
- Full website: https://your-website-url.com
- All recommended papers: https://your-website-url.com/recommended

This email was automatically generated by Quantum RSS Radar.
To update your research interests or unsubscribe, visit your account settings.

© {datetime.now().year} Quantum RSS Radar | AI-powered research tracking
"""
    
    return text_content


def send_daily_email(papers_with_analyses: List[tuple[Paper, PaperAnalysis]], 
                    config: Config) -> bool:
    """
    Send daily email with top paper recommendations.
    
    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        config: System configuration
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not config.email_enabled:
        logger.info("Email sending is disabled in configuration")
        return False
    
    if not papers_with_analyses:
        logger.warning("No papers to send in email")
        return False
    
    # Check required email configuration
    required_fields = [
        config.email_sender,
        config.email_recipient,
        config.email_smtp_server,
        config.email_smtp_port,
        config.email_smtp_username,
        config.email_smtp_password
    ]
    
    if not all(required_fields):
        logger.error("Email configuration incomplete")
        return False
    
    try:
        logger.info(f"Preparing daily email for {len(papers_with_analyses)} papers")
        
        # Generate email content
        date_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"Quantum RSS Radar - Daily Research Digest ({date_str})"
        
        html_content = generate_email_html(papers_with_analyses, config)
        text_content = generate_email_text(papers_with_analyses, config)
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config.email_sender
        msg['To'] = config.email_recipient
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Attach text and HTML versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        logger.info(f"Connecting to SMTP server: {config.email_smtp_server}:{config.email_smtp_port}")
        
        with smtplib.SMTP(config.email_smtp_server, config.email_smtp_port) as server:
            server.starttls()  # Use TLS
            server.login(config.email_smtp_username, config.email_smtp_password)
            server.send_message(msg)
        
        logger.info(f"Daily email sent successfully to {config.email_recipient}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def test_email_config(config: Config) -> bool:
    """
    Test email configuration by sending a test email.
    
    Args:
        config: System configuration
        
    Returns:
        True if test email sent successfully, False otherwise
    """
    if not config.email_enabled:
        logger.info("Email sending is disabled in configuration")
        return False
    
    # Create test paper data
    test_paper = Paper(
        id="test_123",
        title="Test Paper: Quantum Algorithm Demonstration",
        authors=["Alice Researcher", "Bob Scientist"],
        abstract="This is a test abstract for email functionality testing.",
        link="https://arxiv.org/abs/1234.56789",
        published=datetime.now(),
        source="arxiv",
        category="quantum",
        feed_name="Test Feed",
        raw_data={}
    )
    
    test_analysis = PaperAnalysis(
        paper_id="test_123",
        relevance_score=8.5,
        recommendation=True,
        summary={
            "tldr": "This is a test paper demonstrating email functionality.",
            "motivation": "To test the email sending capabilities of Quantum RSS Radar.",
            "method": "Used test data generation and email template rendering.",
            "result": "Email system is functional and ready for production use.",
            "conclusion": "The email module works correctly and can be deployed."
        },
        keywords=["test", "email", "quantum"]
    )
    
    test_papers = [(test_paper, test_analysis)]
    
    logger.info("Sending test email...")
    success = send_daily_email(test_papers, config)
    
    if success:
        logger.info("Test email sent successfully!")
    else:
        logger.error("Failed to send test email")
    
    return success