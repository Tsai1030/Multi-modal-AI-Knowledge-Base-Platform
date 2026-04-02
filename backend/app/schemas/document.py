from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    error_message: str | None
    uploaded_by_id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    error_message: str | None
