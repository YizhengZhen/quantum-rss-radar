# Quantum RSS Radar — Change Log

> Entries are newest-first. One entry per logical change set.

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
