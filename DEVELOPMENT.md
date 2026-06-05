# Development Guide

> Pipeline flow, module architecture, data models, and key design decisions.

> 🇨🇳 中文版请见 [DEVELOPMENT_CN.md](DEVELOPMENT_CN.md)

---

## 📊 Pipeline Flow

```
                     ┌─────────────────────────────┐
                     │    orchestrator_jekyll.py    │
                     │         (Orchestrator)        │
                     └─────────────────────────────┘

Step  1: config_loader          ← reads .env + config/*.yaml/*.md
Step  2: rss_fetcher            ← multi-threaded RSS ingestion
Step  3: normalizer             ← normalizes author/date/source format
Step  4: deduplicate            ← arxiv ID first, title hash fallback
Step  5: semantic_analyzer      ← LLM scoring + structured summary (cache-first)
Step  6: filter_and_rank        ← sort by relevance score
Step  7: arxiv_deep_reader      ← download PDF + re-analyze high-score papers
Step  8: data_exporter          ← JSONL + MD report + Jekyll
Step  9: database               ← SQLite persistence
Step 10: email_sender           ← daily digest email
```

---

## 🏗️ Module Architecture

```
scheduler
    ↓
orchestrator_jekyll  (Main orchestrator)
    ├── config_loader        ← reads .env + config/
    ├── rss_fetcher → normalizer → deduplicate
    ├── semantic_analyzer    ← LLM calls + cache (llm_cache.json)
    ├── arxiv_deep_reader    ← PDF download + full-text analysis
    ├── data_exporter        ← JSONL / MD / Jekyll _data/
    ├── database             ← SQLite storage (radar.db)
    └── email_sender         ← SMTP HTML email

Modules communicate only through the dataclasses in models.py — no circular dependencies.
```

### Module Responsibilities

| Module | File | Responsibility |
|--------|------|----------------|
| Config Loading | `config_loader.py` | Reads `.env` + `config/*.yaml/*.md` |
| RSS Ingestion | `rss_fetcher.py` | Multi-threaded RSS fetch with rate limiting |
| Normalizer | `normalizer.py` | Standardizes author/date/source format |
| Deduplication | `deduplicate.py` | Dedup via arxiv ID + title hash |
| Semantic Analysis | `semantic_analyzer.py` | LLM API calls + cache + structured summaries |
| Deep Reading | `arxiv_deep_reader.py` | Downloads high-score arXiv PDFs for deep analysis |
| Data Export | `data_exporter.py` | JSONL + Markdown reports + Jekyll `_data/papers.json` |
| Database | `database.py` | SQLite persistence (`data/radar.db`), cross-day queries |
| Email | `email_sender.py` | SMTP HTML email |
| Tag Manager | `tag_manager.py` | Keyword accumulation, matching, categorization |
| Scheduler | `scheduler.py` | Cron expression scheduling |
| Data Models | `models.py` | Paper / PaperAnalysis / Config dataclasses |

---

## 📁 File Structure

```
quantum-rss-radar/
├── .env.example                  # Environment variable template
├── Dockerfile / docker-compose.yaml
├── pyproject.toml / requirements.txt
│
├── src/                          # Python source code
│   ├── orchestrator_jekyll.py    # Main orchestrator (10-step pipeline)
│   ├── config_loader.py          # Config loading
│   ├── rss_fetcher.py            # RSS ingestion
│   ├── normalizer.py             # Normalization
│   ├── deduplicate.py            # Deduplication
│   ├── semantic_analyzer.py      # LLM analysis + cache
│   ├── arxiv_deep_reader.py      # PDF deep reading
│   ├── data_exporter.py          # Data export
│   ├── database.py               # SQLite storage
│   ├── email_sender.py           # Email push
│   ├── tag_manager.py            # Tag management
│   ├── models.py                 # Data models
│   └── scheduler.py              # Scheduling
│
├── config/
│   ├── rss_sources.yaml          # RSS source definitions
│   └── research_directions.md    # Research directions (edit as needed)
│
├── jekyll_site/                  # Jekyll website template
│   ├── _config.yml
│   ├── _data/                    # ← auto-generated papers.json after run
│   ├── _layouts/
│   ├── _includes/
│   └── assets/
│
├── scripts/                      # Helper scripts
│   ├── run_local.sh
│   ├── setup_github.sh
│   └── deploy_to_public_repo.py
│
└── data/                         # Run output (gitignored)
    ├── all/                      # JSONL daily full data
    ├── reports/                  # MD daily reports
    ├── llm_cache.json            # LLM analysis cache
    └── radar.db                  # SQLite database
```

---

## 🧩 Key Data Models

Defined in `src/models.py`:

```
Paper
  ├── id: str              # Unique ID (arxiv ID first → title hash fallback)
  ├── title: str
  ├── authors: List[str]
  ├── abstract: str
  ├── published: datetime
  ├── source: SourceType   # arxiv / nature / aps / ieee / acm ...
  ├── source_id: str       # Source ID (e.g. arxiv:2301.00001)
  ├── link: str
  └── tags: List[str]

PaperAnalysis
  ├── paper_id: str
  ├── relevance_score: float    # 0.0 - 10.0
  ├── recommendation: bool
  ├── summary: Dict             # {tldr, motivation, method, result, conclusion}
  ├── keywords: List[str]
  ├── direction: str            # Research direction (LLM-assigned)
  └── deep_read: str | None     # PDF deep reading note

Config
  ├── llm_api_key / llm_model / llm_provider / llm_base_url
  ├── max_papers_per_feed / min_relevance_score
  ├── email_enabled / email_smtp_*
  └── llm_cache_enabled
```

---

## 🔑 Key Design Decisions

### 1. LLM Cache

- Cache file: `data/llm_cache.json`
- Cache key: `paper.id` (stable ID after deduplication)
- A paper appearing in both arXiv + journal feeds gets the same deduped ID, so cache hits
- Disable via `LLM_CACHE_ENABLED=false` in `.env`
- Saves 50-80% API costs

### 2. Deduplication Strategy

1. arxiv ID first (extracted from link: `2301.xxxxx`)
2. No arxiv ID → SHA256 hash of normalized title for comparison
3. `INSERT OR REPLACE` into SQLite, naturally deduped

### 3. Research Direction vs Tags

- **Direction**: LLM assigns papers to one of your defined research directions from `research_directions.md`
- **Tags**: LLM extracts technical keywords; `tag_manager.py` accumulates, matches, and categorizes them over time

### 4. Minimal Scraping Principle

- Only arXiv papers with score ≥ high threshold (default 8.0) have their PDF downloaded for full-text analysis
- All other papers rely on title + abstract from RSS feeds only
- Default deep-read ratio ≤ 5%

### 5. Modular Design

- All modules communicate only through `models.py` dataclasses — no circular dependencies
- LLM provider is swappable: OpenAI / DeepSeek / Azure / local Ollama
- Just change `LLM_PROVIDER` / `LLM_BASE_URL` in `.env`

### 6. SQLite Persistence

- Database file: `data/radar.db`
- Tables: `papers` (paper + analysis), `pipeline_runs` (run history)
- Retains historical data for cross-day queries
- JSONL still kept as the Jekyll website data source

---

## ⚙️ Key Configuration Variables

All config via `.env` or environment variables:

```
# ===== Required =====
LLM_API_KEY="sk-..."              # OpenAI / DeepSeek API key

# ===== LLM (Optional) =====
LLM_PROVIDER="deepseek"           # openai / deepseek / azure / local
LLM_BASE_URL="https://api.deepseek.com"
LLM_MODEL="deepseek-chat"

# ===== Processing Controls =====
MAX_PAPERS_PER_FEED=50            # Max papers per feed
MIN_RELEVANCE_SCORE=5.0           # Minimum score for recommendation
TOP_N_RECOMMENDATIONS=10          # Top-N for email
LLM_CACHE_ENABLED=true            # Enable analysis cache

# ===== Email =====
EMAIL_ENABLED=false
EMAIL_SMTP_SERVER="smtp.gmail.com"
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME="your-email@gmail.com"
EMAIL_SMTP_PASSWORD="your-app-password"
EMAIL_SENDER="your-email@gmail.com"
EMAIL_RECIPIENT="your-email@gmail.com"
```

---

## 🧪 Local Development

```bash
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
cp .env.example .env                    # Fill in LLM_API_KEY

# Test mode (10 papers, quick validation)
python -m src.orchestrator_jekyll --test

# Full run
python -m src.orchestrator_jekyll

# View logs
tail -f quantum_rss_radar_jekyll.log
```

---

## 🐳 Docker

```bash
docker-compose up --build
# or
docker build -t quantum-rss-radar .
docker run --env-file .env quantum-rss-radar
```

---

## 🔮 Roadmap

- [ ] Web UI dashboard — visualize run history, manual pipeline trigger
- [ ] Paper bookmark / dismiss mechanism — feedback-based scoring
- [ ] Custom Note template for deep-read papers
- [ ] Unit test coverage (currently none)
- [ ] Multi-language prompt support
