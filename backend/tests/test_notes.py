import pytest
from unittest.mock import patch
from uuid import uuid4
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.document import Document, DocumentChunk
from app.models.syllabus import SyllabusVersion, SyllabusModule, SyllabusTopic
from app.models.note import GeneratedNote, NoteVersion, NoteCitation
from app.core import security
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test user
    hashed_pwd = security.get_password_hash("testpassword")
    user = User(email="notes_test@example.com", hashed_password=hashed_pwd, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test project
    project = Project(user_id=user.id, name="DBMS Study", subject="Database Management Systems")
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create active syllabus version
    syllabus = SyllabusVersion(
        project_id=project.id,
        raw_json={},
        is_active=True
    )
    db.add(syllabus)
    db.commit()
    db.refresh(syllabus)

    # Create module
    module = SyllabusModule(
        syllabus_version_id=syllabus.id,
        module_number=1,
        title="Introduction to DBMS",
        position=0
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    # Create topic
    topic = SyllabusTopic(
        module_id=module.id,
        name="DBMS Architecture",
        position=0,
        depth=1,
        status="not_started"
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)

    # Create dummy document
    doc = Document(
        project_id=project.id,
        filename="dbms_textbook.pdf",
        file_size=1000,
        storage_key="dbms_textbook.pdf",
        processing_status="indexed",
        sha256_hash="randomhash777"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Insert dummy document chunk
    chunk = DocumentChunk(
        document_id=doc.id,
        project_id=project.id,
        content="The three schema architecture defines external conceptual and internal schemas. It offers logical and physical data independence.",
        token_count=20,
        pdf_page_start=45,
        pdf_page_end=45,
        printed_page_start="40",
        printed_page_end="40",
        content_type="prose",
        chunk_hash="hashchunk45"
    )
    db.add(chunk)
    db.commit()
    
    token = security.create_access_token(user.email)
    
    yield {
        "db": db, "user": user, "project": project, "doc": doc, 
        "topic": topic, "chunk": chunk, "token": token
    }
    
    # Cleanup
    db.query(NoteCitation).delete()
    db.query(NoteVersion).delete()
    db.query(GeneratedNote).delete()
    db.delete(chunk)
    db.delete(doc)
    db.delete(topic)
    db.delete(module)
    db.delete(syllabus)
    db.delete(project)
    db.delete(user)
    db.commit()
    db.close()

@patch("app.services.verifier.NoteVerificationService.verify_and_refine_notes")
@patch("app.services.ai_providers.AIProviderService.generate_text")
@patch("app.services.ai_providers.AIProviderService.generate_structured")
def test_generate_and_edit_notes(mock_gen_struct, mock_gen_text, mock_verify, setup_database):
    token = setup_database["token"]
    project_id = str(setup_database["project"].id)
    topic_id = str(setup_database["topic"].id)

    # Mock query expansion planner
    from app.services.rag_engine import ResearchPlan
    mock_plan = {
        "topic": "DBMS Architecture",
        "expected_concepts": ["three schema architecture"],
        "expanded_queries": ["three schema architecture DBMS"],
        "key_terms": ["architecture"]
    }
    mock_gen_struct.return_value = ResearchPlan.model_validate(mock_plan)

    # Mock verifier to bypass inner LLM verification checks in notes test
    mock_gen_text.return_value = (
        "The three schema architecture comprises external, conceptual, and internal levels [Ref_1]. "
        "It supports data independence."
    )
    mock_verify.return_value = (100.0, mock_gen_text.return_value)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"/api/v1/notes/{project_id}/topic/{topic_id}/generate?mode=detailed",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["topic_id"] == topic_id
    assert "three schema architecture" in data["canonical_content"]
    assert data["active_version"]["version_number"] == 1
    
    # Check that citation was parsed and mapped in response
    assert len(data["active_version"]["citations"]) == 1
    assert data["active_version"]["citations"][0]["citation_label"] == "Ref_1"
    assert data["active_version"]["citations"][0]["pdf_page_start"] == 45

    # Test retrieval endpoint
    get_response = client.get(
        f"/api/v1/notes/{project_id}/topic/{topic_id}?mode=detailed",
        headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["canonical_content"] == data["canonical_content"]

    # Test editing endpoint (triggers version count increase)
    edit_payload = {"content": "User modified notes: Three schema architecture is essential."}
    edit_response = client.put(
        f"/api/v1/notes/{project_id}/topic/{topic_id}?mode=detailed",
        json=edit_payload,
        headers=headers
    )

    assert edit_response.status_code == 200
    edit_data = edit_response.json()
    assert edit_data["active_version"]["version_number"] == 2
    assert edit_data["active_version"]["created_by_type"] == "user"
    assert edit_data["canonical_content"] == edit_payload["content"]

    # Test exporting to PDF
    pdf_response = client.get(
        f"/api/v1/notes/{project_id}/export/pdf",
        headers=headers
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"

    # Test exporting to DOCX
    docx_response = client.get(
        f"/api/v1/notes/{project_id}/export/docx",
        headers=headers
    )
    assert docx_response.status_code == 200
    assert "wordprocessingml" in docx_response.headers["content-type"]
