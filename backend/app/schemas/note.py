from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional

class NoteCitationResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_filename: str
    pdf_page_start: int
    pdf_page_end: int
    citation_label: str

    class Config:
        from_attributes = True

class NoteVersionResponse(BaseModel):
    id: UUID
    note_id: UUID
    content: str
    version_number: int
    created_by_type: str  # ai, user
    created_at: datetime
    citations: List[NoteCitationResponse] = []

    class Config:
        from_attributes = True

class GeneratedNoteResponse(BaseModel):
    id: UUID
    project_id: UUID
    topic_id: UUID
    mode: str
    canonical_content: str
    coverage_score: float
    source_grounding_status: str
    created_at: datetime
    updated_at: datetime
    active_version: Optional[NoteVersionResponse] = None

    class Config:
        from_attributes = True

class NoteEditRequest(BaseModel):
    content: str

class CoverageReportItem(BaseModel):
    topic_id: UUID
    topic_name: str
    status: str  # Covered, Partially Covered, Missing, not_started
    score: float

class ModuleCoverageReport(BaseModel):
    module_id: UUID
    module_title: str
    module_number: int
    coverage_score: float
    topics: List[CoverageReportItem] = []

class OverallCoverageReport(BaseModel):
    project_id: UUID
    overall_coverage_score: float
    modules: List[ModuleCoverageReport] = []
