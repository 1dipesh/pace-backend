from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.core.auth import InvalidAccessTokenError, SupabaseTokenVerifier
from app.main import app

client = TestClient(app)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def build_real_token_verifier() -> tuple[SupabaseTokenVerifier, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = SupabaseTokenVerifier(
        issuer="https://pace-test.supabase.co/auth/v1",
        jwks_url="https://pace-test.supabase.co/auth/v1/.well-known/jwks.json",
        audience="authenticated",
        algorithms=["RS256"],
    )
    verifier.jwks_client.get_signing_key_from_jwt = lambda _token: SimpleNamespace(
        key=private_key.public_key()
    )
    return verifier, private_key


def test_protected_endpoint_requires_bearer_token() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_is_rejected() -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers("invalid-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


def test_supabase_verifier_validates_signature_and_claims() -> None:
    verifier, private_key = build_real_token_verifier()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "https://pace-test.supabase.co/auth/v1",
            "sub": "signed-user",
            "aud": "authenticated",
            "role": "authenticated",
            "email": "signed@example.com",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "user_metadata": {
                "full_name": "Signed User",
                "avatar_url": "https://example.com/signed.png",
            },
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    identity = verifier.verify_access_token(token)

    assert identity.subject == "signed-user"
    assert identity.email == "signed@example.com"
    assert identity.display_name == "Signed User"


def test_supabase_verifier_rejects_expired_token() -> None:
    verifier, private_key = build_real_token_verifier()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "https://pace-test.supabase.co/auth/v1",
            "sub": "expired-user",
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=2),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify_access_token(token)


@pytest.mark.integration
def test_first_authenticated_request_provisions_and_updates_user() -> None:
    created = client.get("/api/v1/auth/me", headers=auth_headers("user-a-token"))

    assert created.status_code == 200
    created_body = created.json()
    assert created_body["email"] == "user-a@example.com"
    assert created_body["display_name"] == "User A"

    updated = client.get("/api/v1/auth/me", headers=auth_headers("updated-user-a-token"))

    assert updated.status_code == 200
    assert updated.json()["id"] == created_body["id"]
    assert updated.json()["display_name"] == "User A Updated"
    assert updated.json()["avatar_url"] == "https://example.com/user-a-new.png"


@pytest.mark.integration
def test_user_owned_records_are_isolated() -> None:
    profile = {
        "date_of_birth": "1990-12-20",
        "height_cm": 178,
        "weight_kg": 78,
        "calorie_estimate_sex": "male",
        "goal": "build_muscle",
        "activity_level": "active",
        "training_experience": "intermediate",
        "training_days_per_week": 4,
    }

    client.delete("/api/v1/profile", headers=auth_headers("user-a-token"))
    created = client.post(
        "/api/v1/profile",
        json=profile,
        headers=auth_headers("user-a-token"),
    )
    assert created.status_code == 201

    other_user = client.get("/api/v1/profile", headers=auth_headers("user-b-token"))
    assert other_user.status_code == 404

    owner = client.get("/api/v1/profile", headers=auth_headers("user-a-token"))
    assert owner.status_code == 200
    assert owner.json()["id"] == created.json()["id"]

    assert client.delete(
        "/api/v1/profile", headers=auth_headers("user-a-token")
    ).status_code == 204
