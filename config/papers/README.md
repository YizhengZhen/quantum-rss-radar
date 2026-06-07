# config/papers/ — Reference Paper PDFs

Drop your personal research papers here to calibrate the LLM scoring system.

## Folder Structure

```
config/papers/
├── core/          → Papers you would read in full (expected score: 8.5–9.5)
├── relevant/      → Related but not core papers   (expected score: 5.0–6.5)
├── not_priority/  → In-field but not your focus   (expected score: 1.5–3.0)
└── unrelated/     → Completely unrelated papers   (expected score: 0.0–1.0)
```

## How It Works

1. Drop a PDF into the appropriate subfolder (e.g. `core/my_paper.pdf`)
2. On the next pipeline run, the system will:
   - Extract text from the PDF
   - Ask the LLM to identify the title, research direction, and key contribution
   - Generate `config/ref_core_my_paper.yaml` automatically
3. The generated YAML is injected as a few-shot example into the scoring prompt

## Rules

- **File format**: PDF only
- **One paper per file**, any filename (spaces are fine)
- **Tier is determined by folder**, not by filename
- If a corresponding YAML already exists, the PDF is skipped (no re-analysis)
- To re-analyze, delete the YAML and re-run the pipeline

## Naming Convention for Generated YAMLs

```
config/ref_{tier}_{pdf_stem_sanitized}.yaml
```

Examples:
```
config/papers/core/entropy_accumulation.pdf
  → config/ref_core_entropy_accumulation.yaml

config/papers/unrelated/battery_paper.pdf
  → config/ref_unrelated_battery_paper.yaml
```
