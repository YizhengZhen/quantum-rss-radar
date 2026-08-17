"""
Paper deduplication for the Quantum RSS Radar system.

Deterministic, key-based deduplication (O(n)):
  1. doi (normalized)        — most stable, cross-source unique
  2. arxiv id               — when no DOI
  3. normalized title hash  — exact-match fallback (no fuzzy matching)

Within a duplicate group the canonical paper is chosen: a published (journal)
version is preferred over the arXiv preprint, and the arXiv link is kept as
alternate_link.
"""

import hashlib
import logging
from collections import defaultdict

from .models import Paper, PaperSource
from .rss_fetcher import extract_arxiv_id, normalize_doi

logger = logging.getLogger(__name__)


def compute_paper_key(paper: Paper) -> str:
    """Return the deterministic dedup key for a paper (doi → arxiv id → title hash)."""
    doi = normalize_doi(getattr(paper, "doi", None))
    if doi:
        return f"doi:{doi}"

    arx = (paper.raw_data or {}).get("arxiv_id", "") or extract_arxiv_id(paper.link)
    if arx:
        return f"arx:{arx}"

    norm_title = " ".join(paper.title.lower().split())
    return f"title:{hashlib.sha256(norm_title.encode()).hexdigest()[:16]}"


def _info_score(paper: Paper) -> float:
    """Completeness score used to pick the canonical paper within a tier."""
    return len(paper.abstract) + len(paper.authors) * 20 + (2 if paper.doi else 0)


def select_canonical(group: list[Paper]) -> Paper:
    """Pick the canonical paper: published (journal) version preferred, else most complete."""
    journals = [p for p in group if p.source != PaperSource.ARXIV]
    pool = journals if journals else group
    return max(pool, key=_info_score)


def merge_into_canonical(canonical: Paper, group: list[Paper]) -> Paper:
    """Merge other members' metadata into the canonical paper (in place)."""
    for member in group:
        if member is canonical:
            continue

        # Keep arXiv id for cross-linking
        m_arx = (member.raw_data or {}).get("arxiv_id", "") or extract_arxiv_id(
            member.link
        )
        if m_arx and not (canonical.raw_data or {}).get("arxiv_id"):
            canonical.raw_data["arxiv_id"] = m_arx

        # If canonical is the journal version, keep the arXiv link as alternate
        if canonical.source != PaperSource.ARXIV and member.source == PaperSource.ARXIV:
            if not canonical.alternate_link:
                canonical.alternate_link = member.link

        # DOI
        if getattr(member, "doi", None) and not getattr(canonical, "doi", None):
            canonical.doi = member.doi

        # Fuller abstract / authors
        if len(member.abstract) > len(canonical.abstract):
            canonical.abstract = member.abstract
        if len(member.authors) > len(canonical.authors):
            canonical.authors = member.authors

        # Both preprints → keep the earliest publication date; merge tags
        if canonical.source == PaperSource.ARXIV and member.source == PaperSource.ARXIV:
            canonical.published = min(canonical.published, member.published)
        for tag in member.tags:
            if tag not in canonical.tags:
                canonical.tags.append(tag)

    return canonical


def deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    """Remove duplicates using deterministic keys (doi → arxiv id → title hash)."""
    if len(papers) <= 1:
        return papers

    logger.info(f"Deduplicating {len(papers)} papers (key-based)")

    groups: dict[str, list[Paper]] = defaultdict(list)
    for paper in papers:
        groups[compute_paper_key(paper)].append(paper)

    deduplicated: list[Paper] = []
    removed = 0
    for key, group in groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
        else:
            canonical = select_canonical(group)
            merge_into_canonical(canonical, group)
            deduplicated.append(canonical)
            removed += len(group) - 1
            logger.info(
                f"Merged {len(group)} duplicates under key '{key}' → "
                f"kept {canonical.source.value}:{canonical.id}"
            )

    logger.info(
        f"Removed {removed} duplicate papers, kept {len(deduplicated)} unique papers"
    )
    return deduplicated
