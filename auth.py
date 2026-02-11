"""Authentication module with magic link email login."""

import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urljoin

from flask import session, redirect, url_for, request, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from models import db, User

# Token expiry time (1 hour)
TOKEN_EXPIRY_SECONDS = 3600

# Admin email (gets unlimited free access)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')


def get_serializer():
    """Get the URL-safe serializer for magic links."""
    secret_key = current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret_key)


def generate_magic_link(email: str, base_url: str) -> str:
    """Generate a magic link for email authentication."""
    serializer = get_serializer()
    token = serializer.dumps(email, salt='magic-link')
    return urljoin(base_url, f'/auth/verify?token={token}')


def verify_magic_link(token: str) -> str | None:
    """Verify a magic link token and return the email if valid."""
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='magic-link', max_age=TOKEN_EXPIRY_SECONDS)
        return email
    except (SignatureExpired, BadSignature):
        return None


def get_or_create_user(email: str) -> User:
    """Get existing user or create a new one."""
    email = email.lower().strip()
    user = User.query.filter_by(email=email).first()

    if not user:
        # Check if this is the admin email
        is_admin = (email == ADMIN_EMAIL.lower()) if ADMIN_EMAIL else False

        user = User(
            email=email,
            credits=1 if not is_admin else 0,  # Give new users 1 free credit, admin gets unlimited
            is_admin=is_admin
        )
        db.session.add(user)
        db.session.commit()

    return user


def login_user(user: User):
    """Log in a user by setting session data."""
    user.last_login = datetime.utcnow()
    db.session.commit()

    session['user_id'] = user.id
    session['user_email'] = user.email
    session['is_admin'] = user.is_admin


def logout_user():
    """Log out the current user."""
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('is_admin', None)


def get_current_user() -> User | None:
    """Get the currently logged-in user."""
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None


def is_logged_in() -> bool:
    """Check if a user is logged in."""
    return 'user_id' in session


def can_generate(user: User) -> bool:
    """Check if a user can generate a digest (has credits or is admin)."""
    if user.is_admin:
        return True
    return user.credits > 0


def use_credit(user: User) -> bool:
    """Use one credit for a generation. Returns True if successful."""
    if user.is_admin:
        return True  # Admins don't use credits

    if user.credits > 0:
        user.credits -= 1
        db.session.commit()
        return True

    return False


def add_credits(user: User, amount: int):
    """Add credits to a user's account."""
    user.credits += amount
    db.session.commit()


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            # Store the intended destination
            session['next_url'] = request.url
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def credits_required(f):
    """Decorator to require login AND available credits for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            session['next_url'] = request.url
            return redirect(url_for('login_page'))

        user = get_current_user()
        if not user:
            return redirect(url_for('login_page'))

        if not can_generate(user):
            return redirect(url_for('pricing_page'))

        return f(*args, **kwargs)
    return decorated_function
