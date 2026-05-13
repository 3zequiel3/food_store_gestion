"""
UserProfile service.

Orchestrates self-service profile operations for authenticated users.

Each public method opens its own UnitOfWork context. Commit is performed
by ``__exit__`` on clean exit. The router never calls uow.commit().
"""

from features.auth.repository import RefreshTokenRepository
from features.users.models import Usuario
from features.users.repository import UserProfileRepository
from features.users.schemas import ChangePasswordRequest, UpdateProfileRequest
from shared.exceptions import BusinessRuleError, NotFoundError, UnauthorizedError
from shared.security import hash_password, verify_password
from shared.unit_of_work import UnitOfWork


class UserProfileService:
    """Service for user profile self-service operations.

    Stateless — each method opens its own UnitOfWork context.
    Registered repositories inside each with-block:
    - uow.usuarios       → UserProfileRepository
    - uow.refresh_tokens → RefreshTokenRepository (when needed)
    """

    def __init__(self) -> None:
        pass

    def get_profile(self, user_id: int) -> Usuario:
        """Return the user's full profile with roles eager-loaded.

        Raises:
            NotFoundError: If user not found (defensive — get_current_user should
                           already have validated this).
        """
        with UnitOfWork() as uow:
            uow.register_repository("usuarios", UserProfileRepository(uow.session))

            user = uow.usuarios.find_by_id_with_roles(user_id)
            if not user:
                raise NotFoundError("Usuario no encontrado")
            return user

    def update_profile(self, user_id: int, payload: UpdateProfileRequest) -> Usuario:
        """Apply a partial update to the user's editable profile fields.

        Collapses the double-read pattern: updates the profile AND returns the
        Usuario with roles eager-loaded within the same transaction. The router
        does NOT call get_profile() after this method.

        Uses model_dump(exclude_unset=True) so omitted fields are preserved
        and an explicit null for `telefono` is honored.

        Trims whitespace from nombre/apellido and rejects post-trim empty strings
        as BusinessRuleError (Pydantic min_length won't catch "   " with 3 spaces).

        Raises:
            NotFoundError: If user not found.
            BusinessRuleError: If nombre or apellido collapses to empty after trim.
        """
        with UnitOfWork() as uow:
            uow.register_repository("usuarios", UserProfileRepository(uow.session))

            user = uow.usuarios.find_by_id_with_roles(user_id)
            if not user:
                raise NotFoundError("Usuario no encontrado")

            data = payload.model_dump(exclude_unset=True)
            if not data:
                # PATCH with no fields → no-op, return current state
                return user

            # Trim non-null strings; reject empties post-trim
            for key in ("nombre", "apellido"):
                if key in data and data[key] is not None:
                    data[key] = data[key].strip()
                    if not data[key]:
                        raise BusinessRuleError(f"El campo {key} no puede ser vacío")

            uow.usuarios.update(user_id, **data)
            # Reload user with roles after update so the router can serialize
            # ProfileResponse correctly (roles is an eagerly-loaded M2N relation).
            user_with_roles = uow.usuarios.find_by_id_with_roles(user_id)
            if not user_with_roles:
                raise NotFoundError("Usuario no encontrado")
            return user_with_roles

    def change_password(self, user_id: int, payload: ChangePasswordRequest) -> None:
        """Change the user's password and revoke ALL their refresh tokens.

        Steps (order matters for atomicity):
        1. Load user (no roles needed here).
        2. Verify password_actual — 401 generic on mismatch (RN-AU08).
        3. Reject password_nuevo == password_actual (avoids needless revocation).
        4. Hash and persist the new password via flush().
        5. Revoke ALL refresh tokens (RN-AU05, US-063).

        The flush() before revoking ensures the UPDATE order is deterministic
        within the UoW session.  If __exit__ fails, the UoW rolls back both the
        password update and the revocations atomically.

        Raises:
            NotFoundError: If user not found (defensive).
            UnauthorizedError: If password_actual is wrong — generic message, no leak.
            BusinessRuleError: If password_nuevo equals the current password.
        """
        with UnitOfWork() as uow:
            uow.register_repository("usuarios", UserProfileRepository(uow.session))
            uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

            user = uow.usuarios.read(user_id)
            if not user:
                raise NotFoundError("Usuario no encontrado")

            # Verify current password — always 401 with generic message (no leak)
            if not verify_password(payload.password_actual, user.password_hash):
                raise UnauthorizedError("Credenciales inválidas")

            # Reject if new password equals the current one
            if verify_password(payload.password_nuevo, user.password_hash):
                raise BusinessRuleError(
                    "La nueva contraseña debe ser diferente de la actual"
                )

            # Hash and stage the new password
            user.password_hash = hash_password(payload.password_nuevo)
            uow.session.flush()  # guarantee UPDATE order before bulk revocation

            # Revoke ALL refresh tokens for this user (RN-AU05)
            uow.refresh_tokens.revoke_all_user_tokens(user_id)
