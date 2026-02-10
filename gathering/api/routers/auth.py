"""
Authentication router for GatheRing API.
Provides login, registration, and token management endpoints.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from gathering.api.auth import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    authenticate_user,
    blacklist_token,
    create_access_token,
    create_user,
    get_blacklist_stats,
    get_current_active_user,
    get_user_by_email,
    log_auth_event,
    require_admin,
    ACCESS_TOKEN_EXPIRE_HOURS,
    oauth2_scheme_required,
)
from gathering.api.dependencies import DatabaseService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Authenticate user and return JWT token.

    Accepts OAuth2 password flow (username field is used as email).

    - **username**: User email address
    - **password**: User password

    Returns JWT access token valid for 24 hours.
    """
    db = DatabaseService.get_instance()
    user = await authenticate_user(form_data.username, form_data.password, db=db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.post("/login/json", response_model=Token)
async def login_json(credentials: UserLogin):
    """
    Authenticate user with JSON body and return JWT token.

    Alternative to OAuth2 form-based login for API clients.

    - **email**: User email address
    - **password**: User password

    Returns JWT access token valid for 24 hours.
    """
    db = DatabaseService.get_instance()
    user = await authenticate_user(credentials.email, credentials.password, db=db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.

    - **email**: Unique email address
    - **password**: Password (min 8 characters)
    - **name**: User display name

    Returns the created user (without password).
    """
    db = DatabaseService.get_instance()

    # Check if email already exists
    existing = await get_user_by_email(user_data.email, db=db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = await create_user(user_data, db=db)

    # Log registration event
    log_auth_event(db, "user_registered", user_id=user["id"], message=f"New user registered: {user_data.email}")

    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user.get("created_at"),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[TokenData, Depends(get_current_active_user)]
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    # For admin, return admin info
    if current_user.sub == "admin":
        return UserResponse(
            id="admin",
            email=current_user.email or "admin@localhost",
            name="Administrator",
            role="admin",
            is_active=True,
        )

    # For database users, fetch from DB
    from gathering.api.auth import get_user_by_id

    db = DatabaseService.get_instance()
    user = await get_user_by_id(current_user.sub, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("name", ""),
        role=user.get("role", "user"),
        is_active=user.get("is_active", True),
        created_at=user.get("created_at"),
    )


@router.post("/verify")
async def verify_token(
    current_user: Annotated[TokenData, Depends(get_current_active_user)]
):
    """
    Verify that the current token is valid.

    Returns token information if valid.
    """
    return {
        "valid": True,
        "user_id": current_user.sub,
        "email": current_user.email,
        "role": current_user.role,
        "expires_at": current_user.exp.isoformat() if current_user.exp else None,
    }


@router.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme_required)],
    current_user: Annotated[TokenData, Depends(get_current_active_user)]
):
    """
    Logout the current user by blacklisting their token.

    The token will be invalidated until its original expiry time.
    Subsequent requests with this token will be rejected.

    Requires valid JWT token in Authorization header.
    """
    success = blacklist_token(token, user_id=current_user.sub)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to invalidate token",
        )

    return {
        "message": "Successfully logged out",
        "user_id": current_user.sub,
    }


@router.get("/blacklist/stats")
async def get_token_blacklist_stats(
    current_user: Annotated[TokenData, Depends(require_admin)]
):
    """
    Get token blacklist statistics (admin only).

    Returns the number of blacklisted tokens and last cleanup time.
    """
    return get_blacklist_stats()
