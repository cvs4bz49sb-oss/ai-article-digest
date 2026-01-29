"""Configuration settings for the Article Digest Generator."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Scraping Configuration
DEFAULT_ARTICLE_COUNT = 10
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# User agent for web requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Summary constraints
MAX_SUMMARY_WORDS = 50

# Common article selectors for different website structures
# These can be customized per website
ARTICLE_SELECTORS = {
    "default": {
        "article_list": ["article", ".post", ".entry", ".blog-post", ".article-item"],
        "title": ["h1", "h2", ".entry-title", ".post-title", ".article-title", "a"],
        "author": [".author", ".byline", ".post-author", ".entry-author", "rel='author'"],
        "content": [".entry-content", ".post-content", ".article-content", ".content", "article p"],
        "link": ["a[href]", ".read-more", ".entry-title a"],
    }
}
