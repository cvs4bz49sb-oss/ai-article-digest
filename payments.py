"""Stripe payment integration for credit purchases."""

import os
import stripe
from flask import url_for

from models import db, User, Purchase
from auth import add_credits

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

# Pricing tiers (credits, price in cents, name)
PRICING_TIERS = [
    {'credits': 1, 'price_cents': 100, 'name': '1 Generation', 'description': 'Single digest generation'},
    {'credits': 10, 'price_cents': 900, 'name': '10 Generations', 'description': 'Save 10% - $0.90 each'},
    {'credits': 100, 'price_cents': 7500, 'name': '100 Generations', 'description': 'Save 25% - $0.75 each'},
]


def get_pricing_tiers():
    """Return available pricing tiers."""
    return PRICING_TIERS


def create_checkout_session(user: User, tier_index: int, success_url: str, cancel_url: str) -> str | None:
    """Create a Stripe checkout session for purchasing credits."""
    if tier_index < 0 or tier_index >= len(PRICING_TIERS):
        return None

    tier = PRICING_TIERS[tier_index]

    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': tier['name'],
                        'description': tier['description'],
                    },
                    'unit_amount': tier['price_cents'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user.email,
            metadata={
                'user_id': user.id,
                'credits': tier['credits'],
                'tier_index': tier_index,
            }
        )

        # Record the pending purchase
        purchase = Purchase(
            user_id=user.id,
            stripe_session_id=checkout_session.id,
            credits_purchased=tier['credits'],
            amount_cents=tier['price_cents'],
            status='pending'
        )
        db.session.add(purchase)
        db.session.commit()

        return checkout_session.url

    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return None


def handle_successful_payment(session_id: str) -> bool:
    """Handle a successful payment by adding credits to the user."""
    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != 'paid':
            return False

        # Find the purchase record
        purchase = Purchase.query.filter_by(stripe_session_id=session_id).first()
        if not purchase:
            return False

        # Check if already processed
        if purchase.status == 'completed':
            return True  # Already processed, just return success

        # Update purchase status
        purchase.status = 'completed'
        purchase.stripe_payment_intent = session.payment_intent

        # Add credits to user
        user = User.query.get(purchase.user_id)
        if user:
            add_credits(user, purchase.credits_purchased)

        db.session.commit()
        return True

    except stripe.error.StripeError as e:
        print(f"Stripe error handling payment: {e}")
        return False


def handle_webhook_event(payload: bytes, sig_header: str, webhook_secret: str) -> bool:
    """Handle Stripe webhook events."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return False
    except stripe.error.SignatureVerificationError:
        return False

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session['id'])

    return True
