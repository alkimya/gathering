"""
Authentication module for GatheRing API.
Implements JWT-based authentication with admin from .env and users from database.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
from pydantic import BaseModel, EmailStr, Field

from gathering.core.config import get_settings


# =============================================================================
# Configuration
# =============================================================================

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
oauth2_scheme_required = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# =============================================================================
# Schemas
# =============================================================================


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration in seconds")


class TokenData(BaseModel):
    """Decoded JWT token data."""
    sub: str  # user_id or "admin"
    email: Optional[str] = None
    role: str = "user"
    exp: Optional[datetime] = None


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response (without password)."""
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None


class AdminUser(BaseModel):
    """Admin user from environment variables."""
    id: str = "admin"
    email: str
    name: str = "Administrator"
    role: str = "admin"
    is_active: bool = True


# =============================================================================
# Password Utilities
# =============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# =============================================================================
# JWT Utilities
# =============================================================================


def get_secret_key() -> str:
    """Get JWT secret key from settings."""
    settings = get_settings()
    return settings.secret_key.get_secret_value()


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data (should include 'sub' for user identification)
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, check_blacklist: bool = True) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        check_blacklist: Whether to check if token is blacklisted

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        # Check if token is blacklisted (for logout)
        if check_blacklist and is_token_blacklisted(token):
            return None

        return TokenData(
            sub=user_id,
            email=payload.get("email"),
            role=payload.get("role", "user"),
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc) if payload.get("exp") else None
        )
    except PyJWTError:
        return None


# =============================================================================
# Token Blacklist (for logout/revocation)
# =============================================================================

# In-memory blacklist with automatic cleanup
# Format: {token_hash: expiry_timestamp}
_token_blacklist: dict[str, float] = {}
_blacklist_cleanup_interval = 3600  # Clean up every hour
_last_cleanup = 0.0


def _get_token_hash(token: str) -> str:
    """Get a hash of the token for storage (don't store full tokens)."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _cleanup_blacklist() -> None:
    """Remove expired tokens from blacklist."""
    global _last_cleanup
    now = datetime.now(timezone.utc).timestamp()

    if now - _last_cleanup < _blacklist_cleanup_interval:
        return

    expired = [h for h, exp in _token_blacklist.items() if exp < now]
    for h in expired:
        _token_blacklist.pop(h, None)

    _last_cleanup = now


def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist (for logout).

    The token will remain blacklisted until its original expiry time.

    Args:
        token: JWT token to blacklist

    Returns:
        True if blacklisted successfully
    """
    try:
        # Decode without checking blacklist to get expiry
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        exp = payload.get("exp", 0)

        # Only blacklist if not already expired
        now = datetime.now(timezone.utc).timestamp()
        if exp > now:
            token_hash = _get_token_hash(token)
            _token_blacklist[token_hash] = exp

            # Periodic cleanup
            _cleanup_blacklist()

        return True
    except PyJWTError:
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token: JWT token to check

    Returns:
        True if blacklisted, False otherwise
    """
    token_hash = _get_token_hash(token)
    exp = _token_blacklist.get(token_hash)

    if exp is None:
        return False

    # Check if blacklist entry has expired
    now = datetime.now(timezone.utc).timestamp()
    if exp < now:
        # Clean up expired entry
        _token_blacklist.pop(token_hash, None)
        return False

    return True


def get_blacklist_stats() -> dict:
    """Get statistics about the token blacklist."""
    _cleanup_blacklist()
    return {
        "blacklisted_tokens": len(_token_blacklist),
        "last_cleanup": datetime.fromtimestamp(_last_cleanup, tz=timezone.utc).isoformat() if _last_cleanup else None,
    }


# =============================================================================
# Admin User (from .env)
# =============================================================================


def get_admin_from_env() -> Optional[AdminUser]:
    """
    Get admin user credentials from environment variables.

    Environment variables:
        ADMIN_EMAIL: Admin email address
        ADMIN_PASSWORD_HASH: Bcrypt hash of admin password

    To generate a password hash:
        python -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
    """
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if admin_email and admin_password_hash:
        return AdminUser(email=admin_email)

    return None


def verify_admin_credentials(email: str, password: str) -> Optional[AdminUser]:
    """
    Verify admin credentials from environment variables.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        email: Admin email
        password: Plain text password

    Returns:
        AdminUser if valid, None otherwise
    """
    admin_email = os.getenv("ADMIN_EMAIL", "")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

    # Use a dummy hash for timing-safe comparison when no admin configured
    # This prevents timing attacks from revealing if admin email exists
    dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWWQIe0u0S."

    if not admin_email or not admin_password_hash:
        # Still do password verification to maintain constant time
        verify_password(password, dummy_hash)
        return None

    # Constant-time email comparison (case-insensitive)
    email_match = secrets.compare_digest(
        email.lower().encode("utf-8"),
        admin_email.lower().encode("utf-8")
    )

    # Always verify password to prevent timing attacks
    password_valid = verify_password(password, admin_password_hash)

    # Only return admin if BOTH email and password match
    if email_match and password_valid:
        return AdminUser(email=admin_email)

    return None


# =============================================================================
# Database User Operations (to be implemented with actual DB)
# =============================================================================


# In-memory user store for development (replace with database in production)
_users_store: dict[str, dict] = {}


async def get_user_by_email(email: str) -> Optional[dict]:
    """
    Get user by email from database.

    TODO: Replace with actual database query.
    """
    return _users_store.get(email.lower())


async def get_user_by_id(user_id: str) -> Optional[dict]:
    """
    Get user by ID from database.

    TODO: Replace with actual database query.
    """
    for user in _users_store.values():
        if user.get("id") == user_id:
            return user
    return None


async def create_user(user_data: UserCreate) -> dict:
    """
    Create a new user in the database.

    TODO: Replace with actual database insert.
    """
    import uuid

    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email.lower(),
        "name": user_data.name,
        "password_hash": get_password_hash(user_data.password),
        "role": "user",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    _users_store[user_data.email.lower()] = user
    return user


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[TokenData]:
    """
    Get current user from JWT token (optional - returns None if no token).
    Use this for endpoints that work with or without authentication.
    """
    if token is None:
        return None

    token_data = decode_token(token)
    return token_data


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme_required)]
) -> TokenData:
    """
    Get current user from JWT token (required).
    Raises 401 if token is invalid or missing.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception

    return token_data


async def get_current_active_user(
    current_user: Annotated[TokenData, Depends(get_current_user)]
) -> TokenData:
    """
    Get current active user.
    Additional check that user is still active (for database users).
    """
    # For admin users, always active
    if current_user.sub == "admin":
        return current_user

    # For database users, check if still active
    user = await get_user_by_id(current_user.sub)
    if user is None or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or does not exist",
        )

    return current_user


async def require_admin(
    current_user: Annotated[TokenData, Depends(get_current_user)]
) -> TokenData:
    """
    Require admin role.
    Raises 403 if user is not an admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


# =============================================================================
# Authentication Service
# =============================================================================


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by email and password.
    Checks admin credentials first, then database users.

    Returns:
        User dict with 'id', 'email', 'role' if valid, None otherwise
    """
    # Check admin first
    admin = verify_admin_credentials(email, password)
    if admin:
        return {
            "id": admin.id,
            "email": admin.email,
            "name": admin.name,
            "role": admin.role,
        }

    # Check database users
    user = await get_user_by_email(email)
    if user is None:
        return None

    if not verify_password(password, user.get("password_hash", "")):
        return None

    if not user.get("is_active", False):
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role", "user"),
    }
