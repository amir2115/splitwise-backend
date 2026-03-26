from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    min_supported_version_code: Optional[int] = Field(default=None)
    latest_version_code: Optional[int] = Field(default=None)
    update_mode: Optional[str] = Field(default=None)
    store_url: Optional[str] = Field(default=None)
    update_title: Optional[str] = Field(default=None)
    update_message: Optional[str] = Field(default=None)
