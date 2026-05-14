"""Storage abstraction for product assets.

`STORAGE=local` writes files under backend/uploads/productos/<id>/.
`STORAGE=s3` uploads files to an S3-compatible bucket and serves them through
this backend unless a public storage base URL is explicitly configured.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from fastapi import UploadFile

from config import settings
from shared.exceptions import BusinessRuleError, NotFoundError

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_PRODUCT_IMAGE_PREFIX = "productos/"


def _clean_public_base_url(value: str) -> str:
    return value.rstrip("/")


def _extension_for(file: UploadFile) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in _ALLOWED_EXTENSIONS:
        return suffix

    guessed = mimetypes.guess_extension(file.content_type or "")
    if guessed == ".jpe":
        return ".jpg"
    return guessed or ".bin"


def _validate_product_image_key(key: str) -> str:
    normalized = key.strip().lstrip("/")
    path = Path(normalized)
    if (
        not normalized.startswith(_PRODUCT_IMAGE_PREFIX)
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise BusinessRuleError("Ruta de imagen inválida")
    return normalized


class StorageService:
    """Save and serve product images using the configured storage backend."""

    async def save_product_image(self, producto_id: int, file: UploadFile) -> str:
        content_type = file.content_type or "application/octet-stream"
        if content_type not in _ALLOWED_IMAGE_TYPES:
            raise BusinessRuleError(
                "El archivo debe ser una imagen JPG, PNG, WEBP o GIF"
            )

        content = await file.read()
        if not content:
            raise BusinessRuleError("El archivo está vacío")

        max_bytes = settings.STORAGE_MAX_UPLOAD_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise BusinessRuleError(
                f"La imagen no puede superar {settings.STORAGE_MAX_UPLOAD_MB} MB"
            )

        key = f"productos/{producto_id}/{uuid4().hex}{_extension_for(file)}"

        if settings.STORAGE == "local":
            self._save_local(key, content)
            return self.product_image_url(key)
        if settings.STORAGE == "s3":
            self._save_s3(key, content, content_type)
            return self.product_image_url(key)

        raise BusinessRuleError("STORAGE debe ser 'local' o 's3'")

    def product_image_url(self, key: str) -> str:
        """Return the public URL the frontend should render for a stored image.

        Accepts both storage keys ('productos/...') and absolute URLs.
        Absolute URLs (presigned S3 or previously-resolved local URLs) are
        returned as-is to avoid double-resolution or validation errors.
        """
        # If already an absolute URL, return it directly (presigned S3,
        # or local URL previously stored in DB).
        if key.startswith(("http://", "https://", "//")):
            return key

        safe_key = _validate_product_image_key(key)

        if settings.STORAGE == "local":
            public_base = _clean_public_base_url(settings.STORAGE_PUBLIC_BASE_URL)
            if public_base:
                return f"{public_base}/uploads/{safe_key}"
            return f"/uploads/{safe_key}"

        # S3: generate presigned GET URL (valid for 1 hour)
        if settings.STORAGE == "s3":
            return self._presign_get(safe_key)

        raise BusinessRuleError("STORAGE debe ser 'local' o 's3'")

    def presign_upload(self, producto_id: int, content_type: str) -> dict[str, str]:
        """Generate a presigned POST for direct client-to-S3 upload.

        Returns a dict with { url, fields, key } ready for the frontend to POST a file.
        The `key` is needed to register the image in the DB after successful upload.
        """
        if settings.STORAGE == "local":
            raise BusinessRuleError("Uploads directos solo disponibles con STORAGE=s3")

        key = f"productos/{producto_id}/{uuid4().hex}{self._extension_from_content_type(content_type)}"
        safe_key = _validate_product_image_key(key)

        client = self._s3_client()
        response = client.generate_presigned_post(
            Bucket=settings.S3_BUCKET_NAME,
            Key=safe_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                ["eq", "$Content-Type", content_type],
                [
                    "content-length-range",
                    0,
                    settings.STORAGE_MAX_UPLOAD_MB * 1024 * 1024,
                ],
            ],
            ExpiresIn=3600,
        )
        response["key"] = safe_key
        return response

    def _presign_get(self, key: str) -> str:
        """Generate a presigned GET URL for an S3 object (valid for 1 hour)."""
        client = self._s3_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=3600,
        )

    def _extension_from_content_type(self, content_type: str) -> str:
        ext = mimetypes.guess_extension(content_type)
        if ext == ".jpe":
            return ".jpg"
        return ext or ".bin"

    def open_product_image(self, key: str) -> tuple[BinaryIO, str]:
        """Open a product image for backend proxy serving."""
        safe_key = _validate_product_image_key(key)
        if settings.STORAGE == "local":
            return self._open_local(safe_key)
        if settings.STORAGE == "s3":
            return self._open_s3(safe_key)
        raise BusinessRuleError("STORAGE debe ser 'local' o 's3'")

    def _save_local(self, key: str, content: bytes) -> None:
        root = Path(settings.STORAGE_LOCAL_DIR).resolve()
        destination = (root / key).resolve()
        if root not in destination.parents:
            raise BusinessRuleError("Ruta de imagen inválida")

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

    def _open_local(self, key: str) -> tuple[BinaryIO, str]:
        root = Path(settings.STORAGE_LOCAL_DIR).resolve()
        source = (root / key).resolve()
        if root not in source.parents:
            raise BusinessRuleError("Ruta de imagen inválida")
        if not source.is_file():
            raise NotFoundError("Imagen no encontrada")

        content_type = (
            mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        )
        return source.open("rb"), content_type

    def _save_s3(self, key: str, content: bytes, content_type: str) -> None:
        client = self._s3_client()
        client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def _open_s3(self, key: str) -> tuple[BinaryIO, str]:
        client = self._s3_client()
        try:
            response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        except Exception as exc:
            if exc.__class__.__name__ == "NoSuchKey":
                raise NotFoundError("Imagen no encontrada") from exc

            response = getattr(exc, "response", {})
            error_code = response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise NotFoundError("Imagen no encontrada") from exc
            raise

        content_type = response.get("ContentType") or "application/octet-stream"
        return response["Body"], content_type

    def _s3_client(self):
        required = {
            "S3_ENDPOINT_URL": settings.S3_ENDPOINT_URL,
            "S3_BUCKET_NAME": settings.S3_BUCKET_NAME,
            "S3_ACCESS_KEY_ID": settings.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": settings.S3_SECRET_ACCESS_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise BusinessRuleError(
                "Faltan variables de entorno para STORAGE=s3: " + ", ".join(missing)
            )

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise BusinessRuleError(
                "Falta instalar boto3 para usar STORAGE=s3"
            ) from exc

        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
