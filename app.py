"""Flask web application for AI Article Digest Generator."""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from scraper import ArticleScraper
from summarizer import DigestGenerator

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    """Render the main page with the form."""
    return render_template("index.html")


@app.route("/history-view")
def history_view():
    """Render the history view page (data comes from localStorage via JS)."""
    return render_template("history_view.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Generate a digest from the submitted URL."""
    url = request.form.get("url", "").strip()
    mode = request.form.get("mode", "recent")
    output_type = request.form.get("output_type", "both")  # digest, social, or both
    count = request.form.get("count", "10")
    specific_urls = request.form.get("specific_urls", "").strip()

    try:
        count = int(count)
        count = max(1, min(count, 20))  # Limit between 1 and 20
    except ValueError:
        count = 10

    # For specific mode, URL is not required
    if mode != "specific" and not url:
        return render_template("index.html", error="Please enter a URL")

    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraper = ArticleScraper(url) if url else None

        if mode == "specific" and specific_urls:
            # Parse specific URLs from textarea
            urls_list = [u.strip() for u in specific_urls.split('\n') if u.strip()]
            urls_list = [u if u.startswith(('http://', 'https://')) else 'https://' + u for u in urls_list]

            if not urls_list:
                return render_template("index.html", error="Please provide at least one article URL")

            # Create scraper from first URL's domain if not already created
            if not scraper:
                scraper = ArticleScraper(urls_list[0])

            # Scrape specific articles
            articles, site_name = scraper.scrape_specific_articles(urls_list)
        else:
            # Scrape recent articles
            articles, site_name = scraper.scrape_articles(count)

        if not articles:
            return render_template("index.html", error="No articles found at that URL")

        # Generate content based on output_type
        generator = DigestGenerator()
        digest = generator.generate_digest(articles, site_name=site_name, output_type=output_type)
        formatted = generator.format_digest(digest) if output_type in ['digest', 'both'] else ""

        return render_template(
            "result.html",
            digest=digest,
            formatted=formatted,
            url=url or urls_list[0] if mode == "specific" else url,
            count=len(articles),
            output_type=output_type
        )

    except ValueError as e:
        return render_template("index.html", error=str(e))
    except RuntimeError as e:
        return render_template("index.html", error=str(e))
    except Exception as e:
        return render_template("index.html", error=f"An error occurred: {str(e)}")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """API endpoint for generating digests."""
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    count = data.get("count", 10)

    try:
        count = int(count)
        count = max(1, min(count, 20))
    except (ValueError, TypeError):
        count = 10

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        scraper = ArticleScraper(url)
        articles, site_name = scraper.scrape_articles(count)

        if not articles:
            return jsonify({"error": "No articles found"}), 404

        generator = DigestGenerator()
        digest = generator.generate_digest(articles, site_name=site_name)

        return jsonify({
            "success": True,
            "url": url,
            "article_count": len(articles),
            "digest": digest
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
