"""Web scraping module for extracting articles from websites."""

import html
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)


@dataclass
class Article:
    """Represents a scraped article."""
    title: str
    author: str
    content: str
    url: str


class ArticleScraper:
    """Scrapes articles from websites."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
        return None

    def _check_robots_txt(self) -> bool:
        """Check if scraping is allowed by robots.txt."""
        try:
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                content = response.text.lower()
                if "disallow: /" in content and "user-agent: *" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "user-agent: *" in line:
                            for j in range(i + 1, min(i + 5, len(lines))):
                                if lines[j].strip() == "disallow: /":
                                    return False
            return True
        except requests.RequestException:
            return True

    def _extract_text(self, element) -> str:
        """Extract clean text from a BeautifulSoup element."""
        if element is None:
            return ""
        for script in element(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        text = element.get_text(separator=" ", strip=True)
        # Decode HTML entities like &#39; -> ' and &amp; -> &
        text = html.unescape(text)
        return " ".join(text.split())

    def _clean_author_name(self, author: str) -> str:
        """Clean author name by removing common extraneous text like 'About', 'Follow', etc."""
        if not author:
            return ""

        # Remove common prefixes
        author = author.replace("By ", "").replace("by ", "")
        author = author.replace("Written by ", "").replace("written by ", "")
        author = author.replace("Author: ", "").replace("author: ", "")

        # Common words/phrases to remove (case-insensitive patterns)
        remove_patterns = [
            "About the Author",
            "About the Authors",
            "About",
            "Follow on Twitter",
            "Follow on X",
            "Follow",
            "Subscribe",
            "Share",
            "Twitter",
            "Facebook",
            "LinkedIn",
            "Email",
            "More articles",
            "View all posts",
            "Read more",
            "Contact",
            " | ",
            " - ",
        ]

        # Sort by length descending to remove longer patterns first
        remove_patterns.sort(key=len, reverse=True)

        for pattern in remove_patterns:
            # Case-insensitive replacement
            lower_author = author.lower()
            lower_pattern = pattern.lower()
            while lower_pattern in lower_author:
                idx = lower_author.find(lower_pattern)
                author = author[:idx] + author[idx + len(pattern):]
                lower_author = author.lower()

        # Clean up multiple spaces and trim
        author = " ".join(author.split()).strip()

        # If author contains multiple names separated by commas or 'and', that's fine
        # But if it's too long (likely contains extra junk), try to extract just the name part
        if len(author) > 60:
            # Try to get just the first part before any obvious separator
            for sep in [",", " and ", " & ", "."]:
                if sep in author:
                    parts = author.split(sep)
                    if parts[0].strip() and len(parts[0].strip()) < 50:
                        author = parts[0].strip()
                        break

        # Remove any trailing/leading punctuation
        author = author.strip(".,;:-|/\\\"'")

        return author.strip()

    def _is_article_url(self, url: str) -> bool:
        """Check if a URL looks like an article (not a tag, category, or utility page)."""
        skip_patterns = [
            "/tag/", "/tags/", "/category/", "/categories/",
            "/author/", "/page/", "/search", "/login", "/signup",
            "/contact", "/about", "/privacy", "/terms", "/subscribe",
            "/feed", "/rss", "#", "javascript:", "mailto:",
            # Additional patterns for sites like Unchained that use blog- prefix
            "/blog-tag/", "/blog-category/", "/blog-author/",
            "-tag/", "-category/", "-author/"
        ]
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in skip_patterns)

    def _extract_article_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract article links from the main page."""
        links = []
        parsed_base = urlparse(self.base_url)
        base_domain = parsed_base.netloc

        # Strategy 1: Look for card-based layouts (like Mere Orthodoxy, Unchained)
        card_selectors = [
            ".section--listing--card",
            ".post-card",
            ".article-card",
            ".entry-card",
            ".blog-card",
            "[class*='blog-card']",
            "[class*='post-card']",
            "[class*='article-card']",
            "[class*='card']"
        ]

        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                for card in cards:
                    link = card.find("a", href=True)
                    if link:
                        href = link.get("href", "")
                        full_url = urljoin(self.base_url, href)
                        if (self._is_article_url(full_url) and
                            base_domain in urlparse(full_url).netloc and
                            full_url not in links):
                            links.append(full_url)
                if links:
                    break

        # Strategy 2: Look for article/post containers
        if not links:
            container_selectors = [
                "article",
                ".post",
                ".entry",
                ".blog-post",
                ".article-item",
                "[class*='post']",
                "[class*='article']"
            ]

            for selector in container_selectors:
                containers = soup.select(selector)
                if containers:
                    for container in containers:
                        link = container.find("a", href=True)
                        if link:
                            href = link.get("href", "")
                            full_url = urljoin(self.base_url, href)
                            if (self._is_article_url(full_url) and
                                base_domain in urlparse(full_url).netloc and
                                full_url not in links):
                                links.append(full_url)
                    if links:
                        break

        # Strategy 3: Look in main content area for article-like links
        if not links:
            main_content = soup.find("main") or soup.find(class_=["content", "posts", "blog", "articles"])
            if main_content:
                for link in main_content.find_all("a", href=True):
                    href = link.get("href", "")
                    full_url = urljoin(self.base_url, href)
                    parsed_url = urlparse(full_url)

                    # Check if it looks like an article URL (has path segments)
                    path_parts = [p for p in parsed_url.path.split("/") if p]
                    if (len(path_parts) >= 1 and
                        self._is_article_url(full_url) and
                        base_domain in parsed_url.netloc and
                        full_url not in links):
                        links.append(full_url)

        # Strategy 4: Look for any links with article-like patterns in the entire page
        # This helps with blog subpages like /blog that may have different structures
        if not links:
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                full_url = urljoin(self.base_url, href)
                parsed_url = urlparse(full_url)

                # Must be on same domain
                if base_domain not in parsed_url.netloc:
                    continue

                # Skip if not article-like
                if not self._is_article_url(full_url):
                    continue

                # Look for URLs that have date patterns or /blog/ prefix with slug
                path = parsed_url.path.lower()
                path_parts = [p for p in path.split("/") if p]

                # Skip if it's just the blog index
                if path_parts == ["blog"] or path_parts == ["articles"] or path_parts == ["posts"]:
                    continue

                # Accept URLs like /blog/article-slug or /2024/01/article-slug
                if len(path_parts) >= 2:
                    # Has multiple path segments (likely an article)
                    if full_url not in links:
                        links.append(full_url)

        return links

    def _scrape_article_page(self, url: str) -> Optional[Article]:
        """Scrape a single article page."""
        try:
            soup = self._fetch_page(url)
            if not soup:
                return None

            # Extract title - try multiple approaches
            title = ""
            title_selectors = [
                "h1.entry-title",
                "h1.post-title",
                "h1.article-title",
                "article h1",
                ".post h1",
                "main h1",
                "h1"
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = self._extract_text(title_elem)
                    if title and len(title) < 300:
                        break

            # Extract author - try multiple approaches
            author = ""
            author_selectors = [
                ".author-name",
                ".post-author",
                ".entry-author",
                ".byline",
                "[rel='author']",
                ".author",
                "[class*='author']"
            ]
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = self._extract_text(author_elem)
                    author = self._clean_author_name(author)
                    if author and len(author) < 100:
                        break

            if not author:
                author = "Unknown Author"

            # Extract content - try multiple approaches
            # Order matters: more specific selectors first, then generic ones
            content = ""
            content_selectors = [
                # Webflow-specific (used by sites like Unchained)
                ".blog-content__copy",
                ".w-richtext",
                # Common blog platforms
                ".entry-content",
                ".post-content",
                ".article-content",
                ".post-body",
                ".blog-post-content",
                ".article-body",
                ".story-content",
                ".post__content",
                ".content-body",
                # Generic patterns
                "article .content",
                "[class*='post-content']",
                "[class*='article-content']",
                "[class*='entry-content']",
                "[class*='blog-content']",
                "article",
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Get all paragraphs within the content area
                    paragraphs = content_elem.find_all("p")
                    if paragraphs:
                        content = " ".join(self._extract_text(p) for p in paragraphs if self._extract_text(p))
                    else:
                        content = self._extract_text(content_elem)

                    if content and len(content) > 200:
                        break

            # Fallback: get all paragraphs in main/article
            if not content or len(content) < 200:
                main_elem = soup.find("article") or soup.find("main") or soup.find(class_="post")
                if main_elem:
                    paragraphs = main_elem.find_all("p")
                    content = " ".join(self._extract_text(p) for p in paragraphs if self._extract_text(p))

            if not title or not content or len(content) < 100:
                return None

            return Article(
                title=title[:500],
                author=author[:100],
                content=content[:10000],
                url=url
            )

        except Exception as e:
            print(f"  Warning: Failed to scrape {url}: {e}")
            return None

    def scrape_articles(self, count: int, progress_callback=None) -> list[Article]:
        """Scrape articles from the website."""
        if not self._check_robots_txt():
            print("Warning: robots.txt may disallow scraping. Proceeding with caution...")

        if progress_callback:
            progress_callback("Fetching main page...")

        soup = self._fetch_page(self.base_url)
        if not soup:
            raise RuntimeError(f"Failed to fetch main page: {self.base_url}")

        if progress_callback:
            progress_callback("Extracting article links...")

        article_links = self._extract_article_links(soup)

        if not article_links:
            raise RuntimeError("No article links found on the page. The website structure may not be supported.")

        if progress_callback:
            progress_callback(f"Found {len(article_links)} potential articles. Scraping up to {count}...")

        # Scrape individual articles
        articles = []
        for i, link in enumerate(article_links[:count * 2]):
            if len(articles) >= count:
                break

            if progress_callback:
                progress_callback(f"Scraping article {len(articles) + 1}/{count}: {link[:60]}...")

            article = self._scrape_article_page(link)
            if article:
                articles.append(article)
                time.sleep(0.5)  # Be polite to the server

        if not articles:
            raise RuntimeError("Failed to scrape any articles. The website structure may not be supported.")

        return articles
