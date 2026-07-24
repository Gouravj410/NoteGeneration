from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    subject: str = Field(..., max_length=255)
    course: str | None = Field(None, max_length=255)
    semester: str | None = Field(None, max_length=50)
    university: str | None = Field(None, max_length=255)
    preferred_language: str = Field("English", max_length=50)

class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=255)
    course: str | None = Field(None, max_length=255)
    semester: str | None = Field(None, max_length=50)
    university: str | None = Field(None, max_length=255)
    preferred_language: str | None = Field(None, max_length=50)

class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    subject: str
    course: str | None
    semester: str | None
    university: str | None
    preferred_language: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
