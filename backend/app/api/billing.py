"""Billing API endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter()


@router.post("/checkout")
async def create_checkout_session(db: AsyncSession = Depends(get_db)):
    """Create Stripe Checkout session."""
    # TODO: Implement Stripe Checkout
    return {"checkout_url": "https://checkout.stripe.com/..."}


@router.post("/webhooks")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhooks."""
    # TODO: Implement webhook handler
    return {"received": True}


@router.get("/portal")
async def customer_portal(db: AsyncSession = Depends(get_db)):
    """Get Stripe Customer Portal link."""
    # TODO: Implement portal link generation
    return {"portal_url": "https://billing.stripe.com/..."}
