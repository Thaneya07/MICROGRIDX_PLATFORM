"""
Microgrid listing API.

Read-only. Lists microgrids that already exist in the database — this
endpoint does not create anything. It exists so the frontend can offer a
"choose an existing microgrid" picker instead of requiring the user to
already know a UUID.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.microgrid import Microgrid
from app.schemas.microgrid import MicrogridSummary

router = APIRouter(prefix="/api/microgrids", tags=["microgrids"])


@router.get("", response_model=List[MicrogridSummary])
def list_microgrids(db: Session = Depends(get_db)) -> List[MicrogridSummary]:
    rows = db.execute(select(Microgrid).order_by(Microgrid.created_at.desc())).scalars().all()
    return [MicrogridSummary.model_validate(r) for r in rows]
