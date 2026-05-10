from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UpdateRequestCreate(BaseModel):
    family_id: int
    requested_changes: str


class UpdateRequestResponse(BaseModel):
    id: int
    family_id: int
    requested_changes: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None

    model_config = ConfigDict(
        from_attributes = True
    )

class UpdateRequestReview(BaseModel):
    status: str  # approved / rejected
