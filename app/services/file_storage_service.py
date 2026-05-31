from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from app.core.config import get_settings
from app.core.errors import DomainError


@dataclass(frozen=True)
class StoredFile:
    key: str
    public_url: str


class FileStorage:
    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None) -> StoredFile:
        raise NotImplementedError

    def public_url(self, key: str) -> str:
        raise NotImplementedError


def normalize_object_key(key: str) -> str:
    parts = [part for part in key.replace("\\", "/").split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        raise DomainError(code="invalid_storage_key", message="Invalid storage key")
    return "/".join(parts)


def build_storage_key(*parts: str) -> str:
    settings = get_settings()
    clean_parts = [settings.file_storage_prefix.strip("/")]
    clean_parts.extend(part.strip("/") for part in parts if part.strip("/"))
    return normalize_object_key("/".join(part for part in clean_parts if part))


class LocalFileStorage(FileStorage):
    def __init__(self, *, base_dir: str, public_base_url: str) -> None:
        self.base_dir = Path(base_dir)
        self.public_base_url = public_base_url.rstrip("/") + "/"

    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None) -> StoredFile:
        normalized_key = normalize_object_key(key)
        path = self.base_dir / normalized_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return StoredFile(key=normalized_key, public_url=self.public_url(normalized_key))

    def public_url(self, key: str) -> str:
        normalized_key = normalize_object_key(key)
        return urljoin(self.public_base_url, normalized_key)


class S3FileStorage(FileStorage):
    def __init__(
        self,
        *,
        endpoint_url: str,
        region_name: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        public_base_url: str,
    ) -> None:
        import boto3

        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/") + "/"
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def put_bytes(self, *, key: str, content: bytes, content_type: str | None = None) -> StoredFile:
        normalized_key = normalize_object_key(key)
        extra_args = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=normalized_key, Body=content, **extra_args)
        return StoredFile(key=normalized_key, public_url=self.public_url(normalized_key))

    def public_url(self, key: str) -> str:
        normalized_key = normalize_object_key(key)
        return urljoin(self.public_base_url, normalized_key)


def get_file_storage() -> FileStorage:
    settings = get_settings()
    public_base_url = settings.file_storage_public_base_url or f"{settings.app_download_public_base_url.rstrip('/')}/files"
    backend = settings.file_storage_backend.strip().lower()
    if backend == "s3":
        missing = [
            name
            for name, value in (
                ("ARVAN_S3_ENDPOINT_URL", settings.arvan_s3_endpoint_url),
                ("ARVAN_S3_BUCKET", settings.arvan_s3_bucket),
                ("ARVAN_S3_ACCESS_KEY_ID", settings.arvan_s3_access_key_id),
                ("ARVAN_S3_SECRET_ACCESS_KEY", settings.arvan_s3_secret_access_key),
                ("FILE_STORAGE_PUBLIC_BASE_URL", settings.file_storage_public_base_url),
            )
            if not value
        ]
        if missing:
            raise DomainError(
                code="file_storage_not_configured",
                message=f"File storage is missing required settings: {', '.join(missing)}",
            )
        return S3FileStorage(
            endpoint_url=settings.arvan_s3_endpoint_url or "",
            region_name=settings.arvan_s3_region,
            bucket=settings.arvan_s3_bucket or "",
            access_key_id=settings.arvan_s3_access_key_id or "",
            secret_access_key=settings.arvan_s3_secret_access_key or "",
            public_base_url=settings.file_storage_public_base_url or "",
        )
    if backend == "local":
        return LocalFileStorage(base_dir=settings.file_storage_local_dir, public_base_url=public_base_url)
    raise DomainError(code="invalid_file_storage_backend", message="FILE_STORAGE_BACKEND must be local or s3")
