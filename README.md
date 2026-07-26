# NoteGeneration (StudyForge AI)

A production-ready study notes generation platform powered by FastAPI, Next.js, and GenAI.

## Key Features

- **Project Workspaces**: Group study resources, syllabus, and notes.
- **Syllabus Parsing & Structuring**: Upload standard syllabi and parse them into structured modules/topics.
- **Document Processing & Storage**: Upload references, textbook sections, and PDFs. Auto-extraction of text with optical character recognition (OCR) and layout parsing.
- **RAG-Grounded Note Generation**: Create notes, summaries, and explanations fully grounded in uploaded reference materials.
- **Interactive AI Tutor**: Chat with an AI tutor based on the uploaded materials.
- **Multi-Format Export**: Export generated study guides and notes to PDF or DOCX.

## Architecture

- **Backend**: FastAPI, PostgreSQL + PGVector, SQLAlchemy, Alembic, Celery, Redis.
- **Frontend**: Next.js (TypeScript, TailwindCSS).
