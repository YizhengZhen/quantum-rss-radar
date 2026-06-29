"""
Reference Paper Analyzer — converts user-supplied PDFs in config/papers/{tier}/
into entries in the single calibration file config/curated_papers.yaml.

Flow (called once per pipeline run, before the main RSS analysis):
  1. Scan config/papers/{core,relevant,not_priority,unrelated}/ for PDF files
  2. For each PDF whose id is NOT already in curated_papers.yaml:
     a. Extract text from PDF
     b. Call LLM to identify title, direction, reason, abstract_snippet
     c. Append a new entry to config/curated_papers.yaml
  3. Deleted entries in curated_papers.yaml are respected (not re-added
     even if the source PDF still exists, because id is the primary key
     and manual deletes are intentional)

Score-to-tier mapping (used when adding pipeline-recommended papers):
  core          8.0 – 10.0
  relevant      6.0 –  8.0
  not_priority  4.0 –  6.0
  unrelated     0.0 –  4.0

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import logging
import re
import time
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from .models import Config

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

CURATED_FILE = "curated_papers.yaml"

# Score ranges per tier (for PDF-added papers)
# These MUST match the Tier Guide in config/research_directions.md
TIER_SCORE_DEFAULTS = {
    "core":         9.0,
    "relevant":     6.0,
    "not_priority": 3.5,
    "unrelated":    1.0,
}

TIER_SCORE_RANGES = {
    "core":         (7.5, 10.0),
    "relevant":     (5.0,  7.4),
    "not_priority": (2.0,  4.9),
    "unrelated":    (0.0,  1.9),
}

TIER_DESCRIPTIONS = {
    "core": (
        "Papers you would read in full — directly aligned, novel, technically deep, "
        "clearly advances the field. Score range: 7.5–10.0."
    ),
    "relevant": (
        "Papers related in topic or method, but not the primary focus or contribution "
        "is incremental. Score range: 5.0–7.4."
    ),
    "not_priority": (
        "Papers broadly in the field but too applied, too narrow, or not directly "
        "useful. Score range: 2.0–4.9."
    ),
    "unrelated": (
        "Papers completely unrelated to your research. "
        "Score range: 0.0–1.9."
    ),
}

# ── curated_papers.yaml helpers ───────────────────────────────────────────────


def load_curated_papers(config_dir: str) -> dict:
    """
    Load config/curated_papers.yaml.
    Returns the full dict (with 'papers' list). Creates the file if missing.
    """
    path = Path(config_dir) / CURATED_FILE
    if not path.exists():
        return {"papers": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if "papers" not in data:
            data["papers"] = []
        return data
    except Exception as e:
        logger.warning(f"Could not load {CURATED_FILE}: {e}")
        return {"papers": []}


def save_curated_papers(config_dir: str, data: dict) -> None:
    """Persist config/curated_papers.yaml while keeping the header comment."""
    path = Path(config_dir) / CURATED_FILE

    # Preserve header comment block if the file exists
    header = ""
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            lines = []
            for line in f:
                if line.startswith("#") or line.strip() == "":
                    lines.append(line)
                else:
                    break
            header = "".join(lines)

    body = yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    with path.open("w", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(body)


def existing_ids(data: dict) -> set:
    """Return the set of all 'id' values currently in the curated papers list."""
    return {entry.get("id") for entry in data.get("papers", []) if entry.get("id")}


def score_to_tier(score: float) -> str:
    """Map a relevance score to the corresponding tier name.

    Tiers and boundaries MUST match the Tier Guide in config/research_directions.md:
      core          7.5 – 10.0
      relevant      5.0 –  7.4
      not_priority  2.0 –  4.9
      unrelated     0.0 –  1.9
    """
    if score >= 7.5:
        return "core"
    elif score >= 5.0:
        return "relevant"
    elif score >= 2.0:
        return "not_priority"
    else:
        return "unrelated"


# ── PDF text extraction ───────────────────────────────────────────────────────


def _extract_pdf_text(pdf_path: Path, max_chars: int = 8000) -> Optional[str]:
    """Extract plain text from a local PDF. Tries PyMuPDF, falls back to pdfminer."""
    pdf_bytes = pdf_path.read_bytes()

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        parts, total = [], 0
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
            return text
    except ImportError:
        logger.debug("PyMuPDF not available, trying pdfminer")
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {pdf_path.name}: {e}")

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


# ── LLM call ──────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a research analyst helping calibrate an automated paper-scoring system. "
    "Output ONLY valid JSON — no markdown fences, no extra text."
)

_USER_PROMPT_TEMPLATE = """\
A user placed this PDF in the "{tier}" reference folder.

TIER "{tier}": {tier_description}
Expected score range: {score_range_str} (use a float, e.g. {score_default})

RESEARCHER'S INTERESTS (use exact H2 direction names for "direction"):
{research_directions}

PAPER TEXT (first 6000 chars):
{text_excerpt}

Return a JSON object with exactly these fields:
{{
  "title": "<exact title from the paper>",
  "direction": "<one of the 4 exact direction names, or 'General / Other'>",
  "score": <float in {score_range_str}>,
  "reason": "<2-3 sentences: why this tier/score given the researcher's directions>",
  "abstract_snippet": "<100-150 word direct quote from the abstract/introduction>"
}}
"""


def _call_llm(config: Config, user: str) -> Optional[str]:
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url or None,
        )
        resp = client.chat.completions.create(
            model=config.llm_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


def _parse_json(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ── Main entry point ──────────────────────────────────────────────────────────


def run_reference_paper_analysis(
    config_dir: str,
    config: Config,
    research_directions: str,
) -> int:
    """
    Scan config/papers/{tier}/ for new PDFs and append entries to
    config/curated_papers.yaml.

    Returns the number of new entries added.
    """
    papers_dir = Path(config_dir) / "papers"
    if not papers_dir.exists():
        logger.debug("config/papers/ not found — skipping reference paper analysis")
        return 0

    data = load_curated_papers(config_dir)
    known = existing_ids(data)
    added = 0

    for tier in ("core", "relevant", "not_priority", "unrelated"):
        tier_dir = papers_dir / tier
        if not tier_dir.exists():
            continue

        pdfs = sorted(tier_dir.glob("*.pdf"))
        if not pdfs:
            continue

        logger.info(f"Reference papers [{tier}]: found {len(pdfs)} PDF(s)")

        for pdf_path in pdfs:
            safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", pdf_path.stem)
            entry_id = f"local_{safe_stem}"

            if entry_id in known:
                logger.debug(f"  ↷ {entry_id} already in curated_papers.yaml, skipping")
                continue

            logger.info(f"  Analyzing {pdf_path.name} ...")

            text = _extract_pdf_text(pdf_path)
            if not text:
                logger.warning(f"  ✗ No text from {pdf_path.name}, skipping")
                continue

            lo, hi = TIER_SCORE_RANGES[tier]
            user_prompt = _USER_PROMPT_TEMPLATE.format(
                tier=tier,
                tier_description=TIER_DESCRIPTIONS[tier],
                score_range_str=f"{lo:.1f}–{hi:.1f}",
                score_default=TIER_SCORE_DEFAULTS[tier],
                research_directions=research_directions,
                text_excerpt=text[:6000],
            )

            raw = _call_llm(config, user_prompt)
            if not raw:
                logger.warning(f"  ✗ LLM returned nothing for {pdf_path.name}, skipping")
                continue

            llm_data = _parse_json(raw)
            if not llm_data:
                logger.warning(f"  ✗ Could not parse LLM response for {pdf_path.name}, skipping")
                continue

            score = float(llm_data.get("score", TIER_SCORE_DEFAULTS[tier]))
            entry = {
                "id": entry_id,
                "title": llm_data.get("title", pdf_path.stem),
                "direction": llm_data.get("direction", "General / Other"),
                "score": round(score, 2),
                "tier": score_to_tier(score),
                "reason": llm_data.get("reason", "").strip(),
                "abstract_snippet": llm_data.get("abstract_snippet", "").strip(),
                "source": "pdf",
                "added_at": date.today().isoformat(),
            }

            data["papers"].append(entry)
            known.add(entry_id)
            save_curated_papers(config_dir, data)

            logger.info(f"  ✓ Added {entry_id} to curated_papers.yaml (score={score:.1f}, tier={entry['tier']})")
            added += 1
            time.sleep(1.0)

    if added:
        logger.info(f"Reference paper analysis complete: {added} new entry/entries added")
    return added


def generate_research_directions_from_papers(
    config_dir: str,
    config: "Config",
) -> Optional[str]:
    """
    Auto-generate research_directions.md from PDFs in config/papers/{tier}/.

    Called when config/research_directions.md does NOT exist but config/papers/
    has PDFs. Uses LLM to infer research directions from the papers.

    Returns the generated markdown content as a string, or None on failure.
    """
    papers_dir = Path(config_dir) / "papers"
    if not papers_dir.exists():
        logger.warning("config/papers/ not found — cannot auto-generate research directions")
        return None

    # Collect all PDFs across all tiers
    all_pdfs = []
    for tier in ("core", "relevant", "not_priority", "unrelated"):
        tier_dir = papers_dir / tier
        if tier_dir.exists():
            for pdf in sorted(tier_dir.glob("*.pdf")):
                all_pdfs.append((tier, pdf))

    if not all_pdfs:
        logger.warning("No PDFs found in config/papers/ — cannot auto-generate research directions")
        return None

    logger.info(f"Auto-generating research directions from {len(all_pdfs)} PDF(s)")

    # Extract text from up to 5 PDFs (first pages only, to keep prompt small)
    excerpts = []
    for tier, pdf_path in all_pdfs[:5]:
        text = _extract_pdf_text(pdf_path, max_chars=2000)
        if text:
            excerpts.append(f"--- PDF: {pdf_path.name} (tier: {tier}) ---\n{text[:1500]}")

    if not excerpts:
        logger.warning("Could not extract text from any PDF — cannot auto-generate")
        return None

    # Build LLM prompt
    prompt = (
        "You are a research analyst. A user has placed the following PDFs into a reference paper library.\n\n"
        + "\n\n".join(excerpts)
        + "\n\n"
        + "Based on these papers, generate a research_directions.md file that defines the user's research interests.\n"
        + "Use this exact format:\n\n"
        + "# Research Interests\n\n"
        + "## 🟢 Tier Guide\n\n"
        + "| Tier | Score Range | Meaning |\n"
        + "|---|---|---|\n"
        + "| **Core focus** | **7.5 – 10.0** | Directly aligned. Novel, technically deep, clearly advances the field. |\n"
        + "| **Also relevant** | **5.0 – 7.4** | Related in topic or method, but not the primary focus or contribution is incremental. |\n"
        + "| **Not priority** | **2.0 – 4.9** | Broadly in the field but too applied, too narrow, or not directly useful. |\n"
        + "| **General / Other** | **0.0 – 1.9** | Does not fit any of the directions below. |\n\n"
        + "Then define 2-4 research directions as H2 headings (`## N. Direction Name`).\n"
        + "Each direction must have three subsections:\n"
        + "  - `**🟢 Core focus**` — topics directly aligned\n"
        + "  - `**🟡 Also relevant**` — related but not core\n"
        + "  - `**🔴 Not priority**` — in the field but not of interest\n\n"
        + "Output ONLY the markdown content, no extra text."
    )

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url or None,
        )
        resp = client.chat.completions.create(
            model=config.llm_model or "deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a research analyst. Output ONLY the requested markdown, no extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        content = resp.choices[0].message.content.strip()

        # Write to research_directions.md
        rd_path = Path(config_dir) / "research_directions.md"
        with rd_path.open("w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Auto-generated research_directions.md from {len(all_pdfs)} PDF(s)")
        return content

    except Exception as e:
        logger.error(f"Failed to auto-generate research directions: {e}")
        return None


def append_pipeline_papers(
    config_dir: str,
    papers_with_analyses: list,
    min_score: float = 5.0,
) -> int:
    """
    Append pipeline-recommended papers (score ≥ min_score) to curated_papers.yaml.
    Only adds papers whose id is not already in the file.

    Returns the number of new entries added.
    """
    from .models import Paper, PaperAnalysis

    data = load_curated_papers(config_dir)
    known = existing_ids(data)
    added = 0

    for paper, analysis in papers_with_analyses:
        if analysis.relevance_score < min_score:
            continue
        if paper.id in known:
            continue

        # Build abstract snippet from summary tldr + result, or truncated abstract
        snippet = ""
        if analysis.summary:
            tldr = analysis.summary.get("tldr", "")
            result = analysis.summary.get("result", "")
            snippet = f"{tldr} {result}".strip()
        if not snippet and paper.abstract:
            snippet = paper.abstract[:400]

        entry = {
            "id": paper.id,
            "title": paper.title,
            "direction": analysis.direction or "General / Other",
            "score": round(analysis.relevance_score, 2),
            "tier": score_to_tier(analysis.relevance_score),
            "reason": (
                f"Score {analysis.relevance_score:.1f} from pipeline analysis. "
                f"Recommendation: {'yes' if analysis.recommendation else 'no'}."
            ),
            "abstract_snippet": snippet[:600],
            "source": "pipeline",
            "added_at": date.today().isoformat(),
        }

        data["papers"].append(entry)
        known.add(paper.id)
        added += 1

    if added:
        save_curated_papers(config_dir, data)
        logger.info(f"Appended {added} pipeline paper(s) to curated_papers.yaml")

    return added
