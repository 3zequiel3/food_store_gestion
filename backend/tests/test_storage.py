from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from config import settings
from shared.storage import StorageService


@pytest.mark.asyncio
async def test_local_storage_saves_product_image(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_PUBLIC_BASE_URL", "http://localhost:8000")
    monkeypatch.setattr(settings, "STORAGE_MAX_UPLOAD_MB", 5)

    file = UploadFile(
        filename="pizza.png",
        file=BytesIO(b"fake-png-bytes"),
        headers={"content-type": "image/png"},
    )

    url = await StorageService().save_product_image(42, file)

    assert url.startswith("http://localhost:8000/uploads/productos/42/")
    saved = list((tmp_path / "productos" / "42").glob("*.png"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"fake-png-bytes"


def test_s3_storage_returns_backend_proxy_url_by_default(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE", "s3")
    monkeypatch.setattr(settings, "STORAGE_PUBLIC_BASE_URL", "https://api.example.com")
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", None)

    url = StorageService().product_image_url("productos/42/pizza.png")

    assert url == "https://api.example.com/api/v1/productos/imagenes/productos/42/pizza.png"


def test_s3_storage_can_use_explicit_public_image_base(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE", "s3")
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://cdn.example.com/bucket")

    url = StorageService().product_image_url("productos/42/pizza.png")

    assert url == "https://cdn.example.com/bucket/productos/42/pizza.png"
