from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthConfigurationError,
    AuthIdentity,
    AuthProviderUnavailableError,
    InvalidAccessTokenError,
    SupabaseTokenVerifier,
    get_supabase_token_verifier,
)
from app.db.session import get_db
from app.models.user import PaceUser
from app.repositories.user_repository import get_or_create_authenticated_user

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_verifier() -> SupabaseTokenVerifier:
    try:
        return get_supabase_token_verifier()
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc


def get_authenticated_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[SupabaseTokenVerifier, Depends(get_token_verifier)],
) -> AuthIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        return verifier.verify_access_token(credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise _unauthorized("Invalid or expired access token") from exc
    except AuthProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider unavailable",
        ) from exc


def get_current_user(
    identity: Annotated[AuthIdentity, Depends(get_authenticated_identity)],
    db: Session = Depends(get_db),
) -> PaceUser:
    user = get_or_create_authenticated_user(
        db,
        auth_subject=identity.subject,
        email=identity.email,
        display_name=identity.display_name,
        avatar_url=identity.avatar_url,
    )
    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pace account is inactive",
        )
    return user
