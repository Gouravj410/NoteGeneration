import os
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class SyllabusVersion(Base):
    __tablename__ = "syllabus_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_json = Column(JSONB if os.getenv("TESTING", "").lower() != "true" else JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="syllabus_versions")
    modules = relationship("SyllabusModule", back_populates="syllabus_version", cascade="all, delete-orphan")

class SyllabusModule(Base):
    __tablename__ = "syllabus_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    syllabus_version_id = Column(UUID(as_uuid=True), ForeignKey("syllabus_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    module_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    syllabus_version = relationship("SyllabusVersion", back_populates="modules")
    topics = relationship("SyllabusTopic", back_populates="module", cascade="all, delete-orphan")

class SyllabusTopic(Base):
    __tablename__ = "syllabus_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("syllabus_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_topic_id = Column(UUID(as_uuid=True), ForeignKey("syllabus_topics.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    depth = Column(Integer, default=1)
    status = Column(String(50), default="not_started")  # not_started, generating, completed, partial, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    module = relationship("SyllabusModule", back_populates="topics")
    generated_notes = relationship("GeneratedNote", back_populates="topic", cascade="all, delete-orphan")
    quiz_questions = relationship("QuizQuestion", back_populates="topic")
    
    # Self-referential relationship for subtopics
    subtopics = relationship(
        "SyllabusTopic",
        backref=backref("parent_topic", remote_side=[id]),
        cascade="all, delete-orphan"
    )
