from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedResponse(ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
