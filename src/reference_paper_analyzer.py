"""
Reference Paper Analyzer — automatically converts user-supplied PDF files in
config/papers/{tier}/ into few-shot calibration YAML files in config/.

Flow (called once per pipeline run, before the main RSS analysis):
  1. Scan config/papers/{core,relevant,not_priority,unrelated}/ for PDF files
  2. For each PDF that has no corresponding YAML in config/, extract text
  3. Call LLM to identify title, direction, reason, abstract_snippet
  4. Write config/ref_{tier}_{stem}.yaml

The tier is determined solely by the subfolder name; the LLM determines
direction and fills in the reason.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import yaml

from .models import Config

logger = logging.getLogger(__name__)

# ── Tier configuration ────────────────────────────────────────────────────────

TIER_CONFIGS = {
    "core": {
        "score_range": "8.5–9.5",
        "description": (
            "Papers you would read in full and consider highly relevant to your "
            "research directions. These are the gold standard for high scores."
        ),
    },
    "relevant": {
        "score_range": "5.0–6.5",
        "description": (
            "Papers that are related to your research but not central. "
            "Worth reading the abstract and skimming. Middle-tier calibration."
        ),
    },
    "not_priority": {
        "score_range": "1.5–3.0",
        "description": (
            "Papers that belong to your research field but address sub-topics "
            "you do not actively follow. Low score even if technically solid."
        ),
    },
    "unrelated": {
        "score_range": "0.0–1.0",
        "description": (
            "Papers completely unrelated to your research. "
            "Used to anchor the bottom of the scoring scale and prevent the "
            "LLM from over-scoring irrelevant work."
        ),
    },
}

# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a research analyst helping to calibrate an automated paper-scoring system. "
    "You will receive the text of a research paper and must produce structured JSON output. "
    "Be precise and concise. Output ONLY valid JSON — no markdown fences, no extra text."
)

USER_PROMPT_TEMPLATE = """\
A user has placed this PDF in the "{tier}" reference folder.

TIER DEFINITION for "{tier}":
{tier_description}
Expected score range: {score_range}

RESEARCHER'S INTERESTS (use exact direction names for the "direction" field):
{research_directions}

PAPER TEXT (first 6000 characters):
{text_excerpt}

TASK:
Analyze this paper and return a JSON object with exactly these fields:

{{
  "title": "<exact title from the paper, as written in the document>",
  "direction": "<one of the 4 exact direction names from RESEARCHER'S INTERESTS, or 'General / Other'>",
  "expected_score": <a float in range {score_range_numeric}, reflecting how representative this paper is of the tier>,
  "reason": "<2-3 sentences: why this paper belongs to tier '{tier}' given the researcher's directions>",
  "abstract_snippet": "<100-150 word excerpt from the abstract or introduction capturing the paper's core contribution>"
}}

Rules:
- "direction" must be copied verbatim from one of the H2 headings in RESEARCHER'S INTERESTS (strip "## N. " prefix), or "General / Other"
- "expected_score" must be a float (e.g. 8.7, not 9 or 9.0 only if truly round)
- "reason" must reference specific content from the paper
- "abstract_snippet" must be a direct quote from the paper text above
"""

# ── PDF text extraction ───────────────────────────────────────────────────────


def _extract_pdf_text(pdf_path: Path, max_chars: int = 8000) -> Optional[str]:
    """
    Extract plain text from a local PDF file.

    Tries PyMuPDF (fitz) first, falls back to pdfminer.six.
    Returns None if extraction fails.
    """
    pdf_bytes = pdf_path.read_bytes()

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        parts = []
        total = 0
        for page in doc:
            page_text = page.get_text()
            if total + len(page_text) >= max_chars:
                parts.append(page_text[: max_chars - total])
                break
            parts.append(page_text)
            total += len(page_text)
        doc.close()
        text = "\n".join(parts).strip()
        if text:
            logger.debug(f"PyMuPDF extracted {len(text)} chars from {pdf_path.name}")
            return text
    except ImportError:
        logger.debug("PyMuPDF not available, trying pdfminer")
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {pdf_path.name}: {e}")

    # Fallback: pdfminer.six
    try:
        from io import BytesIO
        from pdfminer.high_level import extract_text as pm_extract
        text = pm_extract(BytesIO(pdf_bytes))
        if text:
            return text[:max_chars].strip()
    except ImportError:
        logger.warning("Neither PyMuPDF nor pdfminer.six is installed")
    except Exception as e:
        logger.warning(f"pdfminer fallback failed for {pdf_path.name}: {e}")

    return None


# ── LLM call + JSON parsing ───────────────────────────────────────────────────


def _call_llm(config: Config, system: str, user: str) -> Optional[str]:
    """Minimal LLM call — reuses the same provider config as SemanticAnalyzer."""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url or None,
        )
        resp = client.chat.completions.create(
            model=config.llm_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


def _parse_json_response(text: str) -> Optional[dict]:
    """Three-layer JSON parsing with fallback."""
    # Layer 1: direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Layer 2: extract first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse LLM response as JSON")
    return None


# ── YAML writer ───────────────────────────────────────────────────────────────


def _write_yaml(out_path: Path, pdf_path: Path, tier: str, data: dict) -> None:
    """Write the calibration YAML file."""
    stem = re.sub(r"[^a-zA-Z0-9_-]", "_", pdf_path.stem)
    content = {
        "id": f"local_{stem}",
        "title": data.get("title", pdf_path.stem),
        "direction": data.get("direction", "General / Other"),
        "expected_score": float(data.get("expected_score", 0.0)),
        "tier": tier,
        "reason": data.get("reason", "").strip(),
        "abstract_snippet": data.get("abstract_snippet", "").strip(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"# Auto-generated from config/papers/{tier}/{pdf_path.name}\n")
        f.write(f"# Re-generate: delete this file and re-run the pipeline\n\n")
        yaml.dump(
            content,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    logger.info(f"  ✓ Generated {out_path.name}")


# ── Main entry point ──────────────────────────────────────────────────────────


def _tier_score_numeric(tier: str) -> str:
    """Return a numeric range string suitable for the LLM prompt."""
    return {
        "core": "8.5 and 9.5",
        "relevant": "5.0 and 6.5",
        "not_priority": "1.5 and 3.0",
        "unrelated": "0.0 and 1.0",
    }.get(tier, "0.0 and 10.0")


def run_reference_paper_analysis(
    config_dir: str,
    config: Config,
    research_directions: str,
) -> int:
    """
    Scan config/papers/{tier}/ for new PDFs and generate calibration YAMLs.

    Args:
        config_dir:            Path to the config directory (e.g. "config")
        config:                Loaded Config object (for LLM credentials)
        research_directions:   Full text of research_directions.md

    Returns:
        Number of new YAMLs generated.
    """
    papers_dir = Path(config_dir) / "papers"
    config_path = Path(config_dir)

    if not papers_dir.exists():
        logger.debug("config/papers/ not found — skipping reference paper analysis")
        return 0

    generated = 0

    for tier in ("core", "relevant", "not_priority", "unrelated"):
        tier_dir = papers_dir / tier
        if not tier_dir.exists():
            continue

        pdfs = sorted(tier_dir.glob("*.pdf"))
        if not pdfs:
            continue

        logger.info(f"Reference papers [{tier}]: found {len(pdfs)} PDF(s)")

        for pdf_path in pdfs:
            # Derive expected YAML name
            safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", pdf_path.stem)
            yaml_path = config_path / f"ref_{tier}_{safe_stem}.yaml"

            if yaml_path.exists():
                logger.debug(f"  ↷ {yaml_path.name} already exists, skipping")
                continue

            logger.info(f"  Analyzing {pdf_path.name} ...")

            # 1. Extract text
            text = _extract_pdf_text(pdf_path)
            if not text:
                logger.warning(f"  ✗ Could not extract text from {pdf_path.name}, skipping")
                continue

            # 2. Build prompt
            tier_cfg = TIER_CONFIGS[tier]
            user_prompt = USER_PROMPT_TEMPLATE.format(
                tier=tier,
                tier_description=tier_cfg["description"],
                score_range=tier_cfg["score_range"],
                score_range_numeric=_tier_score_numeric(tier),
                research_directions=research_directions,
                text_excerpt=text[:6000],
            )

            # 3. Call LLM
            raw = _call_llm(config, SYSTEM_PROMPT, user_prompt)
            if not raw:
                logger.warning(f"  ✗ LLM returned nothing for {pdf_path.name}, skipping")
                continue

            # 4. Parse JSON
            data = _parse_json_response(raw)
            if not data:
                logger.warning(f"  ✗ Could not parse LLM response for {pdf_path.name}, skipping")
                continue

            # 5. Write YAML
            _write_yaml(yaml_path, pdf_path, tier, data)
            generated += 1

            # Be polite to the LLM API
            time.sleep(1.0)

    if generated:
        logger.info(f"Reference paper analysis complete: {generated} new YAML(s) generated")
    else:
        logger.debug("Reference paper analysis: no new PDFs found")

    return generated
