"""File storage abstraction so brochure files can live locally or in S3
without changing the upload service."""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod

from app.config.settings import Settings


class BaseStorageProvider(ABC):
    @abstractmethod
    async def save(self, file_bytes: bytes, original_filename: str) -> str:
        """Persist the file and return a storage path/key."""
        raise NotImplementedError

    @abstractmethod
    def resolve_path(self, storage_key: str) -> str:
        """Return a filesystem path usable by the PDF parser (downloads if remote)."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        raise NotImplementedError


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    async def save(self, file_bytes: bytes, original_filename: str) -> str:
        safe_name = f"{uuid.uuid4()}_{os.path.basename(original_filename)}"
        full_path = os.path.join(self.base_path, safe_name)
        with open(full_path, "wb") as f:
            f.write(file_bytes)
        return full_path

    def resolve_path(self, storage_key: str) -> str:
        return storage_key

    async def delete(self, storage_key: str) -> None:
        if os.path.exists(storage_key):
            os.remove(storage_key)


def get_storage_provider(settings: Settings) -> BaseStorageProvider:
    if settings.STORAGE_PROVIDER == "s3":
        raise NotImplementedError(
            "S3StorageProvider is not bundled by default — implement BaseStorageProvider "
            "using boto3 and wire it in here when needed."
        )
    return LocalStorageProvider(settings.LOCAL_STORAGE_PATH)
