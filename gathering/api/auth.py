"""
Authentication module for GatheRing API.
Implements JWT-based authentication with admin from .env and users from database.
"""

import json
import hashlib
import logging
import os
import secrets
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
from pydantic import BaseModel, EmailStr, Field

from gathering.core.config import get_settings
from gathering.api.dependencies import DatabaseService

logger = logging.getLogger(__name__)


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
# Audit Event Logging
# =============================================================================


def log_auth_event(
    db,
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    message: str = "",
    details: Optional[dict] = None,
    severity: str = "info",
) -> None:
    """Log authentication event to audit.security_events table.

    Fails silently (logs warning) to avoid blocking auth operations.
    """
    try:
        db.execute(
            "INSERT INTO audit.security_events "
            "(event_type, severity, user_id, ip_address, message, details) "
            "VALUES (%(event_type)s, %(severity)s, %(user_id)s, "
            "%(ip_address)s::inet, %(message)s, %(details)s::jsonb)",
            {
                "event_type": event_type,
                "severity": severity,
                "user_id": user_id,
                "ip_address": ip_address or "0.0.0.0",
                "message": message,
                "details": json.dumps(details or {}),
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log auth event: {e}")


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
# Token Blacklist (persistent with in-memory LRU cache)
# =============================================================================


def _get_token_hash(token: str) -> str:
    """Get a hash of the token for storage (don't store full tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()[:32]


class TokenBlacklist:
    """Two-layer token blacklist: in-memory LRU cache backed by PostgreSQL.

    The cache provides sub-millisecond lookups for hot tokens.
    The database ensures blacklist survives server restarts.
    Write-through: every blacklist addition writes to both layers.
    """

    _instance: Optional['TokenBlacklist'] = None

    def __init__(self, db=None, cache_max_size: int = 10000):
        self._db = db
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._cache_max_size = cache_max_size

    @classmethod
    def get_instance(cls, db=None) -> 'TokenBlacklist':
        if cls._instance is None:
            cls._instance = cls(db=db or DatabaseService.get_instance())
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _get_db(self):
        if self._db is None:
            self._db = DatabaseService.get_instance()
        return self._db

    def blacklist(self, token_hash: str, expires_at: float, user_id: str = None, reason: str = "logout") -> None:
        """Add token to blacklist (write-through to cache and DB)."""
        # Write to cache
        self._cache[token_hash] = expires_at
        if len(self._cache) > self._cache_max_size:
            self._cache.popitem(last=False)

        # Write to DB
        try:
            self._get_db().execute(
                "INSERT INTO auth.token_blacklist (token_hash, expires_at, user_id, reason) "
                "VALUES (%(hash)s, to_timestamp(%(exp)s), %(user_id)s, %(reason)s) "
                "ON CONFLICT (token_hash) DO NOTHING",
                {"hash": token_hash, "exp": expires_at, "user_id": user_id, "reason": reason}
            )
        except Exception as e:
            logger.warning(f"Failed to persist token blacklist entry: {e}")

    def is_blacklisted(self, token_hash: str) -> bool:
        """Check if token is blacklisted. Cache first, then DB fallback."""
        now = datetime.now(timezone.utc).timestamp()

        # Check cache
        if token_hash in self._cache:
            exp = self._cache[token_hash]
            if exp > now:
                return True
            else:
                del self._cache[token_hash]
                return False

        # Check DB
        try:
            result = self._get_db().execute_one(
                "SELECT EXTRACT(EPOCH FROM expires_at) as exp "
                "FROM auth.token_blacklist "
                "WHERE token_hash = %(hash)s AND expires_at > NOW()",
                {"hash": token_hash}
            )
            if result:
                # Promote to cache
                self._cache[token_hash] = float(result["exp"])
                if len(self._cache) > self._cache_max_size:
                    self._cache.popitem(last=False)
                return True
        except Exception as e:
            logger.warning(f"Failed to check token blacklist in DB: {e}")

        return False

    def get_stats(self) -> dict:
        """Get blacklist statistics."""
        try:
            db_count = self._get_db().execute_one(
                "SELECT COUNT(*) as count FROM auth.token_blacklist WHERE expires_at > NOW()"
            )
            db_total = db_count["count"] if db_count else 0
        except Exception:
            db_total = "unknown"

        return {
            "cache_size": len(self._cache),
            "cache_max_size": self._cache_max_size,
            "db_active_tokens": db_total,
        }


def blacklist_token(token: str, user_id: str = None) -> bool:
    """Add a token to the blacklist (for logout)."""
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        if exp > now:
            token_hash = _get_token_hash(token)
            TokenBlacklist.get_instance().blacklist(token_hash, exp, user_id=user_id)
        return True
    except PyJWTError:
        return False


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    token_hash = _get_token_hash(token)
    return TokenBlacklist.get_instance().is_blacklisted(token_hash)


def get_blacklist_stats() -> dict:
    """Get statistics about the token blacklist."""
    return TokenBlacklist.get_instance().get_stats()


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
# Database User Operations
# =============================================================================


async def get_user_by_email(email: str, db=None) -> Optional[dict]:
    """Get user by email from database."""
    if db is None:
        db = DatabaseService.get_instance()
    result = db.execute_one(
        "SELECT external_id as id, email, name, password_hash, role, is_active, created_at "
        "FROM auth.users WHERE email_lower = %(email)s",
        {"email": email.lower()}
    )
    return result


async def get_user_by_id(user_id: str, db=None) -> Optional[dict]:
    """Get user by external ID from database."""
    if db is None:
        db = DatabaseService.get_instance()
    result = db.execute_one(
        "SELECT external_id as id, email, name, password_hash, role, is_active, created_at "
        "FROM auth.users WHERE external_id = %(user_id)s",
        {"user_id": user_id}
    )
    return result


async def create_user(user_data: UserCreate, db=None) -> dict:
    """Create a new user in the database."""
    if db is None:
        db = DatabaseService.get_instance()
    result = db.execute_one(
        "INSERT INTO auth.users (email, name, password_hash, role, is_active) "
        "VALUES (%(email)s, %(name)s, %(password_hash)s, 'user', TRUE) "
        "RETURNING external_id as id, email, name, role, is_active, created_at",
        {
            "email": user_data.email,
            "name": user_data.name,
            "password_hash": get_password_hash(user_data.password),
        }
    )
    return result


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


async def authenticate_user(email: str, password: str, db=None) -> Optional[dict]:
    """
    Authenticate a user by email and password.
    Checks admin credentials first, then database users.
    Uses constant-time operations to prevent timing attacks.

    Returns:
        User dict with 'id', 'email', 'role' if valid, None otherwise
    """
    if db is None:
        db = DatabaseService.get_instance()

    # Check admin first (already constant-time)
    admin = verify_admin_credentials(email, password)
    if admin:
        log_auth_event(db, "auth_success", user_id="admin", message=f"Admin login: {email}")
        return {"id": admin.id, "email": admin.email, "name": admin.name, "role": admin.role}

    # Always query database (even if we'll fail -- constant time)
    user = await get_user_by_email(email, db)

    # Always verify password (use dummy hash if user not found -- constant time)
    dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWWQIe0u0S."
    stored_hash = user.get("password_hash", "") if user else dummy_hash

    password_valid = verify_password(password, stored_hash)

    if user and password_valid and user.get("is_active", False):
        log_auth_event(db, "auth_success", user_id=user["id"], message=f"User login: {email}")
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user.get("role", "user"),
        }

    # Log failure (don't reveal which part failed)
    log_auth_event(db, "auth_failure", message=f"Failed login attempt for: {email}", severity="warning")
    return None
