// Main application for Quantum RSS Radar Jekyll site
// Alpine.js reactive data and functionality

function app() {
    return {
        // Data
        searchQuery: '',
        selectedCategory: '',
        selectedSource: '',
        showOnlyRecommended: false,
        sortBy: 'score',
        showCalendar: false,
        selectedDate: '',
        theme: localStorage.getItem('theme') || 'light',
        
        // Papers data
        allPapers: [],
        categories: {},
        
        // Computed properties
        get filteredPapers() {
            let papers = [...this.allPapers];
            
            // Apply filters
            if (this.selectedCategory) {
                papers = papers.filter(p => p.category === this.selectedCategory);
            }
            
            if (this.selectedSource) {
                papers = papers.filter(p => p.source === this.selectedSource);
            }
            
            if (this.showOnlyRecommended) {
                papers = papers.filter(p => p.recommended);
            }
            
            if (this.selectedDate) {
                papers = papers.filter(p => this.matchDate(p.published_date, this.selectedDate));
            }
            
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                papers = papers.filter(p => 
                    p.title.toLowerCase().includes(query) ||
                    p.authors.some(a => a.toLowerCase().includes(query)) ||
                    p.abstract.toLowerCase().includes(query) ||
                    (p.analysis.tldr && p.analysis.tldr.toLowerCase().includes(query))
                );
            }
            
            // Apply sorting
            papers.sort((a, b) => {
                switch (this.sortBy) {
                    case 'score':
                        return b.score - a.score;
                    case 'date':
                        return new Date(b.date) - new Date(a.date);
                    case 'title':
                        return a.title.localeCompare(b.title);
                    default:
                        return b.score - a.score;
                }
            });
            
            return papers;
        },
        
        get recommendedPapers() {
            return this.filteredPapers.filter(p => p.recommended);
        },
        
        // Bookmarks
        get bookmarks() {
            return JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]');
        },
        
        // Modal
        modalOpen: false,
        modalPaper: null,
        
        // Initialization
        init() {
            // Load papers data from Jekyll data files
            if (window.siteData && window.siteData.papers) {
                this.allPapers = window.siteData.papers.papers || [];
                this.categories = window.siteData.papers.categories || {};
            }
            
            // Set initial theme
            document.documentElement.setAttribute('data-theme', this.theme);
            
            console.log(`Loaded ${this.allPapers.length} papers`);
        },
        
        // Theme toggle
        toggleTheme() {
            this.theme = this.theme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', this.theme);
            localStorage.setItem('theme', this.theme);
        },
        
        // Calendar functions
        toggleCalendar() {
            this.showCalendar = !this.showCalendar;
        },
        
        filterByDate() {
            this.filterPapers();
        },
        
        setDate(range) {
            const today = new Date();
            
            switch(range) {
                case 'today':
                    this.selectedDate = today.toISOString().split('T')[0];
                    break;
                case 'yesterday':
                    const yesterday = new Date(today);
                    yesterday.setDate(yesterday.getDate() - 1);
                    this.selectedDate = yesterday.toISOString().split('T')[0];
                    break;
                case 'last_3_days':
                    const threeDaysAgo = new Date(today);
                    threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
                    this.selectedDate = threeDaysAgo.toISOString().split('T')[0];
                    break;
                case 'last_7_days':
                    const weekAgo = new Date(today);
                    weekAgo.setDate(weekAgo.getDate() - 7);
                    this.selectedDate = weekAgo.toISOString().split('T')[0];
                    break;
                case 'this_month':
                    this.selectedDate = today.toISOString().slice(0, 7);
                    break;
                case '':
                    this.selectedDate = '';
                    break;
            }
            
            this.filterByDate();
        },
        
        // Paper filtering and sorting
        filterPapers() {
            // Reactivity handled by computed properties
        },
        
        sortPapers() {
            // Reactivity handled by computed properties
        },
        
        // Improved date filtering logic
        matchDate(paperDate, filterDate) {
            if (!filterDate) return true;
            
            const paperDateObj = new Date(paperDate);
            const filterDateObj = new Date(filterDate);
            
            // Check if filterDate is just YYYY-MM (month)
            if (filterDate.length === 7 && filterDate[4] === '-' && filterDate[6] === '-') {
                // Month filter: compare year and month
                return paperDateObj.getFullYear() === filterDateObj.getFullYear() &&
                       paperDateObj.getMonth() === filterDateObj.getMonth();
            }
            
            // Check if filterDate is YYYY-MM-DD (full date)
            if (filterDate.length === 10 && filterDate[4] === '-' && filterDate[7] === '-') {
                // Full date filter
                return paperDateObj.toISOString().split('T')[0] === filterDate;
            }
            
            // Default: try string contains
            return paperDate.includes(filterDate);
        },
        
        // Category helpers
        getCategoryName(categoryId) {
            return this.categories[categoryId]?.name || categoryId;
        },
        
        categoryStyle(categoryId) {
            const category = this.categories[categoryId];
            if (category && category.color) {
                return {
                    'background-color': `${category.color}20`,
                    'color': category.color,
                    'border': `1px solid ${category.color}`
                };
            }
            return {};
        },
        
        // Date formatting
        formatDate(dateString) {
            if (!dateString) return 'Unknown';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        },
        
        // Bookmark functions
        isBookmarked(paper) {
            return this.bookmarks.includes(paper.id);
        },
        
        toggleBookmark(paper) {
            let bookmarks = this.bookmarks;
            const index = bookmarks.indexOf(paper.id);
            
            if (index === -1) {
                bookmarks.push(paper.id);
            } else {
                bookmarks.splice(index, 1);
            }
            
            localStorage.setItem('quantumRssBookmarks', JSON.stringify(bookmarks));
            
            // Force Alpine.js to re-evaluate
            this.bookmarks = bookmarks;
        },
        
        // Modal functions
        openModal(paper) {
            this.modalPaper = paper;
            this.modalOpen = true;
            document.body.style.overflow = 'hidden';
        },
        
        closeModal() {
            this.modalOpen = false;
            this.modalPaper = null;
            document.body.style.overflow = '';
        },
        
        // Helper for external links
        openLink(url) {
            window.open(url, '_blank');
        }
    };
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Load papers data from Jekyll if available
    if (typeof siteData === 'undefined') {
        // Try to load from Jekyll data file
        fetch('/assets/js/data.json')
            .then(response => response.json())
            .then(data => {
                window.siteData = data;
            })
            .catch(error => {
                console.log('Could not load papers data:', error);
                window.siteData = { papers: { papers: [], categories: {}, stats: {} } };
            });
    }
    
    // Bookmark initialization
    function initBookmarks() {
        const bookmarks = JSON.parse(localStorage.getItem('quantumRssBookmarks') || '[]');
        
        // Update bookmark button states
        document.querySelectorAll('.bookmark-btn, .bookmark-btn-small').forEach(button => {
            const paperId = button.getAttribute('data-paper-id');
            if (paperId) {
                const isBookmarked = bookmarks.includes(paperId);
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = isBookmarked ? 'fas fa-bookmark' : 'far fa-bookmark';
                    icon.style.color = isBookmarked ? '#4A90E2' : '';
                    button.title = isBookmarked ? 'Remove bookmark' : 'Bookmark paper';
                }
            }
        });
    }
    
    initBookmarks();
    
    // Theme initialization
    (function() {
        const theme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    })();
    
    // Calendar date input - set max to today
    const dateInput = document.querySelector('input[type="date"]');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.max = today;
    }
});

// Export for module usage (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { app };
}