"""
Archive loader & aggregation for digests and the quarterly web view.

Reads the JSONL archive (data/all/data_*.jsonl) — the only history that
persists across CI runs (it is pushed to the `data` branch) — merges records
by id (and by DOI), applies window filtering, and provides preprint/publication
classification plus record → Paper/PaperAnalysis conversion for email rendering.

Copyright (c) 2026 Yizheng Zhen
Licensed under the MIT License
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from .models import (
    DeepReadResult,
    Paper,
    PaperAnalysis,
    PaperSource,
)

logger = logging.getLogger(__name__)


# ── Date helpers ─────────────────────────────────────────────


def _parse_datetime(value) -> datetime | None:
    """Parse an ISO-ish datetime string; return datetime or None."""
    if not value:
        return None
    v = str(value).strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        pass
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _parse_date(value) -> Any | None:
    dt = _parse_datetime(value)
    return dt.date() if dt else None


def paper_window_date(record: dict[str, Any]) -> str:
    """决策5：arXiv → rss_fetch_date（每日更新时间）；非 arXiv → published_date。"""
    src = (record.get("source") or "").lower()
    if src == "arxiv":
        return record.get("rss_fetch_date") or record.get("published_date") or ""
    return record.get("published_date") or ""


def classify_preprint_publication(record: dict[str, Any]) -> str:
    """决策4：仅 source==arxiv → 'preprint'，其余 → 'publication'。"""
    src = (record.get("source") or "").lower()
    return "preprint" if src == "arxiv" else "publication"


# ── Archive loading ──────────────────────────────────────────


def _normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    return (
        str(doi)
        .strip()
        .lower()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .replace("doi:", "")
        .strip()
    )


def load_jsonl_archive(archive_dir: str = "data/all") -> list[dict[str, Any]]:
    """Load all data_*.jsonl, merge by id (latest wins), then merge by DOI."""
    archive_path = Path(archive_dir)
    if not archive_path.exists():
        logger.warning(f"Archive directory not found: {archive_path}")
        return []

    files = sorted(archive_path.glob("data_*.jsonl"))
    if not files:
        logger.warning(f"No data_*.jsonl found in archive: {archive_path}")
        return []

    by_id: dict[str, dict[str, Any]] = {}
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rid = rec.get("id")
                    if rid:
                        by_id[rid] = rec  # newer files overwrite older records
        except OSError as e:
            logger.warning(f"Failed to read archive file {f}: {e}")

    records = list(by_id.values())
    merged = _merge_by_doi(records)
    logger.info(
        f"Archive loaded: {len(records)} records from {len(files)} file(s) "
        f"→ {len(merged)} after DOI merge"
    )
    return merged


def _pick_best(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the best record from a DOI group: journal preferred, then highest score."""

    def is_journal(r):
        return (r.get("source") or "").lower() != "arxiv"

    journals = [r for r in group if is_journal(r)]
    pool = journals if journals else group
    return max(pool, key=lambda r: (r.get("score", 0), len(str(r.get("abstract", "")))))


def _merge_by_doi(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge PUBLISHED records that share a DOI (same paper across runs).

    Per product decision, arXiv records are never DOI-merged: an arXiv preprint
    and its journal version are different papers (no cross-source dedup).
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    no_doi: list[dict[str, Any]] = []
    for rec in records:
        if (rec.get("source") or "").lower() == "arxiv":
            no_doi.append(rec)
            continue
        doi = _normalize_doi(rec.get("doi"))
        if doi:
            groups.setdefault(doi, []).append(rec)
        else:
            no_doi.append(rec)

    merged = list(no_doi)
    for group in groups.values():
        merged.append(_pick_best(group))
    return merged

# ── Re-keying & canonical merge (used by historical archive cleanup) ──

def _doi_from_link(link: str) -> str:
    """Extract a raw DOI from a link, if present."""
    if not link:
        return ""
    import re
    m = re.search(r"(10\.\d{4,9}/[^\s&?#]+)", link, re.IGNORECASE)
    return m.group(1) if m else ""


def compute_record_key(record: Dict[str, Any]) -> str:
    """Deterministic identity key for a flat record.

    Product decision: NO cross-source dedup and arXiv versions are distinct.
      - arXiv     → arx:<id-with-version>  (or pre_title:<title hash>)
      - Published → doi:<doi>              (or pub_title:<title hash>)
    """
    import hashlib

    from .rss_fetcher import (
        extract_arxiv_id_keep_version as _exv,
        normalize_doi as _norm,
    )

    if (record.get("source") or "").lower() == "arxiv":
        # Prefer an existing arx: id — historical links carry no version, so a
        # stored versioned id (e.g. after arXiv-API backfill) must be kept.
        rid = record.get("id", "")
        if rid.startswith("arx:"):
            return rid
        arx = _exv(record.get("link", ""))
        if arx:
            return f"arx:{arx}"
        norm_title = " ".join((record.get("title") or "").lower().split())
        return f"pre_title:{hashlib.sha256(norm_title.encode()).hexdigest()[:16]}"

    doi = _norm(record.get("doi") or _doi_from_link(record.get("link", "")))
    if doi:
        return f"doi:{doi}"

    norm_title = " ".join((record.get("title") or "").lower().split())
    return f"pub_title:{hashlib.sha256(norm_title.encode()).hexdigest()[:16]}"


_ANALYSIS_FIELDS = [
    "score", "recommended", "direction", "tldr", "motivation", "method",
    "result", "conclusion", "keywords", "analysis_timestamp", "deep_read",
    "abstract", "authors",
]


def canonical_record(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge a group of records sharing one key into a canonical record.

    Identity (source / link / doi) prefers the journal version; the analysis
    content (score, summary, …) comes from the newest analysis in the group.
    """
    def is_journal(r):
        return (r.get("source") or "").lower() != "arxiv"

    def ts(r):
        d = _parse_datetime(r.get("analysis_timestamp"))
        return d.timestamp() if d else 0.0

    best_id = max(group, key=lambda r: (is_journal(r), r.get("score", 0), ts(r)))
    newest = max(group, key=lambda r: ts(r))

    out = dict(best_id)
    for field in _ANALYSIS_FIELDS:
        if newest.get(field) is not None:
            out[field] = newest[field]

    for member in group:
        if member is best_id:
            continue
        if is_journal(best_id) and not is_journal(member) and not out.get("alternate_link"):
            if "arxiv.org" in (member.get("link") or ""):
                out["alternate_link"] = member.get("link")
        if not out.get("doi") and member.get("doi"):
            out["doi"] = member["doi"]
        if len(str(member.get("abstract", ""))) > len(str(out.get("abstract", ""))):
            out["abstract"] = member["abstract"]
        if len(member.get("authors", [])) > len(out.get("authors", [])):
            out["authors"] = member["authors"]

    # Populate the doi field from the link-derived DOI (normalized) so the
    # archive loader's DOI merge works on re-keyed historical records.
    if not out.get("doi"):
        from .rss_fetcher import normalize_doi as _norm

        link_doi = _norm(_doi_from_link(out.get("link", "")))
        if link_doi:
            out["doi"] = link_doi

    out["id"] = compute_record_key(out)
    return out

# ── Filtering ────────────────────────────────────────────────


def filter_by_window(
    records: list[dict[str, Any]], window_days: int | None, today=None
) -> list[dict[str, Any]]:
    """Keep records whose window date (arXiv: rss_fetch_date, else published_date)
    falls within the last `window_days` days. window_days<=0 → no filtering."""
    if not window_days or window_days <= 0:
        return records
    today = today or datetime.now().date()
    if isinstance(today, datetime):
        today = today.date()
    cutoff = today - timedelta(days=window_days)
    result = []
    for rec in records:
        d = _parse_date(paper_window_date(rec))
        if d is not None and d >= cutoff:
            result.append(rec)
    return result


# ── Record → Paper / PaperAnalysis (reuse email card renderers) ──


def record_to_paper(record: dict[str, Any]) -> Paper:
    """Convert a flat archive record back into a Paper object."""
    try:
        source = PaperSource(record.get("source", "other"))
    except ValueError:
        source = PaperSource.OTHER

    published = _parse_datetime(record.get("published_date")) or datetime.now()

    return Paper(
        id=record.get("id", ""),
        title=record.get("title", ""),
        authors=record.get("authors", []),
        abstract=record.get("abstract", ""),
        link=record.get("link", ""),
        published=published,
        source=source,
        feed_name=record.get("feed_name", ""),
        rss_fetch_date=_parse_datetime(record.get("rss_fetch_date")) or datetime.now(),
        tags=record.get("tags", []),
        doi=record.get("doi") or None,
        alternate_link=record.get("alternate_link") or None,
        raw_data={"arxiv_id": record.get("id", "")},
    )


def record_to_analysis(record: dict[str, Any]) -> PaperAnalysis:
    """Convert a flat archive record back into a PaperAnalysis object."""
    summary = {
        "tldr": record.get("tldr", ""),
        "motivation": record.get("motivation", ""),
        "method": record.get("method", ""),
        "result": record.get("result", ""),
        "conclusion": record.get("conclusion", ""),
    }

    deep_read = None
    dr = record.get("deep_read")
    if isinstance(dr, dict) and dr:
        try:
            deep_read = DeepReadResult(**dr)
        except Exception:
            deep_read = None

    return PaperAnalysis(
        paper_id=record.get("id", ""),
        relevance_score=float(record.get("score", 0) or 0),
        recommendation=bool(record.get("recommended", False)),
        summary=summary,
        keywords=record.get("keywords", []),
        direction=record.get("direction", ""),
        processing_time=_parse_datetime(record.get("analysis_timestamp"))
        or datetime.now(),
        deep_read=deep_read,
    )


def records_to_pairs(
    records: list[dict[str, Any]],
) -> list[tuple[Paper, PaperAnalysis]]:
    """Convert archive records to (Paper, PaperAnalysis) pairs for email rendering."""
    pairs: list[tuple[Paper, PaperAnalysis]] = []
    for rec in records:
        try:
            pairs.append((record_to_paper(rec), record_to_analysis(rec)))
        except Exception as e:
            logger.warning(f"Skipping record in digest: {e}")
    return pairs
