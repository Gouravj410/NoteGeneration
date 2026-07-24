import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    course = Column(String(255), nullable=True)
    semester = Column(String(50), nullable=True)
    university = Column(String(255), nullable=True)
    preferred_language = Column(String(50), default="English")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="projects")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    syllabus_versions = relationship("SyllabusVersion", back_populates="project", cascade="all, delete-orphan")
    generated_notes = relationship("GeneratedNote", back_populates="project", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="project", cascade="all, delete-orphan")
