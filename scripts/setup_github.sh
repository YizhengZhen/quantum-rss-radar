#!/bin/bash
# Setup script for pushing Quantum RSS Radar to GitHub as private repository

echo "🚀 Quantum RSS Radar - GitHub Setup"
echo "========================================"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install git first."
    exit 1
fi

# Check if SSH key is configured
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo "⚠️  No SSH key found. You'll need to authenticate via HTTPS instead."
    echo "   To generate SSH key: ssh-keygen -t rsa -b 4096 -C \"your-email@example.com\""
fi

echo ""
echo "📝 Manual Steps Required:"
echo "========================="
echo ""
echo "1. Create a new private repository on GitHub:"
echo "   - Go to https://github.com/new"
echo "   - Repository name: quantum-rss-radar"
echo "   - Description: AI-assisted daily academic research tracking system based on RSS feeds"
echo "   - Select: Private"
echo "   - Do NOT initialize with README, .gitignore, or license"
echo ""
echo "2. Add remote and push code:"
echo ""
echo "   Copy and run these commands:"
echo ""
echo "   # Add GitHub remote (choose HTTPS or SSH):"
echo ""
echo "   # Option 1: HTTPS (requires login each time)"
echo "   git remote add origin https://github.com/YOUR_USERNAME/quantum-rss-radar.git"
echo ""
echo "   # Option 2: SSH (requires SSH key setup)"
echo "   git remote add origin git@github.com:YOUR_USERNAME/quantum-rss-radar.git"
echo ""
echo "   # Push to GitHub"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Set up GitHub Actions secrets (optional):"
echo "   - Go to Settings → Secrets and variables → Actions"
echo "   - Add these secrets if you want to use GitHub Actions:"
echo "     * LLM_API_KEY: Your OpenAI/DeepSeek API key"
echo "     * EMAIL_PASSWORD: SMTP password for email notifications"
echo ""
echo "✅ Done! Your Quantum RSS Radar is ready on GitHub."
echo ""
echo "📁 Project structure pushed:"
echo "   - Core system code in src/"
echo "   - Configuration templates in config/"
echo "   - Docker files for deployment"
echo "   - GitHub Actions workflow for daily updates"
echo "   - Test scripts and documentation"
echo ""
echo "🔧 Next steps:"
echo "   - Configure config/settings.yaml with your API keys"
echo "   - Customize config/research_directions.md with your research interests"
echo "   - Run test: python test_mock_data.py"
echo "   - Run full system: python -m src.orchestrator"