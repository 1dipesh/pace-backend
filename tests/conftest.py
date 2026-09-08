import os

import pytest

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./.pytest_pace.db"
os.environ["SUPABASE_URL"] = "https://pace-test.supabase.co"

from app.api.deps import get_token_verifier  # noqa: E402
from app.core.auth import AuthIdentity, InvalidAccessTokenError  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
import app.models as models  # noqa: E402,F401


class FakeTokenVerifier:
    identities = {
        "dev-token": AuthIdentity(
            subject="dev-local-user",
            email="dev@pace.local",
            display_name="Pace Developer",
        ),
        "user-a-token": AuthIdentity(
            subject="auth-user-a",
            email="user-a@example.com",
            display_name="User A",
            avatar_url="https://example.com/user-a.png",
        ),
        "updated-user-a-token": AuthIdentity(
            subject="auth-user-a",
            email="user-a@example.com",
            display_name="User A Updated",
            avatar_url="https://example.com/user-a-new.png",
        ),
        "user-b-token": AuthIdentity(
            subject="auth-user-b",
            email="user-b@example.com",
            display_name="User B",
        ),
    }

    def verify_access_token(self, token: str) -> AuthIdentity:
        identity = self.identities.get(token)
        if identity is None:
            raise InvalidAccessTokenError("Test token is invalid")
        return identity


@pytest.fixture(scope="session", autouse=True)
def configure_test_application():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_token_verifier] = lambda: FakeTokenVerifier()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.remove(".pytest_pace.db")
    except FileNotFoundError:
        pass
