# Quantum RSS Radar: AI-Assisted Academic Research Tracking

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Static Site](https://img.shields.io/badge/Deployment-GitHub%20Pages-blueviolet.svg)](https://pages.github.com/)

An intelligent research assistant that aggregates RSS feeds from academic journals and uses LLMs (OpenAI/DeepSeek) to classify, score, and rank papers based on semantic relevance to your research interests.

> **Smart Research, Simplified**: Track relevant papers daily without manual effort. Perfect for researchers, PhD students, and academics who want to stay current in their field.

## ✨ Features

### 🔍 Intelligent Paper Discovery
- **Comprehensive RSS Aggregation**: arXiv (all categories), APS, Nature, Science, Springer, IEEE, ACM journals
- **Semantic Analysis**: LLM-powered classification and scoring based on your research directions
- **Daily Updates**: Automatically fetches and analyzes new papers every day

### 🤖 AI-Powered Analysis
- **Structured Summaries**: TLDR, motivation, method, result, conclusion for each paper
- **Relevance Scoring**: 0-10 scores based on semantic similarity to your interests
- **Smart Recommendations**: "Yes"/"No" recommendations with reasoning
- **Categorization**: Automatic tagging based on research topics

### 🌐 Beautiful Static Website
- **Responsive Design**: Mobile-friendly interface with dark/light modes
- **Advanced Filtering**: Search, filter by category, score, date, recommendation
- **Paper Details**: Complete AI analysis summaries and metadata
- **Local Storage**: Bookmark papers for later reading

### 🔧 DevOps & Deployment
- **Local-First Development**: Test everything locally before deployment
- **GitHub Pages**: Deploy static site for free with automatic updates
- **Docker Support**: Portable container for any cloud (Aliyun ECS, AWS, etc.)
- **GitHub Actions**: Fully automated daily runs with secrets protection

## 📁 Project Structure

```
quantum-rss-radar/
├── config/                    # Configuration files
│   ├── research_directions.md   # Your research interests (edit this)
│   ├── rss_sources.yaml         # RSS feed configurations (edit this)
│   ├── settings.yaml.example    # Example configuration (copy to settings.yaml)
│   └── settings.yaml            # Main configuration (gitignored - use secrets)
├── src/                       # Python source code
│   ├── __init__.py
│   ├── config_loader.py       # Configuration loading
│   ├── rss_fetcher.py         # RSS feed fetching
│   ├── semantic_analyzer.py   # LLM-based paper analysis
│   ├── website_builder.py     # Jekyll website generation
│   └── ... (more modules)
├── jekyll_site/               # Jekyll website templates
│   ├── _config.yml            # Jekyll configuration
│   ├── _layouts/              # Page layouts
│   ├── _includes/             # Reusable components
│   ├── assets/                # CSS, JS files
│   └── pages/                 # Content pages
├── scripts/                   # Utility scripts
│   ├── run_local.sh           # Run full pipeline locally
│   └── setup_github.sh        # Setup GitHub repository
├── docker/                    # Docker configuration
├── .github/workflows/         # GitHub Actions workflows
├── pyproject.toml             # Python dependencies (uv)
├── requirements.txt           # Python dependencies (pip)
├── Dockerfile                 # Docker container definition
├── docker-compose.yaml        # Docker compose configuration
└── README.md                  # This file
```

## 🚀 Quick Start: Local Development

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- LLM API key (OpenAI or DeepSeek)

### Step 1: Setup Environment
```bash
# Clone repository
git clone https://github.com/yourusername/quantum-rss-radar.git
cd quantum-rss-radar

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure Your Research
```bash
# 1. Edit your research interests
nano config/research_directions.md

# 2. Configure RSS feeds (optional - default includes major journals)
nano config/rss_sources.yaml

# 3. Create settings.yaml from example
cp config/settings.yaml.example config/settings.yaml

# 4. Configure API keys using environment variables
export OPENAI_API_KEY="your-api-key-here"  # or DEEPSEEK_API_KEY
```

### Step 3: Run Locally
```bash
# Run full pipeline
./scripts/run_local.sh

# Or run manually
python -m src.orchestrator_jekyll

# The pipeline will:
# 1. Fetch RSS feeds from all configured sources
# 2. Analyze papers using LLM
# 3. Generate website in jekyll_site/_site/
```

### Step 4: View Results
```bash
# Serve the generated website
cd jekyll_site
bundle exec jekyll serve

# Open http://localhost:4001 in your browser
```

## 🔐 Security: Protecting API Keys

### Local Development (Environment Variables)
```bash
# Method 1: Direct export
export OPENAI_API_KEY="your-key-here"
export EMAIL_SMTP_PASSWORD="your-password"

# Method 2: Use .env file (gitignored)
echo "OPENAI_API_KEY=your-key-here" >> config/.env
echo "DEEPSEEK_API_KEY=your-key-here" >> config/.env
```

### GitHub Deployment (GitHub Secrets)
1. Go to your repository → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `OPENAI_API_KEY` or `DEEPSEEK_API_KEY`
   - `EMAIL_SMTP_PASSWORD` (if using email)
   - `EMAIL_SENDER`, `EMAIL_RECIPIENT`, etc.

3. GitHub Actions will automatically use these secrets

### Configuration File Example (`config/settings.yaml`)
```yaml
# IMPORTANT: This file should NOT contain actual API keys
# Use environment variables or GitHub Secrets instead

llm:
  provider: "openai"  # or "deepseek"
  model: "gpt-4-turbo-preview"
  api_key: "${OPENAI_API_KEY}"  # Read from environment variable

email:
  enabled: false
  sender: "${EMAIL_SENDER}"
  recipient: "${EMAIL_RECIPIENT}"
  smtp_server: "${EMAIL_SMTP_SERVER}"
  smtp_username: "${EMAIL_SMTP_USERNAME}"
  smtp_password: "${EMAIL_SMTP_PASSWORD}"  # From GitHub Secrets
```

## 🌍 Deploy to GitHub Pages

### Option A: Automated GitHub Actions (Recommended)
1. **Fork this repository** or create a new one from this template
2. **Add your GitHub Secrets** as described above
3. **Configure GitHub Pages**:
   - Go to repository Settings → Pages
   - Source: GitHub Actions
   - The workflow will automatically deploy to GitHub Pages

4. **The default workflow** (`daily-run.yml`) will:
   - Run daily at 08:00 UTC
   - Process RSS feeds and analyze papers
   - Build the Jekyll site
   - Deploy to GitHub Pages
   - Keep your site updated automatically

### Option B: Manual GitHub Pages Deployment
```bash
# 1. Push your repository to GitHub
git remote add origin https://github.com/yourusername/quantum-rss-radar.git
git push -u origin main

# 2. Enable GitHub Pages in repository settings
# Settings → Pages → Source: "main branch" → "/jekyll_site/_site" folder

# 3. Run pipeline and deploy
./scripts/run_local.sh
git add jekyll_site/_site
git commit -m "Update site"
git push origin main
```

### Option C: Docker Deployment (Aliyun ECS, AWS, etc.)
```bash
# Build Docker image
docker build -t quantum-rss-radar .

# Run with environment variables
docker run -d \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  quantum-rss-radar

# Or use docker-compose
docker-compose up -d
```

## 📊 Customization

### Research Directions (`config/research_directions.md`)
```markdown
# My Research Interests

## Quantum Computing
- Quantum error correction and fault tolerance
- Quantum algorithms for optimization problems
- NISQ devices and near-term applications
- Quantum machine learning and neural networks

## Artificial Intelligence
- Large language models for scientific discovery
- Federated learning and privacy-preserving ML
- Reinforcement learning for control systems
- Explainable AI in scientific domains

## Materials Science
- Quantum materials and topological insulators
- High-temperature superconductivity
- 2D materials and van der Waals heterostructures
- Computational materials discovery
```

### RSS Sources (`config/rss_sources.yaml`)
```yaml
feeds:
  - name: "arXiv Quantum Physics"
    url: "http://arxiv.org/rss/quant-ph"
    category: "quantum_computing"
    source: "arxiv"
  
  - name: "arXiv Machine Learning"
    url: "http://arxiv.org/rss/cs.LG"
    category: "machine_learning"
    source: "arxiv"
  
  - name: "Nature Physics"
    url: "https://www.nature.com/nphys.rss"
    category: "physics"
    source: "nature"
  
  - name: "Science Magazine"
    url: "https://www.science.org/rss/current.xml"
    category: "general_science"
    source: "science"

categories:
  quantum_computing:
    display_name: "Quantum Computing"
    color: "#4A90E2"
    priority: 1
  
  machine_learning:
    display_name: "Machine Learning"
    color: "#7ED321"
    priority: 2
```

## 🔄 Daily Workflow

The system runs daily via GitHub Actions or local cron job:

```
1. Fetch RSS Feeds (8:00 UTC)
   └── Download latest papers from all configured sources
   
2. Normalize Metadata
   └── Convert to unified paper schema

3. Deduplicate
   └── Remove duplicate papers across sources

4. AI Semantic Analysis
   └── LLM evaluates each paper against research interests
   └── Generates scores, summaries, recommendations

5. Generate Outputs
   ├── JSONL: Structured data for analysis
   ├── Markdown: Human-readable reports
   └── Website: Complete Jekyll site with search/filtering

6. Deploy Website
   └── GitHub Pages, Netlify, or any static hosting

7. Send Email (Optional)
   └── Daily digest with top recommended papers
```

## 🌐 Website Features

Visit your deployed site to access:

- **Home Page**: Top recommended papers, filtering controls
- **Recommended Papers**: All AI-recommended papers with scores
- **All Papers**: Complete database with advanced filtering
- **Categories**: Browse by research category with statistics
- **Search**: Client-side search across titles, abstracts, authors
- **Dark/Light Mode**: Toggle between themes
- **Date Filtering**: Calendar picker for specific dates
- **Paper Details**: Complete AI analysis in modal view
- **Bookmarks**: Save papers locally for later reading

## 🛠️ Development

### Adding New Features
1. Create new module in `src/`
2. Update orchestrator to include it
3. Add configuration options if needed
4. Update website templates for new features

### Running Tests
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Code formatting
uv run black src/
uv run ruff check --fix src/
```

### Building Documentation
```bash
# Generate API documentation
uv run pdoc --html src/ --output-dir docs/

# Build this README with updates
# The project structure section is auto-generated from actual files
```

## 📈 Data Flow

```
Raw RSS Feeds → Fetch → Normalize → Deduplicate → AI Analysis → Outputs
    ↓           ↓          ↓           ↓            ↓           ↓
arXiv/Nature/  XML/Atom  Unified     Unique       Scores     JSONL
Science/APS     Feeds     Schema      Papers      Summaries  Markdown
                                                           Jekyll Site
                                                           Email Digest
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

This is a personal research tracking system designed for academic use. Feel free to:

1. **Fork** for your own research needs
2. **Customize** RSS feeds and categories
3. **Extend** with new analysis features
4. **Share** improvements via pull requests

## 🔮 Roadmap

- [ ] Add more RSS sources (bioRxiv, medRxiv, SSRN)
- [ ] Citation graph analysis
- [ ] Author tracking and collaboration networks
- [ ] Conference deadline tracking
- [ ] Mobile app with notifications
- [ ] Plugin system for custom analyzers

## 📞 Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Email**: Configure daily email digest for personal use

---

**Happy Researching!** 📚✨

Your AI research assistant is ready to help you discover the most relevant papers in your field.