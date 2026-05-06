#!/usr/bin/env python3
"""
[DEPRECATED] Generate categories from research_directions.md for Jekyll data files.
This script is no longer needed — classification is now done by the LLM,
which assigns a research 'direction' during semantic analysis based on the
user's research interests (see semantic_analyzer.py).

The SourceConfig (config/rss_sources.yaml → sources) provides publisher
colour tags.  Directions are dynamically assigned by the LLM during
pipeline execution.

If you still need this script for reference or migration, it remains here
but is no longer called by any pipeline or workflow.
"""

import re
import yaml
import json
from pathlib import Path

import logging
logging.warning("generate_categories_from_research_directions.py is DEPRECATED. "
                "Directions are now assigned by the LLM during analysis. "
                "Source colour tags use SourceConfig (rss_sources.yaml).")

# Retained for reference only
CATEGORY_COLORS = {
    "Information Thermodynamics": {
        "light": "#FF6B6B",
        "dark": "#FF8A8A"
    },
    "Quantum Foundations": {
        "light": "#4A90E2",
        "dark": "#6AAEFF"
    },
    "Quantum Communication": {
        "light": "#7ED321",
        "dark": "#9FE644"
    },
    "Hybrid Quantum Systems": {
        "light": "#F5A623",
        "dark": "#FFC046"
    }
}


def main_deprecated():
    """Deprecated — no-op.  Retained only for import compatibility."""
    print("DEPRECATED: This script is no longer needed. "
          "Directions are assigned by the LLM during pipeline execution.")


if __name__ == "__main__":
    main_deprecated()
