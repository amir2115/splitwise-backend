from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.sync import InitialImportRequest, SyncRequest, SyncResponse
from app.sync.service import initial_import, sync_user_data

router = APIRouter()


@router.post("/import", response_model=SyncResponse)
def import_local_data(
    payload: InitialImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncResponse:
    return initial_import(db, current_user, payload)


@router.post("", response_model=SyncResponse)
def sync(payload: SyncRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SyncResponse:
    return sync_user_data(db, current_user, payload)
