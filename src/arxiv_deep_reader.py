"""
arXiv Deep Reader — downloads PDFs of high-score papers and performs
LLM-powered deep reading analysis.

Flow:
  1. Extract arXiv ID from paper link
  2. Fetch full metadata via arXiv API (http://export.arxiv.org/api/query)
  3. Download PDF and extract plain text
  4. Send extracted text to LLM for structured deep analysis
  5. Return DeepReadResult attached to the PaperAnalysis

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import logging
import re
import time
import json
import hashlib
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

import requests

from .models import Paper, PaperAnalysis, DeepReadResult, Config

logger = logging.getLogger(__name__)

# ── arXiv API / PDF URLs ──────────────────────────────────────
ARXIV_API_URL = "http://export.arxiv.org/api/query?id_list={}"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{}.pdf"

# arXiv imposes a rate limit of ~1 request per 3 seconds
ARXIV_API_DELAY = 3.0


# ── Helpers ───────────────────────────────────────────────────

def extract_arxiv_id(link: str) -> Optional[str]:
    """
    Extract arXiv ID from a paper link.

    Supports:
      - https://arxiv.org/abs/2301.12345
      - https://arxiv.org/pdf/2301.12345.pdf
      - http://arxiv.org/abs/2301.12345v1
      - arxiv:2301.12345
    """
    if not link:
        return None

    # Try direct arXiv ID pattern first (e.g. "2301.12345" or "2301.12345v1")
    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+)(?:v\d+)?', link)
    if match:
        return match.group(1)

    # Try arxiv: prefix
    match = re.search(r'arxiv:(\d+\.\d+)', link)
    if match:
        return match.group(1)

    return None


def fetch_arxiv_metadata(arxiv_id: str) -> Optional[dict]:
    """
    Fetch full metadata from arXiv API for a given paper ID.

    Returns a dict with keys:
      - title, authors, abstract, comments, journal_ref, doi, msc_class, acm_class
      - pdf_url, published, updated
    """
    url = ARXIV_API_URL.format(arxiv_id)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"arXiv API request failed for {arxiv_id}: {e}")
        return None

    # Parse the Atom XML response (simple extraction)
    text = resp.text
    meta = {}

    def extract_tag(tag: str) -> str:
        m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', text, re.DOTALL)
        return m.group(1).strip() if m else ""

    meta["title"] = extract_tag("title")
    meta["abstract"] = extract_tag("summary")
    meta["comments"] = extract_tag("arxiv:comment") or extract_tag("comment")
    meta["journal_ref"] = extract_tag("arxiv:journal_ref") or extract_tag("journal_ref")
    meta["doi"] = extract_tag("arxiv:doi") or extract_tag("doi")
    meta["msc_class"] = extract_tag("arxiv:msc_class") or extract_tag("msc_class")
    meta["acm_class"] = extract_tag("arxiv:acm_class") or extract_tag("acm_class")
    meta["published"] = extract_tag("published")
    meta["updated"] = extract_tag("updated")

    # Extract authors
    authors = re.findall(r'<author><name>(.*?)</name></author>', text, re.DOTALL)
    meta["authors"] = [a.strip() for a in authors]

    # PDF URL
    meta["pdf_url"] = ARXIV_PDF_URL.format(arxiv_id)

    logger.info(f"Fetched arXiv metadata for {arxiv_id}: comments={meta['comments'][:50] if meta['comments'] else 'N/A'}")
    return meta


def download_and_extract_text(pdf_url: str, max_chars: int = 30000) -> Optional[str]:
    """
    Download a PDF and extract its text content.

    Args:
        pdf_url: URL to the PDF file
        max_chars: Maximum characters to extract (to limit LLM token usage)

    Returns:
        Extracted plain text, or None on failure
    """
    try:
        # Download PDF
        logger.info(f"Downloading PDF: {pdf_url}")
        resp = requests.get(pdf_url, timeout=60)
        resp.raise_for_status()
        pdf_content = resp.content

        if len(pdf_content) > 50 * 1024 * 1024:  # 50 MB limit
            logger.warning(f"PDF too large ({len(pdf_content)} bytes), skipping")
            return None

        # Extract text using PyMuPDF (fitz)
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not installed, falling back to pdfminer")
            return _extract_text_fallback(pdf_content, max_chars)

        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_parts = []
        total_chars = 0

        for page_num in range(min(len(doc), 20)):  # Max 20 pages
            page = doc[page_num]
            page_text = page.get_text()
            if total_chars + len(page_text) > max_chars:
                remaining = max_chars - total_chars
                text_parts.append(page_text[:remaining])
                total_chars = max_chars
                break
            text_parts.append(page_text)
            total_chars += len(page_text)

        doc.close()

        if not text_parts or not any(p.strip() for p in text_parts):
            logger.warning("No text extracted from PDF (may be scanned/image-based)")
            return None

        full_text = "\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from PDF ({len(doc)} pages)")
        return full_text

    except Exception as e:
        logger.error(f"Failed to download/extract PDF {pdf_url}: {e}")
        return None


def _extract_text_fallback(pdf_content: bytes, max_chars: int = 30000) -> Optional[str]:
    """
    Fallback text extraction using pdfminer.six (lighter dependency).
    """
    try:
        from io import BytesIO
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(BytesIO(pdf_content))
        if text:
            return text[:max_chars]
        return None
    except Exception as e:
        logger.warning(f"pdfminer fallback also failed: {e}")
        return None


# ── LLM Deep Analysis Prompt ──────────────────────────────────

DEEP_READ_SYSTEM_PROMPT = """You are a senior research analyst specializing in quantum physics, information theory, and related fields. You will receive the full text of a research paper and must produce a structured deep analysis.

Focus on technical substance. Be precise, critical, and specific — avoid vague praise. Where possible, reference actual numbers, equations, or data from the paper."""

DEEP_READ_USER_PROMPT_TEMPLATE = """Please perform a deep reading analysis of the following research paper.

--- RESEARCHER'S INTERESTS ---
{research_directions}

--- PAPER METADATA ---
Title: {title}
Authors: {authors}
Published: {published}
Comments: {comments}
Journal Reference: {journal_ref}
DOI: {doi}

--- PAPER FULL TEXT (extracted from PDF) ---
{full_text}

--- ANALYSIS INSTRUCTIONS ---
Analyze the paper thoroughly and produce a structured JSON output with these fields:

1. "detailed_summary": A 2-3 paragraph comprehensive summary of the paper
2. "key_contributions": List 3-5 specific contributions of this work
3. "methodology_analysis": A detailed analysis of the methods/approach used (1-2 paragraphs)
4. "results_analysis": Analysis of the key results, including specific numbers/values if available (1-2 paragraphs)
5. "strengths": List 2-4 specific strengths of the paper
6. "limitations": List 1-3 limitations, assumptions, or areas for improvement
7. "connections_to_research": How this work connects to the researcher's stated interests (1 paragraph)
8. "overall_assessment": A final verdict on the paper's significance, novelty, and quality (1 paragraph)

OUTPUT FORMAT (JSON only, no markdown):
{{
    "detailed_summary": "...",
    "key_contributions": ["...", "..."],
    "methodology_analysis": "...",
    "results_analysis": "...",
    "strengths": ["...", "..."],
    "limitations": ["...", "..."],
    "connections_to_research": "...",
    "overall_assessment": "..."
}}"""


# ── Cache ─────────────────────────────────────────────────────

def _cache_key(arxiv_id: str) -> str:
    """Generate a cache key for a given arXiv paper."""
    return hashlib.sha256(arxiv_id.encode()).hexdigest()[:16]


def _load_cache(cache_dir: Path, arxiv_id: str) -> Optional[dict]:
    """Load a cached deep read result."""
    key = _cache_key(arxiv_id)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Deep read cache HIT for arXiv:{arxiv_id}")
            return data
        except Exception:
            pass
    return None


def _save_cache(cache_dir: Path, arxiv_id: str, data: dict):
    """Save a deep read result to cache."""
    key = _cache_key(arxiv_id)
    cache_file = cache_dir / f"{key}.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Deep read cached at {cache_file}")
    except Exception as e:
        logger.warning(f"Failed to cache deep read: {e}")


# ── Main Deep Read Function ───────────────────────────────────

def deep_read_paper(
    paper: Paper,
    analysis: PaperAnalysis,
    config: Config,
    llm_client,
    cache_dir: Optional[Path] = None,
) -> Optional[DeepReadResult]:
    """
    Perform a deep reading analysis of a high-score arXiv paper.

    Args:
        paper: The paper to analyze
        analysis: The existing PaperAnalysis (with relevance_score etc.)
        config: System config (for research directions, LLM settings)
        llm_client: OpenAI-compatible LLM client
        cache_dir: Optional directory for caching results

    Returns:
        DeepReadResult if successful, None otherwise
    """
    # Step 1: Extract arXiv ID
    arxiv_id = extract_arxiv_id(paper.link)
    if not arxiv_id:
        logger.info(f"No arXiv ID found for paper {paper.id}, skipping deep read")
        return None

    logger.info(f"Deep reading arXiv:{arxiv_id} — {paper.title[:60]}...")

    # Step 2: Check cache
    if cache_dir:
        cached = _load_cache(cache_dir, arxiv_id)
        if cached:
            return DeepReadResult(paper_id=paper.id, **cached)

    # Step 3: Fetch arXiv metadata
    meta = fetch_arxiv_metadata(arxiv_id)
    if not meta:
        logger.warning(f"Failed to fetch arXiv metadata for {arxiv_id}, skipping deep read")
        return None

    # Throttle: respect arXiv API rate limits
    time.sleep(ARXIV_API_DELAY)

    # Step 4: Download PDF and extract text
    pdf_url = meta.get("pdf_url", ARXIV_PDF_URL.format(arxiv_id))
    full_text = download_and_extract_text(pdf_url)

    if not full_text:
        logger.warning(f"No text extracted for {arxiv_id}, trying abstract-only analysis")
        # Fallback: use arXiv abstract + metadata instead of full PDF
        full_text = meta.get("abstract", paper.abstract)

    # Step 5: Prepare LLM prompt
    research_directions = getattr(config, "_research_directions", "")
    if not research_directions:
        research_directions = "Quantum physics and related fields"

    prompt = DEEP_READ_USER_PROMPT_TEMPLATE.format(
        research_directions=research_directions,
        title=meta.get("title", paper.title),
        authors=", ".join(meta.get("authors", paper.authors)),
        published=meta.get("published", paper.published.isoformat()),
        comments=meta.get("comments", ""),
        journal_ref=meta.get("journal_ref", ""),
        doi=meta.get("doi", ""),
        full_text=full_text,
    )

    # Step 6: Call LLM with retry
    for attempt in range(3):
        try:
            response = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": DEEP_READ_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)

            # Validate required fields
            required = ["detailed_summary", "key_contributions", "methodology_analysis",
                        "results_analysis", "strengths", "limitations",
                        "connections_to_research", "overall_assessment"]
            for field in required:
                if field not in result_data:
                    raise ValueError(f"Missing field: {field}")

            # Ensure lists
            if not isinstance(result_data.get("key_contributions"), list):
                result_data["key_contributions"] = [result_data.get("key_contributions", "")]
            if not isinstance(result_data.get("strengths"), list):
                result_data["strengths"] = [result_data.get("strengths", "")]
            if not isinstance(result_data.get("limitations"), list):
                result_data["limitations"] = [result_data.get("limitations", "")]

            # Save to cache
            if cache_dir:
                _save_cache(cache_dir, arxiv_id, result_data)

            result = DeepReadResult(paper_id=paper.id, **result_data)
            logger.info(f"Deep read complete for arXiv:{arxiv_id} (score={analysis.relevance_score})")
            return result

        except Exception as e:
            logger.warning(f"Deep read LLM call failed (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    logger.error(f"Deep read failed after 3 attempts for arXiv:{arxiv_id}")
    return None


def deep_read_high_score_papers(
    papers_with_analyses: list,
    config: Config,
    llm_client,
) -> list:
    """
    Run deep reading on all high-score papers with arXiv IDs.

    Modifies PaperAnalysis objects in-place by attaching DeepReadResult.

    Args:
        papers_with_analyses: List of (paper, analysis) tuples
        config: System config
        llm_client: OpenAI-compatible LLM client

    Returns:
        The same list with analyses potentially updated with deep_read
    """
    deep_read_enabled = getattr(config, "_deep_read_enabled", True)
    if not deep_read_enabled:
        logger.info("Deep reading is disabled (DEEP_READ_ENABLED=false)")
        return papers_with_analyses

    min_score = config.min_relevance_score
    cache_dir = Path(config.output_dir) / "cache" / "deep_read" if config.output_dir else Path("data/cache/deep_read")

    updated_pairs = []
    deep_read_count = 0

    for paper, analysis in papers_with_analyses:
        if analysis.relevance_score >= min_score:
            result = deep_read_paper(paper, analysis, config, llm_client, cache_dir)
            if result:
                analysis.deep_read = result
                deep_read_count += 1
        updated_pairs.append((paper, analysis))

    logger.info(f"Deep reading complete: {deep_read_count} papers analyzed")
    return updated_pairs
