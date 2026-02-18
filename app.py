"""Flask web application for AI Article Digest Generator."""

import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv

from scraper import ArticleScraper
from summarizer import DigestGenerator
from models import db, User, Generation
from auth import (
    generate_magic_link, verify_magic_link, get_or_create_user,
    login_user, logout_user, get_current_user, is_logged_in,
    can_generate, use_credit, login_required, credits_required
)
from payments import get_pricing_tiers, create_checkout_session, handle_successful_payment

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///digest.db')
# Fix for Heroku/Railway postgres:// vs postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

with app.app_context():
    db.create_all()


def send_magic_link_email(email: str, magic_link: str) -> bool:
    """Send magic link email using SMTP."""
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not smtp_user or not smtp_pass:
        print(f"SMTP not configured. Magic link: {magic_link}")
        return True  # Return True for development

    print(f"Attempting to send email via {smtp_host}:{smtp_port} as {smtp_user}")

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Sign in to Well Done Digest'
        msg['From'] = from_email
        msg['To'] = email

        text = f"""Sign in to Well Done Digest

Click the link below to sign in:
{magic_link}

This link expires in 1 hour.

If you didn't request this, you can safely ignore this email.
"""

        html = f"""
<!DOCTYPE html>
<html>
<head></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px;">
    <div style="max-width: 500px; margin: 0 auto;">
        <h1 style="color: #1a1a1a; font-size: 24px;">Sign in to Well Done Digest</h1>
        <p style="color: #666; font-size: 16px; line-height: 1.5;">Click the button below to sign in:</p>
        <a href="{magic_link}" style="display: inline-block; background: #8b7355; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 500; margin: 20px 0;">Sign In</a>
        <p style="color: #999; font-size: 14px;">This link expires in 1 hour.</p>
        <p style="color: #999; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
    </div>
</body>
</html>
"""

        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, email, msg.as_string())

        return True

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


@app.route("/")
def index():
    """Render the main page with the form."""
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/login")
def login_page():
    """Render the login page."""
    if is_logged_in():
        return redirect(url_for('index'))
    return render_template("login.html")


@app.route("/auth/send-link", methods=["POST"])
def send_magic_link():
    """Send a magic link to the user's email."""
    email = request.form.get("email", "").strip().lower()

    if not email or "@" not in email:
        return render_template("login.html", error="Please enter a valid email address")

    # Generate magic link
    base_url = request.url_root.rstrip('/')
    magic_link = generate_magic_link(email, base_url)

    # Send email
    if send_magic_link_email(email, magic_link):
        return render_template("login.html", success=f"Check your email! We sent a sign-in link to {email}")
    else:
        return render_template("login.html", error="Failed to send email. Please try again.")


@app.route("/auth/verify")
def verify_link():
    """Verify a magic link and log the user in."""
    token = request.args.get("token", "")

    if not token:
        return render_template("login.html", error="Invalid or expired link")

    email = verify_magic_link(token)
    if not email:
        return render_template("login.html", error="Invalid or expired link. Please request a new one.")

    # Get or create user and log them in
    user = get_or_create_user(email)
    login_user(user)

    # Redirect to intended destination or home
    next_url = session.pop('next_url', None)
    return redirect(next_url or url_for('index'))


@app.route("/auth/logout")
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('index'))


@app.route("/pricing")
@login_required
def pricing_page():
    """Render the pricing page."""
    user = get_current_user()
    tiers = get_pricing_tiers()
    return render_template("pricing.html", user=user, tiers=tiers)


@app.route("/purchase", methods=["POST"])
@login_required
def purchase():
    """Initiate a credit purchase."""
    user = get_current_user()
    tier_index = int(request.form.get("tier", 0))

    success_url = request.url_root.rstrip('/') + url_for('purchase_success') + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.url_root.rstrip('/') + url_for('pricing_page')

    checkout_url = create_checkout_session(user, tier_index, success_url, cancel_url)

    if checkout_url:
        return redirect(checkout_url)
    else:
        return render_template("pricing.html", user=user, tiers=get_pricing_tiers(), error="Failed to create checkout session")


@app.route("/purchase/success")
@login_required
def purchase_success():
    """Handle successful purchase redirect."""
    session_id = request.args.get("session_id")

    if session_id:
        handle_successful_payment(session_id)

    return redirect(url_for('index'))


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
