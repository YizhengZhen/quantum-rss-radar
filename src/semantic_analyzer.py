"""
Semantic analyzer using LLM for paper classification and summarization.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time
from openai import OpenAI
from pathlib import Path

from .models import Paper, PaperAnalysis, Config
from .tag_manager import get_tag_manager

logger = logging.getLogger(__name__)

# LLM analysis cache file path
LLM_CACHE_FILE = Path("data") / "llm_cache.json"


class LLMAnalysisCache:
    """Persistent cache for LLM analysis results to avoid redundant API calls.

    Uses paper.id (already deduplicated) as the cache key.
    This handles the case where the same paper appears in multiple feeds
    (e.g. arXiv + journal) because deduplicate.py merges them into one ID.
    """

    def __init__(self, cache_file: Path = LLM_CACHE_FILE, enabled: bool = True):
        self.cache_file = cache_file
        self.enabled = enabled
        self._cache: Dict[str, dict] = {}
        self._load()

    def _load(self):
        """Load cache from disk."""
        if not self.enabled:
            return
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded LLM cache with {len(self._cache)} entries from {self.cache_file}")
        except Exception as e:
            logger.warning(f"Failed to load LLM cache: {e}")
            self._cache = {}

    def _save(self):
        """Save cache to disk."""
        if not self.enabled:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved LLM cache ({len(self._cache)} entries)")
        except Exception as e:
            logger.warning(f"Failed to save LLM cache: {e}")

    def get(self, paper_id: str) -> Optional[dict]:
        """Get cached analysis for a paper ID. Returns None if not cached."""
        if not self.enabled:
            return None
        entry = self._cache.get(paper_id)
        if entry:
            logger.info(f"LLM cache HIT for paper {paper_id[:20]}...")
            return entry
        return None

    def put(self, paper_id: str, prompt: str, response_text: str, analysis: PaperAnalysis):
        """Store an analysis result in the cache."""
        if not self.enabled:
            return
        self._cache[paper_id] = {
            "prompt_preview": prompt[:200],
            "response": response_text,
            "analysis": {
                "paper_id": analysis.paper_id,
                "relevance_score": analysis.relevance_score,
                "recommendation": analysis.recommendation,
                "summary": analysis.summary,
                "keywords": analysis.keywords,
                "direction": analysis.direction,
            },
            "cached_at": datetime.now().isoformat(),
        }
        self._save()

    def clear(self):
        """Clear the entire cache."""
        self._cache = {}
        self._save()

    @property
    def size(self) -> int:
        return len(self._cache)


class SemanticAnalyzer:
    """LLM-based analyzer for research papers."""
    
    def __init__(self, config: Config, config_dir: str = "config"):
        """
        Initialize the semantic analyzer.
        
        Args:
            config: System configuration
            config_dir: Path to configuration directory (for loading prompt template)
        """
        self.config = config
        self.config_dir = config_dir
        self.llm_client = None
        self._initialize_llm_client()
        
        # Cache for research directions (to avoid reloading)
        self._research_directions = None

        # Few-shot calibration examples from config/curated_papers.yaml
        self._curated_papers: list = []
        
        # LLM analysis cache
        cache_enabled = getattr(config, "llm_cache_enabled", True)
        self._cache = LLMAnalysisCache(enabled=cache_enabled)
    
    def _initialize_llm_client(self):
        """Initialize the LLM client based on provider."""
        if not self.config.llm_api_key:
            raise ValueError("LLM API key not configured")
        
        client_kwargs = {
            "api_key": self.config.llm_api_key,
        }
        
        # Add base_url if provided (for custom providers)
        if self.config.llm_base_url:
            client_kwargs["base_url"] = self.config.llm_base_url
        
        if self.config.llm_provider == "openai":
            # Standard OpenAI API
            self.llm_client = OpenAI(**client_kwargs)
        elif self.config.llm_provider == "deepseek":
            # DeepSeek uses OpenAI-compatible API with custom base URL
            if not self.config.llm_base_url:
                client_kwargs["base_url"] = "https://api.deepseek.com"
            self.llm_client = OpenAI(**client_kwargs)
        elif self.config.llm_provider == "custom":
            # Custom OpenAI-compatible API
            if not self.config.llm_base_url:
                raise ValueError("Custom provider requires base_url configuration")
            self.llm_client = OpenAI(**client_kwargs)
        else:
            # Generic provider - try to initialize with whatever base_url is provided
            self.llm_client = OpenAI(**client_kwargs)
    
    def load_research_directions(self, research_directions: str):
        """Load research directions for context."""
        self._research_directions = research_directions

    def load_curated_papers(self, config_dir: str) -> int:
        """
        Load few-shot calibration examples from config/curated_papers.yaml.
        Returns the number of examples loaded.
        """
        try:
            from .reference_paper_analyzer import load_curated_papers as _load
            data = _load(config_dir)
            self._curated_papers = data.get("papers", [])
            logger.info(f"Loaded {len(self._curated_papers)} curated paper(s) for few-shot calibration")
            return len(self._curated_papers)
        except Exception as e:
            logger.warning(f"Could not load curated papers: {e}")
            self._curated_papers = []
            return 0

    def _build_few_shot_block(self) -> str:
        """
        Build a few-shot calibration block from self._curated_papers.
        Selects up to 5 examples, prioritising coverage across tiers.
        Returns an empty string if no curated papers are loaded.
        """
        if not self._curated_papers:
            return ""

        # Pick at most 2 per tier, total ≤ 5
        by_tier: dict = {"core": [], "relevant": [], "not_priority": [], "unrelated": []}
        for p in self._curated_papers:
            t = p.get("tier", "unrelated")
            if t in by_tier:
                by_tier[t].append(p)

        selected = []
        for tier in ("core", "relevant", "not_priority", "unrelated"):
            selected.extend(by_tier[tier][:2])
            if len(selected) >= 5:
                break
        selected = selected[:5]

        if not selected:
            return ""

        lines = ["\nFEW-SHOT CALIBRATION EXAMPLES (use these to anchor your scoring):"]
        for i, p in enumerate(selected, 1):
            lines.append(
                f"\n[Example {i} — tier: {p.get('tier','?')}, score: {p.get('score','?')}]"
                f"\nTitle: {p.get('title','')}"
                f"\nDirection: {p.get('direction','')}"
                f"\nAbstract: {p.get('abstract_snippet','')[:300]}"
                f"\nWhy this score: {p.get('reason','')}"
            )
        lines.append("\n--- End of examples ---")
        return "\n".join(lines)
    
    def analyze_paper(self, paper: Paper, research_directions: str) -> PaperAnalysis:
        """
        Analyze a single paper using LLM and assign tags.
        
        Args:
            paper: Paper to analyze
            research_directions: Research interests as string
            
        Returns:
            PaperAnalysis with scores and summary
        """
        logger.info(f"Analyzing paper: {paper.title[:50]}...")
        
        # Prepare prompt
        prompt = self._create_analysis_prompt(paper, research_directions)
        
        # Call LLM
        response = self._call_llm(prompt)
        
        # Parse response
        analysis = self._parse_llm_response(response, paper.id)
        
        # Assign tags to paper using tag manager
        self._assign_tags_to_paper(paper, analysis.keywords)
        
        logger.info(f"Paper analysis complete: score={analysis.relevance_score}, recommend={analysis.recommendation}, tags={paper.tags}")
        
        return analysis
    
    def _assign_tags_to_paper(self, paper: Paper, llm_keywords: List[str]) -> None:
        """
        Assign tags to paper using tag manager.
        
        Args:
            paper: Paper to assign tags to
            llm_keywords: Keywords extracted by LLM
        """
        try:
            tag_manager = get_tag_manager()
            paper.tags = tag_manager.extract_and_assign_tags(
                paper_title=paper.title,
                abstract=paper.abstract,
                llm_tags=llm_keywords
            )
            logger.debug(f"Assigned tags to paper {paper.id}: {paper.tags}")
        except Exception as e:
            logger.error(f"Failed to assign tags to paper {paper.id}: {e}")
            # Fallback: use LLM keywords directly (normalized)
            from .tag_manager import extract_keywords_from_text
            paper.tags = extract_keywords_from_text(f"{paper.title} {paper.abstract}", max_keywords=5)[:5]
    
    def _create_analysis_prompt(self, paper: Paper, research_directions: str) -> str:
        """Create LLM prompt for paper analysis.

        Priority:
          1. config/analysis_prompt.md (if exists) — user-editable template
          2. Hardcoded fallback below — built-in default
        """
        few_shot_block = self._build_few_shot_block()

        # Try loading from config/analysis_prompt.md first
        prompt_template = self._load_prompt_template()
        if prompt_template:
            return self._fill_prompt_template(
                prompt_template,
                research_directions=research_directions,
                few_shot_examples=few_shot_block,
                title=paper.title,
                authors=', '.join(paper.authors) if paper.authors else 'Unknown',
                abstract=paper.abstract,
                published=paper.published.strftime('%Y-%m-%d') if paper.published else 'Unknown',
                source=paper.source.value,
                link=paper.link,
            )

        # Fallback: hardcoded prompt
        return f"""You are an expert research assistant specializing in quantum computing, condensed matter physics, and machine learning. Your task is to evaluate a research paper based on the user's research interests and provide a structured analysis.

RESEARCH INTERESTS:
{research_directions}
{few_shot_block}

SCORING GUIDE:
  Core focus      7.5 – 10.0  (directly aligned; novel, technically deep, clearly advances the field)
  Also relevant   5.0 –  7.4  (related in topic or method, but not the primary focus or contribution is incremental)
  Not priority    2.0 –  4.9  (broadly in the field but too applied, too narrow, or not directly useful)
  General/Other   0.0 –  1.9  (does not fit any of the four directions)

Scoring precision: output a float with 1 decimal place (e.g. 7.4, 8.2, 5.6). Do NOT round to integers or 0.5 steps.

PAPER TO ANALYZE:
Title: {paper.title}
Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}
Abstract: {paper.abstract}
Published: {paper.published.strftime('%Y-%m-%d') if paper.published else 'Unknown'}
Source: {paper.source.value}
Link: {paper.link}

INSTRUCTIONS:
1. Direction: Identify which one of the user's research directions this paper belongs to.
   Use the exact H2 heading name from RESEARCH INTERESTS (strip "## N. " prefix).
   If it doesn't fit any, use "General / Other".
2. Relevance Score: Score against the SCORING GUIDE above. Output a float with 1 decimal place (e.g. 7.4, not 7 or 7.5).
3. Recommendation: "yes" if score ≥ 6.0, otherwise "no".
4. Structured Summary (5 fields: tldr / motivation / method / result / conclusion).
5. Keywords: 3-5 key technical terms.

OUTPUT FORMAT (JSON only, no markdown):
{{
  "direction": "<exact direction name or 'General / Other'>",
  "relevance_score": <float 0.0–10.0>,
  "recommendation": <"yes" or "no">,
  "summary": {{
    "tldr": "<one sentence>",
    "motivation": "<1-2 sentences>",
    "method": "<1-2 sentences>",
    "result": "<1-2 sentences>",
    "conclusion": "<1-2 sentences>"
  }},
  "keywords": ["<keyword1>", "<keyword2>", ...]
}}

Your analysis:"""

    def _load_prompt_template(self) -> Optional[str]:
        """Load prompt template from config/analysis_prompt.md.

        Returns the template string if the file exists, None otherwise.
        """
        from pathlib import Path
        template_path = Path(self.config_dir) / "analysis_prompt.md" if hasattr(self, 'config_dir') else Path("config") / "analysis_prompt.md"
        if template_path.exists():
            try:
                with template_path.open("r", encoding="utf-8") as f:
                    content = f.read()
                logger.info(f"Loaded prompt template from {template_path}")
                return content
            except Exception as e:
                logger.warning(f"Failed to load prompt template from {template_path}: {e}")
        return None

    def _fill_prompt_template(self, template: str, **kwargs) -> str:
        """Fill {{variable}} placeholders in the template with actual values.

        Uses simple string replacement. Unknown placeholders are left as-is.
        """
        result = template
        for key, value in kwargs.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM API with retry logic.

        All supported providers (openai, deepseek, azure, generic, local) use
        OpenAI-compatible API — they've all been initialised with the correct
        base_url in _initialize_llm_client, so we can call them uniformly.

        For providers that don't support response_format (e.g. some local
        models), we fall back to a plain text call and parse JSON manually.
        """
        for attempt in range(max_retries):
            try:
                # All providers use OpenAI-compatible chat completions
                try:
                    response = self.llm_client.chat.completions.create(
                        model=self.config.llm_model,
                        messages=[
                            {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=getattr(self.config, "llm_temperature", 0.1),
                        max_tokens=1000,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    # Fallback: some local/custom models don't support response_format
                    response = self.llm_client.chat.completions.create(
                        model=self.config.llm_model,
                        messages=[
                            {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=getattr(self.config, "llm_temperature", 0.1),
                        max_tokens=1000,
                    )
                return response.choices[0].message.content

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def _parse_llm_response(self, response_text: str, paper_id: str) -> PaperAnalysis:
        """Parse LLM response into PaperAnalysis object.

        Three-layer fallback:
          1. Direct json.loads
          2. Regex extraction of JSON block
          3. LLM retry with "respond with valid JSON only" prompt
        """
        data = self._try_parse_json(response_text, paper_id)
        if data is not None:
            return data

        # Layer 3: LLM retry — ask the model to reformat as valid JSON
        logger.warning(f"JSON parse failed for {paper_id[:20]}... — requesting LLM retry")
        retry_prompt = (
            "Your previous response was not valid JSON. "
            "Please respond with ONLY valid JSON, no markdown, no extra text.\n\n"
            f"Previous response:\n{response_text}"
        )
        try:
            retry_response = self._call_llm(retry_prompt, max_retries=1)
            data = self._try_parse_json(retry_response, paper_id)
            if data is not None:
                logger.info(f"LLM retry succeeded for {paper_id[:20]}...")
                return data
        except Exception as e:
            logger.warning(f"LLM retry also failed for {paper_id[:20]}...: {e}")

        # Final fallback: return default (score=0)
        logger.error(f"All JSON parse attempts failed for {paper_id[:20]}... — returning score=0")
        return PaperAnalysis(
            paper_id=paper_id,
            relevance_score=0.0,
            recommendation=False,
            summary={
                "tldr": "Analysis failed",
                "motivation": "",
                "method": "",
                "result": "",
                "conclusion": ""
            },
            keywords=[]
        )

    def _try_parse_json(self, response_text: str, paper_id: str) -> Optional[PaperAnalysis]:
        """Attempt to parse LLM response as JSON. Returns PaperAnalysis or None."""
        import re

        # Layer 1: direct json.loads
        try:
            data = json.loads(response_text)
            return self._validate_and_build(data, paper_id)
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        # Layer 2: regex extract JSON block
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return self._validate_and_build(data, paper_id)
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        return None

    def _validate_and_build(self, data: dict, paper_id: str) -> PaperAnalysis:
        """Validate parsed JSON and build PaperAnalysis. Raises on failure."""
        required_fields = ["relevance_score", "recommendation", "summary"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Convert recommendation string to boolean
        recommendation = data["recommendation"].lower() == "yes"

        # Ensure summary has all required fields
        summary = data.get("summary", {})
        required_summary_fields = ["tldr", "motivation", "method", "result", "conclusion"]
        for field in required_summary_fields:
            if field not in summary:
                summary[field] = ""

        # Get keywords
        keywords = data.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        # Get direction
        direction = data.get("direction", "")
        if not direction:
            direction = "General / Other"

        return PaperAnalysis(
            paper_id=paper_id,
            relevance_score=float(data["relevance_score"]),
            recommendation=recommendation,
            summary=summary,
            keywords=keywords,
            direction=direction
        )
    
    def analyze_papers_batch(self, papers: List[Paper], research_directions: str) -> List[PaperAnalysis]:
        """
        Analyze multiple papers with rate limiting and LLM analysis cache.

        Cache key: paper.id (already deduplicated).
        Cache lookup is performed first; only cache misses call the LLM API.

        Args:
            papers: List of papers to analyze
            research_directions: Research interests as string

        Returns:
            List of PaperAnalysis objects
        """
        if not papers:
            return []

        cache_hits = 0
        cache_misses = 0

        analyses: List[PaperAnalysis] = []
        for i, paper in enumerate(papers):
            try:
                # ── Cache lookup ──────────────────────────────────
                cached = self._cache.get(paper.id)
                if cached is not None:
                    # Restore from cache
                    cached_analysis = cached["analysis"]
                    analysis = PaperAnalysis(
                        paper_id=cached_analysis["paper_id"],
                        relevance_score=cached_analysis["relevance_score"],
                        recommendation=cached_analysis["recommendation"],
                        summary=cached_analysis["summary"],
                        keywords=cached_analysis.get("keywords", []),
                        direction=cached_analysis.get("direction", ""),
                    )
                    # Still assign tags (tag assignment doesn't call LLM)
                    self._assign_tags_to_paper(paper, analysis.keywords)
                    analyses.append(analysis)
                    cache_hits += 1
                    logger.info(f"Cache HIT [{cache_hits}]: {paper.title[:50]}... → score={analysis.relevance_score}")
                    continue

                # ── Cache miss → call LLM ─────────────────────────
                cache_misses += 1
                # Rate limiting: 1 request per second
                if i > 0 and cache_misses > 1:
                    time.sleep(1)

                # Prepare prompt
                prompt = self._create_analysis_prompt(paper, research_directions)

                # Call LLM
                response = self._call_llm(prompt)

                # Parse response
                analysis = self._parse_llm_response(response, paper.id)

                # Store in cache
                self._cache.put(paper.id, prompt, response, analysis)

                # Assign tags
                self._assign_tags_to_paper(paper, analysis.keywords)
                analyses.append(analysis)

                # Log progress
                if (i + 1) % 5 == 0 or i == len(papers) - 1:
                    logger.info(f"Progress: {i + 1}/{len(papers)} papers (cache hits: {cache_hits}, misses: {cache_misses})")

            except Exception as e:
                logger.error(f"Failed to analyze paper {paper.id}: {e}")
                # Add a failed analysis marker (don't cache failures)
                analyses.append(PaperAnalysis(
                    paper_id=paper.id,
                    relevance_score=0.0,
                    recommendation=False,
                    summary={
                        "tldr": f"Analysis failed: {str(e)[:50]}",
                        "motivation": "",
                        "method": "",
                        "result": "",
                        "conclusion": ""
                    },
                    keywords=[]
                ))

        logger.info(f"Completed analysis of {len(analyses)} papers "
                     f"(cache hits: {cache_hits}, misses: {cache_misses}, "
                     f"cache size: {self._cache.size})")
        return analyses
    
    def filter_and_rank_papers(self, papers: List[Paper], analyses: List[PaperAnalysis]) -> List[tuple[Paper, PaperAnalysis]]:
        """
        Filter and rank papers based on analysis results.
        
        Args:
            papers: List of papers
            analyses: Corresponding analyses
            
        Returns:
            List of (paper, analysis) tuples sorted by relevance score (descending)
        """
        # Create mapping from paper ID to paper
        paper_dict = {paper.id: paper for paper in papers}
        
        # Combine papers with analyses
        paper_analyses = []
        for analysis in analyses:
            paper = paper_dict.get(analysis.paper_id)
            if paper:
                paper_analyses.append((paper, analysis))
        
        # Filter by minimum relevance score
        filtered = [(p, a) for p, a in paper_analyses if a.relevance_score >= self.config.min_relevance_score]
        
        # Sort by relevance score (descending)
        filtered.sort(key=lambda x: x[1].relevance_score, reverse=True)
        
        logger.info(f"Filtered {len(paper_analyses)} papers to {len(filtered)} with score >= {self.config.min_relevance_score}")
        
        return filtered