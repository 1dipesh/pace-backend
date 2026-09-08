from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import PaceUser


def get_user_by_auth_subject(db: Session, auth_subject: str) -> PaceUser | None:
    return db.scalar(select(PaceUser).where(PaceUser.auth_subject == auth_subject))


def get_or_create_authenticated_user(
    db: Session,
    *,
    auth_subject: str,
    email: str | None,
    display_name: str | None,
    avatar_url: str | None,
) -> PaceUser:
    user = get_user_by_auth_subject(db, auth_subject)
    if user is not None:
        changed = False
        for field, value in (
            ("email", email),
            ("display_name", display_name),
            ("avatar_url", avatar_url),
        ):
            if value is not None and getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

    user = PaceUser(
        auth_subject=auth_subject,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two first requests for the same new identity may arrive together.
        db.rollback()
        user = get_user_by_auth_subject(db, auth_subject)
        if user is None:
            raise
    db.refresh(user)
    return user
