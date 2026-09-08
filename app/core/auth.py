from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

from app.core.config import settings


class AuthConfigurationError(RuntimeError):
    pass


class InvalidAccessTokenError(ValueError):
    pass


class AuthProviderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    subject: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class SupabaseTokenVerifier:
    """Verify Supabase access tokens against the project's public JWKS."""

    def __init__(
        self,
        *,
        issuer: str,
        jwks_url: str,
        audience: str,
        algorithms: list[str],
        clock_skew_seconds: int = 30,
    ) -> None:
        if not algorithms:
            raise AuthConfigurationError("At least one JWT algorithm is required")

        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.clock_skew_seconds = clock_skew_seconds
        self.jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=600,
        )

    def verify_access_token(self, token: str) -> AuthIdentity:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in self.algorithms:
                raise InvalidAccessTokenError("JWT algorithm is not allowed")

            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={"require": ["exp", "iss", "sub"]},
            )
        except InvalidAccessTokenError:
            raise
        except PyJWKClientConnectionError as exc:
            raise AuthProviderUnavailableError("Unable to load authentication keys") from exc
        except (InvalidTokenError, PyJWKClientError, ValueError, TypeError) as exc:
            raise InvalidAccessTokenError("Access token validation failed") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise InvalidAccessTokenError("Access token subject is missing")

        role = claims.get("role")
        if role is not None and role != "authenticated":
            raise InvalidAccessTokenError("Access token role is not authenticated")

        metadata = claims.get("user_metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        email = _optional_string(claims.get("email"))
        display_name = _first_string(metadata, "full_name", "name", "display_name")
        avatar_url = _first_string(metadata, "avatar_url", "picture")

        return AuthIdentity(
            subject=subject,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_string(values: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional_string(values.get(key))
        if value is not None:
            return value
    return None


@lru_cache
def get_supabase_token_verifier() -> SupabaseTokenVerifier:
    issuer = settings.supabase_jwt_issuer
    jwks_url = settings.supabase_jwks_url
    if not issuer or not jwks_url:
        raise AuthConfigurationError("SUPABASE_URL is required")

    return SupabaseTokenVerifier(
        issuer=issuer,
        jwks_url=jwks_url,
        audience=settings.supabase_jwt_audience,
        algorithms=settings.auth_jwt_algorithms,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
    )
