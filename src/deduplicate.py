"""
Paper deduplication for the Quantum RSS Radar system.

Deterministic, key-based deduplication (O(n)).

Product decisions:
  * NO cross-source dedup — an arXiv preprint and its journal version are two
    different papers (they never merge, even if the same work).
  * arXiv versions (v1, v2, …) are different papers, so the version is kept in
    the arXiv identity.

Identity keys:
  - arXiv (preprint)    → arx:<id-with-version>  (or pre_title:<title hash>)
  - Published (journal) → doi:<doi>              (or pub_title:<title hash>)
"""

import hashlib
import logging
from collections import defaultdict

from .models import Paper, PaperSource
from .rss_fetcher import (
    extract_arxiv_id,
    extract_arxiv_id_keep_version,
    normalize_doi,
)

logger = logging.getLogger(__name__)


def compute_paper_key(paper: Paper) -> str:
    """Return the deterministic dedup key for a paper.

    arXiv papers use their versioned arXiv id and never use the DOI (no
    cross-source merge).  Journal papers use DOI, falling back to a
    published-namespaced title hash.
    """
    if paper.source == PaperSource.ARXIV:
        arx = (paper.raw_data or {}).get("arxiv_id", "") or extract_arxiv_id_keep_version(
            paper.link
        )
        if arx:
            return f"arx:{arx}"
        norm_title = " ".join(paper.title.lower().split())
        return f"pre_title:{hashlib.sha256(norm_title.encode()).hexdigest()[:16]}"

    doi = normalize_doi(getattr(paper, "doi", None))
    if doi:
        return f"doi:{doi}"

    norm_title = " ".join(paper.title.lower().split())
    return f"pub_title:{hashlib.sha256(norm_title.encode()).hexdigest()[:16]}"


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
