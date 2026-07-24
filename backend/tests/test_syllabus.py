import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.core import security

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test user
    hashed_pwd = security.get_password_hash("testpassword")
    user = User(email="syllabus_test@example.com", hashed_password=hashed_pwd, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test project
    project = Project(user_id=user.id, name="DBMS Study", subject="Database Management Systems")
    db.add(project)
    db.commit()
    db.refresh(project)
    
    token = security.create_access_token(user.email)
    
    yield {"db": db, "user": user, "project": project, "token": token}
    
    # Cleanup
    db.delete(project)
    db.delete(user)
    db.commit()
    db.close()

@patch("app.services.pdf_processor.PDFProcessorService.extract_pages")
@patch("app.services.ai_providers.AIProviderService.generate_structured")
def test_upload_and_confirm_syllabus(mock_gen_struct, mock_extract, setup_database):
    token = setup_database["token"]
    project_id = str(setup_database["project"].id)
    
    # Mock PDF extraction
    mock_extract.return_value = [{
        "page_index": 0,
        "text": "DBMS Syllabus. This is a very long text to simulate a realistic course syllabus extraction output. Introduction to DBMS, Relational Database Models, Three Schema Architecture, Data Independence, ER Diagrams mapping constraints.",
        "printed_page": "1"
    }]
    
    # Mock AI response
    mock_syllabus_data = {
        "subject": "Database Management Systems",
        "modules": [
            {
                "module_number": 1,
                "title": "Introduction to DBMS",
                "description": "Relational architecture overview",
                "topics": [
                    {
                        "name": "DBMS Architecture",
                        "subtopics": ["Three Schema Architecture", "Data Independence"]
                      }
                ]
            }
        ]
    }
    
    # We mock the validation return value by returning a Pydantic construct equivalent
    from app.schemas.syllabus import SyllabusExtractResponse
    mock_gen_struct.return_value = SyllabusExtractResponse.model_validate(mock_syllabus_data)
    
    # Mock a blank PDF byte content
    pdf_content = b"%PDF-1.4 mock pdf data"
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"/api/v1/projects/syllabus/{project_id}/upload",
        files={"file": ("syllabus.pdf", pdf_content, "application/pdf")},
        headers=headers
    )
    
    assert response.status_code == 200
    assert response.json()["subject"] == "Database Management Systems"
    assert len(response.json()["modules"]) == 1
    
    # Test confirmation endpoint
    confirm_payload = response.json()
    confirm_response = client.put(
        f"/api/v1/projects/syllabus/{project_id}/confirm",
        json=confirm_payload,
        headers=headers
    )
    
    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["is_active"] is True
    assert len(confirm_data["modules"]) == 1
    assert confirm_data["modules"][0]["title"] == "Introduction to DBMS"
    assert len(confirm_data["modules"][0]["topics"]) == 1
    assert confirm_data["modules"][0]["topics"][0]["name"] == "DBMS Architecture"
    assert len(confirm_data["modules"][0]["topics"][0]["subtopics"]) == 2
    assert confirm_data["modules"][0]["topics"][0]["subtopics"][0]["name"] == "Three Schema Architecture"
