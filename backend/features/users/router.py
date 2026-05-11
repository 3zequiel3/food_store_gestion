"""
Users feature router — self-service profile endpoints.

All endpoints operate exclusively on the authenticated user's own data
(current_user.id from Depends(get_current_user)).  No user_id path param
is exposed — this enforces RN-RB05 (a CLIENT can only operate on their
own data).

Mounted at /api/v1/usuarios by backend/main.py (no prefix here).
"""

from fastapi import APIRouter, Depends, Response, status

from backend.features.auth.dependencies import get_current_user
from backend.features.users.models import Usuario
from backend.features.users.schemas import (
    ChangePasswordRequest,
    ProfileResponse,
    UpdateProfileRequest,
)
from backend.features.users.service import UserProfileService

router = APIRouter()


def _to_profile_response(user: Usuario) -> ProfileResponse:
    """Build a ProfileResponse from a Usuario with eagerly loaded roles.

    Constructs the response explicitly (field-by-field) instead of relying on
    Pydantic from_attributes alone, because roles is a M2N relationship that
    returns Rol ORM objects — they must be projected to code strings here.
    """
    return ProfileResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        telefono=user.telefono,
        roles=[r.codigo for r in user.roles],
        creado_en=user.creado_en,
        actualizado_en=user.actualizado_en,
    )


@router.get("/me", response_model=ProfileResponse, summary="Get own profile")
async def get_my_profile(
    current_user: Usuario = Depends(get_current_user),
) -> ProfileResponse:
    """Return the authenticated user's full profile.

    Eager-loads roles via selectinload to avoid lazy-load after session boundary.
    Read-only — no commit needed.
    """
    service = UserProfileService()
    user = service.get_profile(current_user.id)
    return _to_profile_response(user)


@router.patch("/me", response_model=ProfileResponse, summary="Update own profile")
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: Usuario = Depends(get_current_user),
) -> ProfileResponse:
    """Partially update the authenticated user's profile fields.

    Accepted fields: nombre, apellido, telefono (all optional).
    email is NOT editable via this endpoint (extra='forbid' returns 422 for it).

    The service returns the updated user with roles eager-loaded within the
    same transaction — no re-read needed.
    """
    service = UserProfileService()
    user = service.update_profile(current_user.id, payload)
    return _to_profile_response(user)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Usuario = Depends(get_current_user),
) -> Response:
    """Change the authenticated user's password.

    On success: 204 No Content + ALL refresh tokens revoked (RN-AU05).
    The frontend MUST perform a local logout on receiving 204 — the current
    access token remains valid until natural expiration (~30 min, RN-AU02),
    but cannot be refreshed after revocation.
    """
    service = UserProfileService()
    service.change_password(current_user.id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
