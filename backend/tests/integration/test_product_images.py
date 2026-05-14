"""
Tests for ProductoImagen model and ProductRepository image methods.

Covers:
- ProductoImagen model schema and relationship
- list_imagenes excludes soft-deleted
- add_imagen creates row
- delete_imagen soft-deletes
- set_all_non_primaria bulk update
- set_primaria sets flag
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from features.products.models import Producto, ProductoImagen
from features.products.repository import ProductRepository


class TestProductoImagenModel:
    """ProductoImagen model schema and relationship tests."""

    def test_producto_imagen_has_correct_columns(self, test_db_session: Session):
        """product_images table has all required columns."""
        insp = inspect(test_db_session.get_bind())
        columns = {col["name"] for col in insp.get_columns("product_images")}
        expected = {
            "id",
            "producto_id",
            "url",
            "orden",
            "es_primaria",
            "creado_en",
            "actualizado_en",
            "eliminado_en",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    def test_producto_imagen_relationship(self, test_db_session: Session):
        """Producto has imagenes relationship to ProductoImagen."""
        producto = Producto(nombre="Test", precio=10.0)
        test_db_session.add(producto)
        test_db_session.flush()

        img = ProductoImagen(
            producto_id=producto.id,
            url="http://example.com/img.jpg",
            orden=0,
            es_primaria=True,
        )
        test_db_session.add(img)
        test_db_session.flush()

        # Relationship works
        assert producto.imagenes is not None
        # Refresh to load relationship
        test_db_session.refresh(producto)
        assert len(producto.imagenes) == 1
        assert producto.imagenes[0].url == "http://example.com/img.jpg"


class TestProductRepositoryImagenes:
    """ProductRepository image CRUD methods."""

    def _seed_product(self, session: Session) -> Producto:
        p = Producto(nombre="Test Product", precio=10.0, stock_cantidad=5)
        session.add(p)
        session.flush()
        return p

    def _seed_image(
        self,
        session: Session,
        producto_id: int,
        url: str,
        orden: int = 0,
        es_primaria: bool = False,
    ) -> ProductoImagen:
        img = ProductoImagen(
            producto_id=producto_id, url=url, orden=orden, es_primaria=es_primaria
        )
        session.add(img)
        session.flush()
        return img

    def test_list_imagenes_returns_active_ordered(self, test_db_session: Session):
        """list_imagenes returns only active images ordered by orden."""
        product = self._seed_product(test_db_session)
        self._seed_image(test_db_session, product.id, "url3.jpg", orden=2)
        self._seed_image(test_db_session, product.id, "url1.jpg", orden=0)
        self._seed_image(test_db_session, product.id, "url2.jpg", orden=1)

        repo = ProductRepository(test_db_session)
        images = repo.list_imagenes(product.id)

        assert len(images) == 3
        assert images[0].url == "url1.jpg"
        assert images[1].url == "url2.jpg"
        assert images[2].url == "url3.jpg"

    def test_list_imagenes_excludes_soft_deleted(self, test_db_session: Session):
        """list_imagenes excludes images with eliminado_en set."""
        product = self._seed_product(test_db_session)
        self._seed_image(test_db_session, product.id, "active.jpg", orden=0)
        deleted = self._seed_image(test_db_session, product.id, "deleted.jpg", orden=1)
        deleted.eliminado_en = datetime.now(timezone.utc)
        test_db_session.flush()

        repo = ProductRepository(test_db_session)
        images = repo.list_imagenes(product.id)

        assert len(images) == 1
        assert images[0].url == "active.jpg"

    def test_list_imagenes_empty_for_product_without_images(
        self, test_db_session: Session
    ):
        """list_imagenes returns empty list for product with no images."""
        product = self._seed_product(test_db_session)
        repo = ProductRepository(test_db_session)
        images = repo.list_imagenes(product.id)
        assert images == []

    def test_add_imagen_creates_row(self, test_db_session: Session):
        """add_imagen inserts a new ProductoImagen row."""
        product = self._seed_product(test_db_session)
        repo = ProductRepository(test_db_session)

        img = repo.add_imagen(product.id, "http://example.com/new.jpg")

        assert img.producto_id == product.id
        assert img.url == "http://example.com/new.jpg"
        assert img.eliminado_en is None

    def test_add_imagen_returns_persisted_row(self, test_db_session: Session):
        """add_imagen returns a row with id assigned."""
        product = self._seed_product(test_db_session)
        repo = ProductRepository(test_db_session)

        img = repo.add_imagen(product.id, "http://example.com/test.jpg")

        assert img.id is not None
        # Verify it's in the DB
        row = test_db_session.execute(
            text("SELECT COUNT(*) FROM product_images WHERE id = :iid"),
            {"iid": img.id},
        ).scalar()
        assert row == 1

    def test_delete_imagen_soft_deletes(self, test_db_session: Session):
        """delete_imagen sets eliminado_en on the image row."""
        product = self._seed_product(test_db_session)
        img = self._seed_image(test_db_session, product.id, "to-delete.jpg")
        img_id = img.id

        repo = ProductRepository(test_db_session)
        result = repo.delete_imagen(img_id)

        assert result is True
        # Verify soft-delete
        row = test_db_session.execute(
            text("SELECT eliminado_en FROM product_images WHERE id = :iid"),
            {"iid": img_id},
        ).fetchone()
        assert row is not None
        assert row[0] is not None

    def test_delete_imagen_returns_false_for_nonexistent(
        self, test_db_session: Session
    ):
        """delete_imagen returns False if image doesn't exist."""
        repo = ProductRepository(test_db_session)
        result = repo.delete_imagen(99999)
        assert result is False

    def test_set_all_non_primaria(self, test_db_session: Session):
        """set_all_non_primaria sets es_primaria=False on all product images."""
        product = self._seed_product(test_db_session)
        self._seed_image(test_db_session, product.id, "a.jpg", es_primaria=True)
        self._seed_image(test_db_session, product.id, "b.jpg", es_primaria=False)

        repo = ProductRepository(test_db_session)
        repo.set_all_non_primaria(product.id)

        rows = test_db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_images WHERE producto_id = :pid AND es_primaria = true"
            ),
            {"pid": product.id},
        ).scalar()
        assert rows == 0

    def test_set_primaria(self, test_db_session: Session):
        """set_primaria sets es_primaria=True on target image."""
        product = self._seed_product(test_db_session)
        img = self._seed_image(
            test_db_session, product.id, "target.jpg", es_primaria=False
        )

        repo = ProductRepository(test_db_session)
        repo.set_primaria(img.id)

        row = test_db_session.execute(
            text("SELECT es_primaria FROM product_images WHERE id = :iid"),
            {"iid": img.id},
        ).fetchone()
        assert row[0] == True  # SQLite returns 1 for boolean
