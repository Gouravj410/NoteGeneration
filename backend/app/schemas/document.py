from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    file_size: int
    page_count: int
    processing_status: str  # uploaded, extracting, chunking, embedding, indexed, failed
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: str | None
    printed_page_end: str | None
    chapter: str | None
    section: str | None
    subsection: str | None

    class Config:
        from_attributes = True
