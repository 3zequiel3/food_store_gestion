"""
Auth service layer.

Implements business logic for authentication including:
- User registration with automatic CLIENT role assignment (atomic: Usuario + UsuarioRol + RefreshToken)
- Login with secure credential verification
- Token refresh with rotation and replay attack detection (RN-AU04, RN-AU05)
- Logout with token revocation

Transaction ownership: each public method opens its own UnitOfWork context.
The HTTP adapter (router) does NOT receive any Session or UnitOfWork via DI,
and does NOT call commit() or rollback() explicitly.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.features.auth.models import RefreshToken
from backend.features.auth.repository import RefreshTokenRepository
from backend.features.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenPairResponse,
)
from backend.features.users.models import Usuario, UsuarioRol
from backend.shared.exceptions import ConflictError, UnauthorizedError
from backend.shared.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from backend.shared.unit_of_work import UnitOfWork


class AuthService:
    """Service for authentication operations.

    Owns the transaction boundary for every public operation.
    Each method opens a UnitOfWork context internally — the router
    does NOT inject a session.
    """

    # Role ID constants (from seed data, RN-AU07)
    ROLE_CLIENT_ID = 4

    def __init__(self) -> None:
        pass

    def register(self, data: RegisterRequest) -> TokenPairResponse:
        """
        Register a new user with CLIENT role.

        Atomicity guarantee (R1): Usuario, UsuarioRol, and RefreshToken are
        persisted in a SINGLE transaction. If any insert fails, none of them
        are committed.

        Args:
            data: Registration request data

        Returns:
            TokenPairResponse (access_token + refresh_token)

        Raises:
            ConflictError: If email already exists
        """
        with UnitOfWork() as uow:
            uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

            # Check if email already exists
            existing_user = uow.session.execute(
                select(Usuario).where(
                    Usuario.email.ilike(data.email),
                    Usuario.eliminado_en.is_(None),
                )
            ).scalar_one_or_none()
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
            uow.session.add(user)
            uow.session.flush()  # Get the ID

            # Assign CLIENT role automatically (RN-AU07)
            user_role = UsuarioRol(
                user_id=user.id,
                role_id=self.ROLE_CLIENT_ID,
            )
            uow.session.add(user_role)
            uow.session.flush()

            # Refresh to get roles loaded
            uow.session.refresh(user)

            # Create token pair within the same transaction (D4, R1)
            return self._create_token_pair(user, uow.session)

    def login(
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
        with UnitOfWork() as uow:
            uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

            # Find user by email (case-insensitive)
            user = uow.session.execute(
                select(Usuario).where(
                    Usuario.email.ilike(data.email),
                    Usuario.eliminado_en.is_(None),
                )
            ).scalar_one_or_none()

            # Verify password or user not found
            # RN-AU08: Same error message for both cases (security)
            if not user or not verify_password(data.password, user.password_hash):
                raise UnauthorizedError("Credenciales inválidas")

            # Check if user is active
            if not user.is_active:
                raise UnauthorizedError("Credenciales inválidas")

            # Generate tokens
            return self._create_token_pair(user, uow.session)

    def refresh(self, refresh_token_str: str) -> TokenPairResponse:
        """
        Refresh access token using refresh token.

        Implements token rotation (RN-AU04) and replay attack detection (RN-AU05).
        All updates and the new token insert happen within a single transaction (R5).

        Args:
            refresh_token_str: The raw refresh token string

        Returns:
            New token pair

        Raises:
            UnauthorizedError: If token is invalid, expired, or reused
        """
        with UnitOfWork() as uow:
            uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

            # Hash the token to lookup in DB
            token_hash = hash_token(refresh_token_str)

            # Find token in database
            token = uow.refresh_tokens.get_by_token_hash(token_hash)

            if not token:
                raise UnauthorizedError("Token de refresco inválido")

            # RN-AU05: Replay attack detection — revoked_at set means already consumed or logged out
            if token.revoked_at is not None:
                # Potential replay attack — revoke ALL tokens of this user
                uow.refresh_tokens.revoke_all_user_tokens(token.user_id)
                uow.session.flush()  # R5: flush bulk UPDATE before raising
                raise UnauthorizedError("Token reutilizado detectado")

            # SQLite (used in tests) drops tzinfo on read; coerce to UTC-aware
            # before comparing. Postgres TIMESTAMPTZ keeps tzinfo natively.
            expires_at = token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                raise UnauthorizedError("Token de refresco expirado")

            # Mark current token as revoked (rotation — RN-AU04)
            uow.refresh_tokens.mark_token_as_revoked(token.id)
            uow.session.flush()  # R5: flush single UPDATE before SELECT in _create_token_pair

            # Get user
            user = token.usuario
            if not user or not user.is_active:
                raise UnauthorizedError("Usuario no válido")

            # Generate new token pair within the same transaction
            return self._create_token_pair(user, uow.session)

    def logout(self, refresh_token_str: str) -> None:
        """
        Logout user by revoking refresh token.

        Args:
            refresh_token_str: The refresh token to revoke

        Raises:
            UnauthorizedError: If token is invalid
        """
        with UnitOfWork() as uow:
            uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))

            token_hash = hash_token(refresh_token_str)
            token = uow.refresh_tokens.get_by_token_hash(token_hash)

            if not token:
                raise UnauthorizedError("Token de refresco inválido")

            # Revoke the token (sets revoked_at); __exit__ commits
            uow.refresh_tokens.mark_token_as_revoked(token.id)
            uow.session.flush()

    def _create_token_pair(
        self,
        user: Usuario,
        session: Session,
    ) -> TokenPairResponse:
        """
        Create a new token pair for a user.

        IMPORTANT: this helper is intentionally NOT self-contained — it operates
        within the caller's open transaction (session). It does NOT open a new
        UnitOfWork. The caller MUST pass uow.session so that the RefreshToken
        INSERT is part of the same atomic transaction (D6).

        Args:
            user: The user to create tokens for
            session: The active SQLAlchemy session from the caller's UnitOfWork

        Returns:
            Token pair response with expires_in derived from settings
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

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Store refresh token in DB (no family_id, no used flag — ERD v5 §3.1)
        refresh_token_db = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        session.add(refresh_token_db)
        session.flush()

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token_raw,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
