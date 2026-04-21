#!/bin/bash
# Quantum RSS Radar - Local Execution Script
# Run the full pipeline locally for testing and development

set -e  # Exit on error

echo "🚀 Quantum RSS Radar - Local Pipeline"
echo "====================================="

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
python --version | grep -q "3.10\|3.11" || {
    echo "Error: Python 3.10 or 3.11 is required"
    python --version
    exit 1
}

# Check for required configuration files
echo "Checking configuration files..."
# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Copying from example configuration..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and settings"
    echo "Required: LLM_API_KEY"
    echo "Optional: LLM_BASE_URL, LLM_MODEL, and other settings"
    exit 1
fi

if [ ! -f "config/research_directions.md" ]; then
    echo "Error: config/research_directions.md not found"
    echo "Please create this file with your research interests"
    exit 1
fi

if [ ! -f "config/rss_sources.yaml" ]; then
    echo "Error: config/rss_sources.yaml not found"
    echo "Please create this file with your RSS feed configurations"
    exit 1
fi

# Create data directories if they don't exist
echo "Setting up data directories..."
mkdir -p data/raw data/processed data/markdown web

# Install dependencies if needed
echo "Checking dependencies..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "Error: Could not find virtual environment activation script"
    exit 1
fi

echo "Installing/upgrading dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run the pipeline
echo "Starting Quantum RSS Radar pipeline..."
echo "--------------------------------------"

python -m src.orchestrator

echo "--------------------------------------"
echo "✅ Pipeline completed successfully!"

# Show output locations
echo ""
echo "📁 Outputs:"
echo "  - Data: data/processed/papers_analyzed.jsonl"
echo "  - Reports: data/markdown/"
echo "  - Website: web/"
echo ""
echo "To view the website locally:"
echo "  python -m http.server -d web 8000"
echo "  Then open http://localhost:8000"
echo ""
echo "To run in test mode (limited papers):"
echo "  python -m src.orchestrator --test"
echo ""

# Deactivate virtual environment
deactivate

echo "✨ Done!"