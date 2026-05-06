"""
Auth service layer.

Implements business logic for authentication including:
- User registration with automatic CLIENT role assignment
- Login with secure credential verification
- Token refresh with rotation and replay attack detection
- Logout with token revocation
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.features.auth.models import RefreshToken
from backend.features.auth.repository import RefreshTokenRepository
from backend.features.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenPairResponse,
)
from backend.features.catalog.models import Rol
from backend.features.users.models import Usuario, UsuarioRol
from backend.shared.exceptions import ConflictError, UnauthorizedError
from backend.shared.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


class AuthService:
    """Service for authentication operations."""

    # Role ID constants (from seed data)
    ROLE_CLIENT_ID = 4

    def __init__(self, session: Session):
        self.session = session
        self.refresh_token_repo = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> Usuario:
        """
        Register a new user with CLIENT role.

        Args:
            data: Registration request data

        Returns:
            Created user

        Raises:
            ConflictError: If email already exists
        """
        # Check if email already exists
        existing_user = self._get_user_by_email(data.email)
        if existing_user:
            raise ConflictError("El email ya está registrado")

        # Hash password
        password_hash = hash_password(data.password)

        # Create user
        user = Usuario(
            email=data.email,
            password_hash=password_hash,
            nombre=data.nombre,
            apellido=data.apellido,
            is_active=True,
        )
        self.session.add(user)
        self.session.flush()  # Get the ID

        # Assign CLIENT role automatically (RN-AU07)
        user_role = UsuarioRol(
            user_id=user.id,
            role_id=self.ROLE_CLIENT_ID,
        )
        self.session.add(user_role)
        self.session.flush()

        # Refresh to get roles loaded
        self.session.refresh(user)

        return user

    async def login(
        self,
        data: LoginRequest,
        client_ip: Optional[str] = None,
    ) -> TokenPairResponse:
        """
        Authenticate user and return token pair.

        Args:
            data: Login credentials
            client_ip: Client IP for logging (optional)

        Returns:
            Token pair response

        Raises:
            UnauthorizedError: If credentials are invalid
        """
        # Find user by email
        user = self._get_user_by_email(data.email)

        # Verify password or user not found
        # RN-AU08: Same error message for both cases (security)
        if not user or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Credenciales inválidas")

        # Check if user is active
        if not user.is_active:
            raise UnauthorizedError("Credenciales inválidas")

        # Generate tokens
        return await self._create_token_pair(user)

    async def refresh(self, refresh_token_str: str) -> TokenPairResponse:
        """
        Refresh access token using refresh token.

        Implements token rotation (RN-AU04) and replay attack detection (RN-AU05).

        Args:
            refresh_token_str: The raw refresh token string

        Returns:
            New token pair

        Raises:
            UnauthorizedError: If token is invalid, expired, or reused
        """
        # Hash the token to lookup in DB
        token_hash = hash_token(refresh_token_str)

        # Find token in database
        token = self.refresh_token_repo.get_by_token_hash(token_hash)

        if not token:
            raise UnauthorizedError("Token de refresco inválido")

        # Check if token is revoked or expired
        if token.revoked_at:
            raise UnauthorizedError("Token de refresco revocado")

        if token.expires_at < datetime.utcnow():
            raise UnauthorizedError("Token de refresco expirado")

        # RN-AU05: Replay attack detection
        if token.used:
            # Token was already used — potential replay attack!
            # Revoke ALL tokens in this family
            self.refresh_token_repo.revoke_family_tokens(token.family_id)
            self.session.flush()
            raise UnauthorizedError("Token reutilizado detectado")

        # Mark current token as used (rotation)
        self.refresh_token_repo.mark_token_as_used(token.id)
        self.session.flush()

        # Get user
        user = token.usuario
        if not user or not user.is_active:
            raise UnauthorizedError("Usuario no válido")

        # Generate new token pair
        return await self._create_token_pair(user, family_id=token.family_id)

    async def logout(self, refresh_token_str: str) -> None:
        """
        Logout user by revoking refresh token.

        Args:
            refresh_token_str: The refresh token to revoke

        Raises:
            UnauthorizedError: If token is invalid
        """
        token_hash = hash_token(refresh_token_str)
        token = self.refresh_token_repo.get_by_token_hash(token_hash)

        if not token:
            raise UnauthorizedError("Token de refresco inválido")

        # Revoke the token
        token.revoked_at = datetime.utcnow()
        self.session.flush()

    async def _create_token_pair(
        self,
        user: Usuario,
        family_id: Optional[uuid.UUID] = None,
    ) -> TokenPairResponse:
        """
        Create a new token pair for a user.

        Args:
            user: The user to create tokens for
            family_id: Optional family ID for token rotation

        Returns:
            Token pair response
        """
        # Get user roles
        roles = [rol.codigo for rol in user.roles]

        # Create access token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=roles,
        )

        # Create refresh token (opaque UUID)
        refresh_token_raw = create_refresh_token()
        refresh_token_hash = hash_token(refresh_token_raw)

        # Create new family if not provided
        if family_id is None:
            family_id = uuid.uuid4()

        # Calculate expiration
        from backend.config import settings
        expires_at = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Store refresh token in DB
        refresh_token_db = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            family_id=family_id,
            used=False,
            expires_at=expires_at,
        )
        self.session.add(refresh_token_db)
        self.session.flush()

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token_raw,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes in seconds
        )

    def _get_user_by_email(self, email: str) -> Optional[Usuario]:
        """Find user by email (case-insensitive)."""
        query = select(Usuario).where(
            Usuario.email.ilike(email),
            Usuario.eliminado_en.is_(None),
        )
        return self.session.execute(query).scalar_one_or_none()
