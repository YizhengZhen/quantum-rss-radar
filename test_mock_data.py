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
    
    # Paper 1: Quantum Foundations
    paper1 = Paper(
        id="mock_quantum_001",
        title="Quantum Error Correction with Surface Codes",
        authors=["John Quantum", "Alice Researcher", "Bob Scientist"],
        abstract="We demonstrate a new approach to quantum error correction using surface codes with improved fault tolerance. Our method reduces the overhead required for fault-tolerant quantum computation by 30% compared to previous approaches. Experimental results show a logical error rate of 1e-5 per cycle, making practical quantum computation more feasible.",
        link="https://arxiv.org/abs/2401.12345",
        published=datetime(2024, 1, 15),
        source="arxiv",
        category="quantum_foundations",
        feed_name="arXiv Quantum Physics - Foundations",
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
    
    # Paper 2: Quantum Communication
    paper2 = Paper(
        id="mock_comm_002",
        title="Secure Quantum Key Distribution with Continuous Variables",
        authors=["Alice Quantum", "Bob Crypto", "Eve Researcher"],
        abstract="We present a new continuous-variable quantum key distribution protocol that achieves higher key rates and improved security against collective attacks. The protocol uses squeezed states and homodyne detection to establish secure communication channels over metropolitan distances. Experimental results demonstrate key rates of 10 Mbps over 50 km of optical fiber.",
        link="https://arxiv.org/abs/2401.67890",
        published=datetime(2024, 1, 20),
        source="arxiv",
        category="quantum_communication",
        feed_name="arXiv Quantum Physics - Communication",
        rss_fetch_date=datetime.now() - timedelta(days=2),
        tags=["quantum-key-distribution", "continuous-variables", "quantum-communication", "security"],
        raw_data={}
    )
    
    analysis2 = PaperAnalysis(
        paper_id="mock_comm_002",
        relevance_score=8.3,
        recommendation=True,
        summary={
            "tldr": "Continuous-variable quantum key distribution achieves 10 Mbps over 50 km.",
            "motivation": "Increasing key rates and security for practical quantum communication.",
            "method": "Continuous-variable protocol using squeezed states and homodyne detection.",
            "result": "10 Mbps key rates over 50 km optical fiber with improved security.",
            "conclusion": "Enables practical metropolitan-scale quantum-secure communication."
        },
        keywords=["quantum key distribution", "continuous variables", "quantum communication", "security"]
    )
    
    # Paper 3: Hybrid Quantum Systems
    paper3 = Paper(
        id="mock_hybrid_003",
        title="Superconducting Circuits Coupled to Spin Ensembles for Quantum Transduction",
        authors=["Charlie Super", "Diana Spin"],
        abstract="We demonstrate efficient quantum transduction between microwave and optical frequencies using superconducting circuits coupled to spin ensembles. The system achieves conversion efficiency of 15% with high fidelity, enabling hybrid quantum networks. Experimental results show coherence times exceeding 10 microseconds at millikelvin temperatures.",
        link="https://www.nature.com/articles/s41567-024-02456-8",
        published=datetime(2024, 2, 5),
        source="nature",
        category="hybrid_systems",
        feed_name="Nature Materials",
        rss_fetch_date=datetime.now() - timedelta(days=5),
        tags=["superconducting-circuits", "spin-ensembles", "quantum-transduction", "hybrid-systems"],
        raw_data={}
    )
    
    analysis3 = PaperAnalysis(
        paper_id="mock_hybrid_003",
        relevance_score=8.9,
        recommendation=True,
        summary={
            "tldr": "Superconducting circuits coupled to spin ensembles enable 15% efficient quantum transduction.",
            "motivation": "Connecting different quantum platforms requires efficient frequency conversion.",
            "method": "Hybrid system using superconducting circuits and spin ensembles for microwave-to-optical conversion.",
            "result": "15% conversion efficiency with high fidelity, 10µs coherence times.",
            "conclusion": "Enables practical hybrid quantum networks connecting different quantum technologies."
        },
        keywords=["superconducting circuits", "spin ensembles", "quantum transduction", "hybrid systems"]
    )
    
    # Paper 4: Thermodynamics
    paper4 = Paper(
        id="mock_thermo_004",
        title="Finite-Time Thermodynamics of Quantum Information Processing",
        authors=["Thermo Researcher", "Quantum Scientist"],
        abstract="We investigate the thermodynamic cost of quantum information operations in finite time. Our results show a fundamental trade-off between operation speed and energy dissipation, with implications for the design of energy-efficient quantum processors. The analysis reveals optimal protocols that minimize entropy production while maintaining high fidelity.",
        link="https://journals.aps.org/pre/abstract/10.1103/PhysRevE.109.012345",
        published=datetime(2024, 1, 10),
        source="aps",
        category="thermodynamics",
        feed_name="Physical Review E",
        rss_fetch_date=datetime.now() - timedelta(days=10),
        tags=["finite-time-thermodynamics", "quantum-information", "energy-dissipation", "entropy-production"],
        raw_data={}
    )
    
    analysis4 = PaperAnalysis(
        paper_id="mock_thermo_004",
        relevance_score=9.5,
        recommendation=True,
        summary={
            "tldr": "Fundamental trade-off between speed and energy dissipation in quantum information processing.",
            "motivation": "Understanding thermodynamic constraints on quantum operations.",
            "method": "Finite-time thermodynamics analysis of quantum protocols.",
            "result": "Optimal protocols that minimize entropy production while maintaining fidelity.",
            "conclusion": "Key insights for designing energy-efficient quantum processors."
        },
        keywords=["thermodynamics", "quantum information", "energy dissipation", "finite-time"]
    )
    
    mock_papers = [
        (paper1, analysis1),
        (paper2, analysis2),
        (paper3, analysis3),
        (paper4, analysis4)
    ]
    
    return mock_papers


def create_mock_categories():
    """Create mock category configurations aligned with research directions."""
    from src.models import CategoryConfig
    
    return {
        "thermodynamics": CategoryConfig(
            display_name="Thermodynamics & Statistical Mechanics",
            color="#FF6B6B",
            priority=1
        ),
        "quantum_foundations": CategoryConfig(
            display_name="Quantum Foundations",
            color="#4A90E2",
            priority=2
        ),
        "quantum_communication": CategoryConfig(
            display_name="Quantum Communication",
            color="#7ED321",
            priority=3
        ),
        "hybrid_systems": CategoryConfig(
            display_name="Hybrid Quantum Systems",
            color="#F5A623",
            priority=4
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