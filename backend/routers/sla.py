from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import require_admin, require_agent
from database import get_db
from models import SLATarget, TicketPriority, User
from schemas.sla import SLATargetResponse, SLATargetUpdate


router = APIRouter(prefix="/api/sla", tags=["sla"])


@router.get("/targets", response_model=list[SLATargetResponse])
def list_sla_targets(current_user: User = Depends(require_agent), db: Session = Depends(get_db)):
    del current_user
    return list(db.scalars(select(SLATarget).order_by(SLATarget.priority)).all())


@router.put("/targets/{priority}", response_model=SLATargetResponse)
def update_sla_target(
    priority: TicketPriority,
    payload: SLATargetUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del current_user
    if payload.resolution_minutes < payload.response_minutes:
        raise HTTPException(status_code=422, detail="Resolution target must be at least the response target")
    target = db.get(SLATarget, priority)
    if target is None:
        target = SLATarget(priority=priority, **payload.model_dump())
        db.add(target)
    else:
        target.response_minutes = payload.response_minutes
        target.resolution_minutes = payload.resolution_minutes
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    return target
