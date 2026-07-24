from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Raw Syllabus Extraction Schemas (Matching LLM Output Constraints) ---

class SyllabusExtractTopic(BaseModel):
    name: str = Field(..., description="Name of the main topic")
    subtopics: List[str] = Field(default=[], description="List of subtopics or learning goals under this topic")

class SyllabusExtractModule(BaseModel):
    module_number: int = Field(..., description="Sequence number of the module")
    title: str = Field(..., description="Module title")
    description: Optional[str] = Field(None, description="Short summary/description of this module if available")
    topics: List[SyllabusExtractTopic] = Field(default=[], description="Topics in this module")

class SyllabusExtractResponse(BaseModel):
    subject: str = Field(..., description="Calculated subject title")
    modules: List[SyllabusExtractModule] = Field(..., description="List of academic modules extracted")

# --- Database Confirmed / API Active Syllabus Schemas ---

class TopicBase(BaseModel):
    name: str
    description: Optional[str] = None
    position: int

class SubtopicResponse(BaseModel):
    id: UUID
    parent_topic_id: UUID
    name: str
    description: Optional[str]
    position: int
    status: str

    class Config:
        from_attributes = True

class TopicResponse(BaseModel):
    id: UUID
    module_id: UUID
    parent_topic_id: Optional[UUID]
    name: str
    description: Optional[str]
    position: int
    depth: int
    status: str
    subtopics: List[SubtopicResponse] = []

    class Config:
        from_attributes = True

class ModuleResponse(BaseModel):
    id: UUID
    module_number: int
    title: str
    description: Optional[str]
    position: int
    topics: List[TopicResponse] = []

    class Config:
        from_attributes = True

class SyllabusVersionResponse(BaseModel):
    id: UUID
    project_id: UUID
    raw_json: dict
    is_active: bool
    created_at: datetime
    modules: List[ModuleResponse] = []

    class Config:
        from_attributes = True
