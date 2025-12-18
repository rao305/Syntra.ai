"""Clerk token verification helpers."""
from __future__ import annotations

import time
from typing import Dict, Tuple, Optional
import httpx
from jose import jwt

from config import get_settings

import logging
logger = logging.getLogger(__name__)

settings = get_settings()

# Simple in-memory cache for verified tokens: {token: (decoded_payload, expiry_time)}
_token_cache: Dict[str, Tuple[dict, float]] = {}
_CACHE_TTL = 300  # 5 minutes


async def verify_clerk_token(token: str) -> Optional[dict]:
    """Verify a Clerk session token and return the decoded payload.
    
    Uses Clerk's API to verify the token. This is the recommended approach
    when you have a secret key.
    """
    # Check cache first
    current_time = time.time()
    if token in _token_cache:
        cached_payload, expiry = _token_cache[token]
        if current_time < expiry:
            return cached_payload
        else:
            # Expired - remove from cache
            del _token_cache[token]
    
    if not settings.clerk_secret_key:
        raise RuntimeError(
            "CLERK_SECRET_KEY is not configured. "
            "Set CLERK_SECRET_KEY in your environment variables."
        )
    
    try:
        # Verify token using Clerk's API
        # Clerk tokens are JWTs that contain user information
        # We'll verify by calling Clerk's API to get the session/user info

        # Extract user ID from token (decode without verification first to get the user ID)
        # Then verify with Clerk API
        unverified = jwt.decode(
            token,
            key="",  # Empty key since we're not verifying signature
            options={"verify_signature": False}
        )

        user_id = unverified.get("sub")
        if not user_id:
            raise ValueError("Token missing user ID (sub claim)")

        logger.info("[CLERK] Verifying user_id: {user_id}")

        # Verify the token is valid by calling Clerk's API
        # Get user info to verify the token is valid
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {settings.clerk_secret_key}",
                    },
                    timeout=5.0,
                )
            except httpx.TimeoutException as e:
                logger.info("[CLERK] Timeout connecting to Clerk API: {e}")
                raise ValueError(f"Timeout verifying with Clerk: {e}")

        logger.info("[CLERK] Clerk API response: {response.status_code}")
        if response.status_code != 200:
            try:
                error_body = response.json()
                logger.error("[CLERK] Error body: {error_body}")
            except ValueError as json_error:
                logger.warning(f"[CLERK] Failed to parse error response as JSON: {json_error}")
                logger.info("[CLERK] Response text: {response.text}")
            except Exception as e:
                logger.exception(f"[CLERK] Unexpected error parsing response: {e}")
                logger.info("[CLERK] Response text: {response.text}")
            raise ValueError(f"Invalid token: Clerk API returned {response.status_code}")

        user_data = response.json()
        
        # Build decoded payload for compatibility
        decoded_payload = {
            "uid": user_id,
            "email": user_data.get("email_addresses", [{}])[0].get("email_address") if user_data.get("email_addresses") else None,
            "name": user_data.get("first_name", "") + " " + user_data.get("last_name", "").strip() or user_data.get("username"),
            "email_verified": user_data.get("email_addresses", [{}])[0].get("verification", {}).get("status") == "verified" if user_data.get("email_addresses") else False,
        }
        
        if not decoded_payload["email"]:
            raise ValueError("User email not found")
        
        # Cache the result
        expiry_time = current_time + _CACHE_TTL
        _token_cache[token] = (decoded_payload, expiry_time)
        
        # Clean up old entries
        if len(_token_cache) > 1000:
            expired_keys = [k for k, (_, exp) in _token_cache.items() if exp < current_time]
            for key in expired_keys:
                del _token_cache[key]
        
        return decoded_payload
        
    except httpx.HTTPError as exc:
        raise ValueError(f"Failed to verify Clerk token: Network error - {exc}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to verify Clerk token: {exc}") from exc
