import hashlib
import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.storage import storage_service
from app.tasks.document_tasks import process_document

router = APIRouter()

@router.get("/{project_id}", response_model=list[DocumentResponse])
def list_documents(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    
    return db.query(Document).filter(Document.project_id == project_id).all()

@router.post("/{project_id}/upload", response_model=DocumentResponse)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Secure uploads
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF textbook materials are supported currently."
        )

    # Read bytes to calculate SHA-256 for duplicate checks
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > 100 * 1024 * 1024: # 100MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference books must not exceed 100MB in size."
        )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Check if this exact file is already uploaded in the project
    existing_doc = db.query(Document).filter(
        Document.project_id == project_id,
        Document.sha256_hash == sha256_hash
    ).first()

    if existing_doc:
        # If it was failed, allow re-triggering, otherwise return existing
        if existing_doc.processing_status != "failed":
            return existing_doc
        else:
            db.delete(existing_doc)
            db.commit()

    # Generate unique storage key
    clean_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    storage_key = f"{project_id}/{uuid.uuid4()}_{clean_filename}"

    # Write file to storage
    # Reset file read cursor
    file.file.seek(0)
    storage_service.save_file(file.file, storage_key)

    # Create Document record
    db_doc = Document(
        project_id=project_id,
        filename=file.filename,
        file_size=file_size,
        storage_key=storage_key,
        processing_status="uploaded",
        sha256_hash=sha256_hash
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Trigger asynchronous Celery indexing worker task
    process_document.delay(str(db_doc.id))

    return db_doc

@router.get("/status/{document_id}", response_model=DocumentResponse)
def get_document_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).join(Project).filter(
        Document.id == document_id,
        Project.user_id == current_user.id
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    # Remove files from physical storage
    try:
        storage_service.delete_file(document.storage_key)
    except Exception:
        pass
        
    db.delete(document)
    db.commit()
    return
