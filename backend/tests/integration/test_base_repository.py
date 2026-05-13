"""
Integration tests for BaseRepository soft-delete semantics.

Regression contract:
- Tests 1–4 MUST fail before the fix in repository.py (because _has_deleted_at
  always evaluates False, so soft-delete paths are dead code).
- Test 5 validates the hard-delete fallback for models that lack eliminado_en.
- Test 6 validates hard_delete() always removes the row physically.
- ALL 6 tests MUST pass after the fix.

Design note: Rol inherits BaseModel (and therefore has eliminado_en), so we
cannot use Rol for the hard-delete-fallback test as the original design assumed.
Instead, we define a lightweight test-only model (ModelSinEliminadoEn) that
inherits from AppendOnlyBaseModel (id + creado_en only, no eliminado_en).
This matches the spirit of Decision 5 without expanding the change scope.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from shared.models import AppendOnlyBaseModel
from shared.repository import BaseRepository
from features.users.models import Usuario


# ---------------------------------------------------------------------------
# Test-only model for hard-delete fallback test (no eliminado_en column)
# ---------------------------------------------------------------------------

class ModelSinEliminadoEn(AppendOnlyBaseModel):
    """
    Minimal test-only model that does NOT have an eliminado_en column.

    Used exclusively by test_delete_falls_back_to_hard_delete_when_model_lacks_eliminado_en
    to verify that BaseRepository falls back to physical deletion when the bound
    model does not declare the soft-delete column.
    """

    __tablename__ = "test_model_sin_eliminado_en"

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)


# ---------------------------------------------------------------------------
# Test 1 — delete() sets eliminado_en on a BaseModel instance
# ---------------------------------------------------------------------------

def test_delete_sets_eliminado_en_on_basemodel_instance(
    test_db_session, sample_user
):
    """
    repo.delete(id) on a Usuario (BaseModel with eliminado_en) MUST:
    - return True
    - set eliminado_en to a non-null timestamp
    - NOT physically remove the row (it stays in the table)
    """
    repo = BaseRepository(test_db_session, Usuario)
    result = repo.delete(sample_user.id)

    assert result is True

    # Query directly, bypassing _get_base_query soft-delete filter
    raw_query = select(Usuario).where(Usuario.id == sample_user.id)
    row = test_db_session.execute(raw_query).scalar_one_or_none()

    # Row must still exist physically
    assert row is not None, "Row was physically deleted — expected soft delete"
    # eliminado_en must be set
    assert row.eliminado_en is not None, (
        "eliminado_en is None after delete() — soft-delete path was not executed"
    )


# ---------------------------------------------------------------------------
# Test 2 — read() returns None for soft-deleted records
# ---------------------------------------------------------------------------

def test_read_returns_none_for_soft_deleted_record(test_db_session, sample_user):
    """
    After repo.delete(id), repo.read(id) MUST return None because _get_base_query
    filters out rows where eliminado_en IS NOT NULL.
    """
    repo = BaseRepository(test_db_session, Usuario)
    repo.delete(sample_user.id)

    found = repo.read(sample_user.id)

    assert found is None, (
        f"repo.read() returned a record after soft delete — "
        f"_get_base_query is not filtering soft-deleted rows (got {found})"
    )


# ---------------------------------------------------------------------------
# Test 3 — list() excludes soft-deleted records
# ---------------------------------------------------------------------------

def test_list_excludes_soft_deleted_records(test_db_session, sample_roles):
    """
    Create 3 users, soft-delete the first one.
    repo.list() MUST return exactly 2 users (the deleted one is excluded).
    """
    from shared.security import hash_password

    users = [
        Usuario(
            email=f"user{i}@test.com",
            password_hash=hash_password("password123"),
            nombre=f"User{i}",
            apellido="Test",
            is_active=True,
        )
        for i in range(3)
    ]
    for u in users:
        test_db_session.add(u)
    test_db_session.flush()

    repo = BaseRepository(test_db_session, Usuario)
    repo.delete(users[0].id)

    listed = repo.list()

    assert len(listed) == 2, (
        f"repo.list() returned {len(listed)} records — expected 2 "
        f"(soft-deleted user should be excluded)"
    )
    listed_ids = {u.id for u in listed}
    assert users[0].id not in listed_ids, (
        "Soft-deleted user appeared in repo.list() — filter is not applied"
    )


# ---------------------------------------------------------------------------
# Test 4 — count() excludes soft-deleted records
# ---------------------------------------------------------------------------

def test_count_excludes_soft_deleted_records(test_db_session, sample_roles):
    """
    Create 3 users, soft-delete one.
    repo.count() MUST return 2.
    """
    from shared.security import hash_password

    users = [
        Usuario(
            email=f"countuser{i}@test.com",
            password_hash=hash_password("password123"),
            nombre=f"CountUser{i}",
            apellido="Test",
            is_active=True,
        )
        for i in range(3)
    ]
    for u in users:
        test_db_session.add(u)
    test_db_session.flush()

    repo = BaseRepository(test_db_session, Usuario)
    repo.delete(users[0].id)

    total = repo.count()

    assert total == 2, (
        f"repo.count() returned {total} — expected 2 "
        f"(soft-deleted user must not be counted)"
    )


# ---------------------------------------------------------------------------
# Test 5 — delete() falls back to hard delete when model lacks eliminado_en
# ---------------------------------------------------------------------------

def test_delete_falls_back_to_hard_delete_when_model_lacks_eliminado_en(
    test_db_session,
):
    """
    BaseRepository bound to a model WITHOUT eliminado_en (ModelSinEliminadoEn)
    MUST perform a hard delete: the row disappears from the table entirely.

    Note: The original design assumed Rol would serve this purpose, but Rol
    inherits BaseModel and therefore HAS eliminado_en. This test uses a
    purpose-built test model (ModelSinEliminadoEn / AppendOnlyBaseModel)
    which only has id + creado_en.
    """
    # Ensure the test table exists in the in-memory SQLite DB
    ModelSinEliminadoEn.__table__.create(bind=test_db_session.get_bind(), checkfirst=True)

    instance = ModelSinEliminadoEn(nombre="to-be-hard-deleted")
    test_db_session.add(instance)
    test_db_session.flush()
    instance_id = instance.id

    repo = BaseRepository(test_db_session, ModelSinEliminadoEn)
    result = repo.delete(instance_id)

    assert result is True

    # Row must be physically gone
    raw_query = select(ModelSinEliminadoEn).where(
        ModelSinEliminadoEn.id == instance_id
    )
    row = test_db_session.execute(raw_query).scalar_one_or_none()

    assert row is None, (
        "Row still exists after delete() on a model without eliminado_en — "
        "hard-delete fallback was not triggered"
    )


# ---------------------------------------------------------------------------
# Test 6 — hard_delete() always removes the row physically
# ---------------------------------------------------------------------------

def test_hard_delete_always_removes_record_physically(test_db_session, sample_user):
    """
    repo.hard_delete(id) on a Usuario (which HAS eliminado_en) MUST:
    - return True
    - physically remove the row (even though the model supports soft delete)
    """
    repo = BaseRepository(test_db_session, Usuario)
    result = repo.hard_delete(sample_user.id)

    assert result is True

    # Query directly — row must be physically gone
    raw_query = select(Usuario).where(Usuario.id == sample_user.id)
    row = test_db_session.execute(raw_query).scalar_one_or_none()

    assert row is None, (
        "Row still exists after hard_delete() — hard delete did not remove it physically"
    )


# ---------------------------------------------------------------------------
# Test 7 — update() must not overwrite creado_en (immutable audit field)
# ---------------------------------------------------------------------------

def test_update_does_not_overwrite_creado_en(test_db_session, sample_user):
    """
    Regression contract for fix-base-repository-immutable-fields.

    repo.update(id, creado_en=<other_ts>) MUST NOT mutate the row's creado_en.
    The guard at repository.py:100 must list the project's actual field name
    ("creado_en"), not the English placeholder "created_at".

    BEFORE the fix this test fails: creado_en gets overwritten because
    "creado_en" is not in the protected set.
    AFTER the fix this test passes: creado_en stays at its original value.
    """
    repo = BaseRepository(test_db_session, Usuario)

    # Capture the original timestamp BEFORE the update attempt.
    creado_en_original = sample_user.creado_en
    assert creado_en_original is not None, (
        "Fixture precondition violated: sample_user.creado_en must be set"
    )

    # Attempt to overwrite with a wildly different timestamp.
    forged_ts = datetime.now(timezone.utc) + timedelta(days=999)
    repo.update(sample_user.id, creado_en=forged_ts)

    # Re-read the row directly (bypass any soft-delete filter) and verify
    # creado_en remains untouched.
    raw_query = select(Usuario).where(Usuario.id == sample_user.id)
    row = test_db_session.execute(raw_query).scalar_one_or_none()

    assert row is not None, "Sample user row disappeared after update()"
    assert row.creado_en == creado_en_original, (
        f"creado_en was mutated by update(): expected {creado_en_original}, "
        f"got {row.creado_en}. The guard at repository.py:100 is not "
        f"protecting the actual field name."
    )


# ---------------------------------------------------------------------------
# Test 8 — update() must not overwrite id (defense by method signature)
# ---------------------------------------------------------------------------

def test_update_does_not_overwrite_id(test_db_session, sample_user):
    """
    Regression test guaranteeing the row's primary key cannot be mutated via
    update() under any code path.

    Note on the protection mechanism:
      BaseRepository.update(self, id, **kwargs) makes `id` a positional
      parameter. Any caller that tries to pass id=<forged> alongside the
      target id (either explicitly or by **payload spread when payload
      contains "id") triggers a Python TypeError "got multiple values for
      argument 'id'" BEFORE the row is ever read or mutated.

      This means the "id" entry inside the guard at repository.py:100 is
      effectively unreachable for current callers — the method signature
      itself is the real defense. We test the realistic path: a payload
      dict that contains an "id" key being splatted into kwargs.

      If someone ever refactors update() to remove the positional `id`
      (e.g. switches to update(self, **kwargs)), this test will start
      reaching the guard, and the guard's "id" entry must continue to
      protect against mutation. The assertion at the bottom covers that
      future scenario.
    """
    repo = BaseRepository(test_db_session, Usuario)

    id_original = sample_user.id
    forged_id = 999999

    # Realistic path: an external payload dict contains "id" and gets splatted.
    payload = {"id": forged_id, "apellido": "ShouldNotChangeId"}

    with pytest.raises(TypeError, match="multiple values for argument 'id'"):
        repo.update(id_original, **payload)

    # Even after the failed call, the row's id must remain unchanged
    # and no row must exist at the forged id.
    row = repo.read(id_original)
    assert row is not None, "Original row disappeared after failed update()"
    assert row.id == id_original

    raw_query = select(Usuario).where(Usuario.id == forged_id)
    forged_row = test_db_session.execute(raw_query).scalar_one_or_none()
    assert forged_row is None, (
        f"A row exists at forged id={forged_id} — id protection broke."
    )
