#!/usr/bin/env python3
"""
Test script for Quantum RSS Radar using mock data.
This allows testing the system locally without API calls or RSS feeds.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.models import Paper, PaperAnalysis, Config
from src.website_builder import WebsiteBuilder
from src.md_generator import save_jsonl_output, generate_markdown_report

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_papers():
    """Create mock paper data for testing."""
    
    mock_papers = []
    
    # Paper 1: Quantum Computing
    paper1 = Paper(
        id="mock_quantum_001",
        title="Quantum Error Correction with Surface Codes",
        authors=["John Quantum", "Alice Researcher", "Bob Scientist"],
        abstract="We demonstrate a new approach to quantum error correction using surface codes with improved fault tolerance. Our method reduces the overhead required for fault-tolerant quantum computation by 30% compared to previous approaches. Experimental results show a logical error rate of 1e-5 per cycle, making practical quantum computation more feasible.",
        link="https://arxiv.org/abs/2401.12345",
        published=datetime(2024, 1, 15),
        source="arxiv",
        category="quantum",
        feed_name="arXiv Quantum Physics",
        rss_fetch_date=datetime.now(),
        tags=["quantum-error-correction", "surface-codes", "fault-tolerance", "quantum-computing"],
        raw_data={}
    )
    
    analysis1 = PaperAnalysis(
        paper_id="mock_quantum_001",
        relevance_score=8.7,
        recommendation=True,
        summary={
            "tldr": "Improved quantum error correction using surface codes reduces overhead by 30%.",
            "motivation": "Fault-tolerant quantum computation requires efficient error correction methods.",
            "method": "Surface codes with optimized lattice structures and novel decoding algorithms.",
            "result": "30% reduction in overhead, logical error rate of 1e-5 per cycle.",
            "conclusion": "Practical quantum computation becomes more feasible with this approach."
        },
        keywords=["quantum computing", "error correction", "surface codes", "fault tolerance"]
    )
    
    # Paper 2: Machine Learning
    paper2 = Paper(
        id="mock_ml_002",
        title="Federated Learning for Privacy-Preserving Medical Diagnosis",
        authors=["Emma AI", "David Doctor", "Lisa Data"],
        abstract="We present a federated learning framework for medical diagnosis that preserves patient privacy while achieving state-of-the-art accuracy. The system allows multiple hospitals to collaboratively train a model without sharing sensitive patient data. Results show 95% accuracy on pneumonia detection, comparable to centralized training.",
        link="https://arxiv.org/abs/2401.67890",
        published=datetime(2024, 1, 20),
        source="arxiv",
        category="machine_learning",
        feed_name="arXiv Computer Science - Machine Learning",
        rss_fetch_date=datetime.now() - timedelta(days=2),
        tags=["federated-learning", "medical-ai", "privacy", "healthcare", "machine-learning"],
        raw_data={}
    )
    
    analysis2 = PaperAnalysis(
        paper_id="mock_ml_002",
        relevance_score=7.2,
        recommendation=True,
        summary={
            "tldr": "Federated learning enables privacy-preserving medical diagnosis with 95% accuracy.",
            "motivation": "Medical data privacy regulations limit data sharing for AI model training.",
            "method": "Federated learning with differential privacy and secure aggregation.",
            "result": "95% accuracy on pneumonia detection, comparable to centralized training.",
            "conclusion": "Federated learning is a viable approach for privacy-sensitive medical applications."
        },
        keywords=["federated learning", "medical AI", "privacy", "diagnosis"]
    )
    
    # Paper 3: Condensed Matter Physics
    paper3 = Paper(
        id="mock_cm_003",
        title="Topological Insulators for Quantum Information Processing",
        authors=["Charlie Topo", "Diana Matter"],
        abstract="We investigate topological insulators as a platform for quantum information processing. Our experimental results show protected edge states with coherence times exceeding 100 microseconds. These materials provide a promising path toward robust quantum bits with inherent protection against certain types of noise.",
        link="https://journals.aps.org/prb/abstract/10.1103/PhysRevB.109.045123",
        published=datetime(2024, 2, 5),
        source="aps",
        category="condensed_matter",
        feed_name="Physical Review B",
        rss_fetch_date=datetime.now() - timedelta(days=5),
        tags=["topological-insulators", "quantum-information", "coherence", "edge-states", "condensed-matter"],
        raw_data={}
    )
    
    analysis3 = PaperAnalysis(
        paper_id="mock_cm_003",
        relevance_score=9.1,
        recommendation=True,
        summary={
            "tldr": "Topological insulators show promise for quantum computing with 100µs coherence times.",
            "motivation": "Quantum bits need long coherence times and noise protection.",
            "method": "Experimental study of topological insulator edge states using microwave spectroscopy.",
            "result": "Coherence times >100µs, protected edge states observed.",
            "conclusion": "Topological insulators are promising for robust quantum information processing."
        },
        keywords=["topological insulators", "quantum computing", "coherence", "edge states"]
    )
    
    # Paper 4: Not recommended (low score)
    paper4 = Paper(
        id="mock_low_004",
        title="Traditional Approaches to Classical Optimization",
        authors=["Old School", "Traditional Researcher"],
        abstract="This paper revisits classical optimization techniques from the 1980s with minor improvements. We show that gradient descent with momentum can sometimes outperform newer methods on certain convex problems. The improvements are marginal but statistically significant.",
        link="https://example.com/paper4",
        published=datetime(2024, 1, 10),
        source="springer",
        category="optimization",
        feed_name="Springer Optimization",
        rss_fetch_date=datetime.now() - timedelta(days=10),
        tags=["classical-optimization", "gradient-descent", "legacy-methods"],
        raw_data={}
    )
    
    analysis4 = PaperAnalysis(
        paper_id="mock_low_004",
        relevance_score=3.5,
        recommendation=False,
        summary={
            "tldr": "Minor improvements to classical optimization techniques from the 1980s.",
            "motivation": "Revisiting classical methods to understand their limitations.",
            "method": "Gradient descent with momentum and careful hyperparameter tuning.",
            "result": "Marginal improvements on specific convex problems.",
            "conclusion": "Classical methods still have value but offer limited advancement."
        },
        keywords=["optimization", "gradient descent", "classical methods"]
    )
    
    mock_papers = [
        (paper1, analysis1),
        (paper2, analysis2),
        (paper3, analysis3),
        (paper4, analysis4)
    ]
    
    return mock_papers


def create_mock_categories():
    """Create mock category configurations."""
    from src.models import CategoryConfig
    
    return {
        "quantum": CategoryConfig(
            display_name="Quantum Computing",
            color="#4A90E2",
            priority=1
        ),
        "condensed_matter": CategoryConfig(
            display_name="Condensed Matter Physics",
            color="#7ED321",
            priority=2
        ),
        "machine_learning": CategoryConfig(
            display_name="Machine Learning",
            color="#F5A623",
            priority=3
        ),
        "physics": CategoryConfig(
            display_name="Physics",
            color="#BD10E0",
            priority=4
        ),
        "optimization": CategoryConfig(
            display_name="Optimization",
            color="#417505",
            priority=5
        )
    }


def test_website_builder():
    """Test the website builder with mock data."""
    logger.info("Testing website builder with mock data...")
    
    # Create mock data
    mock_papers = create_mock_papers()
    mock_categories = create_mock_categories()
    
    # Build website
    website_builder = WebsiteBuilder("web_test")
    website_builder.build_website(mock_papers, mock_categories)
    
    # Check if website files were created
    web_dir = Path("web_test")
    if web_dir.exists():
        files = list(web_dir.rglob("*"))
        logger.info(f"Website built successfully: {len(files)} files created")
        
        # List main files
        for file in web_dir.iterdir():
            if file.is_file():
                logger.info(f"  - {file.name}")
    else:
        logger.error("Website directory not created")
        return False
    
    return True


def test_markdown_generator():
    """Test the markdown generator with mock data."""
    logger.info("Testing markdown generator with mock data...")
    
    # Create mock data
    mock_papers = create_mock_papers()
    mock_categories = create_mock_categories()
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate markdown report
    generate_markdown_report(mock_papers, mock_categories, output_dir)
    
    # Check if markdown files were created
    markdown_dir = output_dir / "markdown"
    if markdown_dir.exists():
        files = list(markdown_dir.rglob("*.md"))
        logger.info(f"Markdown reports generated: {len(files)} files created")
        
        for file in files:
            logger.info(f"  - {file.relative_to(markdown_dir)}")
    else:
        logger.error("Markdown directory not created")
        return False
    
    return True


def test_jsonl_output():
    """Test JSONL output with mock data."""
    logger.info("Testing JSONL output with mock data...")
    
    # Create mock data
    mock_papers = create_mock_papers()
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Save JSONL output
    save_jsonl_output(mock_papers, output_dir)
    
    # Check if JSONL file was created
    jsonl_file = output_dir / "processed" / "papers_analyzed.jsonl"
    if jsonl_file.exists():
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        logger.info(f"JSONL output saved: {len(lines)} papers")
        return True
    else:
        logger.error("JSONL file not created")
        return False


def main():
    """Run all tests with mock data."""
    print("🧪 Quantum RSS Radar - Mock Data Tests")
    print("=" * 50)
    
    # Create test output directory
    Path("test_output").mkdir(exist_ok=True)
    
    # Run tests
    tests = [
        ("Website Builder", test_website_builder),
        ("Markdown Generator", test_markdown_generator),
        ("JSONL Output", test_jsonl_output)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        try:
            if test_func():
                print(f"  ✅ {test_name}: PASSED")
            else:
                print(f"  ❌ {test_name}: FAILED")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {test_name}: ERROR - {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed successfully!")
        print("\n📁 Outputs created:")
        print("  - Website: web_test/")
        print("  - Reports: test_output/markdown/")
        print("  - JSONL: test_output/processed/papers_analyzed.jsonl")
        
        print("\nTo view the test website:")
        print("  python -m http.server -d web_test 8000")
        print("  Then open http://localhost:8000")
    else:
        print("⚠️  Some tests failed")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)