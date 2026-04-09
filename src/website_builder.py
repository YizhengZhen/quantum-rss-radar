"""
Static website builder for the Quantum RSS Radar system.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import shutil
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Paper, PaperAnalysis, CategoryConfig

logger = logging.getLogger(__name__)


class WebsiteBuilder:
    """Builds static website from paper data."""
    
    def __init__(self, web_dir: str = "web"):
        """
        Initialize website builder.
        
        Args:
            web_dir: Directory for website output
        """
        self.web_dir = Path(web_dir)
        self.templates_dir = Path(__file__).parent / "templates"
        
        # Create template directory if it doesn't exist
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default HTML templates if they don't exist."""
        default_templates = {
            "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum RSS Radar - AI Research Tracker</title>
    <link rel="stylesheet" href="css/styles.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body x-data="app()">
    <header>
        <div class="container header-container">
            <div class="header-left">
                <h1><i class="fa-solid fa-satellite-dish"></i> Quantum RSS Radar</h1>
                <p class="subtitle">AI-assisted daily academic research tracking</p>
            </div>
            <div class="header-right">
                <div class="header-controls">
                    <button class="theme-toggle" @click="toggleTheme()" :title="theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'">
                        <i class="fas" :class="theme === 'light' ? 'fa-moon' : 'fa-sun'"></i>
                    </button>
                    <p class="date">Last updated: {{ last_updated }}</p>
                </div>
            </div>
        </div>
    </header>
    
    <nav>
        <div class="container">
            <ul>
                <li><a href="index.html" class="active"><i class="fas fa-home"></i> Home</a></li>
                <li><a href="papers.html"><i class="fas fa-file-alt"></i> All Papers</a></li>
                <li><a href="recommended.html"><i class="fas fa-star"></i> Recommended</a></li>
                <li><a href="categories.html"><i class="fas fa-tags"></i> Categories</a></li>
            </ul>
        </div>
    </nav>
    
    <main class="container">
        <section class="stats">
            <div class="stat-card">
                <h3><i class="fas fa-file-alt"></i> Total Papers</h3>
                <p class="stat-number">{{ total_papers }}</p>
            </div>
            <div class="stat-card">
                <h3><i class="fas fa-star"></i> Recommended</h3>
                <p class="stat-number">{{ recommended_papers }}</p>
            </div>
            <div class="stat-card">
                <h3><i class="fas fa-tags"></i> Categories</h3>
                <p class="stat-number">{{ total_categories }}</p>
            </div>
            <div class="stat-card">
                <h3><i class="fas fa-calendar-alt"></i> Last Update</h3>
                <p class="stat-date">{{ last_updated }}</p>
            </div>
        </section>
        
        <section class="search-section">
            <div class="search-box">
                <i class="fas fa-search"></i>
                <input type="text" 
                       placeholder="Search papers by title, author, or keyword..." 
                       x-model="searchQuery"
                       @input="filterPapers()">
            </div>
            <div class="filter-controls">
                <select x-model="selectedCategory" @change="filterPapers()">
                    <option value="">All Categories</option>
                    {% for category_id, category in categories.items() %}
                    <option value="{{ category_id }}">{{ category.display_name }}</option>
                    {% endfor %}
                </select>
                <select x-model="selectedSource" @change="filterPapers()">
                    <option value="">All Sources</option>
                    <option value="arxiv">arXiv</option>
                    <option value="nature">Nature</option>
                    <option value="science">Science</option>
                    <option value="aps">APS</option>
                    <option value="ieee">IEEE</option>
                    <option value="acm">ACM</option>
                    <option value="springer">Springer</option>
                </select>
                <label>
                    <input type="checkbox" x-model="showRecommendedOnly" @change="filterPapers()">
                    Show recommended only
                </label>
            </div>
        </section>
        
        <section class="top-papers">
            <h2><i class="fas fa-crown"></i> Top Recommended Papers</h2>
            <div class="papers-grid">
                {% for paper, analysis in top_papers %}
                <div class="paper-card" 
                     :class="{ 'recommended': {{ 'true' if analysis.recommendation else 'false' }} }"
                     x-show="paperVisible('{{ paper.title }}', '{{ paper.category }}', '{{ paper.source.value }}', {{ analysis.relevance_score }}, {{ 'true' if analysis.recommendation else 'false' }})">
                    <div class="paper-header">
                        <span class="paper-score">⭐ {{ "%.1f"|format(analysis.relevance_score) }}/10</span>
                        {% if analysis.recommendation %}
                        <span class="paper-badge">RECOMMENDED</span>
                        {% endif %}
                        <span class="paper-source">{{ paper.source.value|upper }}</span>
                    </div>
                    <h3 class="paper-title">
                        <a href="paper_{{ paper.id }}.html">{{ paper.title }}</a>
                    </h3>
                    <p class="paper-authors">
                        {{ paper.authors[:3]|join(', ') }}{% if paper.authors|length > 3 %} et al.{% endif %}
                    </p>
                    <p class="paper-tldr">{{ analysis.tldr }}</p>
                    <div class="paper-footer">
                        <span class="paper-category" style="background-color: {{ categories[paper.category].color }}20; color: {{ categories[paper.category].color }};">
                            {{ categories[paper.category].display_name }}
                        </span>
                        <span class="paper-date">{{ paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown' }}</span>
                        <button class="bookmark-btn" @click="toggleBookmark('{{ paper.id }}')">
                            <i class="fas fa-bookmark" x-show="!isBookmarked('{{ paper.id }}')"></i>
                            <i class="fas fa-bookmark" style="color: #4A90E2;" x-show="isBookmarked('{{ paper.id }}')"></i>
                        </button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
        
        <section class="categories">
            <h2><i class="fas fa-tags"></i> Papers by Category</h2>
            <div class="categories-grid">
                {% for category_id, category in categories.items() %}
                {% set category_papers = papers_by_category.get(category_id, []) %}
                {% if category_papers %}
                <div class="category-card" style="border-left-color: {{ category.color }};">
                    <h3 style="color: {{ category.color }};">{{ category.display_name }}</h3>
                    <p class="category-count">{{ category_papers|length }} papers</p>
                    <ul class="category-papers">
                        {% for paper, analysis in category_papers[:3] %}
                        <li>
                            <a href="paper_{{ paper.id }}.html">{{ paper.title[:60] }}{% if paper.title|length > 60 %}...{% endif %}</a>
                            <span class="paper-score-mini">⭐ {{ "%.1f"|format(analysis.relevance_score) }}</span>
                        </li>
                        {% endfor %}
                    </ul>
                    {% if category_papers|length > 3 %}
                    <a href="category_{{ category_id }}.html" class="category-link">View all {{ category_papers|length }} papers →</a>
                    {% endif %}
                </div>
                {% endif %}
                {% endfor %}
            </div>
        </section>
    </main>
    
    <footer>
        <div class="container">
            <p>Quantum RSS Radar &copy; {{ current_year }} | AI-powered research tracking system</p>
            <p>Data updated daily via RSS feeds from arXiv, Nature, Science, APS, IEEE, ACM, and Springer</p>
            <p class="footer-links">
                <a href="https://github.com/yourusername/quantum-rss-radar"><i class="fab fa-github"></i> GitHub</a> |
                <a href="about.html"><i class="fas fa-info-circle"></i> About</a> |
                <a href="privacy.html"><i class="fas fa-shield-alt"></i> Privacy</a>
            </p>
        </div>
    </footer>
    
    <script>
        function app() {
            return {
                searchQuery: '',
                selectedCategory: '',
                selectedSource: '',
                showRecommendedOnly: false,
                bookmarks: JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]'),
                
                init() {
                    // Load bookmarks from localStorage
                    this.updateBookmarks();
                },
                
                paperVisible(title, category, source, score, recommended) {
                    if (this.showRecommendedOnly && !recommended) return false;
                    if (this.selectedCategory && category !== this.selectedCategory) return false;
                    if (this.selectedSource && source !== this.selectedSource) return false;
                    
                    if (this.searchQuery) {
                        const query = this.searchQuery.toLowerCase();
                        const searchText = (title + ' ' + category + ' ' + source).toLowerCase();
                        return searchText.includes(query);
                    }
                    
                    return true;
                },
                
                filterPapers() {
                    // Filtering is handled by x-show in template
                },
                
                isBookmarked(paperId) {
                    return this.bookmarks.includes(paperId);
                },
                
                toggleBookmark(paperId) {
                    const index = this.bookmarks.indexOf(paperId);
                    if (index === -1) {
                        this.bookmarks.push(paperId);
                    } else {
                        this.bookmarks.splice(index, 1);
                    }
                    this.updateBookmarks();
                },
                
                updateBookmarks() {
                    localStorage.setItem('quantumRssBookmarks', JSON.stringify(this.bookmarks));
                }
            }
        }
    </script>
</body>
</html>""",
            
            "papers.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Papers - Quantum RSS Radar</title>
    <link rel="stylesheet" href="css/styles.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body x-data="app()">
    <header>
        <div class="container">
            <h1><i class="fa-solid fa-satellite-dish"></i> Quantum RSS Radar</h1>
            <p class="subtitle">All Research Papers</p>
            <p class="date">Last updated: {{ last_updated }}</p>
        </div>
    </header>
    
    <nav>
        <div class="container">
            <ul>
                <li><a href="index.html"><i class="fas fa-home"></i> Home</a></li>
                <li><a href="papers.html" class="active"><i class="fas fa-file-alt"></i> All Papers</a></li>
                <li><a href="recommended.html"><i class="fas fa-star"></i> Recommended</a></li>
                <li><a href="categories.html"><i class="fas fa-tags"></i> Categories</a></li>
            </ul>
        </div>
    </nav>
    
    <main class="container">
        <section class="search-section">
            <div class="search-box">
                <i class="fas fa-search"></i>
                <input type="text" 
                       placeholder="Search {{ total_papers }} papers by title, author, or keyword..." 
                       x-model="searchQuery"
                       @input="filterPapers()">
            </div>
            <div class="filter-controls">
                <select x-model="selectedCategory" @change="filterPapers()">
                    <option value="">All Categories</option>
                    {% for category_id, category in categories.items() %}
                    <option value="{{ category_id }}">{{ category.display_name }}</option>
                    {% endfor %}
                </select>
                <select x-model="selectedSource" @change="filterPapers()">
                    <option value="">All Sources</option>
                    <option value="arxiv">arXiv</option>
                    <option value="nature">Nature</option>
                    <option value="science">Science</option>
                    <option value="aps">APS</option>
                    <option value="ieee">IEEE</option>
                    <option value="acm">ACM</option>
                    <option value="springer">Springer</option>
                </select>
                <select x-model="sortBy" @change="filterPapers()">
                    <option value="score">Sort by Score</option>
                    <option value="date">Sort by Date</option>
                    <option value="title">Sort by Title</option>
                </select>
                <label>
                    <input type="checkbox" x-model="showRecommendedOnly" @change="filterPapers()">
                    Show recommended only
                </label>
            </div>
        </section>
        
        <section class="papers-list">
            <div class="papers-count">
                Showing <span x-text="visibleCount"></span> of {{ total_papers }} papers
            </div>
            
            <div class="papers-container">
                {% for paper, analysis in all_papers %}
                <div class="paper-list-item"
                     :class="{ 'recommended': {{ 'true' if analysis.recommendation else 'false' }} }"
                     x-show="paperVisible('{{ paper.title }}', '{{ paper.authors|join(' ') }}', '{{ paper.category }}', '{{ paper.source.value }}', {{ analysis.relevance_score }}, {{ 'true' if analysis.recommendation else 'false' }})"
                     x-init="visibleCount++">
                    <div class="list-item-score">
                        <div class="score-circle" style="background: linear-gradient(135deg, #4A90E2 {{ analysis.relevance_score * 10 }}%, #f0f0f0 {{ analysis.relevance_score * 10 }}%);">
                            <span>{{ "%.1f"|format(analysis.relevance_score) }}</span>
                        </div>
                        {% if analysis.recommendation %}
                        <div class="recommended-badge">✅</div>
                        {% endif %}
                    </div>
                    
                    <div class="list-item-content">
                        <h3><a href="paper_{{ paper.id }}.html">{{ paper.title }}</a></h3>
                        <p class="list-authors">{{ paper.authors[:5]|join(', ') }}{% if paper.authors|length > 5 %} et al.{% endif %}</p>
                        <p class="list-tldr">{{ analysis.tldr }}</p>
                        
                        <div class="list-meta">
                            <span class="meta-category" style="background-color: {{ categories[paper.category].color }}20; color: {{ categories[paper.category].color }};">
                                {{ categories[paper.category].display_name }}
                            </span>
                            <span class="meta-source">{{ paper.source.value|upper }}</span>
                            <span class="meta-date">{{ paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown' }}</span>
                            <button class="bookmark-btn-small" @click="toggleBookmark('{{ paper.id }}')" :title="isBookmarked('{{ paper.id }}') ? 'Remove bookmark' : 'Bookmark paper'">
                                <i class="fas fa-bookmark" x-show="!isBookmarked('{{ paper.id }}')"></i>
                                <i class="fas fa-bookmark" style="color: #4A90E2;" x-show="isBookmarked('{{ paper.id }}')"></i>
                            </button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div class="no-results" x-show="visibleCount === 0">
                <i class="fas fa-search"></i>
                <h3>No papers found</h3>
                <p>Try adjusting your search or filters</p>
            </div>
        </section>
    </main>
    
    <footer>
        <div class="container">
            <p>Quantum RSS Radar &copy; {{ current_year }} | AI-powered research tracking system</p>
            <p>Data updated daily via RSS feeds from arXiv, Nature, Science, APS, IEEE, ACM, and Springer</p>
        </div>
    </footer>
    
    <script>
        function app() {
            return {
                searchQuery: '',
                selectedCategory: '',
                selectedSource: '',
                sortBy: 'score',
                showRecommendedOnly: false,
                visibleCount: 0,
                bookmarks: JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]'),
                
                init() {
                    this.filterPapers();
                },
                
                paperVisible(title, authors, category, source, score, recommended) {
                    if (this.showRecommendedOnly && !recommended) return false;
                    if (this.selectedCategory && category !== this.selectedCategory) return false;
                    if (this.selectedSource && source !== this.selectedSource) return false;
                    
                    if (this.searchQuery) {
                        const query = this.searchQuery.toLowerCase();
                        const searchText = (title + ' ' + authors + ' ' + category + ' ' + source).toLowerCase();
                        return searchText.includes(query);
                    }
                    
                    return true;
                },
                
                filterPapers() {
                    this.visibleCount = 0;
                    // The actual filtering is done by x-show in template
                },
                
                isBookmarked(paperId) {
                    return this.bookmarks.includes(paperId);
                },
                
                toggleBookmark(paperId) {
                    const index = this.bookmarks.indexOf(paperId);
                    if (index === -1) {
                        this.bookmarks.push(paperId);
                    } else {
                        this.bookmarks.splice(index, 1);
                    }
                    localStorage.setItem('quantumRssBookmarks', JSON.stringify(this.bookmarks));
                }
            }
        }
    </script>
</body>
</html>""",
            
            "styles.css": """/* Quantum RSS Radar - Main Stylesheet */

:root {
    --primary-color: #4A90E2;
    --secondary-color: #7ED321;
    --accent-color: #F5A623;
    --danger-color: #D0021B;
    --light-color: #F8F9FA;
    --dark-color: #212529;
    --gray-color: #6C757D;
    --light-gray: #E9ECEF;
    --border-radius: 8px;
    --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --transition: all 0.3s ease;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    line-height: 1.6;
    color: var(--dark-color);
    background-color: #f5f7fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
header {
    background: linear-gradient(135deg, var(--primary-color), #2C6FB7);
    color: white;
    padding: 2rem 0;
    text-align: center;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

header h1 i {
    margin-right: 10px;
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 0.5rem;
}

.date {
    font-size: 0.9rem;
    opacity: 0.8;
}

/* Navigation */
nav {
    background-color: white;
    box-shadow: var(--box-shadow);
    position: sticky;
    top: 0;
    z-index: 1000;
}

nav ul {
    display: flex;
    list-style: none;
    padding: 1rem 0;
}

nav li {
    margin-right: 2rem;
}

nav a {
    text-decoration: none;
    color: var(--gray-color);
    font-weight: 500;
    display: flex;
    align-items: center;
    padding: 0.5rem 0;
    transition: var(--transition);
    border-bottom: 3px solid transparent;
}

nav a i {
    margin-right: 8px;
}

nav a:hover {
    color: var(--primary-color);
}

nav a.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
}

/* Main Content */
main {
    padding: 2rem 0;
}

/* Stats Section */
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
}

.stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    text-align: center;
    transition: var(--transition);
}

.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.stat-card h3 {
    color: var(--gray-color);
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}

.stat-card h3 i {
    margin-right: 8px;
}

.stat-number {
    font-size: 2.5rem;
    font-weight: bold;
    color: var(--primary-color);
}

.stat-date {
    font-size: 1.2rem;
    font-weight: bold;
    color: var(--primary-color);
}

/* Search Section */
.search-section {
    background: white;
    padding: 1.5rem;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    margin-bottom: 2rem;
}

.search-box {
    position: relative;
    margin-bottom: 1rem;
}

.search-box i {
    position: absolute;
    left: 1rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--gray-color);
}

.search-box input {
    width: 100%;
    padding: 0.8rem 1rem 0.8rem 3rem;
    border: 2px solid var(--light-gray);
    border-radius: var(--border-radius);
    font-size: 1rem;
    transition: var(--transition);
}

.search-box input:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.filter-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
}

.filter-controls select,
.filter-controls input[type="checkbox"] {
    padding: 0.5rem;
    border: 1px solid var(--light-gray);
    border-radius: var(--border-radius);
    background: white;
}

.filter-controls label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

/* Papers Grid */
.papers-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}

.paper-card {
    background: white;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    padding: 1.5rem;
    transition: var(--transition);
    border: 2px solid transparent;
}

.paper-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.paper-card.recommended {
    border-color: var(--secondary-color);
}

.paper-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    font-size: 0.9rem;
}

.paper-score {
    font-weight: bold;
    color: var(--accent-color);
}

.paper-badge {
    background-color: var(--secondary-color);
    color: white;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
}

.paper-source {
    color: var(--gray-color);
    font-size: 0.8rem;
}

.paper-title {
    font-size: 1.2rem;
    margin-bottom: 0.5rem;
    line-height: 1.4;
}

.paper-title a {
    color: var(--dark-color);
    text-decoration: none;
    transition: var(--transition);
}

.paper-title a:hover {
    color: var(--primary-color);
}

.paper-authors {
    color: var(--gray-color);
    font-size: 0.9rem;
    margin-bottom: 1rem;
}

.paper-tldr {
    margin-bottom: 1rem;
    color: var(--dark-color);
    line-height: 1.5;
}

.paper-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--light-gray);
}

.paper-category {
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
}

.paper-date {
    color: var(--gray-color);
    font-size: 0.9rem;
}

.bookmark-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
    color: var(--gray-color);
    transition: var(--transition);
    padding: 0.3rem;
}

.bookmark-btn:hover {
    color: var(--primary-color);
}

/* Categories */
.categories-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}

.category-card {
    background: white;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    padding: 1.5rem;
    border-left: 4px solid;
    transition: var(--transition);
}

.category-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.category-card h3 {
    font-size: 1.3rem;
    margin-bottom: 0.5rem;
}

.category-count {
    color: var(--gray-color);
    margin-bottom: 1rem;
}

.category-papers {
    list-style: none;
    margin-bottom: 1rem;
}

.category-papers li {
    margin-bottom: 0.8rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--light-gray);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.category-papers li:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
}

.category-papers a {
    color: var(--dark-color);
    text-decoration: none;
    flex: 1;
    transition: var(--transition);
}

.category-papers a:hover {
    color: var(--primary-color);
}

.paper-score-mini {
    background-color: var(--light-gray);
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    color: var(--accent-color);
}

.category-link {
    display: inline-block;
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
    transition: var(--transition);
}

.category-link:hover {
    text-decoration: underline;
}

/* Papers List */
.papers-list {
    background: white;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    padding: 1.5rem;
}

.papers-count {
    color: var(--gray-color);
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--light-gray);
}

.papers-count span {
    font-weight: bold;
    color: var(--primary-color);
}

.paper-list-item {
    display: flex;
    padding: 1.5rem;
    border-bottom: 1px solid var(--light-gray);
    transition: var(--transition);
}

.paper-list-item:last-child {
    border-bottom: none;
}

.paper-list-item:hover {
    background-color: var(--light-color);
}

.paper-list-item.recommended {
    background-color: rgba(126, 211, 33, 0.05);
    border-left: 3px solid var(--secondary-color);
}

.list-item-score {
    flex-shrink: 0;
    margin-right: 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.score-circle {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    margin-bottom: 0.5rem;
}

.recommended-badge {
    font-size: 0.8rem;
}

.list-item-content {
    flex: 1;
}

.list-item-content h3 {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}

.list-item-content h3 a {
    color: var(--dark-color);
    text-decoration: none;
    transition: var(--transition);
}

.list-item-content h3 a:hover {
    color: var(--primary-color);
}

.list-authors {
    color: var(--gray-color);
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.list-tldr {
    margin-bottom: 1rem;
    line-height: 1.5;
}

.list-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.meta-category {
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
}

.meta-source {
    color: var(--gray-color);
    font-size: 0.9rem;
}

.meta-date {
    color: var(--gray-color);
    font-size: 0.9rem;
}

.bookmark-btn-small {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--gray-color);
    transition: var(--transition);
    padding: 0.3rem;
}

.bookmark-btn-small:hover {
    color: var(--primary-color);
}

.no-results {
    text-align: center;
    padding: 3rem;
    color: var(--gray-color);
}

.no-results i {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: var(--light-gray);
}

/* Footer */
footer {
    background-color: var(--dark-color);
    color: white;
    padding: 2rem 0;
    text-align: center;
    margin-top: 3rem;
}

footer p {
    margin-bottom: 0.5rem;
    opacity: 0.8;
}

.footer-links {
    margin-top: 1rem;
}

.footer-links a {
    color: white;
    text-decoration: none;
    margin: 0 0.5rem;
    transition: var(--transition);
}

.footer-links a:hover {
    color: var(--primary-color);
}

/* Responsive Design */
@media (max-width: 768px) {
    .container {
        padding: 0 15px;
    }
    
    header h1 {
        font-size: 2rem;
    }
    
    nav ul {
        flex-direction: column;
        align-items: center;
    }
    
    nav li {
        margin-right: 0;
        margin-bottom: 0.5rem;
    }
    
    .stats {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .papers-grid {
        grid-template-columns: 1fr;
    }
    
    .categories-grid {
        grid-template-columns: 1fr;
    }
    
    .filter-controls {
        flex-direction: column;
        align-items: stretch;
    }
    
    .paper-list-item {
        flex-direction: column;
    }
    
    .list-item-score {
        margin-right: 0;
        margin-bottom: 1rem;
        flex-direction: row;
        justify-content: center;
        gap: 1rem;
    }
}

@media (max-width: 480px) {
    .stats {
        grid-template-columns: 1fr;
    }
    
    .stat-number {
        font-size: 2rem;
    }
}"""
        }
        
        for filename, content in default_templates.items():
            template_path = self.templates_dir / filename
            if not template_path.exists():
                template_path.write_text(content, encoding="utf-8")
                logger.debug(f"Created default template: {filename}")
    
    def build_website(self, 
                     papers_with_analyses: List[tuple[Paper, PaperAnalysis]],
                     categories: Dict[str, CategoryConfig],
                     top_n: int = 10):
        """
        Build complete static website.
        
        Args:
            papers_with_analyses: List of (paper, analysis) tuples
            categories: Category configurations
            top_n: Number of top papers to feature on homepage
        """
        logger.info(f"Building website in {self.web_dir}")
        
        # Clear and create web directory
        if self.web_dir.exists():
            shutil.rmtree(self.web_dir)
        self.web_dir.mkdir(parents=True)
        
        # Create subdirectories
        (self.web_dir / "css").mkdir()
        (self.web_dir / "js").mkdir()
        (self.web_dir / "assets").mkdir()
        
        # Prepare data for templates
        context = self._prepare_template_context(papers_with_analyses, categories, top_n)
        
        # Generate main pages
        self._generate_main_pages(context)
        
        # Generate individual paper pages
        self._generate_paper_pages(papers_with_analyses, categories, context)
        
        # Generate category pages
        self._generate_category_pages(papers_with_analyses, categories, context)
        
        # Copy static assets
        self._copy_static_assets()
        
        logger.info(f"Website built successfully in {self.web_dir}")
    
    def _prepare_template_context(self, papers_with_analyses, categories, top_n):
        """Prepare context data for templates."""
        # Group papers by category
        papers_by_category = {}
        for paper, analysis in papers_with_analyses:
            if paper.category not in papers_by_category:
                papers_by_category[paper.category] = []
            papers_by_category[paper.category].append((paper, analysis))
        
        # Sort papers in each category by score
        for cat in papers_by_category:
            papers_by_category[cat].sort(key=lambda x: x[1].relevance_score, reverse=True)
        
        # Get top papers (sorted by score)
        top_papers = sorted(papers_with_analyses, 
                          key=lambda x: x[1].relevance_score, 
                          reverse=True)[:top_n]
        
        # Count recommended papers
        recommended_papers = sum(1 for _, analysis in papers_with_analyses if analysis.recommendation)
        
        return {
            "all_papers": papers_with_analyses,
            "top_papers": top_papers,
            "papers_by_category": papers_by_category,
            "categories": categories,
            "total_papers": len(papers_with_analyses),
            "recommended_papers": recommended_papers,
            "total_categories": len(papers_by_category),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_year": datetime.now().year
        }
    
    def _generate_main_pages(self, context):
        """Generate main HTML pages."""
        # Index page
        template = self.env.get_template("index.html")
        html = template.render(**context)
        (self.web_dir / "index.html").write_text(html, encoding="utf-8")
        
        # Papers page
        papers_context = context.copy()
        papers_context["active_page"] = "papers"
        template = self.env.get_template("papers.html")
        html = template.render(**papers_context)
        (self.web_dir / "papers.html").write_text(html, encoding="utf-8")
        
        # Recommended page (filtered)
        recommended_papers = [(p, a) for p, a in context["all_papers"] if a.recommendation]
        recommended_context = context.copy()
        recommended_context["all_papers"] = recommended_papers
        recommended_context["total_papers"] = len(recommended_papers)
        recommended_context["active_page"] = "recommended"
        
        template = self.env.get_template("papers.html")
        html = template.render(**recommended_context)
        (self.web_dir / "recommended.html").write_text(html, encoding="utf-8")
        
        # Categories page
        self._generate_categories_page(context)
    
    def _generate_categories_page(self, context):
        """Generate categories overview page."""
        categories_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Categories - Quantum RSS Radar</title>
            <!-- Theme initialization to prevent flash -->
            <script>
                (function() {
                    const theme = localStorage.getItem('theme') || 'light';
                    document.documentElement.setAttribute('data-theme', theme);
                })();
            </script>
            <link rel="stylesheet" href="css/styles.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        </head>
        <body x-data="app()">
            <header>
                <div class="container header-container">
                    <div class="header-left">
                        <h1><i class="fa-solid fa-satellite-dish"></i> Quantum RSS Radar</h1>
                        <p class="subtitle">AI-assisted daily academic research tracking</p>
                    </div>
                    <div class="header-right">
                        <div class="header-controls">
                            <button class="theme-toggle" @click="toggleTheme()" :title="theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'">
                                <i class="fas" :class="theme === 'light' ? 'fa-moon' : 'fa-sun'"></i>
                            </button>
                            <p class="date">Last updated: """ + context["last_updated"] + """</p>
                        </div>
                    </div>
                </div>
            </header>
            
            <nav>
                <div class="container">
                    <ul>
                        <li><a href="index.html"><i class="fas fa-home"></i> Home</a></li>
                        <li><a href="papers.html"><i class="fas fa-file-alt"></i> All Papers</a></li>
                        <li><a href="recommended.html"><i class="fas fa-star"></i> Recommended</a></li>
                        <li><a href="categories.html" class="active"><i class="fas fa-tags"></i> Categories</a></li>
                    </ul>
                </div>
            </nav>
            
            <main class="container">
                <section class="categories">
                    <h2><i class="fas fa-tags"></i> All Research Categories</h2>
                    <p>Browse papers by research category. Click on any category to see all papers in that area.</p>
                    
                    <div class="categories-grid">
        """
        
        for category_id, category in context["categories"].items():
            papers_in_category = context["papers_by_category"].get(category_id, [])
            if papers_in_category:
                categories_html += f"""
                        <div class="category-card" style="border-left-color: {category.color};">
                            <h3 style="color: {category.color};"><i class="fas fa-folder"></i> {category.display_name}</h3>
                            <p class="category-count">{len(papers_in_category)} papers</p>
                            <ul class="category-papers">
                """
                
                for paper, analysis in papers_in_category[:3]:
                    categories_html += f"""
                                <li>
                                    <a href="paper_{paper.id}.html">{paper.title[:60]}{'...' if len(paper.title) > 60 else ''}</a>
                                    <span class="paper-score-mini">⭐ {analysis.relevance_score:.1f}</span>
                                </li>
                    """
                
                categories_html += f"""
                            </ul>
                            <a href="category_{category_id}.html" class="category-link">View all {len(papers_in_category)} papers →</a>
                        </div>
                """
        
        categories_html += """
                    </div>
                </section>
            </main>
            
            <footer>
                <div class="container">
                    <p>Quantum RSS Radar &copy; """ + str(context["current_year"]) + """ | AI-powered research tracking system</p>
                    <p>Data updated daily via RSS feeds from arXiv, Nature, Science, APS, IEEE, ACM, and Springer</p>
                </div>
            </footer>
            
            <script>
                function app() {
                    return {
                        theme: localStorage.getItem('theme') || 'light',
                        
                        init() {
                            // Apply theme immediately
                            document.documentElement.setAttribute('data-theme', this.theme);
                        },
                        
                        applyTheme() {
                            document.documentElement.setAttribute('data-theme', this.theme);
                            localStorage.setItem('theme', this.theme);
                        },
                        
                        toggleTheme() {
                            this.theme = this.theme === 'light' ? 'dark' : 'light';
                            this.applyTheme();
                        }
                    }
                }
            </script>
        </body>
        </html>
        """
        
        (self.web_dir / "categories.html").write_text(categories_html, encoding="utf-8")
    
    def _generate_paper_pages(self, papers_with_analyses, categories, context):
        """Generate individual paper detail pages."""
        for paper, analysis in papers_with_analyses:
            category = categories.get(paper.category, CategoryConfig(
                display_name=paper.category, 
                color="#000000", 
                priority=999
            ))
            
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{paper.title} - Quantum RSS Radar</title>
                <link rel="stylesheet" href="css/styles.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
            </head>
            <body x-data="{{ bookmarked: localStorage.getItem('quantumRssBookmarks') ? JSON.parse(localStorage.getItem('quantumRssBookmarks')).includes('{paper.id}') : false }}">
                <header>
                    <div class="container">
                        <h1><i class="fa-solid fa-satellite-dish"></i> Quantum RSS Radar</h1>
                        <p class="subtitle">Research Paper Details</p>
                        <p class="date">Last updated: {context['last_updated']}</p>
                    </div>
                </header>
                
                <nav>
                    <div class="container">
                        <ul>
                            <li><a href="index.html"><i class="fas fa-home"></i> Home</a></li>
                            <li><a href="papers.html"><i class="fas fa-file-alt"></i> All Papers</a></li>
                            <li><a href="recommended.html"><i class="fas fa-star"></i> Recommended</a></li>
                            <li><a href="categories.html"><i class="fas fa-tags"></i> Categories</a></li>
                        </ul>
                    </div>
                </nav>
                
                <main class="container">
                    <article class="paper-detail">
                        <div class="paper-detail-header">
                            <div class="paper-meta">
                                <span class="paper-score-large">⭐ {analysis.relevance_score:.1f}/10</span>
                                {'<span class="paper-badge-large">RECOMMENDED</span>' if analysis.recommendation else ''}
                                <span class="paper-source-large">{paper.source.value.upper()}</span>
                                <span class="paper-category-large" style="background-color: {category.color}20; color: {category.color};">
                                    {category.display_name}
                                </span>
                                <span class="paper-date-large">
                                    <i class="fas fa-calendar-alt"></i> {paper.published.strftime('%B %d, %Y') if paper.published else 'Unknown'}
                                </span>
                                <button class="bookmark-btn-large" @click="toggleBookmark()" :title="bookmarked ? 'Remove bookmark' : 'Bookmark paper'">
                                    <i class="fas fa-bookmark" x-show="!bookmarked"></i>
                                    <i class="fas fa-bookmark" style="color: #4A90E2;" x-show="bookmarked"></i>
                                    <span x-text="bookmarked ? 'Bookmarked' : 'Bookmark'"></span>
                                </button>
                            </div>
                            
                            <h1 class="paper-title-large">{paper.title}</h1>
                            
                            <div class="paper-authors-large">
                                <i class="fas fa-users"></i>
                                {', '.join(paper.authors)}
                            </div>
                            
                            <a href="{paper.link}" class="paper-link-btn" target="_blank" rel="noopener noreferrer">
                                <i class="fas fa-external-link-alt"></i> Read Full Paper
                            </a>
                        </div>
                        
                        <div class="paper-detail-content">
                            <section class="paper-summary">
                                <h2><i class="fas fa-clipboard-list"></i> AI Summary</h2>
                                
                                <div class="summary-section">
                                    <h3>TL;DR</h3>
                                    <p>{analysis.tldr}</p>
                                </div>
                                
                                <div class="summary-section">
                                    <h3>Motivation</h3>
                                    <p>{analysis.motivation}</p>
                                </div>
                                
                                <div class="summary-section">
                                    <h3>Method</h3>
                                    <p>{analysis.method}</p>
                                </div>
                                
                                <div class="summary-section">
                                    <h3>Result</h3>
                                    <p>{analysis.result}</p>
                                </div>
                                
                                <div class="summary-section">
                                    <h3>Conclusion</h3>
                                    <p>{analysis.conclusion}</p>
                                </div>
                                
                                {('<div class="summary-section"><h3>Keywords</h3><div class="keywords">' + ', '.join(f'<span class="keyword-tag">{k}</span>' for k in analysis.keywords) + '</div></div>') if analysis.keywords else ''}
                            </section>
                            
                            <section class="paper-abstract">
                                <h2><i class="fas fa-file-alt"></i> Abstract</h2>
                                <div class="abstract-content">
                                    {paper.abstract}
                                </div>
                            </section>
                            
                            <section class="paper-metadata">
                                <h2><i class="fas fa-info-circle"></i> Metadata</h2>
                                <div class="metadata-grid">
                                    <div class="metadata-item">
                                        <strong>Paper ID:</strong> {paper.id}
                                    </div>
                                    <div class="metadata-item">
                                        <strong>Source Feed:</strong> {paper.feed_name}
                                    </div>
                                    <div class="metadata-item">
                                        <strong>Publication Date:</strong> {paper.published.strftime('%Y-%m-%d %H:%M:%S') if paper.published else 'Unknown'}
                                    </div>
                                    <div class="metadata-item">
                                        <strong>Analysis Date:</strong> {analysis.processing_time.strftime('%Y-%m-%d %H:%M:%S') if analysis.processing_time else 'Unknown'}
                                    </div>
                                    <div class="metadata-item">
                                        <strong>Recommendation:</strong> {'✅ Yes' if analysis.recommendation else '❌ No'}
                                    </div>
                                </div>
                            </section>
                        </div>
                    </article>
                </main>
                
                <footer>
                    <div class="container">
                        <p>Quantum RSS Radar &copy; {context['current_year']} | AI-powered research tracking system</p>
                        <p>Data updated daily via RSS feeds from arXiv, Nature, Science, APS, IEEE, ACM, and Springer</p>
                    </div>
                </footer>
                
                <script>
                    function toggleBookmark() {{
                        this.bookmarked = !this.bookmarked;
                        let bookmarks = JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]');
                        const index = bookmarks.indexOf('{paper.id}');
                        
                        if (this.bookmarked && index === -1) {{
                            bookmarks.push('{paper.id}');
                        }} else if (!this.bookmarked && index !== -1) {{
                            bookmarks.splice(index, 1);
                        }}
                        
                        localStorage.setItem('quantumRssBookmarks', JSON.stringify(bookmarks));
                    }}
                </script>
                
                <style>
                    .paper-detail {{
                        background: white;
                        border-radius: var(--border-radius);
                        box-shadow: var(--box-shadow);
                        padding: 2rem;
                    }}
                    
                    .paper-detail-header {{
                        border-bottom: 2px solid var(--light-gray);
                        padding-bottom: 2rem;
                        margin-bottom: 2rem;
                    }}
                    
                    .paper-meta {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 1rem;
                        align-items: center;
                        margin-bottom: 1rem;
                    }}
                    
                    .paper-score-large {{
                        font-size: 1.5rem;
                        font-weight: bold;
                        color: var(--accent-color);
                    }}
                    
                    .paper-badge-large {{
                        background-color: var(--secondary-color);
                        color: white;
                        padding: 0.5rem 1rem;
                        border-radius: 20px;
                        font-weight: bold;
                    }}
                    
                    .paper-source-large {{
                        background-color: var(--light-gray);
                        padding: 0.5rem 1rem;
                        border-radius: 20px;
                        font-weight: 500;
                    }}
                    
                    .paper-category-large {{
                        padding: 0.5rem 1rem;
                        border-radius: 20px;
                        font-weight: 500;
                    }}
                    
                    .paper-date-large {{
                        color: var(--gray-color);
                    }}
                    
                    .bookmark-btn-large {{
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                        background: none;
                        border: 2px solid var(--light-gray);
                        padding: 0.5rem 1rem;
                        border-radius: var(--border-radius);
                        cursor: pointer;
                        transition: var(--transition);
                    }}
                    
                    .bookmark-btn-large:hover {{
                        border-color: var(--primary-color);
                        color: var(--primary-color);
                    }}
                    
                    .paper-title-large {{
                        font-size: 2rem;
                        line-height: 1.3;
                        margin-bottom: 1rem;
                    }}
                    
                    .paper-authors-large {{
                        font-size: 1.1rem;
                        color: var(--gray-color);
                        margin-bottom: 2rem;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }}
                    
                    .paper-link-btn {{
                        display: inline-flex;
                        align-items: center;
                        gap: 0.5rem;
                        background-color: var(--primary-color);
                        color: white;
                        text-decoration: none;
                        padding: 0.8rem 1.5rem;
                        border-radius: var(--border-radius);
                        font-weight: 500;
                        transition: var(--transition);
                    }}
                    
                    .paper-link-btn:hover {{
                        background-color: #2C6FB7;
                        transform: translateY(-2px);
                    }}
                    
                    .paper-detail-content {{
                        display: grid;
                        gap: 2rem;
                    }}
                    
                    .paper-summary, .paper-abstract, .paper-metadata {{
                        padding: 1.5rem;
                        border-radius: var(--border-radius);
                        background-color: var(--light-color);
                    }}
                    
                    .paper-summary h2, .paper-abstract h2, .paper-metadata h2 {{
                        margin-bottom: 1rem;
                        color: var(--primary-color);
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }}
                    
                    .summary-section {{
                        margin-bottom: 1.5rem;
                    }}
                    
                    .summary-section:last-child {{
                        margin-bottom: 0;
                    }}
                    
                    .summary-section h3 {{
                        color: var(--dark-color);
                        margin-bottom: 0.5rem;
                        font-size: 1.1rem;
                    }}
                    
                    .keywords {{
                        display: flex;
                        flex-wrap: wrap;
                        gap: 0.5rem;
                    }}
                    
                    .keyword-tag {{
                        background-color: white;
                        padding: 0.3rem 0.8rem;
                        border-radius: 20px;
                        font-size: 0.9rem;
                        border: 1px solid var(--light-gray);
                    }}
                    
                    .abstract-content {{
                        line-height: 1.6;
                        white-space: pre-line;
                    }}
                    
                    .metadata-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                        gap: 1rem;
                    }}
                    
                    .metadata-item {{
                        padding: 0.8rem;
                        background: white;
                        border-radius: var(--border-radius);
                    }}
                    
                    @media (max-width: 768px) {{
                        .paper-meta {{
                            flex-direction: column;
                            align-items: flex-start;
                        }}
                        
                        .paper-title-large {{
                            font-size: 1.5rem;
                        }}
                        
                        .metadata-grid {{
                            grid-template-columns: 1fr;
                        }}
                    }}
                </style>
            </body>
            </html>
            """
            
            (self.web_dir / f"paper_{paper.id}.html").write_text(html, encoding="utf-8")
        
        logger.info(f"Generated {len(papers_with_analyses)} individual paper pages")
    
    def _generate_category_pages(self, papers_with_analyses, categories, context):
        """Generate category-specific pages."""
        papers_by_category = context["papers_by_category"]
        
        for category_id, category_papers in papers_by_category.items():
            category = categories.get(category_id, CategoryConfig(
                display_name=category_id,
                color="#000000",
                priority=999
            ))
            
            # Sort papers in this category by score
            category_papers_sorted = sorted(category_papers, 
                                          key=lambda x: x[1].relevance_score, 
                                          reverse=True)
            
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{category.display_name} - Quantum RSS Radar</title>
                <link rel="stylesheet" href="css/styles.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
                <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
            </head>
            <body x-data="app()">
                <header>
                    <div class="container">
                        <h1><i class="fa-solid fa-satellite-dish"></i> Quantum RSS Radar</h1>
                        <p class="subtitle">{category.display_name} Research Papers</p>
                        <p class="date">Last updated: {context['last_updated']}</p>
                    </div>
                </header>
                
                <nav>
                    <div class="container">
                        <ul>
                            <li><a href="index.html"><i class="fas fa-home"></i> Home</a></li>
                            <li><a href="papers.html"><i class="fas fa-file-alt"></i> All Papers</a></li>
                            <li><a href="recommended.html"><i class="fas fa-star"></i> Recommended</a></li>
                            <li><a href="categories.html"><i class="fas fa-tags"></i> Categories</a></li>
                        </ul>
                    </div>
                </nav>
                
                <main class="container">
                    <section class="category-header-section" style="border-left-color: {category.color};">
                        <h1><i class="fas fa-folder"></i> {category.display_name}</h1>
                        <p class="category-description">
                            {len(category_papers)} research papers in this category. 
                            Color: <span class="color-sample" style="background-color: {category.color};"></span> {category.color}
                        </p>
                        
                        <div class="category-stats-large">
                            <div class="stat-large">
                                <div class="stat-number-large">{len(category_papers)}</div>
                                <div class="stat-label">Total Papers</div>
                            </div>
                            <div class="stat-large">
                                <div class="stat-number-large">{sum(1 for _, analysis in category_papers if analysis.recommendation)}</div>
                                <div class="stat-label">Recommended</div>
                            </div>
                            <div class="stat-large">
                                <div class="stat-number-large">{sum(analysis.relevance_score for _, analysis in category_papers) / len(category_papers):.1f}</div>
                                <div class="stat-label">Avg Score</div>
                            </div>
                        </div>
                    </section>
                    
                    <section class="search-section">
                        <div class="search-box">
                            <i class="fas fa-search"></i>
                            <input type="text" 
                                   placeholder="Search {len(category_papers)} papers in {category.display_name}..." 
                                   x-model="searchQuery"
                                   @input="filterPapers()">
                        </div>
                        <div class="filter-controls">
                            <select x-model="selectedSource" @change="filterPapers()">
                                <option value="">All Sources</option>
                                <option value="arxiv">arXiv</option>
                                <option value="nature">Nature</option>
                                <option value="science">Science</option>
                                <option value="aps">APS</option>
                                <option value="ieee">IEEE</option>
                                <option value="acm">ACM</option>
                                <option value="springer">Springer</option>
                            </select>
                            <label>
                                <input type="checkbox" x-model="showRecommendedOnly" @change="filterPapers()">
                                Show recommended only
                            </label>
                        </div>
                    </section>
                    
                    <section class="papers-list">
                        <div class="papers-count">
                            Showing <span x-text="visibleCount"></span> of {len(category_papers)} papers in {category.display_name}
                        </div>
                        
                        <div class="papers-container">
            """
            
            for paper, analysis in category_papers_sorted:
                html += f"""
                            <div class="paper-list-item"
                                 :class="{{ 'recommended': {'true' if analysis.recommendation else 'false'} }}"
                                 x-show="paperVisible('{paper.title}', '{" ".join(paper.authors)}', '{paper.source.value}', {analysis.relevance_score}, {'true' if analysis.recommendation else 'false'})"
                                 x-init="visibleCount++">
                                <div class="list-item-score">
                                    <div class="score-circle" style="background: linear-gradient(135deg, {category.color} {analysis.relevance_score * 10}%, #f0f0f0 {analysis.relevance_score * 10}%);">
                                        <span>{analysis.relevance_score:.1f}</span>
                                    </div>
                                    {'<div class="recommended-badge">✅</div>' if analysis.recommendation else ''}
                                </div>
                                
                                <div class="list-item-content">
                                    <h3><a href="paper_{paper.id}.html">{paper.title}</a></h3>
                                    <p class="list-authors">{', '.join(paper.authors[:5])}{' et al.' if len(paper.authors) > 5 else ''}</p>
                                    <p class="list-tldr">{analysis.tldr}</p>
                                    
                                    <div class="list-meta">
                                        <span class="meta-source">{paper.source.value.upper()}</span>
                                        <span class="meta-date">{paper.published.strftime('%b %d, %Y') if paper.published else 'Unknown'}</span>
                                        <button class="bookmark-btn-small" @click="toggleBookmark('{paper.id}')" :title="isBookmarked('{paper.id}') ? 'Remove bookmark' : 'Bookmark paper'">
                                            <i class="fas fa-bookmark" x-show="!isBookmarked('{paper.id}')"></i>
                                            <i class="fas fa-bookmark" style="color: #4A90E2;" x-show="isBookmarked('{paper.id}')"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                """
            
            html += """
                        </div>
                        
                        <div class="no-results" x-show="visibleCount === 0">
                            <i class="fas fa-search"></i>
                            <h3>No papers found</h3>
                            <p>Try adjusting your search or filters</p>
                        </div>
                    </section>
                </main>
                
                <footer>
                    <div class="container">
                        <p>Quantum RSS Radar &copy; """ + str(context['current_year']) + """ | AI-powered research tracking system</p>
                        <p>Data updated daily via RSS feeds from arXiv, Nature, Science, APS, IEEE, ACM, and Springer</p>
                    </div>
                </footer>
                
                <script>
                    function app() {
                        return {
                            searchQuery: '',
                            selectedSource: '',
                            showRecommendedOnly: false,
                            visibleCount: 0,
                            bookmarks: JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]'),
                            
                            init() {
                                this.filterPapers();
                            },
                            
                            paperVisible(title, authors, source, score, recommended) {
                                if (this.showRecommendedOnly && !recommended) return false;
                                if (this.selectedSource && source !== this.selectedSource) return false;
                                
                                if (this.searchQuery) {
                                    const query = this.searchQuery.toLowerCase();
                                    const searchText = (title + ' ' + authors + ' ' + source).toLowerCase();
                                    return searchText.includes(query);
                                }
                                
                                return true;
                            },
                            
                            filterPapers() {
                                this.visibleCount = 0;
                            },
                            
                            isBookmarked(paperId) {
                                return this.bookmarks.includes(paperId);
                            },
                            
                            toggleBookmark(paperId) {
                                const index = this.bookmarks.indexOf(paperId);
                                if (index === -1) {
                                    this.bookmarks.push(paperId);
                                } else {
                                    this.bookmarks.splice(index, 1);
                                }
                                localStorage.setItem('quantumRssBookmarks', JSON.stringify(this.bookmarks));
                            }
                        }
                    }
                </script>
                
                <style>
                    .category-header-section {
                        background: white;
                        border-radius: var(--border-radius);
                        box-shadow: var(--box-shadow);
                        padding: 2rem;
                        margin-bottom: 2rem;
                        border-left: 6px solid;
                    }
                    
                    .category-header-section h1 {
                        color: """ + category.color + """;
                        margin-bottom: 1rem;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }
                    
                    .category-description {
                        color: var(--gray-color);
                        margin-bottom: 2rem;
                    }
                    
                    .color-sample {
                        display: inline-block;
                        width: 20px;
                        height: 20px;
                        border-radius: 4px;
                        vertical-align: middle;
                        margin: 0 5px;
                    }
                    
                    .category-stats-large {
                        display: grid;
                        grid-template-columns: repeat(3, 1fr);
                        gap: 2rem;
                    }
                    
                    .stat-large {
                        text-align: center;
                    }
                    
                    .stat-number-large {
                        font-size: 3rem;
                        font-weight: bold;
                        color: """ + category.color + """;
                        line-height: 1;
                    }
                    
                    .stat-label {
                        color: var(--gray-color);
                        font-size: 0.9rem;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-top: 0.5rem;
                    }
                </style>
            </body>
            </html>
            """
            
            (self.web_dir / f"category_{category_id}.html").write_text(html, encoding="utf-8")
        
        logger.info(f"Generated {len(papers_by_category)} category pages")
    
    def _copy_static_assets(self):
        """Copy static assets to web directory."""
        # Copy CSS
        css_content = (self.templates_dir / "styles.css").read_text(encoding="utf-8")
        (self.web_dir / "css" / "styles.css").write_text(css_content, encoding="utf-8")
        
        # Create JavaScript files
        js_files = {
            "search.js": """
// Search functionality for Quantum RSS Radar
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('.search-box input');
    const paperCards = document.querySelectorAll('.paper-card, .paper-list-item');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
            paperCards.forEach(card => {
                const title = card.querySelector('.paper-title, h3 a').textContent.toLowerCase();
                const authors = card.querySelector('.paper-authors, .list-authors')?.textContent.toLowerCase() || '';
                const abstract = card.querySelector('.paper-tldr, .list-tldr')?.textContent.toLowerCase() || '';
                
                const searchText = title + ' ' + authors + ' ' + abstract;
                
                if (searchText.includes(query)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }
});
            """,
            
            "bookmarks.js": """
// Bookmark functionality for Quantum RSS Radar
const BOOKMARKS_KEY = 'quantumRssBookmarks';

function getBookmarks() {
    return JSON.parse(localStorage.getItem(BOOKMARKS_KEY) || '[]');
}

function saveBookmarks(bookmarks) {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
}

function toggleBookmark(paperId) {
    const bookmarks = getBookmarks();
    const index = bookmarks.indexOf(paperId);
    
    if (index === -1) {
        bookmarks.push(paperId);
    } else {
        bookmarks.splice(index, 1);
    }
    
    saveBookmarks(bookmarks);
    updateBookmarkUI(paperId);
    return bookmarks.includes(paperId);
}

function isBookmarked(paperId) {
    return getBookmarks().includes(paperId);
}

function updateBookmarkUI(paperId) {
    const buttons = document.querySelectorAll(`[data-paper-id="${paperId}"]`);
    const isBooked = isBookmarked(paperId);
    
    buttons.forEach(button => {
        const icon = button.querySelector('i');
        if (icon) {
            if (isBooked) {
                icon.className = 'fas fa-bookmark';
                icon.style.color = '#4A90E2';
                button.title = 'Remove bookmark';
            } else {
                icon.className = 'fas fa-bookmark';
                icon.style.color = '';
                button.title = 'Bookmark paper';
            }
        }
    });
}

// Initialize bookmark buttons
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.bookmark-btn, .bookmark-btn-small').forEach(button => {
        const paperId = button.getAttribute('data-paper-id');
        if (paperId) {
            updateBookmarkUI(paperId);
            
            button.addEventListener('click', function() {
                toggleBookmark(paperId);
            });
        }
    });
});
            """
        }
        
        for filename, content in js_files.items():
            (self.web_dir / "js" / filename).write_text(content, encoding="utf-8")
        
        logger.info("Copied static assets to web directory")