from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.account import DeletePaceAccountRequest, DeletePaceAccountResponse
from app.services.account_service import delete_account, export_account


router = APIRouter(prefix="/api/v1/account", tags=["account"])


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, private"


@router.get("/export", dependencies=[Depends(_private)])
def download_account_export(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return export_account(db, user)


@router.delete("", response_model=DeletePaceAccountResponse, dependencies=[Depends(_private)])
def remove_pace_account(
    payload: DeletePaceAccountRequest,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
) -> DeletePaceAccountResponse:
    delete_account(db, user)
    return DeletePaceAccountResponse(deleted=True)
