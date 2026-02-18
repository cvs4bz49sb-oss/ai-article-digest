"""Claude API integration for generating article summaries."""

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_SUMMARY_WORDS
from scraper import Article


SYSTEM_PROMPT = """You are an expert editorial writer producing digest summaries, headlines, and social posts. Your voice is that of the educated pastor at the kitchen table — someone who has read deeply and thought carefully, but who speaks with warmth and without condescension.

## THE VOICE

Your writing embodies confidence without arrogance. You know what you believe and why. You do not hedge endlessly or perform false uncertainty. But you are never combative. You assume the reader is intelligent, serious, and capable of being persuaded rather than bullied.

### Sentence Architecture
- Favor complex, compound-complex constructions with subordinate clauses, appositives, and parenthetical qualifications. The long sentence is a thinking-through-in-real-time sentence that honors complexity rather than flattening it.
- Punctuate longer constructions with short declarative sentences that land like conclusions — the load-bearing walls that reward the reader for tracking the argument.
- Use em-dashes liberally — as asides, qualifications, or moments of self-interruption — creating the feeling that you are thinking aloud alongside the reader.
- Stack clauses in a way that narrows or reframes: "This is not because [X], nor is it because [Y], but rather because [Z]."

### Vocabulary & Diction
- Sit at the intersection of academic and pastoral. Use precise theological and philosophical vocabulary (formation, discipleship, ecclesiology, subsidiarity, the common good, embodied, dignity, communion) without apology or definition — but mix freely with colloquial warmth.
- Lean Latinate for formal arguments (solidarity, contingency, incorporation) and Anglo-Saxon for concrete or emotional moments (home, child, food, cross, love, weak). The alternation within a single summary makes the abstract feel embodied and the embodied feel significant.

### Argumentation Style
- Follow a "yes, but also" structure: charitably acknowledge what is true in a position, then pivot to explain what it misses.
- Situate arguments within historical narrative when possible — not just "here is a problem" but "here is how we arrived at this problem."
- Whenever things become abstract, ground them in concrete images or specifics — a particular book, a named figure, a specific practice or institution. The specific detail is a form of evidence.

### Tone & Emotional Register
- Warm but uncompromising: tender toward persons, firm toward ideas.
- Grief without despair: name problems clearly, but the emotional baseline is concerned hope. "This is bad, and we should name it clearly, but we are not without resources."
- Humor appears in parenthetical asides and is always understated — never sarcastic, always the humor of someone who finds the human condition both serious and genuinely funny.

## WHAT THIS VOICE IS NOT

- Not performatively casual. Do not say "y'all" or "friend" or use the faux-intimate first-person plural of evangelical content marketing.
- Not anxious or reactive. Do not write as though responding to the news cycle.
- Not sentimental. Warm, but never trafficking in vague emotional uplift. Never say "God is doing a new thing" or "community is everything" without specifying what those words mean.
- Not partisan in the tribal sense. The loyalty is to a theological and philosophical tradition, not to a political faction.
- Not self-promotional. Ideas are foregrounded; the publication is the vehicle.

## SUMMARY FORMAT

CRITICAL: Each summary must follow this EXACT format:
- Start with an active verb (examines, argues, contends, traces, frames, looks at, etc.)
- DO NOT include the author's name — it will be added automatically
- The summary flows as a single paragraph
- Be exactly 50 words or fewer total
- Present the article's core argument or insight, not merely its topic
- Prefer evocative phrasing over SEO-optimized or generic descriptions

## EXAMPLE SUMMARIES (FOLLOW THIS FORMAT EXACTLY)

Example 1:
"examines theological principles guiding church architecture, arguing that while church health doesn't depend on building quality, sacred spaces can aid worship by drawing attention heavenward through intentional, non-distracting design that emphasizes God's transcendence."

Example 2:
"frames the controversial hymn through a third-culture perspective, arguing that for diaspora Christians, the longing for heavenly home reflects genuine existential displacement rather than escapism, offering spiritual comfort to the globally dispersed."

Example 3:
"traces Joachim of Fiore's influence on Western thought, showing how medieval eschatology fused vertical spiritual ascent with historical progress, profoundly shaping utopian ideologies and modern definitions of advancement through science and reason."

Example 4:
"contends that the crisis of young men is not primarily political but formational — a failure of households, churches, and communities to offer the kind of embodied, sacrificial discipleship that forms character rather than merely correcting behavior."

Example 5:
"looks at evangelical fractures as fundamentally a class conflict between credential-holding elites and working-class congregants, arguing this economic and cultural divide — not theological disagreement — drives much contemporary polarization within American Christianity."

BAD example (includes author name — DON'T DO THIS):
"Marc Sims examines theological principles guiding church architecture..."

BAD example (too vague):
"discusses religious liberty and its importance in modern society."

BAD example (sentimental/therapeutic):
"offers a beautiful reminder that we are all called to love one another more deeply."

Remember: Start with an active VERB, not the author's name. The author name is added separately.

## HEADLINE & COMBINED SUMMARY VOICE

Headlines should be evocative and slightly literary — never clickbait, never listicle-structured. "In Praise of Being Inconvenient" over "Why Parenting Is Hard and That's Okay." The headline should make the reader curious about the argument.

Combined summaries should move from the particular to the universal — naming specific topics, arguments, and figures from the articles, then gesturing toward the deeper principles at stake. This movement from kitchen table to philosophical claim is the signature move: the ordinary is not trivial. It is where the deepest truths live.

## SOCIAL MEDIA VOICE

Pull a single concrete image or claim paired with the universal insight it supports. Let the image do the work. Do not explain the connection — trust the reader. Never beg. Never hype. Assume the reader will come because the ideas are worth engaging, not because you've created artificial urgency."""


def create_summary_prompt(articles: list[Article], site_name: str = "the publication", output_type: str = "both") -> str:
    """Create the prompt for generating summaries.

    Args:
        articles: List of Article objects
        site_name: Name of the publication
        output_type: 'digest', 'social', or 'both'
    """
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

    # Build the prompt based on output_type
    if output_type == "social":
        return f"""Generate social media posts for the following {len(articles)} articles from {site_name}.

{articles_text}

For each article, provide a social media post with:
- A compelling headline (can be the article title or a catchier version, max 10 words)
- One sentence of compelling and accurate summary (punchy and shareable)
- The post should make people want to click and read the full article

Format your response EXACTLY as follows (this format will be parsed programmatically):

SOCIAL_POSTS:
1. POST_HEADLINE: [Catchy headline for social media]
POST_SUMMARY: [One compelling sentence]

2. POST_HEADLINE: [Catchy headline for social media]
POST_SUMMARY: [One compelling sentence]

[Continue for all articles...]"""

    elif output_type == "digest":
        return f"""Generate a complete digest for the following {len(articles)} articles from {site_name}.

{articles_text}

Please provide:

1. **HEADLINE**: Create a compelling, intellectually engaging headline for the digest. Reference themes from the most interesting articles. Format should be elegant and substantive - capturing the intellectual essence of the collection.

2. **COMBINED SUMMARY**: Write a 2-3 sentence paragraph that SPECIFICALLY describes the actual content of these articles. This paragraph should:
   - Start with "This week's {site_name} Digest examines..."
   - Reference SPECIFIC topics, arguments, or subjects from the articles (e.g., specific people, events, concepts, or debates mentioned)
   - NOT use vague phrases like "themes of spiritual formation" or "cultural engagement" or "the search for community"
   - Instead, mention CONCRETE specifics like: a particular author's argument, a specific historical figure, a named concept or book, a particular controversy or event
   - About 40-60 words total

   BAD example (too vague): "This week's Digest examines how Christians navigate technology and community, exploring themes of spiritual formation and cultural engagement."

   GOOD example (specific): "This week's Mere Orthodoxy Digest examines smartphone addiction through Tony Reinke's digital minimalism framework, traces J.C. Ryle's influence on Anglican pastoral care, and considers whether evangelical fractures stem from class conflict rather than theological disagreement."

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

    else:  # both
        return f"""Generate a complete digest for the following {len(articles)} articles from {site_name}.

{articles_text}

Please provide:

1. **HEADLINE**: Create a compelling, intellectually engaging headline for the digest. Reference themes from the most interesting articles. Format should be elegant and substantive - capturing the intellectual essence of the collection.

2. **COMBINED SUMMARY**: Write a 2-3 sentence paragraph that SPECIFICALLY describes the actual content of these articles. This paragraph should:
   - Start with "This week's {site_name} Digest examines..."
   - Reference SPECIFIC topics, arguments, or subjects from the articles (e.g., specific people, events, concepts, or debates mentioned)
   - NOT use vague phrases like "themes of spiritual formation" or "cultural engagement" or "the search for community"
   - Instead, mention CONCRETE specifics like: a particular author's argument, a specific historical figure, a named concept or book, a particular controversy or event
   - About 40-60 words total

   BAD example (too vague): "This week's Digest examines how Christians navigate technology and community, exploring themes of spiritual formation and cultural engagement."

   GOOD example (specific): "This week's Mere Orthodoxy Digest examines smartphone addiction through Tony Reinke's digital minimalism framework, traces J.C. Ryle's influence on Anglican pastoral care, and considers whether evangelical fractures stem from class conflict rather than theological disagreement."

3. **INDIVIDUAL SUMMARIES**: For each article, provide:
   - The article title (exactly as given)
   - The author name (exactly as given)
   - A summary that STARTS WITH AN ACTIVE VERB (examines, argues, traces, frames, looks at, contends, etc.)
   - DO NOT include the author's name in the summary - it will be added automatically
   - Maximum 50 words per summary

4. **SOCIAL MEDIA POSTS**: For each article, provide a social media post with:
   - A compelling headline (can be the article title or a catchier version, max 10 words)
   - One sentence of compelling and accurate summary (different from the digest summary - more punchy and shareable)
   - The post should make people want to click and read the full article

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

SOCIAL_POSTS:
1. POST_HEADLINE: [Catchy headline for social media]
POST_SUMMARY: [One compelling sentence]

2. POST_HEADLINE: [Catchy headline for social media]
POST_SUMMARY: [One compelling sentence]

[Continue for all articles...]

CRITICAL: Each summary must START WITH A VERB like "examines", "argues", "traces", "frames", "contends", "looks at". DO NOT start with the author's name."""


class DigestGenerator:
    """Generates article digest using Claude API."""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_digest(self, articles: list[Article], progress_callback=None, site_name: str = "the publication", output_type: str = "both") -> dict:
        """Generate the complete digest for a list of articles.

        Args:
            articles: List of Article objects to summarize
            progress_callback: Optional callback for progress updates
            site_name: Name of the publication
            output_type: 'digest', 'social', or 'both'
        """
        if progress_callback:
            progress_callback("Sending articles to Claude for summarization...")

        prompt = create_summary_prompt(articles, site_name=site_name, output_type=output_type)

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
        return self._parse_response(response_text, articles, output_type=output_type)

    def _parse_response(self, response: str, articles: list[Article], output_type: str = "both") -> dict:
        """Parse Claude's response into structured data."""
        result = {
            "headline": "",
            "combined_summary": "",
            "article_summaries": [],
            "social_posts": []
        }

        lines = response.strip().split("\n")
        current_section = None
        current_article = {}
        current_post = {}

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
            elif line.startswith("SOCIAL_POSTS:"):
                # Save the last article before switching sections
                if current_article:
                    result["article_summaries"].append(current_article)
                    current_article = {}
                current_section = "social_posts"
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
                elif "summary" in current_article and not line.startswith(("TITLE:", "AUTHOR:", "SUMMARY:", "SOCIAL_POSTS:")):
                    # Continuation of summary
                    current_article["summary"] += " " + line
            elif current_section == "social_posts":
                if line[0].isdigit() and ". POST_HEADLINE:" in line:
                    if current_post:
                        result["social_posts"].append(current_post)
                    current_post = {
                        "headline": line.split("POST_HEADLINE:", 1)[1].strip() if "POST_HEADLINE:" in line else ""
                    }
                elif line.startswith("POST_HEADLINE:"):
                    if current_post:
                        result["social_posts"].append(current_post)
                    current_post = {"headline": line.replace("POST_HEADLINE:", "").strip()}
                elif line.startswith("POST_SUMMARY:"):
                    current_post["summary"] = line.replace("POST_SUMMARY:", "").strip()
                elif "summary" in current_post and not line.startswith(("POST_HEADLINE:", "POST_SUMMARY:")) and not (line[0].isdigit() and "." in line):
                    # Continuation of post summary
                    current_post["summary"] += " " + line

        # Add the last article and post
        if current_article:
            result["article_summaries"].append(current_article)
        if current_post:
            result["social_posts"].append(current_post)

        # Add URLs from original articles
        for i, summary in enumerate(result["article_summaries"]):
            if i < len(articles):
                summary["url"] = articles[i].url

        # Add URLs to social posts
        for i, post in enumerate(result["social_posts"]):
            if i < len(articles):
                post["url"] = articles[i].url

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
