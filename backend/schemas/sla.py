from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models import TicketPriority


class SLATargetUpdate(BaseModel):
    response_minutes: int = Field(gt=0, le=525600)
    resolution_minutes: int = Field(gt=0, le=1051200)


class SLATargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    priority: TicketPriority
    response_minutes: int
    resolution_minutes: int
    updated_at: datetime
