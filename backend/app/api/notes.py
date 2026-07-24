from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.note import GeneratedNote, NoteVersion
from app.models.syllabus import SyllabusTopic, SyllabusVersion, SyllabusModule
from app.schemas.note import GeneratedNoteResponse, NoteEditRequest
from app.services.note_generator import NoteGeneratorService
from app.services.exporter import ExporterService

router = APIRouter()

@router.get("/{project_id}/topic/{topic_id}", response_model=GeneratedNoteResponse)
def read_topic_notes(
    project_id: UUID,
    topic_id: UUID,
    mode: str = "detailed",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
    db_note = db.query(GeneratedNote).filter(
        GeneratedNote.project_id == project_id,
        GeneratedNote.topic_id == topic_id,
        GeneratedNote.mode == mode
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notes for this topic have not been generated yet.")
        
    # Populate the active version (the latest version)
    latest_version = db.query(NoteVersion).filter(
        NoteVersion.note_id == db_note.id
    ).order_by(NoteVersion.version_number.desc()).first()
    
    db_note.active_version = latest_version
    
    return db_note

@router.post("/{project_id}/topic/{topic_id}/generate", response_model=GeneratedNoteResponse)
def generate_topic_notes(
    project_id: UUID,
    topic_id: UUID,
    mode: str = "detailed",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Syllabus topic not found")

    # Enforce free-tier token usage quotas
    if current_user.token_usage >= current_user.token_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Your StudyForge AI token usage quota has been exhausted. Contact support to raise limits."
        )
        
    try:
        db_note = NoteGeneratorService.generate_notes_for_topic(
            db=db,
            project_id=project_id,
            topic_id=topic_id,
            mode=mode
        )
        
        # Increment user's token usage count
        note_length = len(db_note.canonical_content)
        # 10,000 input chars + output length divided by average characters per token (approx 4)
        estimated_consumed = (10000 + note_length) // 4
        current_user.token_usage += estimated_consumed
        db.commit()
        db.refresh(current_user)

        # Populate active version details
        latest_version = db.query(NoteVersion).filter(
            NoteVersion.note_id == db_note.id
        ).order_by(NoteVersion.version_number.desc()).first()
        
        db_note.active_version = latest_version
        return db_note
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Notes generation failed: {str(e)}"
        )

@router.put("/{project_id}/topic/{topic_id}", response_model=GeneratedNoteResponse)
def update_topic_notes(
    project_id: UUID,
    topic_id: UUID,
    note_in: NoteEditRequest,
    mode: str = "detailed",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        
    db_note = db.query(GeneratedNote).filter(
        GeneratedNote.project_id == project_id,
        GeneratedNote.topic_id == topic_id,
        GeneratedNote.mode == mode
    ).first()
    
    if not db_note:
        # Create a new notes record if editing first
        db_note = GeneratedNote(
            project_id=project_id,
            topic_id=topic_id,
            mode=mode,
            canonical_content=note_in.content,
            coverage_score=100.0,
            source_grounding_status="user_edited"
        )
        db.add(db_note)
        db.flush()
    else:
        db_note.canonical_content = note_in.content
        db_note.source_grounding_status = "user_edited"
        
    # Build new version
    version_count = db.query(NoteVersion).filter(NoteVersion.note_id == db_note.id).count()
    db_version = NoteVersion(
        note_id=db_note.id,
        content=note_in.content,
        version_number=version_count + 1,
        created_by_type="user"
    )
    db.add(db_version)
    db.commit()
    
    # Refresh to load latest
    db.refresh(db_note)
    db_note.active_version = db_version
    
    return db_note

@router.get("/{project_id}/export/{format_type}")
def export_project_notes(
    project_id: UUID,
    format_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if format_type not in ["pdf", "docx"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format. Use 'pdf' or 'docx'.")

    # Fetch active syllabus version modules and topics
    syllabus_version = db.query(SyllabusVersion).filter(
        SyllabusVersion.project_id == project_id,
        SyllabusVersion.is_active == True
    ).first()

    if not syllabus_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active syllabus outline found for this project.")

    notes_to_export = []
    for mod in syllabus_version.modules:
        for top in mod.topics:
            if top.parent_topic_id is not None:
                continue
            db_note = db.query(GeneratedNote).filter(
                GeneratedNote.project_id == project_id,
                GeneratedNote.topic_id == top.id
            ).first()
            if db_note:
                notes_to_export.append({
                    "module_title": mod.title,
                    "topic_name": top.name,
                    "content": db_note.canonical_content
                })

    if not notes_to_export:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No study notes have been generated to export yet.")

    if format_type == "pdf":
        file_bytes = ExporterService.generate_pdf_notes(project.name, notes_to_export)
        media_type = "application/pdf"
        filename = f"{project.name.lower().replace(' ', '_')}_notes.pdf"
    else:
        file_bytes = ExporterService.generate_docx_notes(project.name, notes_to_export)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{project.name.lower().replace(' ', '_')}_notes.docx"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

