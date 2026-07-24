import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import os
from sqlalchemy.types import UserDefinedType
from pgvector.sqlalchemy import Vector
from app.core.database import Base

# Custom fallback Vector type for SQLite tests
if os.getenv("TESTING", "").lower() == "true":
    class SQLiteVector(UserDefinedType):
        def __init__(self, dim=None):
            self.dim = dim
        def get_col_spec(self, **kw):
            return "TEXT"
        def bind_processor(self, dialect):
            def process(value):
                if value is None:
                    return None
                if isinstance(value, str):
                    return value
                return ",".join(map(str, value))
            return process
        def result_processor(self, dialect, coltype):
            def process(value):
                if value is None:
                    return None
                return list(map(float, value.split(",")))
            return process
    Vector = SQLiteVector

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_key = Column(String(512), nullable=False)
    page_count = Column(Integer, default=0)
    processing_status = Column(String(50), default="uploaded")  # uploaded, extracting, chunking, embedding, indexed, failed
    sha256_hash = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="documents")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentPage(Base):
    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_index = Column(Integer, nullable=False)  # 0-indexed page number in PDF
    printed_page_number = Column(String(50), nullable=True)  # Printed logical page number
    text_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="pages")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    chapter = Column(String(255), nullable=True)
    section = Column(String(255), nullable=True)
    subsection = Column(String(255), nullable=True)
    pdf_page_start = Column(Integer, nullable=False)
    pdf_page_end = Column(Integer, nullable=False)
    printed_page_start = Column(String(50), nullable=True)
    printed_page_end = Column(String(50), nullable=True)
    content_type = Column(String(50), nullable=True)  # prose, definition, formula, code, comparison, example
    embedding = Column(Vector(1536), nullable=True)  # default size is 1536 for OpenAI small-embed, dynamic based on model
    chunk_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")
