"""Per-endpoint rate limiting using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limit tiers
TIER_AUTH = "5/minute"        # Authentication endpoints (login, register)
TIER_WRITE = "30/minute"      # Write/mutation endpoints (POST, PUT, DELETE)
TIER_READ = "120/minute"      # Read endpoints (GET listings)
TIER_HEALTH = "300/minute"    # Health/status/docs endpoints


def create_limiter() -> Limiter:
    """Create the rate limiter with optional Redis backend."""
    import os
    storage_uri = os.getenv("REDIS_URL")  # None = in-memory, redis://... = distributed
    return Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=[TIER_READ],  # Default for endpoints without explicit decorator
    )


# Module-level singleton
limiter = create_limiter()
