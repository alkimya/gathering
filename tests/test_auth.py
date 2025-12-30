"""
Tests for authentication module.
Tests JWT token creation/validation, password hashing, and auth endpoints.
"""

import os
import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from gathering.api.auth import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_admin_credentials,
    authenticate_user,
    TokenData,
    ACCESS_TOKEN_EXPIRE_HOURS,
)


# =============================================================================
# Password Hashing Tests
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing produces a bcrypt hash."""
        password = "secure_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test verifying correct password returns True."""
        password = "test_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password returns False."""
        password = "test_password"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")

        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# =============================================================================
# JWT Token Tests
# =============================================================================


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "user123", "email": "test@example.com", "role": "user"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "user456", "email": "user@test.com", "role": "admin"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.sub == "user456"
        assert decoded.email == "user@test.com"
        assert decoded.role == "admin"

    def test_decode_token_has_expiration(self):
        """Test that decoded token contains expiration."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.exp is not None
        assert decoded.exp > datetime.now(timezone.utc)

    def test_token_with_custom_expiration(self):
        """Test token with custom expiration time."""
        data = {"sub": "user123"}
        expires = timedelta(hours=1)
        token = create_access_token(data, expires_delta=expires)

        decoded = decode_token(token)

        assert decoded is not None
        # Should expire within ~1 hour (with some tolerance)
        time_diff = decoded.exp - datetime.now(timezone.utc)
        assert timedelta(minutes=59) < time_diff < timedelta(hours=1, minutes=1)

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        invalid_token = "invalid.token.here"
        decoded = decode_token(invalid_token)

        assert decoded is None

    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        data = {"sub": "user123"}
        # Create token that expired 1 hour ago
        expires = timedelta(hours=-1)
        token = create_access_token(data, expires_delta=expires)

        decoded = decode_token(token)

        assert decoded is None

    def test_decode_tampered_token(self):
        """Test decoding a tampered token returns None."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Tamper with the token
        tampered = token[:-5] + "xxxxx"

        decoded = decode_token(tampered)

        assert decoded is None

    def test_token_default_role(self):
        """Test token without role defaults to 'user'."""
        data = {"sub": "user123"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded.role == "user"


# =============================================================================
# Admin Authentication Tests
# =============================================================================


class TestAdminAuthentication:
    """Tests for admin authentication from environment variables."""

    def test_verify_admin_no_env_vars(self):
        """Test admin verification fails when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = verify_admin_credentials("admin@test.com", "password")
            assert result is None

    def test_verify_admin_correct_credentials(self):
        """Test admin verification with correct credentials."""
        admin_email = "admin@example.com"
        admin_password = "secure_admin_pass"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            result = verify_admin_credentials(admin_email, admin_password)

            assert result is not None
            assert result.id == "admin"
            assert result.email == admin_email
            assert result.role == "admin"

    def test_verify_admin_wrong_email(self):
        """Test admin verification fails with wrong email."""
        admin_hash = get_password_hash("password")

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": "admin@example.com",
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            result = verify_admin_credentials("wrong@example.com", "password")
            assert result is None

    def test_verify_admin_wrong_password(self):
        """Test admin verification fails with wrong password."""
        admin_hash = get_password_hash("correct_password")

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": "admin@example.com",
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            result = verify_admin_credentials("admin@example.com", "wrong_password")
            assert result is None

    def test_verify_admin_case_insensitive_email(self):
        """Test admin email verification is case insensitive."""
        admin_email = "Admin@Example.COM"
        admin_password = "password"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            result = verify_admin_credentials("admin@example.com", admin_password)
            assert result is not None


# =============================================================================
# User Authentication Service Tests
# =============================================================================


class TestAuthenticateUser:
    """Tests for the authenticate_user service function."""

    @pytest.mark.asyncio
    async def test_authenticate_admin_user(self):
        """Test authenticating as admin user."""
        admin_email = "admin@test.com"
        admin_password = "admin_password"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            result = await authenticate_user(admin_email, admin_password)

            assert result is not None
            assert result["id"] == "admin"
            assert result["email"] == admin_email
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self):
        """Test authentication fails with invalid credentials."""
        with patch.dict(os.environ, {}, clear=True):
            result = await authenticate_user("nobody@test.com", "wrong")
            assert result is None


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from gathering.api.main import create_app
        app = create_app(enable_cors=False)
        return TestClient(app)

    def test_login_endpoint_with_admin(self, client):
        """Test login endpoint with admin credentials."""
        admin_email = "admin@test.com"
        admin_password = "admin123"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            response = client.post(
                "/auth/login",
                data={"username": admin_email, "password": admin_password},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == ACCESS_TOKEN_EXPIRE_HOURS * 3600

    def test_login_endpoint_invalid_credentials(self, client):
        """Test login endpoint with invalid credentials."""
        response = client.post(
            "/auth/login",
            data={"username": "invalid@test.com", "password": "wrong"},
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_json_endpoint(self, client):
        """Test JSON login endpoint."""
        admin_email = "admin@test.com"
        admin_password = "admin123"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            response = client.post(
                "/auth/login/json",
                json={"email": admin_email, "password": admin_password},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    def test_register_endpoint(self, client):
        """Test user registration endpoint."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "password123",
                "name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["name"] == "New User"
        assert data["role"] == "user"
        assert data["is_active"] is True

    def test_register_duplicate_email(self, client):
        """Test registration fails with duplicate email."""
        user_data = {
            "email": "duplicate@test.com",
            "password": "password123",
            "name": "User One",
        }

        # First registration should succeed
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 201

        # Second registration with same email should fail
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]

    def test_me_endpoint_authenticated(self, client):
        """Test /me endpoint with valid token."""
        admin_email = "admin@test.com"
        admin_password = "admin123"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            # Login first
            login_response = client.post(
                "/auth/login",
                data={"username": admin_email, "password": admin_password},
            )
            token = login_response.json()["access_token"]

            # Get user info
            response = client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "admin"
            assert data["role"] == "admin"

    def test_me_endpoint_unauthenticated(self, client):
        """Test /me endpoint without token."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_me_endpoint_invalid_token(self, client):
        """Test /me endpoint with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    def test_verify_endpoint(self, client):
        """Test token verification endpoint."""
        admin_email = "admin@test.com"
        admin_password = "admin123"
        admin_hash = get_password_hash(admin_password)

        with patch.dict(os.environ, {
            "ADMIN_EMAIL": admin_email,
            "ADMIN_PASSWORD_HASH": admin_hash,
        }):
            # Login first
            login_response = client.post(
                "/auth/login",
                data={"username": admin_email, "password": admin_password},
            )
            token = login_response.json()["access_token"]

            # Verify token
            response = client.post(
                "/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user_id"] == "admin"
            assert data["role"] == "admin"


# =============================================================================
# Token Data Model Tests
# =============================================================================


class TestTokenDataModel:
    """Tests for TokenData Pydantic model."""

    def test_token_data_with_all_fields(self):
        """Test TokenData with all fields."""
        token_data = TokenData(
            sub="user123",
            email="user@test.com",
            role="admin",
            exp=datetime.now(timezone.utc),
        )

        assert token_data.sub == "user123"
        assert token_data.email == "user@test.com"
        assert token_data.role == "admin"

    def test_token_data_defaults(self):
        """Test TokenData default values."""
        token_data = TokenData(sub="user123")

        assert token_data.sub == "user123"
        assert token_data.email is None
        assert token_data.role == "user"
        assert token_data.exp is None
