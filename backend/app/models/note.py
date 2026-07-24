import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class GeneratedNote(Base):
    __tablename__ = "generated_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(50), default="detailed")  # detailed, exam, revision
    canonical_content = Column(Text, nullable=False)  # Current display content
    coverage_score = Column(Float, default=0.0)
    source_grounding_status = Column(String(50), default="unverified")  # grounded, missing_sources, unverified, mixed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="generated_notes")
    topic = relationship("SyllabusTopic", back_populates="generated_notes")
    versions = relationship("NoteVersion", back_populates="note", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "topic_id", "mode", name="uq_project_topic_mode"),
    )

class NoteVersion(Base):
    __tablename__ = "note_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("generated_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)
    created_by_type = Column(String(50), default="ai")  # ai, user
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    note = relationship("GeneratedNote", back_populates="versions")
    citations = relationship("NoteCitation", back_populates="note_version", cascade="all, delete-orphan")

class NoteCitation(Base):
    __tablename__ = "note_citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_version_id = Column(UUID(as_uuid=True), ForeignKey("note_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    pdf_page_start = Column(Integer, nullable=False)
    pdf_page_end = Column(Integer, nullable=False)
    citation_label = Column(String(50), nullable=False)  # e.g. "[1]"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    note_version = relationship("NoteVersion", back_populates="citations")
    document = relationship("Document")
    chunk = relationship("DocumentChunk")

    @property
    def document_filename(self) -> str:
        return self.document.filename if self.document else "Reference Book"
