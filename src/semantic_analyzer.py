"""
Semantic analyzer using LLM for paper classification and summarization.
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time
from openai import OpenAI
import os

from .models import Paper, PaperAnalysis, Config
from .tag_manager import get_tag_manager

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """LLM-based analyzer for research papers."""
    
    def __init__(self, config: Config):
        """
        Initialize the semantic analyzer.
        
        Args:
            config: System configuration
        """
        self.config = config
        self.llm_client = None
        self._initialize_llm_client()
        
        # Cache for research directions (to avoid reloading)
        self._research_directions = None
    
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
        """Create LLM prompt for paper analysis."""
        return f"""You are an expert research assistant specializing in quantum computing, condensed matter physics, and machine learning. Your task is to evaluate a research paper based on the user's research interests and provide a structured analysis.

RESEARCH INTERESTS:
{research_directions}

PAPER TO ANALYZE:
Title: {paper.title}
Authors: {', '.join(paper.authors) if paper.authors else 'Unknown'}
Abstract: {paper.abstract}
Published: {paper.published.strftime('%Y-%m-%d') if paper.published else 'Unknown'}
Source: {paper.source.value}
Link: {paper.link}

INSTRUCTIONS:
1. Relevance Score (0-10): Score how relevant this paper is to the research interests above. Consider both direct and indirect relevance.
2. Recommendation (yes/no): Should the researcher read this paper? Consider novelty, importance, and alignment with research interests.
3. Structured Summary: Provide a concise summary in the following format:
   - TLDR: One-sentence summary
   - Motivation: Why was this research conducted?
   - Method: What approach/methodology was used?
   - Result: What were the key findings?
   - Conclusion: What are the implications and future directions?
4. Keywords: Extract 3-5 key technical keywords from the paper.

OUTPUT FORMAT (JSON only):
{{
  "relevance_score": <float 0-10>,
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

IMPORTANT:
- Be objective and critical.
- Focus on technical content, not just buzzwords.
- If the abstract lacks details, make reasonable inferences but note limitations.
- Score 0-2: Completely irrelevant, 3-5: Somewhat relevant, 6-8: Highly relevant, 9-10: Essential reading.

Your analysis:"""
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM API with retry logic."""
        for attempt in range(max_retries):
            try:
                if self.config.llm_provider in ["openai", "deepseek"]:
                    response = self.llm_client.chat.completions.create(
                        model=self.config.llm_model,
                        messages=[
                            {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,  # Low temperature for consistent analysis
                        max_tokens=1000,
                        response_format={"type": "json_object"}
                    )
                    return response.choices[0].message.content
                else:
                    raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")
                    
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def _parse_llm_response(self, response_text: str, paper_id: str) -> PaperAnalysis:
        """Parse LLM response into PaperAnalysis object."""
        try:
            data = json.loads(response_text)
            
            # Validate required fields
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
            
            return PaperAnalysis(
                paper_id=paper_id,
                relevance_score=float(data["relevance_score"]),
                recommendation=recommendation,
                summary=summary,
                keywords=keywords
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response_text}")
            
            # Return a default analysis on error
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
    
    def analyze_papers_batch(self, papers: List[Paper], research_directions: str) -> List[PaperAnalysis]:
        """
        Analyze multiple papers with rate limiting.
        
        Args:
            papers: List of papers to analyze
            research_directions: Research interests as string
            
        Returns:
            List of PaperAnalysis objects
        """
        if not papers:
            return []
        
        logger.info(f"Analyzing {len(papers)} papers with LLM")
        
        analyses = []
        for i, paper in enumerate(papers):
            try:
                # Rate limiting: 1 request per second
                if i > 0:
                    time.sleep(1)
                
                analysis = self.analyze_paper(paper, research_directions)
                analyses.append(analysis)
                
                # Log progress
                if (i + 1) % 5 == 0 or i == len(papers) - 1:
                    logger.info(f"Progress: {i + 1}/{len(papers)} papers analyzed")
                    
            except Exception as e:
                logger.error(f"Failed to analyze paper {paper.id}: {e}")
                # Add a failed analysis marker
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
        
        logger.info(f"Completed analysis of {len(analyses)} papers")
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