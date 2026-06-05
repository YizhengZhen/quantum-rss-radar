# Quantum RSS Radar — AI-Powered Daily Research Paper Tracker

Automatically track the latest papers from arXiv / Nature / Science / APS / IEEE / ACM and other RSS sources. Uses an LLM to score and rank papers based on your research interests, then generates a daily recommendation website and optional email digest.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

> 🇨🇳 中文版请见 [README_CN.md](README_CN.md)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📡 **RSS Feed Ingestion** | Fetches paper titles + abstracts from configured RSS sources |
| 🎯 **Research-Direction Scoring** | LLM scores each paper (0-10) against your `research_directions.md` |
| 📝 **High-Score Paper Reports** | Score ≥ threshold → structured summary (TLDR / Motivation / Method / Result / Conclusion) |
| 📄 **arXiv Deep Reading** | Very high scores → auto-download PDF, full-text re-analysis, generates a Note |
| 📧 **Email Digest** | Daily Top-N recommended papers sent via SMTP |
| 🌐 **Static Website** | Jekyll site with search, direction filtering, and statistics |
| 🎯 **Direction Classification** | LLM assigns each paper to a research direction from your config |
| 🏷️ **Auto Keyword Tagging** | LLM extracts keywords; tag manager accumulates, matches, and categorizes them |
| 🗃️ **SQLite History Database** | All papers persisted, cross-day historical queries supported |
| 🔁 **Auto-Deduplication** | Same paper across multiple sources (arXiv + journal) merged automatically |
| 📊 **Direction Statistics** | Per-direction paper counts and average scores at a glance |
| ⚙️ **Multiple Deployment Modes** | GitHub Actions automation (recommended) / Local Python / Docker |

## 💪 Advantages

| Advantage | Description |
|-----------|-------------|
| 🌍 **Pure RSS, No Scraping** | Zero legal risk, covers arXiv / Nature / Science / APS / IEEE / ACM |
| 🎯 **Custom Research Profile** | Write a `research_directions.md`, LLM scores papers against it |
| 💰 **Token-Saving Cache** | `llm_cache.json`: already-analyzed papers skip API calls, saving 50-80% costs |
| 🤖 **Minimal Scraping** | Only the top ~5% of papers get PDF deep reading; everything else uses abstracts only |
| 🔒 **Private Deployment** | Paper data never leaves your GitHub repo / server |
| ♻️ **Incremental Runs** | Each run only processes new papers, reuses previous results |
| 🔌 **Modular, Swappable LLM** | Supports OpenAI / DeepSeek / Azure / local Ollama — just change `.env` |
| 🛠️ **Zero Maintenance** | Set up GitHub Actions once and it runs fully automatically |

> 🇨🇳 中文版请见 [README_CN.md](README_CN.md)

---

## 🚀 Quick Start

### 0. Prerequisites (Required for All Deployment Modes)

Fork or clone this repository on GitHub:

```bash
git clone https://github.com/YizhengZhen/quantum-rss-radar.git && cd quantum-rss-radar
```

Edit the following two files:

| File | Purpose | Note |
|------|---------|------|
| `config/research_directions.md` | Define your research interests; LLM scores & classifies papers against this | See format examples inside the file |
| `config/rss_sources.yaml` | Add/remove RSS sources you want to track | See format examples inside the file |

> The default `research_directions.md` contains the author's quantum information research directions. `rss_sources.yaml` comes pre-configured with arXiv × 4 + APS + Nature + Science and others. Modify as needed.

### Option 1: GitHub Actions + Email Digest (Recommended)

1. **Push the code** to your own GitHub repository

2. **Set Secrets** — Go to your repo **Settings → Secrets and variables → Actions** and add:

   | Secret | Required | Description |
   |--------|----------|-------------|
   | `LLM_API_KEY` | ✅ | OpenAI / DeepSeek API key |
   | `LLM_BASE_URL` | Optional | API endpoint (DeepSeek default: `https://api.deepseek.com`) |
   | `LLM_MODEL` | Optional | Model name (DeepSeek default: `deepseek-chat`) |
   | `MAX_PAPERS_PER_FEED` | Optional | Max papers per feed (default: 50) |
   | `MIN_RELEVANCE_SCORE` | Optional | Minimum score for recommendation (default: 5.0) |
   | `TOP_N_RECOMMENDATIONS` | Optional | Top-N for email (default: 10) |
   | `LLM_CACHE_ENABLED` | Optional | Enable analysis cache (default: true) |
   | `DEEP_READ_ENABLED` | Optional | Enable deep reading (default: true) |
   | `EMAIL_ENABLED` | Optional | `true` to enable email digest |
   | `EMAIL_SENDER` | Optional | Sender email address |
   | `EMAIL_RECIPIENT` | Optional | Recipient email address |
   | `EMAIL_SMTP_SERVER` | Optional | SMTP server, e.g. `smtp.gmail.com` |
   | `EMAIL_SMTP_PORT` | Optional | SMTP port, default 587 |
   | `EMAIL_SMTP_USERNAME` | Optional | SMTP username (usually the email) |
   | `EMAIL_SMTP_PASSWORD` | Optional | SMTP password or app password |

   > Only `LLM_API_KEY` is required to run. Add others as needed.

3. **Enable GitHub Pages** — **Settings → Pages** → Source: "GitHub Actions"

4. The system automatically runs daily at 08:00 UTC and deploys to `https://your-username.github.io/quantum-rss-radar/`

### Option 2: GitHub Pages Only (No Email)

Same as above, skip all `EMAIL_*` Secrets.

### Option 3: Local / Docker

```bash
cp .env.example .env   # Fill in LLM_API_KEY
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
python -m src.orchestrator_jekyll --test   # Test mode (10 papers)
# or docker-compose up
```

**Output paths:**

| Content | Path |
|---------|------|
| JSONL full data | `data/all/data_*.jsonl` |
| MD report (sorted by score) | `data/reports/report_*.md` |
| Jekyll website data | `jekyll_site/_data/papers.json` |
| SQLite history database | `data/radar.db` |
| LLM analysis cache | `data/llm_cache.json` |

---

## 🧠 Architecture

Pipeline flow, module architecture, data models, and key design decisions are detailed in **[DEVELOPMENT.md](DEVELOPMENT.md)** (English) / **[DEVELOPMENT_CN.md](DEVELOPMENT_CN.md)** (中文).

### 🔮 Roadmap

- Web UI dashboard — visualize run history, trigger pipelines manually
- Paper bookmark / dismiss mechanism — feedback-based scoring optimization
- Custom Note template for deep-read papers

---

## 📄 License

MIT License. See [LICENSE](LICENSE).

## 🙏 Credits

Inspired by [dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced).  
LLM support: DeepSeek / OpenAI.
