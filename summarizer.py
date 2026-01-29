"""Claude API integration for generating article summaries."""

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_SUMMARY_WORDS
from scraper import Article


SYSTEM_PROMPT = """You are an expert editorial writer for an intellectually rigorous publication. Your task is to generate article summaries that match the distinctive voice of the Mere Orthodoxy Digest.

## Style Requirements

Your summaries must embody these characteristics:

1. **Intellectual Rigor**: Use sophisticated vocabulary and complex sentence structures. Engage with ideas at a substantive level, not superficially.

2. **Argument-Focused**: Present the article's central argument or thesis, not just its topic. Explain what the author contends, argues, or demonstrates.

3. **Non-Therapeutic Voice**: Avoid emotional, self-help, or therapeutic language. Maintain analytical distance while remaining engaging.

4. **Connecting to Deeper Principles**: Link contemporary issues to underlying philosophical, theological, or ethical principles.

5. **Precise Language**: Every word should earn its place. Avoid filler, hedging, or unnecessary qualifications.

6. **Active Engagement**: Summaries should make readers want to engage with the full article. Hint at the intellectual rewards of deeper reading.

## What to Avoid

- Hype or promotional language
- Vague topic descriptions ("discusses," "explores," "looks at")
- Emotional manipulation or clickbait
- Oversimplification of complex arguments
- Generic or interchangeable descriptions
- Starting summaries with the author's name
- Using phrases like "In this article..." or "The author..."

## Summary Format

Each summary must:
- Be exactly 50 words or fewer
- Present the article's core argument or insight
- Use language that reflects intellectual seriousness
- Be a single, well-crafted paragraph

## Example Summaries (for style reference)

Good example:
"The administrative state's expansion represents not merely bureaucratic growth but a fundamental reordering of constitutional authority. When agencies both make and enforce rules, the separation of powers becomes merely theoretical, leaving citizens subject to a governance structure the Founders explicitly rejected."

Good example:
"Contemporary debates about religious liberty often miss the deeper question: not whether faith should be accommodated, but whether a society that treats transcendent commitments as private preferences can sustain the moral vocabulary necessary for genuine pluralism."

Bad example (too vague):
"This article discusses religious liberty and its importance in modern society. The author explores various perspectives on the topic."

Bad example (too promotional):
"A must-read piece that will change how you think about democracy! The author brilliantly shows why we need to pay attention to this crucial issue."""


def create_summary_prompt(articles: list[Article]) -> str:
    """Create the prompt for generating summaries."""
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"""
---
ARTICLE {i}
Title: {article.title}
Author: {article.author}
URL: {article.url}

Content:
{article.content[:5000]}
---
"""

    return f"""Generate a complete digest for the following {len(articles)} articles.

{articles_text}

Please provide:

1. **HEADLINE**: Create a compelling, intellectually engaging headline that references the most interesting 1-2 articles. The headline should be optimized for email open rates while maintaining intellectual credibility. Do not use clickbait - instead, hint at substantive ideas.

2. **COMBINED SUMMARY**: Write a single sentence (20-30 words) that weaves together the themes from all articles, giving readers a sense of the digest's intellectual range.

3. **INDIVIDUAL SUMMARIES**: For each article, provide:
   - The article title (exactly as given)
   - The author name (exactly as given)
   - A summary of exactly 50 words or fewer that captures the article's central argument

Format your response EXACTLY as follows (this format will be parsed programmatically):

HEADLINE: [Your headline here]

COMBINED_SUMMARY: [Your one-sentence combined summary here]

ARTICLE_SUMMARIES:
1. TITLE: [Article 1 title]
AUTHOR: [Article 1 author]
SUMMARY: [50-word max summary]

2. TITLE: [Article 2 title]
AUTHOR: [Article 2 author]
SUMMARY: [50-word max summary]

[Continue for all articles...]

Remember: Each summary must be 50 words or fewer, intellectually substantive, and focused on arguments rather than topics."""


class DigestGenerator:
    """Generates article digest using Claude API."""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_digest(self, articles: list[Article], progress_callback=None) -> dict:
        """Generate the complete digest for a list of articles."""
        if progress_callback:
            progress_callback("Sending articles to Claude for summarization...")

        prompt = create_summary_prompt(articles)

        message = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        if progress_callback:
            progress_callback("Parsing Claude's response...")

        response_text = message.content[0].text
        return self._parse_response(response_text, articles)

    def _parse_response(self, response: str, articles: list[Article]) -> dict:
        """Parse Claude's response into structured data."""
        result = {
            "headline": "",
            "combined_summary": "",
            "article_summaries": []
        }

        lines = response.strip().split("\n")
        current_section = None
        current_article = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("HEADLINE:"):
                result["headline"] = line.replace("HEADLINE:", "").strip()
            elif line.startswith("COMBINED_SUMMARY:"):
                result["combined_summary"] = line.replace("COMBINED_SUMMARY:", "").strip()
            elif line.startswith("ARTICLE_SUMMARIES:"):
                current_section = "articles"
            elif current_section == "articles":
                if line[0].isdigit() and ". TITLE:" in line:
                    if current_article:
                        result["article_summaries"].append(current_article)
                    current_article = {
                        "title": line.split("TITLE:", 1)[1].strip() if "TITLE:" in line else ""
                    }
                elif line.startswith("TITLE:"):
                    if current_article:
                        result["article_summaries"].append(current_article)
                    current_article = {"title": line.replace("TITLE:", "").strip()}
                elif line.startswith("AUTHOR:"):
                    current_article["author"] = line.replace("AUTHOR:", "").strip()
                elif line.startswith("SUMMARY:"):
                    current_article["summary"] = line.replace("SUMMARY:", "").strip()
                elif "summary" in current_article and not line.startswith(("TITLE:", "AUTHOR:", "SUMMARY:")):
                    # Continuation of summary
                    current_article["summary"] += " " + line

        # Add the last article
        if current_article:
            result["article_summaries"].append(current_article)

        # Add URLs from original articles
        for i, summary in enumerate(result["article_summaries"]):
            if i < len(articles):
                summary["url"] = articles[i].url

        return result

    def format_digest(self, digest: dict) -> str:
        """Format the digest for display/output."""
        output = []

        # Headline
        output.append(digest["headline"])
        output.append("")

        # Combined summary
        output.append(digest["combined_summary"])
        output.append("")
        output.append("Articles")
        output.append("")

        # Individual summaries
        for i, article in enumerate(digest["article_summaries"], 1):
            title = article.get("title", "Untitled")
            author = article.get("author", "Unknown Author")
            summary = article.get("summary", "")

            # Enforce word limit
            words = summary.split()
            if len(words) > MAX_SUMMARY_WORDS:
                summary = " ".join(words[:MAX_SUMMARY_WORDS]) + "..."

            output.append(f"{i}. **{title}**")
            output.append(f"*{author}*")
            output.append(summary)
            output.append("")

        return "\n".join(output)
