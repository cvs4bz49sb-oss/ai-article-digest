"""Web scraping module for extracting articles from websites."""

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
    ARTICLE_SELECTORS,
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
        self.selectors = ARTICLE_SELECTORS["default"]

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
                # Basic check - look for disallow all
                content = response.text.lower()
                if "disallow: /" in content and "user-agent: *" in content:
                    # Check if it's a blanket disallow (simplified check)
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if "user-agent: *" in line:
                            # Check next few lines for disallow: /
                            for j in range(i + 1, min(i + 5, len(lines))):
                                if lines[j].strip() == "disallow: /":
                                    return False
            return True
        except requests.RequestException:
            # If we can't fetch robots.txt, proceed with caution
            return True

    def _extract_text(self, element) -> str:
        """Extract clean text from a BeautifulSoup element."""
        if element is None:
            return ""
        # Remove script and style elements
        for script in element(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        text = element.get_text(separator=" ", strip=True)
        # Clean up whitespace
        return " ".join(text.split())

    def _find_element(self, soup: BeautifulSoup, selectors: list, parent=None) -> Optional[any]:
        """Try multiple selectors to find an element."""
        search_in = parent if parent else soup
        for selector in selectors:
            try:
                element = search_in.select_one(selector)
                if element:
                    return element
            except Exception:
                continue
        return None

    def _find_all_elements(self, soup: BeautifulSoup, selectors: list) -> list:
        """Try multiple selectors to find all matching elements."""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    return elements
            except Exception:
                continue
        return []

    def _extract_article_links(self, soup: BeautifulSoup) -> list[str]:
        """Extract article links from the main page."""
        links = []

        # Try to find article containers first
        articles = self._find_all_elements(soup, self.selectors["article_list"])

        if articles:
            for article in articles:
                # Find links within article containers
                link_elem = article.find("a", href=True)
                if link_elem:
                    href = link_elem.get("href", "")
                    if href and not href.startswith("#"):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in links:
                            links.append(full_url)

        # If no articles found, look for common blog post link patterns
        if not links:
            # Look for links in main content area
            main_content = soup.find("main") or soup.find(class_=["content", "posts", "blog"])
            if main_content:
                for link in main_content.find_all("a", href=True):
                    href = link.get("href", "")
                    # Filter out navigation and utility links
                    if (href and not href.startswith("#") and
                        not any(skip in href.lower() for skip in
                               ["login", "signup", "contact", "about", "privacy", "terms"])):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in links and self.base_url in full_url:
                            links.append(full_url)

        return links

    def _scrape_article_page(self, url: str) -> Optional[Article]:
        """Scrape a single article page."""
        try:
            soup = self._fetch_page(url)
            if not soup:
                return None

            # Extract title
            title_elem = self._find_element(soup, self.selectors["title"])
            title = self._extract_text(title_elem) if title_elem else ""

            # If title is too long, it might be content - try to get just the h1
            if len(title) > 200:
                h1 = soup.find("h1")
                if h1:
                    title = self._extract_text(h1)

            # Extract author
            author_elem = self._find_element(soup, self.selectors["author"])
            author = self._extract_text(author_elem) if author_elem else "Unknown Author"

            # Clean up author text
            author = author.replace("By ", "").replace("by ", "").strip()
            if len(author) > 100:
                author = "Unknown Author"

            # Extract content
            content = ""
            content_elem = self._find_element(soup, self.selectors["content"])
            if content_elem:
                content = self._extract_text(content_elem)

            # Fallback: get all paragraphs in article or main
            if not content or len(content) < 100:
                article_elem = soup.find("article") or soup.find("main")
                if article_elem:
                    paragraphs = article_elem.find_all("p")
                    content = " ".join(self._extract_text(p) for p in paragraphs)

            if not title or not content:
                return None

            return Article(
                title=title[:500],  # Limit title length
                author=author[:100],  # Limit author length
                content=content[:10000],  # Limit content length
                url=url
            )

        except Exception as e:
            print(f"  Warning: Failed to scrape {url}: {e}")
            return None

    def scrape_articles(self, count: int, progress_callback=None) -> list[Article]:
        """Scrape articles from the website."""
        # Check robots.txt
        if not self._check_robots_txt():
            print("Warning: robots.txt may disallow scraping. Proceeding with caution...")

        if progress_callback:
            progress_callback("Fetching main page...")

        # Fetch the main page
        soup = self._fetch_page(self.base_url)
        if not soup:
            raise RuntimeError(f"Failed to fetch main page: {self.base_url}")

        if progress_callback:
            progress_callback("Extracting article links...")

        # Extract article links
        article_links = self._extract_article_links(soup)

        if not article_links:
            raise RuntimeError("No article links found on the page. The website structure may not be supported.")

        if progress_callback:
            progress_callback(f"Found {len(article_links)} potential articles. Scraping up to {count}...")

        # Scrape individual articles
        articles = []
        for i, link in enumerate(article_links[:count * 2]):  # Try extra links in case some fail
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
