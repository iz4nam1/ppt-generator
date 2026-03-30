"""
payments/payment_service.py
============================
Payment processing service — ready for Razorpay or Stripe.

CURRENT STATE:  All functions are placeholders. No real payment processing.
ACTIVATE:       Implement the gateway-specific logic in the TODOs below.
                The rest of the system (credits, DB) is already wired.

CREDIT PACKAGES (adjust prices as needed):
    Starter  — ₹99   → 100 credits
    Popular  — ₹299  → 350 credits  (best value)
    Pro      — ₹599  → 800 credits

HOW TO ADD RAZORPAY:
    pip install razorpay
    import razorpay
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

HOW TO ADD STRIPE:
    pip install stripe
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
"""

import logging
import uuid
from datetime import datetime
from app.database import get_db
from app.services.credits import add_credits

log = logging.getLogger(__name__)


# ── Credit packages ────────────────────────────────────────────────────────────
CREDIT_PACKAGES = {
    "starter": {"credits": 100, "price_inr": 99,  "price_usd": 1.99},
    "popular": {"credits": 350, "price_inr": 299, "price_usd": 4.99},
    "pro":     {"credits": 800, "price_inr": 599, "price_usd": 9.99},
}


def create_payment_order(user_id: str, package_key: str, gateway: str = "razorpay") -> dict:
    """
    Create a payment order with the gateway and return order details to frontend.

    CURRENT:  Returns a mock order (not real)
    FUTURE:
        Razorpay:
            order = razorpay_client.order.create({
                "amount": package["price_inr"] * 100,  # paise
                "currency": "INR",
                "receipt": order_id,
            })
            return {"order_id": order["id"], "amount": order["amount"], ...}

        Stripe:
            intent = stripe.PaymentIntent.create(
                amount=int(package["price_usd"] * 100),  # cents
                currency="usd",
            )
            return {"client_secret": intent.client_secret, ...}

    Args:
        user_id:     Buying user
        package_key: 'starter' | 'popular' | 'pro'
        gateway:     'razorpay' | 'stripe'

    Returns:
        dict with order details for frontend to initiate payment UI
    """
    package = CREDIT_PACKAGES.get(package_key)
    if not package:
        return {"success": False, "error": f"Unknown package: {package_key}"}

    order_id = uuid.uuid4().hex

    # Store pending payment in DB
    with get_db() as conn:
        conn.execute(
            """INSERT INTO payments
               (id, user_id, amount_inr, credits_added, gateway, status, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (order_id, user_id, package["price_inr"], package["credits"],
             gateway, "pending", datetime.utcnow().isoformat())
        )

    log.info(f"[PLACEHOLDER] Payment order created: {order_id} for {user_id} / {package_key}")

    # TODO: Replace with real gateway call (see docstring above)
    return {
        "success":    True,
        "order_id":   order_id,
        "package":    package_key,
        "credits":    package["credits"],
        "amount_inr": package["price_inr"],
        "gateway":    gateway,
        "mock":       True,  # Remove when real gateway is wired
    }


def process_payment(user_id: str, order_id: str, gateway_txn_id: str) -> dict:
    """
    Verify payment with gateway and credit the user.

    CURRENT:  Placeholder — does not verify with any gateway
    FUTURE:
        Razorpay:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id":   order_id,
                "razorpay_payment_id": gateway_txn_id,
                "razorpay_signature":  signature_from_frontend,
            })

        Stripe:
            # Use webhook endpoint instead — see create_stripe_webhook below

        On success:
            mark payment success in DB
            call add_credits(user_id, credits_to_add, reason='purchase')

    Args:
        user_id:        User who paid
        order_id:       Our internal order ID
        gateway_txn_id: Payment ID from gateway

    Returns:
        dict with success status and new credit balance
    """
    log.info(f"[PLACEHOLDER] process_payment: {order_id} / {gateway_txn_id}")

    # TODO: Verify with real gateway
    # TODO: On success, update payment row status to 'success'
    # TODO: Call add_credits() with the purchased amount

    # Example of what the real implementation looks like:
    # with get_db() as conn:
    #     payment = conn.execute(
    #         "SELECT * FROM payments WHERE id=? AND user_id=? AND status='pending'",
    #         (order_id, user_id)
    #     ).fetchone()
    #
    #     if not payment:
    #         return {"success": False, "error": "Order not found"}
    #
    #     # Verify with gateway here...
    #
    #     conn.execute(
    #         "UPDATE payments SET status='success', gateway_txn_id=? WHERE id=?",
    #         (gateway_txn_id, order_id)
    #     )
    #
    # new_balance = add_credits(user_id, payment["credits_added"], reason="purchase")
    # return {"success": True, "credits_added": payment["credits_added"], "new_balance": new_balance}

    return {
        "success": False,
        "message": "Payment processing not yet implemented.",
        "mock":    True,
    }


def handle_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Handle Stripe webhook for async payment confirmation.

    FUTURE:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        if event["type"] == "payment_intent.succeeded":
            process_payment(...)
    """
    log.info("[PLACEHOLDER] Stripe webhook received")
    return {"received": True}


def get_payment_history(user_id: str) -> list:
    """Get payment history for a user. FUTURE: Expose via GET /me/payments"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, amount_inr, credits_added, gateway, status, created_at
               FROM payments WHERE user_id=? ORDER BY created_at DESC""",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]
