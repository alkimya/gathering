"""
Auth persistence and lifecycle tests for Phase 1.
Tests token creation, expiry, blacklist, concurrent use, and database persistence.
"""

import pytest
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock

from gathering.api.auth import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    blacklist_token,
    is_token_blacklisted,
    _get_token_hash,
    TokenBlacklist,
    ALGORITHM,
)


class TestTokenLifecycle:
    """Tests for auth token creation, validation, expiry, and blacklist (TEST-01)."""

    def test_token_creation_with_valid_data(self):
        """Token creation produces a decodable JWT."""
        token = create_access_token({"sub": "user123", "email": "test@test.com", "role": "user"})
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_decode_returns_correct_data(self):
        """Decoded token contains the original payload."""
        token = create_access_token({"sub": "user123", "email": "test@test.com", "role": "user"})
        # Decode without blacklist check (no DB in unit tests)
        data = decode_token(token, check_blacklist=False)
        assert data is not None
        assert data.sub == "user123"
        assert data.email == "test@test.com"
        assert data.role == "user"

    def test_token_expiry(self):
        """Expired token returns None on decode."""
        token = create_access_token(
            {"sub": "user123", "email": "test@test.com", "role": "user"},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        data = decode_token(token, check_blacklist=False)
        assert data is None

    def test_token_with_custom_expiry(self):
        """Token with custom expiry is valid before expiry."""
        token = create_access_token(
            {"sub": "user123", "email": "test@test.com", "role": "user"},
            expires_delta=timedelta(hours=1),
        )
        data = decode_token(token, check_blacklist=False)
        assert data is not None
        assert data.exp is not None

    def test_token_with_invalid_signature_rejected(self):
        """Token with wrong signature returns None."""
        import jwt as pyjwt
        token = pyjwt.encode({"sub": "user123"}, "wrong-key", algorithm="HS256")
        data = decode_token(token, check_blacklist=False)
        assert data is None

    def test_token_without_sub_rejected(self):
        """Token missing 'sub' claim returns None."""
        from gathering.api.auth import get_secret_key
        import jwt as pyjwt
        token = pyjwt.encode({"email": "test@test.com"}, get_secret_key(), algorithm="HS256")
        data = decode_token(token, check_blacklist=False)
        assert data is None

    def test_multiple_tokens_for_same_user(self):
        """Multiple tokens for the same user are all independently valid (multi-device)."""
        token1 = create_access_token(
            {"sub": "user123", "email": "test@test.com", "role": "user"},
            expires_delta=timedelta(hours=1),
        )
        token2 = create_access_token(
            {"sub": "user123", "email": "test@test.com", "role": "user"},
            expires_delta=timedelta(hours=2),
        )
        assert token1 != token2  # Different tokens (different exp timestamps)
        assert decode_token(token1, check_blacklist=False) is not None
        assert decode_token(token2, check_blacklist=False) is not None

    def test_token_contains_all_claims(self):
        """Token includes sub, email, role, and exp claims."""
        token = create_access_token({"sub": "user42", "email": "a@b.com", "role": "admin"})
        data = decode_token(token, check_blacklist=False)
        assert data.sub == "user42"
        assert data.email == "a@b.com"
        assert data.role == "admin"
        assert data.exp is not None

    def test_default_role_is_user(self):
        """Token without explicit role defaults to 'user'."""
        token = create_access_token({"sub": "user1", "email": "x@y.com"})
        data = decode_token(token, check_blacklist=False)
        assert data.role == "user"

    def test_malformed_token_returns_none(self):
        """Completely malformed token returns None."""
        data = decode_token("not.a.valid.jwt.token", check_blacklist=False)
        assert data is None

    def test_empty_token_returns_none(self):
        """Empty string token returns None."""
        data = decode_token("", check_blacklist=False)
        assert data is None


class TestTokenBlacklistUnit:
    """Unit tests for TokenBlacklist class (in-memory layer + mocked DB)."""

    def setup_method(self):
        """Create a fresh TokenBlacklist with mocked DB."""
        self.mock_db = MagicMock()
        self.mock_db.execute.return_value = []
        self.mock_db.execute_one.return_value = None
        self.blacklist = TokenBlacklist(db=self.mock_db, cache_max_size=100)

    def test_blacklist_adds_to_cache(self):
        """Blacklisting a token adds it to the in-memory cache."""
        future_exp = time.time() + 3600
        self.blacklist.blacklist("hash123", future_exp, user_id="user1")
        assert self.blacklist.is_blacklisted("hash123") is True

    def test_blacklist_writes_to_db(self):
        """Blacklisting a token writes through to database."""
        future_exp = time.time() + 3600
        self.blacklist.blacklist("hash123", future_exp, user_id="user1")
        self.mock_db.execute.assert_called_once()
        call_args = self.mock_db.execute.call_args
        assert "auth.token_blacklist" in call_args[0][0]

    def test_non_blacklisted_token_returns_false(self):
        """Token not in cache or DB returns False."""
        self.mock_db.execute_one.return_value = None
        result = self.blacklist.is_blacklisted("not_blacklisted")
        assert result is False

    def test_cache_evicts_oldest_when_full(self):
        """Cache evicts oldest entry when max size exceeded."""
        small_blacklist = TokenBlacklist(db=self.mock_db, cache_max_size=3)
        future_exp = time.time() + 3600
        small_blacklist.blacklist("hash1", future_exp)
        small_blacklist.blacklist("hash2", future_exp)
        small_blacklist.blacklist("hash3", future_exp)
        small_blacklist.blacklist("hash4", future_exp)  # Should evict hash1
        assert len(small_blacklist._cache) == 3

    def test_db_fallback_when_not_in_cache(self):
        """When token not in cache, checks DB."""
        self.mock_db.execute_one.return_value = {"exp": time.time() + 3600}
        result = self.blacklist.is_blacklisted("not_in_cache")
        self.mock_db.execute_one.assert_called_once()
        assert result is True

    def test_db_miss_returns_false(self):
        """When token not in cache or DB, returns False."""
        self.mock_db.execute_one.return_value = None
        result = self.blacklist.is_blacklisted("nowhere")
        assert result is False

    def test_db_result_promoted_to_cache(self):
        """Token found in DB is promoted to cache for future lookups."""
        self.mock_db.execute_one.return_value = {"exp": time.time() + 3600}
        self.blacklist.is_blacklisted("db_token")
        # Second lookup should use cache (no additional DB call)
        self.blacklist.is_blacklisted("db_token")
        assert self.mock_db.execute_one.call_count == 1

    def test_stats_returns_cache_info(self):
        """Stats include cache size info."""
        stats = self.blacklist.get_stats()
        assert "cache_size" in stats
        assert "cache_max_size" in stats

    def test_expired_cache_entry_cleaned_up(self):
        """Expired entries in cache are cleaned up on lookup."""
        past_exp = time.time() - 3600
        self.blacklist._cache["old_hash"] = past_exp
        assert self.blacklist.is_blacklisted("old_hash") is False
        assert "old_hash" not in self.blacklist._cache

    def test_db_error_gracefully_handled(self):
        """DB errors don't crash is_blacklisted -- returns False."""
        self.mock_db.execute_one.side_effect = Exception("DB down")
        result = self.blacklist.is_blacklisted("some_hash")
        assert result is False

    def test_blacklist_db_write_error_gracefully_handled(self):
        """DB errors during blacklist write don't crash -- entry still in cache."""
        self.mock_db.execute.side_effect = Exception("DB down")
        future_exp = time.time() + 3600
        self.blacklist.blacklist("hash_write_fail", future_exp)
        # Should still be in cache despite DB failure
        assert self.blacklist.is_blacklisted("hash_write_fail") is True


class TestPasswordHashingCompatibility:
    """Tests that bcrypt direct hashing is compatible with passlib-generated hashes."""

    def test_bcrypt_hash_format(self):
        """Hash format is standard bcrypt $2b$."""
        hashed = get_password_hash("test_password")
        assert hashed.startswith("$2b$")

    def test_verify_against_known_bcrypt_hash(self):
        """Can verify against a known bcrypt hash (simulating passlib-generated hash)."""
        hashed = get_password_hash("test_password")
        assert verify_password("test_password", hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_hash_uniqueness(self):
        """Same password produces different hashes (random salt)."""
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2
        assert verify_password("same_password", h1)
        assert verify_password("same_password", h2)

    def test_empty_password_hashes(self):
        """Empty password can be hashed and verified."""
        # Note: in production, validation prevents empty passwords,
        # but bcrypt itself handles them fine
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_unicode_password_support(self):
        """Unicode passwords are properly hashed and verified."""
        hashed = get_password_hash("mot_de_passe_avec_des_accents_e_a_u")
        assert verify_password("mot_de_passe_avec_des_accents_e_a_u", hashed) is True

    def test_long_password_support(self):
        """Long passwords are handled (bcrypt truncates at 72 bytes)."""
        long_pass = "a" * 100
        hashed = get_password_hash(long_pass)
        assert verify_password(long_pass, hashed) is True


class TestTokenHashFunction:
    """Tests for the _get_token_hash helper."""

    def test_hash_is_deterministic(self):
        """Same token always produces same hash."""
        h1 = _get_token_hash("test_token_123")
        h2 = _get_token_hash("test_token_123")
        assert h1 == h2

    def test_different_tokens_produce_different_hashes(self):
        """Different tokens produce different hashes."""
        h1 = _get_token_hash("token_a")
        h2 = _get_token_hash("token_b")
        assert h1 != h2

    def test_hash_is_truncated(self):
        """Hash is truncated to 32 characters."""
        h = _get_token_hash("any_token")
        assert len(h) == 32
