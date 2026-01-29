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


@app.route("/branding")
def branding():
    """Render the branding customization page."""
    return render_template("branding.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Generate a digest from the submitted URL."""
    url = request.form.get("url", "").strip()
    count = request.form.get("count", "10")

    try:
        count = int(count)
        count = max(1, min(count, 20))  # Limit between 1 and 20
    except ValueError:
        count = 10

    if not url:
        return render_template("index.html", error="Please enter a URL")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        # Scrape articles
        scraper = ArticleScraper(url)
        articles = scraper.scrape_articles(count)

        if not articles:
            return render_template("index.html", error="No articles found at that URL")

        # Generate digest
        generator = DigestGenerator()
        digest = generator.generate_digest(articles)
        formatted = generator.format_digest(digest)

        return render_template(
            "result.html",
            digest=digest,
            formatted=formatted,
            url=url,
            count=len(articles)
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
        articles = scraper.scrape_articles(count)

        if not articles:
            return jsonify({"error": "No articles found"}), 404

        generator = DigestGenerator()
        digest = generator.generate_digest(articles)

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
