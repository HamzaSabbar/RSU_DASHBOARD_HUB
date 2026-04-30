from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from config import settings

logger = logging.getLogger("uvicorn.error")


class ObjectStorage(ABC):
    @abstractmethod
    def put_bytes(self, object_path: str, content: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, object_path: str) -> bytes:
        raise NotImplementedError

    def put_json(self, object_path: str, payload: dict[str, Any]) -> None:
        self.put_bytes(
            object_path,
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    def get_json(self, object_path: str) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.get_bytes(object_path).decode("utf-8")))


class LocalObjectStorage(ObjectStorage):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def _path(self, object_path: str) -> Path:
        relative = Path(object_path.lstrip("/"))
        return self.base_path / relative

    def put_bytes(self, object_path: str, content: bytes) -> None:
        path = self._path(object_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get_bytes(self, object_path: str) -> bytes:
        return self._path(object_path).read_bytes()


class GCSObjectStorage(ObjectStorage):
    def __init__(self, bucket_name: str) -> None:
        try:
            from google.cloud import storage as gcs_storage
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError("google-cloud-storage n'est pas installé") from exc

        self._client = gcs_storage.Client()
        self._bucket = self._client.bucket(bucket_name)

    def put_bytes(self, object_path: str, content: bytes) -> None:
        blob = self._bucket.blob(object_path)
        blob.upload_from_string(content)

    def get_bytes(self, object_path: str) -> bytes:
        blob = self._bucket.blob(object_path)
        return cast(bytes, blob.download_as_bytes())


def build_object_path(*parts: str) -> str:
    prefix = settings.gcs_prefix.strip("/")
    suffix = "/".join(part.strip("/") for part in parts if part)
    return f"{prefix}/{suffix}" if prefix else suffix


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    driver = settings.storage_driver.lower()
    if driver == "gcs":
        if not settings.gcs_bucket_name:
            logger.warning("GCS_BUCKET_NAME absent; utilisation du stockage local.")
        else:
            try:
                return GCSObjectStorage(settings.gcs_bucket_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("GCS indisponible; repli sur stockage local: %s", exc)

    return LocalObjectStorage(settings.storage_local_path)
