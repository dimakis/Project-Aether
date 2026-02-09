"""Tests for system_config DAL and Fernet encryption."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.dal.system_config import (
    _derive_fernet_key,
    decrypt_token,
    encrypt_token,
)

# =============================================================================
# Fernet encryption tests (pure functions, no DB)
# =============================================================================


class TestFernetEncryption:
    """Tests for token encryption / decryption round-trip."""

    def test_derive_key_is_deterministic(self):
        """Same secret always produces the same key."""
        k1 = _derive_fernet_key("my-secret-123")
        k2 = _derive_fernet_key("my-secret-123")
        assert k1 == k2

    def test_derive_key_different_secrets_differ(self):
        """Different secrets produce different keys."""
        k1 = _derive_fernet_key("secret-a")
        k2 = _derive_fernet_key("secret-b")
        assert k1 != k2

    def test_derive_key_length(self):
        """Derived key is 44 bytes (base64-encoded 32 bytes)."""
        key = _derive_fernet_key("any-secret")
        assert len(key) == 44

    def test_encrypt_decrypt_round_trip(self):
        """Encrypting then decrypting returns the original token."""
        secret = "test-jwt-secret-long-enough-for-sha256"
        token = "my-ha-long-lived-access-token"
        encrypted = encrypt_token(token, secret)
        assert encrypted != token  # Not stored in plaintext
        decrypted = decrypt_token(encrypted, secret)
        assert decrypted == token

    def test_decrypt_with_wrong_secret_fails(self):
        """Decrypting with a different secret raises an error."""
        from cryptography.fernet import InvalidToken

        encrypted = encrypt_token("some-token", "correct-secret")
        with pytest.raises(InvalidToken):
            decrypt_token(encrypted, "wrong-secret")

    def test_encrypted_output_is_string(self):
        """Encrypted output is a plain string (base64), safe for DB TEXT column."""
        encrypted = encrypt_token("token", "secret")
        assert isinstance(encrypted, str)
        # Should be valid base64 (Fernet output)
        assert len(encrypted) > 0


# =============================================================================
# SystemConfigRepository tests (mock-based, no real DB)
# =============================================================================


class TestSystemConfigRepository:
    """Tests for the SystemConfigRepository CRUD operations using mocks."""

    @pytest.mark.asyncio
    async def test_no_config_initially(self):
        """Before setup, get_config returns None."""
        from src.dal.system_config import SystemConfigRepository

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        assert await repo.get_config() is None

    @pytest.mark.asyncio
    async def test_is_setup_complete_false_initially(self):
        """Before setup, is_setup_complete returns False."""
        from src.dal.system_config import SystemConfigRepository

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        assert await repo.is_setup_complete() is False

    @pytest.mark.asyncio
    async def test_create_config(self):
        """Creating config stores all fields correctly."""
        from src.dal.system_config import SystemConfigRepository

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = SystemConfigRepository(session)
        secret = "test-secret-for-encryption"
        ha_token = "my-ha-token-12345"
        encrypted = encrypt_token(ha_token, secret)

        config = await repo.create_config(
            ha_url="http://ha.local:8123",
            ha_token_encrypted=encrypted,
            password_hash="$2b$12$somebcrypthash",
        )

        assert config.ha_url == "http://ha.local:8123"
        assert config.ha_token_encrypted == encrypted
        assert config.password_hash == "$2b$12$somebcrypthash"
        assert config.setup_completed_at is not None
        assert config.id is not None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_setup_complete_true_after_create(self):
        """After creating config, is_setup_complete returns True."""
        from src.dal.system_config import SystemConfigRepository
        from src.storage.entities.system_config import SystemConfig

        mock_config = MagicMock(spec=SystemConfig)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        assert await repo.is_setup_complete() is True

    @pytest.mark.asyncio
    async def test_get_config_returns_row(self):
        """After creating config, get_config returns it."""
        from src.dal.system_config import SystemConfigRepository
        from src.storage.entities.system_config import SystemConfig

        mock_config = MagicMock(spec=SystemConfig)
        mock_config.ha_url = "http://10.0.0.5:8123"
        mock_config.password_hash = None

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        config = await repo.get_config()
        assert config is not None
        assert config.ha_url == "http://10.0.0.5:8123"
        assert config.password_hash is None

    @pytest.mark.asyncio
    async def test_get_ha_connection_decrypts_token(self):
        """get_ha_connection decrypts the stored token."""
        from src.dal.system_config import SystemConfigRepository
        from src.storage.entities.system_config import SystemConfig

        secret = "fernet-test-key"
        ha_token = "long-lived-token-abc"
        encrypted = encrypt_token(ha_token, secret)

        mock_config = MagicMock(spec=SystemConfig)
        mock_config.ha_url = "http://ha.example.com:8123"
        mock_config.ha_token_encrypted = encrypted

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_config
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        result = await repo.get_ha_connection(secret)
        assert result is not None
        url, token = result
        assert url == "http://ha.example.com:8123"
        assert token == ha_token

    @pytest.mark.asyncio
    async def test_get_ha_connection_none_when_no_config(self):
        """get_ha_connection returns None when no config exists."""
        from src.dal.system_config import SystemConfigRepository

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        repo = SystemConfigRepository(session)
        assert await repo.get_ha_connection("any-secret") is None

    @pytest.mark.asyncio
    async def test_password_hash_optional(self):
        """Config can be created without a password hash."""
        from src.dal.system_config import SystemConfigRepository

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        repo = SystemConfigRepository(session)
        config = await repo.create_config(
            ha_url="http://ha.local:8123",
            ha_token_encrypted=encrypt_token("tok", "sec"),
            password_hash=None,
        )
        assert config.password_hash is None
