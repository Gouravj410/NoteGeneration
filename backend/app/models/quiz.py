import os
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("syllabus_topics.id", ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    options_json = Column(JSONB if os.getenv("TESTING", "").lower() != "true" else JSON, nullable=True)  # List of string options for MCQs, null for open Qs
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    difficulty = Column(String(50), default="medium")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    quiz = relationship("Quiz", back_populates="questions")
    topic = relationship("SyllabusTopic", back_populates="quiz_questions")
