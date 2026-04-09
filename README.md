# Quantum RSS Radar

An AI-assisted daily academic research tracking system that aggregates RSS feeds from arXiv and major journals, uses LLMs to classify and rank papers based on semantic relevance, and generates structured summaries with recommendations.

## Features

- **RSS Aggregation**: Fetch papers from arXiv (multiple categories), APS, Nature, Science, Springer, IEEE, ACM, etc.
- **AI Analysis**: Use OpenAI/DeepSeek LLMs to classify, score, and rank papers based on your research directions
- **Structured Summaries**: Generate consistent summaries for each paper including:
  - TLDR
  - Motivation
  - Method
  - Result
  - Conclusion
  - Score (0-10)
  - Recommendation ("yes"/"no")
- **Daily Automation**: Run once per day, save all processed data (JSONL + Markdown)
- **Static Website**: Generate a responsive website with search, filtering, and bookmarking
- **Email Digest**: Send daily email with top recommended papers
- **Local-First Development**: Test everything locally before deployment
- **Docker Support**: Portable deployment for local → GitHub Actions → Aliyun ECS
- **No PDF Downloads**: Use only abstracts from RSS feeds

## Architecture

```
quantum-rss-radar/
├── config/                    # Configuration files
├── src/                      # Python modules
├── web/                      # Static website (HTML/JS/CSS)
├── data/                     # Local data storage (gitignored)
├── docker/                   # Docker configuration
├── .github/workflows/        # GitHub Actions automation
├── scripts/                  # Shell scripts for local execution
├── pyproject.toml           # Python dependencies with uv
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (fast Python package installer)
- LLM API key (OpenAI or DeepSeek)

### Installation

1. **Clone and setup**:
   ```bash
   # Create virtual environment and install dependencies
   uv venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   uv sync
   ```

2. **Configure**:
   - Edit `config/research_directions.md` with your research interests
   - Edit `config/rss_sources.yaml` with your RSS feed URLs
   - Copy `config/settings.yaml.example` to `config/settings.yaml` and add your API keys

3. **Run locally**:
    ```bash
    # Full pipeline
    ./scripts/run_local.sh
    
    # Or directly
    uv run python -m src.orchestrator
    ```

4. **View website**:
   ```bash
   python -m http.server -d web 8000
   # Open http://localhost:8000
   ```

## Configuration

### Research Directions (`config/research_directions.md`)
Define your research interests in Markdown format. This file is used by the LLM to evaluate paper relevance.

Example:
```markdown
# Research Interests

## Quantum Computing
- Quantum error correction
- Quantum algorithms for optimization
- NISQ devices and applications

## Machine Learning
- Quantum machine learning
- Federated learning
- Large language models for scientific discovery
```

### RSS Sources (`config/rss_sources.yaml`)
Define RSS feeds with categories and metadata.

Example:
```yaml
feeds:
  - name: "arXiv Quantum Physics"
    url: "http://arxiv.org/rss/quant-ph"
    category: "quantum"
    source: "arxiv"
  
  - name: "Nature Physics"
    url: "https://www.nature.com/nphys.rss"
    category: "physics"
    source: "nature"
```

### Settings (`config/settings.yaml`)
Configure LLM, email, and processing parameters.

Example:
```yaml
llm:
  provider: "openai"  # or "deepseek"
  model: "gpt-4-turbo-preview"
  api_key: "${OPENAI_API_KEY}"  # Use environment variables

email:
  enabled: true
  sender: "research@example.com"
  recipient: "you@example.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587

processing:
  max_papers_per_feed: 50
  min_relevance_score: 5.0
  top_n_recommendations: 10
```

## Daily Workflow

The system follows this pipeline daily:

1. **Fetch RSS feeds** → Download latest papers from all configured sources
2. **Normalize metadata** → Convert to unified paper schema
3. **Deduplicate** → Remove duplicate papers across sources
4. **AI Analysis** → LLM evaluates each paper against research interests
5. **Generate outputs** → Create JSONL, Markdown reports, and static website
6. **Send email** → Deliver top recommendations via email
7. **Deploy website** → Update GitHub Pages or other hosting

## Deployment Options

### Local Development
```bash
# Run full pipeline
./scripts/run_local.sh

# Test with mock data
./scripts/test_local.sh
```

### GitHub Actions + Pages
- Automated daily runs via GitHub Actions
- Static site deployed to GitHub Pages
- No server costs, fully automated

### Docker (Aliyun ECS)
```bash
# Build and run
docker build -t quantum-rss-radar -f docker/Dockerfile .
docker run -v ./config:/app/config -v ./data:/app/data quantum-rss-radar

# Or use docker-compose
docker-compose -f docker/docker-compose.yaml up
```

## Website Features

The generated static website includes:

- **Search**: Client-side search across titles, abstracts, authors
- **Filtering**: By category, score range, recommendation, source
- **Sorting**: By score, date, relevance
- **Bookmarks**: LocalStorage-based paper saving
- **Responsive Design**: Works on mobile and desktop
- **Paper Details**: Complete summaries and metadata

## Data Storage

- `data/raw/`: Raw RSS XML snapshots (daily)
- `data/processed/`: AI-enhanced JSONL with scores and summaries
- `data/markdown/`: Daily Markdown reports for human reading
- `web/`: Generated static website (can be deployed anywhere)

## Development

### Adding a New Module
1. Create Python file in `src/`
2. Update `src/__init__.py` if needed
3. Import and use in `src/pipeline.py`
4. Add tests if applicable

### Testing
```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Formatting
uv run black src/
uv run ruff check --fix src/
```

## License

MIT License - see LICENSE file for details.

## Contributing

This is a personal research tracking system. Feel free to fork and adapt for your own needs!