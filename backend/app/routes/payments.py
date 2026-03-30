"""
routes/payments.py
==================
Payment endpoints — ready for Razorpay or Stripe.

CURRENT STATE:  Endpoints exist but return placeholder responses.
ACTIVATE:       Implement payment_service.py then flip PAYMENTS_LIVE=True.

FRONTEND FLOW (when live):
    1. User picks a credit package
    2. POST /payments/create-order  → get order_id + gateway details
    3. Frontend opens Razorpay/Stripe checkout with those details
    4. User pays
    5. Gateway calls POST /payments/webhook (Stripe) OR
       Frontend calls POST /payments/verify (Razorpay)
    6. Credits added to user account
    7. Frontend shows new credit balance
"""

import logging
from fastapi import APIRouter, Form, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.payments.payment_service import (
    create_payment_order,
    process_payment,
    handle_stripe_webhook,
    get_payment_history,
    CREDIT_PACKAGES,
)

log     = logging.getLogger(__name__)
router  = APIRouter(prefix="/payments", tags=["payments"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/packages")
async def list_packages():
    """Return available credit packages and their prices."""
    return {"packages": CREDIT_PACKAGES}


@router.post("/create-order")
@limiter.limit("10/minute")
async def create_order(
    request:     Request,
    user_id:     str = Form(...),
    package_key: str = Form(...),
    gateway:     str = Form(default="razorpay"),
):
    """
    Create a payment order.
    CURRENT:  Returns mock order (not real).
    FUTURE:   Returns real gateway order for frontend checkout.
    """
    if not user_id:
        raise HTTPException(400, "user_id required.")
    if package_key not in CREDIT_PACKAGES:
        raise HTTPException(400, f"Invalid package. Choose from: {list(CREDIT_PACKAGES.keys())}")

    result = create_payment_order(user_id, package_key, gateway)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Could not create order."))

    return result


@router.post("/verify")
@limiter.limit("10/minute")
async def verify_payment(
    request:        Request,
    user_id:        str = Form(...),
    order_id:       str = Form(...),
    gateway_txn_id: str = Form(...),
):
    """
    Verify payment and credit the user.
    Used for Razorpay (client-side verification flow).
    FUTURE: Razorpay sends payment_id + signature — verify both here.
    """
    result = process_payment(user_id, order_id, gateway_txn_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("message", "Payment verification failed."))
    return result


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe webhook endpoint — Stripe calls this after successful payment.
    FUTURE: Register this URL in your Stripe dashboard as webhook endpoint.
    """
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result     = handle_stripe_webhook(payload, sig_header)
    return result


@router.get("/history")
@limiter.limit("20/minute")
async def payment_history(request: Request, user_id: str):
    """Get payment history for a user."""
    if not user_id:
        raise HTTPException(400, "user_id required.")
    return {"payments": get_payment_history(user_id)}
