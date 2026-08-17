# Quantum RSS Radar — Change Log

> Entries are newest-first. One entry per logical change set.

---

## 2026-08-17 — Multi-frequency digest emails + quarterly web view + DOI dedup

**Branch:** `feature/email-digests-quarterly-web`
**Changed files:** `src/models.py`, `src/rss_fetcher.py`, `src/deduplicate.py`, `src/history.py` (new), `src/digest_engine.py` (new), `src/digest_cli.py` (new), `src/email_sender.py`, `src/config_loader.py`, `src/database.py`, `src/data_exporter.py`, `src/orchestrator_jekyll.py`, `src/arxiv_deep_reader.py`, `config/digests.yaml` (new), `scripts/archive_preview.py` (new), `.env.example`, `.github/workflows/daily-pipeline.yaml`, `jekyll_site/pages/quarterly.html` (new), `jekyll_site/_includes/navigation.html`, `jekyll_site/assets/js/app.js`, `jekyll_site/assets/css/styles.css`, `.gitignore`, docs

### Feature 1: Multi-frequency emails (weekday / weekly / monthly / seasonal)
- New `config/digests.yaml` + `DigestConfig` model; `digest_engine.py` decides which digests fire today (`should_send_today`) and sends via SMTP
- weekday (Mon–Fri) pushes arXiv only; weekly (Sun) / monthly (1st) / seasonal (quarter start) include published papers only — emails don't overlap
- Triggered inside the single daily workflow (approach A); legacy single daily email kept as fallback when `digests.yaml` is absent
- `digest_cli.py` for local `--dry-run` / `--send`; window semantics `window_days: 0` = since last trigger (Monday covers the weekend)

### Feature 2: Web & email content separation + quarterly top papers
- New `export_quarterly_jekyll()` → `jekyll_site/_data/quarterly.json`; new `pages/quarterly.html` with Preprints / Publications tabs
- Quarterly view = last 90 days, top-scored, split by `source==arxiv` (preprint) vs everything else (publication)

### Feature 3: DOI-first deterministic dedup
- `Paper.doi` / `alternate_link`; `rss_fetcher` extracts DOI (prism:doi / dc:identifier / link)
- arXiv DOI enrichment via arXiv API (`enrich_arxiv_dois`) enables arXiv↔journal cross-source merge
- `deduplicate.py` rewritten to O(n) key dedup (doi → arxiv id → title hash), journal version canonical
- SQLite migration (`_ensure_columns`) adds `doi`/`alternate_link`; JSONL archive merge by id + DOI

### CI
- `daily-pipeline.yaml`: fetch JSONL archive from `data` branch before the run (only cross-run history), pass digest/quarterly env vars

---

## 2026-06-29 — Add "人工品味校准" docs + update ai_analysis.md status

**Changed files:** `docs/ai_analysis.md`, `docs/CHANGELOG.md`

- Added "人工品味校准（手动编辑）" section to §2.2 of `docs/ai_analysis.md`, explaining how to manually edit `config/curated_papers.yaml` score/reason to inject personal scoring preferences
- Updated §2.3 status from "待实现" to "已实现 ✅" (analysis_prompt.md was created in previous commit)
- Updated Appendix A footnote to remove stale "analysis_prompt.md 尚未实现" note
- Pushed to GitHub

---

## 2026-06-29 — Implement 3 pending features: analysis_prompt.md, RD auto-gen, directory restructure

**Changed files:** `config/analysis_prompt.md` (new), `src/semantic_analyzer.py`, `src/orchestrator_jekyll.py`, `src/reference_paper_analyzer.py`, `TODO.md`, `docs/CHANGELOG.md`

### Feature 1: config/analysis_prompt.md (user-editable LLM prompt template)
- Created `config/analysis_prompt.md` — a standalone prompt template with `{{variable}}` placeholders
- `semantic_analyzer.py`: Added `_load_prompt_template()` and `_fill_prompt_template()` methods
- Priority: template file > hardcoded fallback. Users can edit the `.md` file to adjust scoring precision, output format, etc. without touching Python code.
- Added `config_dir` parameter to `SemanticAnalyzer.__init__()` so it can find the template file
- Updated `orchestrator_jekyll.py` to pass `config_dir` when initializing the analyzer

### Feature 2: Auto-generate research_directions.md from PDFs
- `reference_paper_analyzer.py`: Added `generate_research_directions_from_papers()` — scans `config/papers/{tier}/` for PDFs, extracts text from up to 5, calls LLM to infer research directions, writes to `research_directions.md`
- `orchestrator_jekyll.py`: In `load_configuration()`, if `research_directions.md` is missing or empty (<50 bytes) and PDFs exist, auto-generate it
- This handles the "papers only" scenario from the design docs

### Feature 3: Directory restructure (config/data/code)
- Created `code/` directory and moved `src/`, `scripts/`, `jekyll_site/` into it
- Updated all internal imports and path references across the codebase
- Updated `.github/workflows/daily-pipeline.yaml` working directory
- Updated `Dockerfile` and `docker-compose.yaml` paths
- Updated `pyproject.toml` package discovery

### TODO.md update
- Marked 0.4 (prompt alignment) as completed
- Added new completed features to the "已完成功能" table
- Updated version status section with current date
- Fixed outdated references (example_*.yaml → curated_papers.yaml)

---

## 2026-06-29 — Rewrite ai_analysis.md to reflect user's design philosophy

**Changed files:** `docs/ai_analysis.md` (rewritten), `docs/tier_guide.md` (deleted), `docs/CHANGELOG.md`

- **Problem:** `docs/ai_analysis.md` was outdated — it described a "single source of truth" approach where `tier_guide.md` was the canonical scoring document, which contradicted the user's actual design intent.
- **Solution:** Rewrote `docs/ai_analysis.md` from scratch to reflect the correct design:
  - §1.1: Tier Guide is **hardcoded** in Python (not configurable via RD), to keep score distribution stable. Precision defaults to 0.1, adjustable via `analysis_prompt.md`.
  - §1.2: Two calibration dimensions — RD provides coarse direction/range (0.5 steps), curated_papers.yaml provides fine-grained few-shot calibration (0.1 steps).
  - §2.1: Four configuration scenarios documented (RD only / RD+papers / papers only / neither).
  - §2.3: `analysis_prompt.md` documented as a **future feature** — a standalone prompt template users can edit without touching Python.
  - §3: Pipeline flow diagram updated to show prompt construction logic.
  - Appendix A: Directory structure diagram showing the ideal 3-category layout (config/ data/ code/).
- Deleted `docs/tier_guide.md` — its content is now fully covered by the rewritten `ai_analysis.md`.

---

## 2026-06-28 — Unify scoring rules across all modules + JSON parse retry

**Changed files:** `src/semantic_analyzer.py`, `src/reference_paper_analyzer.py`, `config/curated_papers.yaml`, `docs/ai_analysis.md`, `docs/CHANGELOG.md`

- **Problem:** Three different scoring rule sets existed across the codebase:
  - `research_directions.md` Tier Guide: core 7.5–10.0 / relevant 5.0–7.4 / not_priority 2.0–4.9 / unrelated 0.0–1.9
  - `semantic_analyzer.py` prompt (hardcoded): core 8.0–10.0 / relevant 6.0–8.0 / not_priority 4.0–6.0 / unrelated 0.0–4.0
  - `docs/ai_analysis.md` §1.1: core 7.0–10.0 / relevant 4.0–6.9 / not_priority 1.0–3.9
- **Fix:** Unified all modules to use `research_directions.md` Tier Guide as the single source of truth:
  - `semantic_analyzer.py` prompt: replaced hardcoded ranges with Tier Guide values (7.5–10.0 / 5.0–7.4 / 2.0–4.9 / 0.0–1.9)
  - `reference_paper_analyzer.py`: updated `TIER_SCORE_RANGES`, `TIER_SCORE_DEFAULTS`, `TIER_DESCRIPTIONS`, and `score_to_tier()` to match
  - `config/curated_papers.yaml` header: updated SCORE → TIER MAPPING comment
  - `docs/ai_analysis.md`: rewrote §1.1 as "统一评分规则（Tier Guide）" with explicit warning; updated §2.4 Tier table; corrected §1.2 direction names to match actual H2 headings
- **JSON parse retry:** Added three-layer fallback in `_parse_llm_response`: (1) direct `json.loads`, (2) regex JSON extraction, (3) LLM retry with "respond with valid JSON only" prompt. Previously failed directly to score=0.
- **Result:** Single authoritative scoring rule set; JSON parse failures now have two recovery layers before falling back to score=0.

---

## 2026-06-28 — Per-journal colour tags (feed-level display_name/color)

**Changed files:** `src/models.py`, `src/config_loader.py`, `src/email_sender.py`, `src/data_exporter.py`, `src/database.py`, `src/orchestrator_jekyll.py`, `jekyll_site/assets/js/app.js`, `jekyll_site/index.html`, `jekyll_site/_includes/modal.html`, `jekyll_site/pages/all-papers.html`, `jekyll_site/pages/recommended.html`

- **Problem:** Source colour tags in email and website showed publisher-level names (e.g. "Nature", "APS", "Science") rather than the specific journal name (e.g. "Nature Physics", "Phys. Rev. Lett.", "Science Advances").
- **Solution:** Added `display_name` and `color` fields to `FeedConfig` model. Each RSS feed in `config/rss_sources.yaml` already had per-journal `display_name`/`color` — the pipeline now passes these through to all outputs.
- `email_sender.py`: Added `_resolve_feed_config()` helper that checks feed-level config first, falls back to source-level. Updated `format_single_paper_html`, `build_email_html`, `build_email_text`, `send_daily_email` to accept and use `feed_configs`.
- `data_exporter.py`: Updated `_paper_to_flat_dict`, `export_markdown`, `export_all` to accept `feed_configs` and resolve per-journal names.
- `database.py`: Updated `save_papers` to accept `feed_configs` and store per-journal display_name/color.
- `orchestrator_jekyll.py`: Builds `feed_configs` dict (`{feed.name: feed}`) and passes it to `send_daily_email`, `save_papers`, and `export_all`.
- Jekyll frontend: Updated `getSourceName()` and `sourceStyle()` in `app.js` to use per-paper `source_display_name`/`source_color` fields instead of looking up by source key. Updated `index.html`, `modal.html`, `all-papers.html`, `recommended.html` to pass the paper object (not just source key) to these helpers.
- **Result:** Email colour tags and website badges now show the actual journal name (e.g. "Nature Physics", "Phys. Rev. Lett.", "PRX Quantum") with the journal-specific colour.

---

## 2026-06-08 — Make curated_papers.yaml fully user-managed

**Changed files:** `src/orchestrator_jekyll.py`, `docs/ai_analysis.md`, `.clinerules`

- Removed Step 7.5 (`append_pipeline_papers`) from orchestrator: pipeline must NOT auto-write daily recommended papers into `curated_papers.yaml`, because unreviewed samples degrade few-shot calibration quality.
- Removed `append_pipeline_papers` import from orchestrator.
- Updated `docs/ai_analysis.md` §2.2 to document the user-managed policy explicitly, with a prominent warning that pipeline does not write to this file.
- Updated `.clinerules` `Config/Data Idempotency Rules` to match the new policy.
- Added `Change Log Skill` to `.clinerules`: AI assistants must append a CHANGELOG entry and update the relevant docs file after every project modification.

---

## 2026-06-08 — Fix curated_papers.yaml push rejected in GitHub Actions

**Changed files:** `.github/workflows/daily-pipeline.yaml`

- Added `git pull --rebase origin master` before `git push origin master` when committing curated_papers.yaml back to master.
- Root cause: a developer push to master landed after the workflow checked out the repo but before the workflow tried to push, causing "fetch first" rejection.

---

## 2026-06-08 — Fix GitHub Actions data-branch checkout failure

**Changed files:** `.github/workflows/daily-pipeline.yaml`

- Added a pre-checkout step in "Push data to data branch": if `config/curated_papers.yaml` was modified (by Step 1.5 PDF analysis), commit and push it to master *before* switching to the data branch.
- Root cause: `git checkout data` aborted with "would be overwritten" because Step 1.5 left curated_papers.yaml with uncommitted local changes.

---

## 2026-06-07 — Docs/config cleanup + .clinerules project conventions

**Changed files:** `.clinerules`, `docs/ai_analysis.md`, `config/` (deleted files)

- Deleted `config/example_core.yaml` and `config/example_unrelated.yaml`: not referenced by any code, superseded by `curated_papers.yaml`.
- Deleted `config/papers/README.md`: content consolidated into `docs/ai_analysis.md` §2.
- Created `.clinerules` with documentation policy, file structure rules, coding conventions, and idempotency rules for AI assistants.
- Tested `run_reference_paper_analysis` on 19 PDFs: 14 entries written to `curated_papers.yaml` (5 failed due to JSON parse errors or empty LLM responses — known issue, tracked in `docs/ai_analysis.md` §4).

---

## 2026-06-07 — curated_papers.yaml: single accumulated few-shot file

**Changed files:** `config/curated_papers.yaml` (new), `src/reference_paper_analyzer.py`, `src/semantic_analyzer.py`, `src/orchestrator_jekyll.py`, `docs/ai_analysis.md`

> ⚠️ Step 7.5 (pipeline auto-accumulation) superseded by 2026-06-08 entry above.

- Replaced scattered `config/ref_*.yaml` files with a single `config/curated_papers.yaml` (id-keyed, append-only, manual deletes permanent).
- `reference_paper_analyzer.py`: writes to `curated_papers.yaml` instead of individual files; added `load_curated_papers()`, `save_curated_papers()`, `append_pipeline_papers()`, `score_to_tier()`.
- `semantic_analyzer.py`: added `load_curated_papers()` + `_build_few_shot_block()` — up to 5 tier-balanced examples injected into every LLM prompt.
- Updated score ranges across all files: core 8–10 / relevant 6–8 / not_priority 4–6 / unrelated 0–4.
- `orchestrator_jekyll.py`: calls `analyzer.load_curated_papers()` on startup; reloads after Step 1.5.
- Docs: rewrote `ai_analysis.md` §2 (single-file architecture, entry format, idempotency rules).

---

## 2026-06-07 — Reference paper PDF auto-analysis (Step 1.5)

**Changed files:** `src/reference_paper_analyzer.py` (new), `src/orchestrator_jekyll.py`

- New module `reference_paper_analyzer.py`: scans `config/papers/{tier}/` for PDF files, extracts text with `pypdf`, calls LLM to generate structured YAML entries, writes to `curated_papers.yaml`.
- Integrated as Pipeline Step 1.5 in orchestrator (runs before RSS fetch, after config load).
- Idempotent: PDFs already present in `curated_papers.yaml` are skipped on subsequent runs.
