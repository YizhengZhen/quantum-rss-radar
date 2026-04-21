# Quantum RSS Radar - AI-Assisted Academic Research Tracking System

> **"Your personal AI research assistant that tracks, analyzes, and recommends academic papers daily"**

[![GitHub Pages](https://img.shields.io/badge/Deployed%20on-GitHub%20Pages-blue?logo=github)](https://pages.github.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)

**Quantum RSS Radar** is an open-source, AI-powered daily research tracking system that aggregates papers from arXiv and major journals, uses LLMs to analyze relevance to your research interests, and delivers personalized recommendations via a static website.

## ✨ Key Features

- **🔍 Smart RSS Aggregation**: Fetch papers from arXiv (quant-ph), Nature, Science, APS, IEEE, ACM, and more
- **🤖 AI-Powered Analysis**: Uses OpenAI/DeepSeek LLMs to classify, score, and rank papers based on semantic relevance
- **📊 Structured Summaries**: Generates TLDR, motivation, method, results, conclusion for each paper
- **🌐 Static Website**: Generates a clean, searchable research portal deployable on GitHub Pages
- **📧 Daily Email Digest**: Optional email notifications with top recommendations
- **🐳 Docker Support**: Portable container for local development and cloud deployment
- **🔧 Local-First Development**: Test everything locally before deploying to GitHub/Aliyun
- **⚡ Fully Automated**: Runs daily via GitHub Actions, zero maintenance required

## 🚀 Quick Start

### 1. Clone and Configure
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/quantum-rss-radar.git
cd quantum-rss-radar

# Copy example configuration
cp config/settings.yaml.example config/settings.yaml

# Edit configuration (optional)
# See config/settings.yaml for customization options
```

### 2. Set Up LLM API
Create a `.env` file for local testing:
```bash
# .env file
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.deepseek.com  # Optional: DeepSeek default
LLM_MODEL=deepseek-chat                # Optional: DeepSeek default
```

### 3. Run Locally
```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Run the system
python -m src.orchestrator_jekyll
```

### 4. View Results
- **Data Output**: `data/processed/papers_analyzed.jsonl`
- **Website**: `jekyll_site/_site/index.html`
- **Logs**: `data/logs/quantum_rss_radar.log`

## 🎯 GitHub Deployment (Recommended)

### 1. Set Up GitHub Secrets
Go to your repository → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value | Required |
|--------|-------|----------|
| `LLM_API_KEY` | Your DeepSeek/OpenAI API key | ✅ **Required** |
| `LLM_BASE_URL` | `https://api.deepseek.com` (optional) | Optional |
| `LLM_MODEL` | `deepseek-chat` (optional) | Optional |

### 2. Enable GitHub Pages
1. Go to repository **Settings → Pages**
2. Under "Build and deployment", select **Source: GitHub Actions**
3. Click **Save**

### 3. Push to GitHub
```bash
git add .
git commit -m "Initial commit with Quantum RSS Radar"
git push origin main
```

**That's it!** The system will:
- Run daily at 08:00 UTC
- Process arXiv quantum physics papers
- Build a Jekyll static website
- Deploy to GitHub Pages automatically

Your research portal will be available at:  
`https://YOUR_USERNAME.github.io/quantum-rss-radar/`

## 📋 System Architecture

```
quantum-rss-radar/
├── src/                    # Python source code
│   ├── orchestrator_jekyll.py      # Main orchestrator
│   ├── rss_fetcher.py             # RSS feed fetcher
│   ├── semantic_analyzer.py       # LLM-based paper analysis
│   ├── data_manager.py           # JSONL data storage
│   ├── website_generator.py      # Jekyll site generator
│   ├── email_sender.py           # Email notifications
│   └── config_loader.py          # Configuration management
│
├── config/                # Configuration files
│   ├── settings.yaml.example     # Example settings (safe to commit)
│   ├── rss_sources.yaml          # RSS feed configurations
│   └── research_directions.md    # Your research interests
│
├── jekyll_site/          # Static website (Jekyll)
│   ├── _config.yml       # Jekyll configuration
│   ├── _layouts/         # HTML templates
│   ├── _includes/        # Reusable components
│   └── _site/            # Generated site (auto)
│
├── data/                 # Processed data
│   ├── raw/             # Raw RSS feed data
│   ├── processed/       # Analyzed papers (JSONL)
│   └── logs/            # System logs
│
└── .github/workflows/   # GitHub Actions
    └── daily-pipeline.yml # Daily automation workflow
```

## 🔧 Configuration

### LLM Configuration (`config/settings.yaml`)
```yaml
# LLM Configuration - Generic OpenAI-compatible API
llm:
  provider: "generic"                    # Auto-detected from base_url
  model: "deepseek-chat"                 # Can be overridden by LLM_MODEL
  api_key: "${LLM_API_KEY}"              # From environment variable
  base_url: "https://api.deepseek.com"   # Can be overridden by LLM_BASE_URL

# Email Configuration (optional)
email:
  enabled: false
  sender: "${EMAIL_SENDER}"
  recipient: "${EMAIL_RECIPIENT}"
  smtp_server: "${EMAIL_SMTP_SERVER}"
  smtp_port: 587
  smtp_username: "${EMAIL_SMTP_USERNAME}"
  smtp_password: "${EMAIL_SMTP_PASSWORD}"

# Processing Settings
processing:
  max_papers_per_feed: 50
  min_relevance_score: 5.0
  top_n_recommendations: 10

# Output Directories
output_dir: "data"
web_dir: "jekyll_site/_site"
```

### RSS Sources (`config/rss_sources.yaml`)
```yaml
feeds:
  - name: "arXiv Quantum Physics"
    url: "http://arxiv.org/rss/quant-ph"
    category: "quantum_physics"
    source: "arxiv"
    max_items: 50  # Limit for testing

# More sources (commented out for initial testing):
# - name: "Nature Physics"
#   url: "https://www.nature.com/nphys.rss"
# - name: "Physical Review Letters"
#   url: "https://journals.aps.org/prl/rss"
```

### Research Directions (`config/research_directions.md`)
```markdown
# Research Interests

## Primary Areas
- Quantum computing and quantum algorithms
- Quantum information theory and communication
- Quantum foundations and measurement theory

## Specific Topics
- Quantum error correction and fault tolerance
- NISQ (Noisy Intermediate-Scale Quantum) devices
- Quantum machine learning algorithms
- Topological quantum computing
- Quantum cryptography and security

## Methods of Interest
- Tensor network methods
- Quantum Monte Carlo simulations
- Quantum circuit optimization
- Quantum control theory
- Open quantum systems
```

## 📊 Data Flow

1. **Ingestion**: RSS fetcher collects papers from configured sources
2. **Analysis**: LLM analyzes each paper against research directions
3. **Scoring**: Papers scored 0-10 based on relevance
4. **Tagging**: Automatic keyword extraction and categorization
5. **Storage**: Results saved as JSONL + structured summaries
6. **Generation**: Jekyll website built with all analyzed papers
7. **Deployment**: Static site deployed to GitHub Pages/Aliyun
8. **Notification**: Daily email with top recommendations (optional)

## 🐳 Docker Deployment

### Local Docker Testing
```bash
# Build the image
docker build -t quantum-rss-radar .

# Run with environment variables
docker run --env LLM_API_KEY=sk-... quantum-rss-radar

# Or use docker-compose
docker-compose up
```

### Cloud Deployment (Aliyun ECS)
```bash
# 1. Build and push to container registry
docker build -t registry.cn-hangzhou.aliyuncs.com/your-namespace/quantum-rss-radar .
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/quantum-rss-radar

# 2. Deploy to ECS with environment variables
# Set LLM_API_KEY, LLM_BASE_URL, etc. in ECS container configuration
```

## 🔍 Supported LLM Providers

### OpenAI
```bash
LLM_BASE_URL=https://api.openai.com
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-...  # OpenAI API key
```

### DeepSeek (Recommended)
```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-...  # DeepSeek API key
```

### Azure OpenAI
```bash
LLM_BASE_URL=https://your-resource.openai.azure.com/
LLM_MODEL=gpt-4
LLM_API_KEY=sk-...  # Azure OpenAI key
```

### Custom OpenAI-Compatible API
```bash
LLM_BASE_URL=https://your-api-endpoint.com/v1
LLM_MODEL=your-model-name
LLM_API_KEY=sk-...  # Your API key
```

## 📁 Output Structure

### JSONL Data Format
```json
{
  "id": "arxiv:2401.12345",
  "title": "Quantum Algorithm for Linear Systems of Equations",
  "authors": ["Aram Harrow", "Avinatan Hassidim", "Seth Lloyd"],
  "abstract": "We present a quantum algorithm...",
  "published": "2024-01-01T00:00:00Z",
  "link": "https://arxiv.org/abs/2401.12345",
  "source": "arxiv",
  "analysis": {
    "relevance_score": 8.5,
    "recommendation": true,
    "summary": {
      "tldr": "Quantum algorithm solving linear systems exponentially faster than classical.",
      "motivation": "Linear systems are fundamental in scientific computing.",
      "method": "Uses quantum phase estimation and Hamiltonian simulation.",
      "result": "Achieves exponential speedup for sparse, well-conditioned matrices.",
      "conclusion": "Paves way for quantum machine learning applications."
    },
    "keywords": ["quantum algorithm", "linear systems", "HHL", "quantum speedup"]
  },
  "tags": ["quantum-algorithms", "quantum-computing", "linear-algebra"]
}
```

### Generated Website
- **Homepage**: Overview of top recommended papers
- **Categories**: Papers grouped by research areas
- **Search**: Full-text search across all papers
- **Filters**: Filter by score, date, source, tags
- **Details**: Individual paper pages with full analysis

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Report Issues
- Use GitHub Issues to report bugs or request features
- Include steps to reproduce, expected vs actual behavior

### Submit Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/quantum-rss-radar.git
cd quantum-rss-radar

# Install development dependencies
uv venv
source .venv/bin/activate
uv sync --group dev

# Run tests
pytest tests/

# Format code
black src/
ruff check --fix src/
```

### Areas for Contribution
- **New RSS Sources**: Add feeds from your favorite journals/conferences
- **Analysis Improvements**: Better prompt engineering, multi-language support
- **UI/UX Enhancements**: Better website design, mobile optimization
- **Performance**: Caching, parallel processing, rate limiting
- **Documentation**: More examples, tutorials, use cases

## 📄 License

**MIT License**

Copyright (c) 2026 Yizheng Zhen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

For full license text, see [LICENSE](LICENSE) file.

## 📞 Support

- **Issues**: GitHub Issues for bugs and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Email**: Configure daily email digest for personal use

---

**Happy Researching!** 📚✨

Your AI research assistant is ready to help you discover the most relevant papers in your field.