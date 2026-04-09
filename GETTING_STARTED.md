# Getting Started with Quantum RSS Radar

This guide will help you set up and run the Quantum RSS Radar system locally for development and testing.

## Prerequisites

1. **Python 3.10+**: The system requires Python 3.10 or newer
2. **uv**: Fast Python package installer (recommended) or pip
3. **LLM API Key**: OpenAI or DeepSeek API key for AI analysis
4. **Git**: For version control (optional but recommended)

## Quick Setup (5 minutes)

### 1. Clone and Navigate

```bash
# Clone the repository
git clone <your-repo-url>
cd quantum-rss-radar

# Or if you already have the code
cd path/to/quantum-rss-radar
```

### 2. Install Dependencies

Using uv (recommended):
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
```

Using traditional pip:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure the System

```bash
# Copy example configuration files
cp config/settings.yaml.example config/settings.yaml

# Edit your research interests
code config/research_directions.md  # Or use your favorite editor

# Edit RSS feed sources
code config/rss_sources.yaml
```

### 4. Add Your API Key

Edit `config/settings.yaml`:
```yaml
llm:
  provider: "openai"  # or "deepseek"
  model: "gpt-4-turbo-preview"  # or "deepseek-chat"
  api_key: "sk-your-openai-api-key-here"  # Or use environment variable: ${OPENAI_API_KEY}
```

Or use environment variables:
```bash
# On Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"

# On Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"
```

### 5. Run Your First Pipeline

```bash
# Test with mock data (no API calls needed)
uv run python test_mock_data.py

# Or run the actual pipeline (requires API key)
uv run python -m src.orchestrator --test
```

### 6. View the Generated Website

```bash
# Start a local web server
python -m http.server -d web 8000

# Open http://localhost:8000 in your browser
```

## Configuration Details

### Research Directions (`config/research_directions.md`)

This Markdown file defines your research interests. The LLM uses this to evaluate paper relevance.

Example:
```markdown
# My Research Interests

## Quantum Computing
- Quantum error correction and fault tolerance
- NISQ algorithms and applications
- Quantum machine learning
- Quantum simulation of materials

## Machine Learning
- Foundation models for scientific discovery
- Federated learning for privacy-preserving research
- Explainable AI in scientific applications

## Condensed Matter Physics
- Topological materials and phases
- Superconductivity at room temperature
- 2D materials and heterostructures
```

### RSS Sources (`config/rss_sources.yaml`)

Define the RSS feeds to monitor. Example feeds are pre-configured.

Example configuration:
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
  
  - name: "Science Magazine"
    url: "https://www.science.org/action/showFeed?ui=0&mi=0&ai=0&type=etoc&feed=rss"
    category: "science"
    source: "science"
```

### Settings (`config/settings.yaml`)

Main configuration file with LLM, email, and processing settings.

Key settings:
- `llm.provider`: "openai" or "deepseek"
- `llm.model`: Model name (gpt-4-turbo-preview, gpt-3.5-turbo, deepseek-chat)
- `processing.max_papers_per_feed`: Limit papers per RSS feed
- `processing.min_relevance_score`: Minimum score (0-10) for recommendation
- `email.enabled`: Set to true to enable daily email digests

## Running the Pipeline

### Local Development

Use the provided script for easiest setup:
```bash
./scripts/run_local.sh
```

Or manually:
```bash
# Full pipeline (fetch, analyze, generate website)
uv run python -m src.orchestrator

# Test mode (limited data, faster)
uv run python -m src.orchestrator --test

# Skip email sending even if configured
uv run python -m src.orchestrator --skip-email
```

### Docker (For Production)

```bash
# Build the image
docker build -t quantum-rss-radar .

# Run with mounted volumes
docker run -v ./config:/app/config -v ./data:/app/data -v ./web:/app/web quantum-rss-radar

# Or use docker-compose
docker-compose up
```

## Output Files

After running the pipeline, you'll find:

### Data Files (`data/`)
- `data/raw/`: Raw RSS XML snapshots (daily archives)
- `data/processed/papers_analyzed.jsonl`: AI-enhanced papers in JSON Lines format
- `data/markdown/`: Daily Markdown reports for human reading

### Website (`web/`)
- Static HTML website with search, filtering, and bookmarking
- Individual paper detail pages
- Category-specific pages
- Recommended papers page

### Test Outputs (`test_output/`)
- Generated during test runs with mock data
- Useful for development without API calls

## Testing Without API Keys

The system includes a comprehensive test suite that uses mock data:

```bash
# Run all tests with mock data (no API calls)
uv run python test_mock_data.py

# Expected output:
# 🧪 Quantum RSS Radar - Mock Data Tests
# ==================================================
# 📋 Testing Website Builder... ✅ PASSED
# 📋 Testing Markdown Generator... ✅ PASSED
# 📋 Testing JSONL Output... ✅ PASSED
# ==================================================
# 🎉 All tests passed successfully!
```

## Customizing the Website

### Templates
Templates are in `src/templates/`:
- `index.html`: Homepage template
- `papers.html`: Papers listing template (also used for recommended page)
- `styles.css`: Main stylesheet

### Adding Features
1. Create new template files in `src/templates/`
2. Update `src/website_builder.py` to use your templates
3. Re-run the pipeline to regenerate the website

## Email Digest Configuration

To enable daily email digests:

1. Edit `config/settings.yaml`:
```yaml
email:
  enabled: true
  sender: "your-email@gmail.com"
  recipient: "recipient@example.com"
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "${EMAIL_USERNAME}"
  smtp_password: "${EMAIL_PASSWORD}"
```

2. Set environment variables:
```bash
export EMAIL_USERNAME="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
```

3. Test email configuration:
```bash
# The pipeline will automatically send email when enabled
```

## Deployment Options

### GitHub Actions + Pages (Recommended)
- Automated daily runs via GitHub Actions workflow
- Static site deployed to GitHub Pages
- No server costs, fully automated

### Docker on Aliyun ECS
1. Build Docker image
2. Push to container registry
3. Deploy to ECS with cron for daily execution

### Local Server with Cron
```bash
# Add to crontab for daily execution at 8 AM
0 8 * * * cd /path/to/quantum-rss-radar && ./scripts/run_local.sh >> /var/log/quantum-rss-radar.log 2>&1
```

## Troubleshooting

### Common Issues

1. **API Key Not Configured**
   - Error: "LLM API key not configured"
   - Solution: Set `OPENAI_API_KEY` environment variable or edit `config/settings.yaml`

2. **RSS Feed Errors**
   - Error: Failed to fetch RSS feed
   - Solution: Check feed URLs in `config/rss_sources.yaml`

3. **Website Not Updating**
   - Solution: Clear `web/` directory and re-run pipeline
   - Command: `rm -rf web/ && uv run python -m src.orchestrator`

4. **Docker Permission Issues**
   - Error: Permission denied on mounted volumes
   - Solution: Use correct volume paths or adjust permissions

### Getting Help

- Check the log file: `quantum_rss_radar.log`
- Run in verbose mode: Add `--verbose` flag (if supported)
- Review test outputs: `test_output/` directory

## Next Steps

1. **Customize Research Interests**: Edit `config/research_directions.md`
2. **Add Your Favorite Journals**: Edit `config/rss_sources.yaml`
3. **Customize Website**: Modify templates in `src/templates/`
4. **Set Up Automation**: Configure GitHub Actions or cron jobs
5. **Deploy Website**: Push to GitHub Pages or your web server

## Need Help?

- Review the full documentation in `README.md`
- Check the source code in `src/` directory
- Run tests to verify system functionality
- Customize the system to fit your specific needs

Happy researching! 🚀