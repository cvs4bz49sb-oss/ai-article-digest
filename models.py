"""Database models for user authentication and credit tracking."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """User model for tracking credits and authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    credits = db.Column(db.Integer, default=0, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationship to purchases
    purchases = db.relationship('Purchase', backref='user', lazy=True)
    generations = db.relationship('Generation', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Purchase(db.Model):
    """Track credit purchases."""
    __tablename__ = 'purchases'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stripe_session_id = db.Column(db.String(255), unique=True)
    stripe_payment_intent = db.Column(db.String(255))
    credits_purchased = db.Column(db.Integer, nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)  # Amount in cents
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Purchase {self.id} - {self.credits_purchased} credits>'


class Generation(db.Model):
    """Track digest generations for usage history."""
    __tablename__ = 'generations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(500))
    article_count = db.Column(db.Integer)
    output_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Generation {self.id} - {self.url}>'
