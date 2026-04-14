#!/usr/bin/env python3
"""
Generate categories from research_directions.md for Jekyll data files.
This ensures categories match the actual research directions defined in config/research_directions.md.
"""

import re
import yaml
import json
from pathlib import Path

# Color palette optimized for dark/light modes
CATEGORY_COLORS = {
    "Information Thermodynamics": {
        "light": "#FF6B6B",  # Warm red
        "dark": "#FF8A8A"    # Lighter red for dark mode
    },
    "Quantum Foundations": {
        "light": "#4A90E2",  # Blue
        "dark": "#6AAEFF"    # Lighter blue for dark mode
    },
    "Quantum Communication": {
        "light": "#7ED321",  # Green
        "dark": "#9FE644"    # Lighter green for dark mode
    },
    "Hybrid Quantum Systems": {
        "light": "#F5A623",  # Orange
        "dark": "#FFC046"    # Lighter orange for dark mode
    }
}

def extract_research_directions():
    """Extract research directions from config/research_directions.md."""
    directions_path = Path("config/research_directions.md")
    if not directions_path.exists():
        print(f"Error: Research directions file not found at {directions_path}")
        return []
    
    with open(directions_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract h2 headings (## headings)
    pattern = r'##\s+(.+?)\n'
    matches = re.findall(pattern, content)
    
    # Filter out any empty matches
    directions = [match.strip() for match in matches if match.strip()]
    
    return directions

def generate_categories_data():
    """Generate Jekyll categories data from research directions."""
    # Extract research directions
    directions = extract_research_directions()
    print(f"Found {len(directions)} research directions: {directions}")
    
    # Create categories data structure
    categories = {}
    for idx, direction in enumerate(directions, 1):
        # Create slug from direction name
        slug = direction.lower().replace(' ', '_').replace('-', '_')
        
        # Get color scheme for this direction
        color_info = CATEGORY_COLORS.get(direction, {
            "light": "#9B59B6",  # Default purple
            "dark": "#BD7BD9"
        })
        
        categories[slug] = {
            "name": direction,
            "color": color_info["light"],  # Default color for light mode
            "color_dark": color_info["dark"],  # Color for dark mode
            "priority": idx,
            "description": f"Papers related to {direction}"
        }
    
    return categories

def update_jekyll_data(categories):
    """Update Jekyll data files with new categories."""
    jekyll_data_dir = Path("jekyll_site/_data")
    
    # Ensure directory exists
    jekyll_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing papers data to preserve papers
    papers_data_path = jekyll_data_dir / "papers.json"
    if not papers_data_path.exists():
        print(f"Error: Papers data file not found at {papers_data_path}")
        return
    
    with open(papers_data_path, "r", encoding="utf-8") as f:
        papers_data = json.load(f)
    
    # Update categories in papers data
    papers_data["categories"] = categories
    
    # Calculate counts for each category
    papers = papers_data.get("papers", [])
    for category_slug in categories:
        category_papers = [p for p in papers if p.get("category") == category_slug]
        recommended_papers = [p for p in category_papers if p.get("recommended", False)]
        
        categories[category_slug]["count"] = len(category_papers)
        categories[category_slug]["recommended_count"] = len(recommended_papers)
    
    # Update stats
    if "stats" not in papers_data:
        papers_data["stats"] = {}
    
    papers_data["stats"]["total_categories"] = len(categories)
    papers_data["stats"]["last_updated"] = str(datetime.now().isoformat())
    
    # Write updated data back
    with open(papers_data_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated categories in {papers_data_path}")
    print(f"Added {len(categories)} categories from research directions")
    
    # Also create a separate categories file for reference
    categories_data = {
        "categories": categories,
        "generated_at": str(datetime.now().isoformat()),
        "source": "config/research_directions.md"
    }
    
    categories_path = jekyll_data_dir / "categories.json"
    with open(categories_path, "w", encoding="utf-8") as f:
        json.dump(categories_data, f, indent=2, ensure_ascii=False)
    
    print(f"Created categories reference file: {categories_path}")
    
    return categories

def generate_css_color_overrides(categories):
    """Generate CSS overrides for category colors in dark mode."""
    css_lines = []
    css_lines.append("/* Category color overrides for dark mode */")
    css_lines.append("[data-theme=\"dark\"] {")
    
    for slug, category in categories.items():
        if "color_dark" in category:
            css_lines.append(f"    --category-{slug}: {category['color_dark']};")
    
    css_lines.append("}")
    css_lines.append("")
    
    # Generate CSS rules for each category
    css_lines.append("/* Category-specific styles */")
    for slug, category in categories.items():
        name = category["name"]
        css_lines.append(f".category-{slug} {{")
        css_lines.append(f"    background-color: var(--category-{slug}, {category['color']}) !important;")
        css_lines.append(f"    border-color: var(--category-{slug}, {category['color']}) !important;")
        css_lines.append(f"    color: white !important;")
        css_lines.append("}")
        css_lines.append("")
    
    return "\n".join(css_lines)

if __name__ == "__main__":
    from datetime import datetime
    print("Generating categories from research_directions.md...")
    
    categories = generate_categories_data()
    if categories:
        updated_categories = update_jekyll_data(categories)
        
        # Generate CSS overrides
        css_content = generate_css_color_overrides(updated_categories)
        css_path = Path("jekyll_site/assets/css/category-colors.css")
        css_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content)
        
        print(f"Generated CSS color overrides: {css_path}")
        
        # Update categories.html to use new layout
        update_categories_layout()
    else:
        print("No categories generated. Please check research_directions.md file.")

def update_categories_layout():
    """Update categories.html to use new statistics layout."""
    categories_html_path = Path("jekyll_site/pages/categories.html")
    if not categories_html_path.exists():
        print(f"Categories HTML file not found: {categories_html_path}")
        return
    
    with open(categories_html_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the stats section and replace with better layout
    # We'll replace the current vertical stats with a horizontal grid
    stats_section = """<div class="category-stats">
    <h2><i class="fas fa-chart-bar"></i> Category Statistics</h2>
    <div class="stats-grid">
        {% for category in site.data.papers.categories %}
        <div class="category-stat">
            <div class="stat-header">
                <span class="stat-color" style="background-color: {{ category[1].color }};"></span>
                <h4>{{ category[1].name }}</h4>
            </div>
            <div class="stat-content">
                {% assign cat_papers = 0 %}
                {% assign cat_recommended = 0 %}
                {% assign total_score = 0 %}
                {% assign paper_count = 0 %}
                
                {% for paper in site.data.papers.papers %}
                {% if paper.category == category[0] %}
                {% assign cat_papers = cat_papers | plus: 1 %}
                {% if paper.recommended %}
                {% assign cat_recommended = cat_recommended | plus: 1 %}
                {% endif %}
                {% if paper.score %}
                {% assign total_score = total_score | plus: paper.score %}
                {% assign paper_count = paper_count | plus: 1 %}
                {% endif %}
                {% endif %}
                {% endfor %}
                
                <p class="stat-number">{{ cat_papers }}</p>
                <p class="stat-label">Papers</p>
                
                <div class="stat-details">
                    <div class="stat-item">
                        <i class="fas fa-star"></i>
                        <span>{{ cat_recommended }} recommended</span>
                    </div>
                    {% if paper_count > 0 %}
                    <div class="stat-item">
                        <i class="fas fa-chart-line"></i>
                        <span>Avg: {{ total_score | divided_by: paper_count | round: 1 }}/10</span>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>"""
    
    # Replace with new horizontal stats layout
    new_stats_section = """<div class="category-stats-improved">
    <h2><i class="fas fa-chart-bar"></i> Category Overview</h2>
    <div class="category-stats-horizontal">
        {% for category in site.data.papers.categories %}
        {% assign cat_papers = 0 %}
        {% assign cat_recommended = 0 %}
        {% assign total_score = 0 %}
        {% assign paper_count = 0 %}
        
        {% for paper in site.data.papers.papers %}
        {% if paper.category == category[0] %}
        {% assign cat_papers = cat_papers | plus: 1 %}
        {% if paper.recommended %}
        {% assign cat_recommended = cat_recommended | plus: 1 %}
        {% endif %}
        {% if paper.score %}
        {% assign total_score = total_score | plus: paper.score %}
        {% assign paper_count = paper_count | plus: 1 %}
        {% endif %}
        {% endif %}
        {% endfor %}
        
        <div class="category-stat-card" style="border-left-color: {{ category[1].color }};">
            <div class="stat-card-header">
                <div class="stat-color-dot" style="background-color: {{ category[1].color }};"></div>
                <h4>{{ category[1].name }}</h4>
            </div>
            <div class="stat-card-body">
                <div class="stat-main-number">{{ cat_papers }}</div>
                <div class="stat-main-label">Papers</div>
                
                <div class="stat-card-grid">
                    <div class="stat-grid-item">
                        <i class="fas fa-star"></i>
                        <span class="stat-grid-value">{{ cat_recommended }}</span>
                        <span class="stat-grid-label">Rec.</span>
                    </div>
                    <div class="stat-grid-item">
                        <i class="fas fa-chart-line"></i>
                        <span class="stat-grid-value">
                            {% if paper_count > 0 %}
                            {{ total_score | divided_by: paper_count | round: 1 }}
                            {% else %}
                            0
                            {% endif %}
                        </span>
                        <span class="stat-grid-label">Avg</span>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>"""
    
    if stats_section in content:
        content = content.replace(stats_section, new_stats_section)
        
        with open(categories_html_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Updated categories.html with new horizontal stats layout")
    else:
        print("Warning: Could not find stats section in categories.html")