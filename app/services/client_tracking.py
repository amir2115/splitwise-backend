from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.user import User

CLIENT_PLATFORM_ANDROID = "android"
CLIENT_PLATFORM_FRONTEND = "frontend"
CLIENT_PLATFORM_UNKNOWN = "unknown"

ANDROID_VARIANTS = {"bazaar", "myket", "organic"}


@dataclass(frozen=True)
class ClientMetadata:
    platform: str
    android_variant: str | None = None

    @property
    def is_android(self) -> bool:
        return self.platform == CLIENT_PLATFORM_ANDROID


def parse_client_metadata(x_client_platform: Optional[str], x_app_store: Optional[str]) -> ClientMetadata:
    platform = (x_client_platform or "").strip().lower()
    if platform == CLIENT_PLATFORM_ANDROID:
        variant = (x_app_store or "").strip().lower()
        return ClientMetadata(
            platform=CLIENT_PLATFORM_ANDROID,
            android_variant=variant if variant in ANDROID_VARIANTS else None,
        )
    if platform == CLIENT_PLATFORM_FRONTEND:
        return ClientMetadata(platform=CLIENT_PLATFORM_FRONTEND)
    return ClientMetadata(platform=CLIENT_PLATFORM_UNKNOWN)


def apply_client_metadata(user: User, metadata: ClientMetadata) -> bool:
    current_platform = (user.client_platform or "").strip().lower()
    if metadata.platform == CLIENT_PLATFORM_UNKNOWN and current_platform:
        return False

    next_variant = metadata.android_variant if metadata.platform == CLIENT_PLATFORM_ANDROID else None
    user.client_platform = metadata.platform
    user.android_variant = next_variant
    user.last_client_seen_at = utcnow()
    return True


def track_user_client_metadata(db: Session, user: User, metadata: ClientMetadata) -> None:
    if apply_client_metadata(user, metadata):
        db.commit()
