import pytest
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.document import Document, DocumentChunk, DocumentPage
from app.core import security
from app.tasks.document_tasks import process_document

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test user
    hashed_pwd = security.get_password_hash("testpassword")
    user = User(email="doc_test@example.com", hashed_password=hashed_pwd, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test project
    project = Project(user_id=user.id, name="Book Study", subject="Operating Systems")
    db.add(project)
    db.commit()
    db.refresh(project)
    
    token = security.create_access_token(user.email)
    
    yield {"db": db, "user": user, "project": project, "token": token}
    
    # Cleanup
    db.query(Document).filter(Document.project_id == project.id).delete()
    db.delete(project)
    db.delete(user)
    db.commit()
    db.close()

@patch("app.tasks.document_tasks.process_document.delay")
@patch("app.services.storage.FileStorageService.save_file")
def test_upload_document_flow(mock_save_file, mock_celery_delay, setup_database):
    token = setup_database["token"]
    project_id = str(setup_database["project"].id)
    
    pdf_content = b"%PDF-1.4 mock book data"
    mock_save_file.return_value = "storage/mock_book.pdf"
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"/api/v1/documents/{project_id}/upload",
        files={"file": ("operating_systems.pdf", pdf_content, "application/pdf")},
        headers=headers
    )
    
    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["filename"] == "operating_systems.pdf"
    assert doc_data["processing_status"] == "uploaded"
    
    # Verify background Celery task was enqueued
    mock_celery_delay.assert_called_once()
    
    # Test deduplication: uploading same file should yield the same document record
    response_dup = client.post(
        f"/api/v1/documents/{project_id}/upload",
        files={"file": ("operating_systems.pdf", pdf_content, "application/pdf")},
        headers=headers
    )
    assert response_dup.status_code == 200
    assert response_dup.json()["id"] == doc_data["id"]

@patch("app.services.pdf_processor.PDFProcessorService.extract_pages")
@patch("app.services.storage.FileStorageService.get_file_path")
@patch("app.services.ai_providers.AIProviderService.generate_embedding")
def test_celery_indexing_task(mock_embedding, mock_get_file_path, mock_extract_pages, setup_database):
    db = setup_database["db"]
    project_id = setup_database["project"].id
    
    # Create test document directly in DB
    doc = Document(
        project_id=project_id,
        filename="manual_book.pdf",
        file_size=100,
        storage_key="manual_key.pdf",
        processing_status="uploaded",
        sha256_hash="randomhash123"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Mock text extraction: return 2 pages
    mock_extract_pages.return_value = [
        {"page_index": 0, "text": "Chapter 1: Relational Algebra Introduction. Relational databases support selection, projection and joins. selection is marked as sigma and projection is pi.", "printed_page": "15"},
        {"page_index": 1, "text": "This is page 2. Selection operation is used to select rows matching criteria.", "printed_page": "16"}
    ]
    mock_get_file_path.return_value = "storage/manual_key.pdf"
    mock_embedding.return_value = [0.1] * 1536
    
    # Run the Celery task synchronously for testing
    result = process_document(str(doc.id))
    
    assert "Successfully processed" in result
    
    # Query database and verify insertions
    db.refresh(doc)
    assert doc.processing_status == "indexed"
    assert doc.page_count == 2
    
    # Check pages created
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).all()
    assert len(pages) == 2
    
    # Check chunks created
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
    assert len(chunks) > 0
    assert chunks[0].chapter == "Chapter 1: Relational Algebra Introduction. Relational databases suppor"
