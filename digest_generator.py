#!/usr/bin/env python3
"""AI Article Digest Generator - CLI Application.

A command-line tool that scrapes articles from a website, analyzes their content,
and generates thoughtful summaries in the Mere Orthodoxy Digest style.
"""

import sys
from pathlib import Path

import click

from scraper import ArticleScraper
from summarizer import DigestGenerator
from config import DEFAULT_ARTICLE_COUNT


def print_progress(message: str):
    """Print a progress message with formatting."""
    click.echo(click.style(f"  → {message}", fg="cyan"))


def print_error(message: str):
    """Print an error message with formatting."""
    click.echo(click.style(f"✗ Error: {message}", fg="red"), err=True)


def print_success(message: str):
    """Print a success message with formatting."""
    click.echo(click.style(f"✓ {message}", fg="green"))


@click.command()
@click.argument("url")
@click.option(
    "-n", "--count",
    default=DEFAULT_ARTICLE_COUNT,
    help=f"Number of articles to process (default: {DEFAULT_ARTICLE_COUNT})"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Save output to a file (optional)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed progress information"
)
def main(url: str, count: int, output: str, verbose: bool):
    """Generate an article digest from a website.

    URL: The website URL to scrape articles from.

    Examples:

        python digest_generator.py https://example-blog.com

        python digest_generator.py https://example-blog.com -n 5

        python digest_generator.py https://example-blog.com -o digest.md
    """
    click.echo()
    click.echo(click.style("╔════════════════════════════════════════╗", fg="blue"))
    click.echo(click.style("║    AI Article Digest Generator         ║", fg="blue"))
    click.echo(click.style("╚════════════════════════════════════════╝", fg="blue"))
    click.echo()

    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    click.echo(f"Source: {url}")
    click.echo(f"Articles to process: {count}")
    click.echo()

    try:
        # Step 1: Scrape articles
        click.echo(click.style("Step 1/3: Scraping articles...", fg="yellow", bold=True))

        scraper = ArticleScraper(url)
        progress_fn = print_progress if verbose else None
        articles = scraper.scrape_articles(count, progress_callback=progress_fn)

        print_success(f"Successfully scraped {len(articles)} articles")
        click.echo()

        if verbose:
            for i, article in enumerate(articles, 1):
                click.echo(f"  {i}. {article.title[:60]}...")
            click.echo()

        # Step 2: Generate summaries
        click.echo(click.style("Step 2/3: Generating summaries with Claude...", fg="yellow", bold=True))

        generator = DigestGenerator()
        digest = generator.generate_digest(articles, progress_callback=progress_fn)

        print_success("Successfully generated digest")
        click.echo()

        # Step 3: Format and output
        click.echo(click.style("Step 3/3: Formatting output...", fg="yellow", bold=True))

        formatted_digest = generator.format_digest(digest)

        print_success("Digest complete!")
        click.echo()

        # Display the digest
        click.echo(click.style("=" * 60, fg="blue"))
        click.echo(click.style("GENERATED DIGEST", fg="blue", bold=True))
        click.echo(click.style("=" * 60, fg="blue"))
        click.echo()
        click.echo(formatted_digest)
        click.echo(click.style("=" * 60, fg="blue"))

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.write_text(formatted_digest, encoding="utf-8")
            click.echo()
            print_success(f"Digest saved to: {output_path}")

    except ValueError as e:
        print_error(str(e))
        click.echo()
        click.echo("Make sure you have set your ANTHROPIC_API_KEY in the .env file.")
        sys.exit(1)

    except RuntimeError as e:
        print_error(str(e))
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo()
        click.echo(click.style("Operation cancelled by user.", fg="yellow"))
        sys.exit(0)

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
