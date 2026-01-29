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
- Using phrases like "In this article..." or "The article..."

## Summary Format

CRITICAL: Each summary must follow this EXACT format:
- Start with an active verb (examines, argues, contends, traces, frames, looks at, etc.)
- DO NOT include the author's name - it will be added automatically
- The summary flows as a single paragraph
- Be exactly 50 words or fewer total
- Present the article's core argument or insight

## Example Summaries (FOLLOW THIS FORMAT EXACTLY)

Example 1:
"examines theological principles guiding church architecture, arguing that while church health doesn't depend on building quality, sacred spaces can aid worship by drawing attention heavenward through intentional, non-distracting design that emphasizes God's transcendence."

Example 2:
"frames the controversial hymn through a third-culture perspective, arguing that for diaspora Christians, the longing for heavenly home reflects genuine existential displacement rather than escapism, offering spiritual comfort to the globally dispersed."

Example 3:
"traces Joachim of Fiore's influence on Western thought, showing how medieval eschatology fused vertical spiritual ascent with historical progress, profoundly shaping utopian ideologies and modern definitions of advancement through science and reason."

Example 4:
"examines J.C. Ryle's practical holiness emphasis, emphasizing his pastoral approach to suffering, faithfulness to Anglican formularies, preaching clarity, and pastoral care for the dying—offering resources for contemporary Christian witness and formation."

Example 5:
"looks at evangelical fractures as fundamentally a class conflict between credential-holding elites and working-class congregants, arguing this economic and cultural divide—not theological disagreement—drives much contemporary polarization within American Christianity."

BAD example (includes author name - DON'T DO THIS):
"Marc Sims examines theological principles guiding church architecture..."

BAD example (too vague):
"discusses religious liberty and its importance in modern society."

Remember: Start with an active VERB, not the author's name. The author name is added separately."""


def create_summary_prompt(articles: list[Article], site_name: str = "the publication") -> str:
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

    return f"""Generate a complete digest for the following {len(articles)} articles from {site_name}.

{articles_text}

Please provide:

1. **HEADLINE**: Create a compelling, intellectually engaging headline for the digest. Reference themes from the most interesting articles. Format should be elegant and substantive - capturing the intellectual essence of the collection.

2. **COMBINED SUMMARY**: Write a 2-3 sentence paragraph summarizing the themes across ALL the articles. This paragraph should:
   - Start with "This week's {site_name} Digest examines..."
   - Weave together the main themes, arguments, and ideas from the collection
   - Be intellectually engaging and sophisticated
   - About 40-60 words total

3. **INDIVIDUAL SUMMARIES**: For each article, provide:
   - The article title (exactly as given)
   - The author name (exactly as given)
   - A summary that STARTS WITH AN ACTIVE VERB (examines, argues, traces, frames, looks at, contends, etc.)
   - DO NOT include the author's name in the summary - it will be added automatically
   - Maximum 50 words per summary

Format your response EXACTLY as follows (this format will be parsed programmatically):

HEADLINE: [Your headline here]

COMBINED_SUMMARY: [Your 2-3 sentence thematic summary here]

ARTICLE_SUMMARIES:
1. TITLE: [Article 1 title]
AUTHOR: [Article 1 author]
SUMMARY: [active verb] [rest of 50-word max summary - NO author name]

2. TITLE: [Article 2 title]
AUTHOR: [Article 2 author]
SUMMARY: [active verb] [rest of 50-word max summary - NO author name]

[Continue for all articles...]

CRITICAL: Each summary must START WITH A VERB like "examines", "argues", "traces", "frames", "contends", "looks at". DO NOT start with the author's name."""


class DigestGenerator:
    """Generates article digest using Claude API."""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_digest(self, articles: list[Article], progress_callback=None, site_name: str = "the publication") -> dict:
        """Generate the complete digest for a list of articles."""
        if progress_callback:
            progress_callback("Sending articles to Claude for summarization...")

        prompt = create_summary_prompt(articles, site_name=site_name)

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
                current_section = "headline"
            elif line.startswith("COMBINED_SUMMARY:"):
                result["combined_summary"] = line.replace("COMBINED_SUMMARY:", "").strip()
                current_section = "combined_summary"
            elif line.startswith("ARTICLE_SUMMARIES:"):
                current_section = "articles"
            elif current_section == "combined_summary":
                # Continue building combined summary until we hit ARTICLE_SUMMARIES
                if not line.startswith(("HEADLINE:", "ARTICLE_SUMMARIES:", "1.", "TITLE:")):
                    result["combined_summary"] += " " + line
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

        # Clean up combined summary
        result["combined_summary"] = " ".join(result["combined_summary"].split())

        return result

    def format_digest(self, digest: dict) -> str:
        """Format the digest for display/output."""
        output = []

        # Headline
        output.append(digest["headline"])
        output.append("")

        # Combined summary
        if digest.get("combined_summary"):
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
            output.append(f"")
            output.append(f"*{author}* {summary}")
            output.append("")

        return "\n".join(output)
