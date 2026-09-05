from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import PaceUser
from app.repositories.user_repository import get_or_create_dev_user


def get_current_user(db: Session = Depends(get_db)) -> PaceUser:
    """Temporary local-development identity.

    This dependency will be replaced by JWT validation when Supabase/Google Auth
    is introduced. Keeping it behind a dependency means profile routes will not
    need to change shape later.
    """
    return get_or_create_dev_user(
        db,
        auth_subject=settings.dev_auth_subject,
        email=settings.dev_user_email,
    )
