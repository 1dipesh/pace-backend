from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import PaceUser


def get_or_create_dev_user(db: Session, *, auth_subject: str, email: str | None) -> PaceUser:
    user = db.scalar(
        select(PaceUser).where(
            PaceUser.auth_subject == auth_subject,
            PaceUser.deleted_at.is_(None),
        )
    )
    if user is not None:
        return user

    user = PaceUser(auth_subject=auth_subject, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
