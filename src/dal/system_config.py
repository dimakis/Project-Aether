"""System configuration data access layer.

Provides CRUD for the single-row system_config table and
Fernet encryption/decryption of the HA token.
"""

import base64
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.entities.system_config import SystemConfig


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a Fernet key from an arbitrary secret string.

    Uses SHA-256 to produce a 32-byte key, then base64-encodes it
    as required by Fernet (url-safe base64, 32 bytes).

    Args:
        secret: The secret to derive the key from (e.g. JWT_SECRET).

    Returns:
        A valid Fernet key (44 bytes, url-safe base64).
    """
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(token: str, secret: str) -> str:
    """Encrypt a token using Fernet with a key derived from the secret.

    Args:
        token: The plaintext token to encrypt.
        secret: The secret used to derive the encryption key.

    Returns:
        The encrypted token as a string (base64).
    """
    key = _derive_fernet_key(secret)
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str, secret: str) -> str:
    """Decrypt a Fernet-encrypted token.

    Args:
        encrypted: The encrypted token string (base64).
        secret: The secret used to derive the decryption key.

    Returns:
        The decrypted plaintext token.

    Raises:
        cryptography.fernet.InvalidToken: If decryption fails.
    """
    key = _derive_fernet_key(secret)
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()


class SystemConfigRepository:
    """Repository for the single-row system configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_config(self) -> SystemConfig | None:
        """Get the system configuration row, if it exists.

        Returns:
            SystemConfig or None if setup has not been completed.
        """
        result = await self.session.execute(
            select(SystemConfig).limit(1)
        )
        return result.scalar_one_or_none()

    async def is_setup_complete(self) -> bool:
        """Check whether initial setup has been completed.

        Returns:
            True if a system_config row exists.
        """
        config = await self.get_config()
        return config is not None

    async def create_config(
        self,
        ha_url: str,
        ha_token_encrypted: str,
        password_hash: str | None = None,
    ) -> SystemConfig:
        """Create the system configuration (first-time setup).

        Args:
            ha_url: The validated HA instance URL.
            ha_token_encrypted: The Fernet-encrypted HA token.
            password_hash: Optional bcrypt hash of the admin password.

        Returns:
            The created SystemConfig instance.
        """
        config = SystemConfig(
            id=str(uuid4()),
            ha_url=ha_url,
            ha_token_encrypted=ha_token_encrypted,
            password_hash=password_hash,
            setup_completed_at=datetime.now(timezone.utc),
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def get_ha_connection(self, secret: str) -> tuple[str, str] | None:
        """Get HA connection details (URL + decrypted token) from DB.

        Args:
            secret: The secret used to decrypt the HA token.

        Returns:
            Tuple of (ha_url, ha_token) or None if no config exists.
        """
        config = await self.get_config()
        if config is None:
            return None
        ha_token = decrypt_token(config.ha_token_encrypted, secret)
        return config.ha_url, ha_token
