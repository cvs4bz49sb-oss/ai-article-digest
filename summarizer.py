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
- Start with the author's name in a natural sentence
- Use active verbs like "examines," "argues," "contends," "traces," "frames," "looks at"
- The summary flows as a single paragraph starting with the author
- Be exactly 50 words or fewer total
- Present the article's core argument or insight

## Example Summaries (FOLLOW THIS FORMAT EXACTLY)

Example 1:
"Marc Sims examines theological principles guiding church architecture, arguing that while church health doesn't depend on building quality, sacred spaces can aid worship by drawing attention heavenward through intentional, non-distracting design that emphasizes God's transcendence."

Example 2:
"Shebuel Varghesee frames the controversial hymn through a third-culture perspective, arguing that for diaspora Christians, the longing for heavenly home reflects genuine existential displacement rather than escapism, offering spiritual comfort to the globally dispersed."

Example 3:
"Michael Horton traces Joachim of Fiore's influence on Western thought, showing how medieval eschatology fused vertical spiritual ascent with historical progress, profoundly shaping utopian ideologies and modern definitions of advancement through science and reason."

Example 4:
"Joshua Heavin examines J.C. Ryle's practical holiness emphasis, emphasizing his pastoral approach to suffering, faithfulness to Anglican formularies, preaching clarity, and pastoral care for the dying—offering resources for contemporary Christian witness and formation."

Example 5:
"John Ehrett looks at evangelical fractures as fundamentally a class conflict between credential-holding elites and working-class congregants, arguing this economic and cultural divide—not theological disagreement—drives much contemporary polarization within American Christianity."

BAD example (doesn't start with author):
"The administrative state's expansion represents not merely bureaucratic growth but a fundamental reordering of constitutional authority."

BAD example (too vague):
"This article discusses religious liberty and its importance in modern society. The author explores various perspectives on the topic."

Remember: EVERY summary must begin with the author's name followed by an active verb."""


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

1. **HEADLINE**: Create a compelling, intellectually engaging headline for the digest. Reference the most interesting 1-2 articles. Format: "This Week At Mere Orthodoxy" style - elegant and understated.

2. **INDIVIDUAL SUMMARIES**: For each article, provide:
   - The article title (exactly as given)
   - The author name (exactly as given)
   - A summary that STARTS WITH THE AUTHOR'S NAME followed by an active verb (examines, argues, traces, frames, looks at, contends, etc.)
   - Maximum 50 words per summary

Format your response EXACTLY as follows (this format will be parsed programmatically):

HEADLINE: [Your headline here]

ARTICLE_SUMMARIES:
1. TITLE: [Article 1 title]
AUTHOR: [Article 1 author]
SUMMARY: [Author name] [active verb] [rest of 50-word max summary]

2. TITLE: [Article 2 title]
AUTHOR: [Article 2 author]
SUMMARY: [Author name] [active verb] [rest of 50-word max summary]

[Continue for all articles...]

CRITICAL REMINDER: Each summary MUST start with the author's name (e.g., "Marc Sims examines...", "John Smith argues...", "Jane Doe traces..."). This is non-negotiable."""


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
