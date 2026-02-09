"""User profile model.

Stores user identity data including optional Google OAuth linkage.
"""

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.models import Base, TimestampMixin, UUIDMixin


class UserProfile(Base, UUIDMixin, TimestampMixin):
    """User profile for authentication and display.

    Supports local accounts and Google OAuth linked accounts.
    """

    __tablename__ = "user_profiles"

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username (used in JWT sub claim)",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Display name shown in UI",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        doc="Email address (unique if set)",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Profile picture URL (e.g. Google profile picture)",
    )
    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        doc="Google OAuth subject identifier (unique per Google account)",
    )

    __table_args__ = (Index("ix_user_profiles_google_sub", "google_sub", unique=True),)

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, username={self.username})>"
