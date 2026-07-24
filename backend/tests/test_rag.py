import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.document import Document, DocumentChunk
from app.core import security
from app.services.rag_engine import RAGEngineService, ResearchPlan

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test user
    hashed_pwd = security.get_password_hash("testpassword")
    user = User(email="rag_test@example.com", hashed_password=hashed_pwd, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test project
    project = Project(user_id=user.id, name="DBMS Study", subject="Database Management Systems")
    db.add(project)
    db.commit()
    db.refresh(project)

    # Create dummy document
    doc = Document(
        project_id=project.id,
        filename="dbms_textbook.pdf",
        file_size=1000,
        storage_key="dbms_textbook.pdf",
        processing_status="indexed",
        sha256_hash="randomhash987"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Insert dummy document chunks with search keywords
    chunk1 = DocumentChunk(
        document_id=doc.id,
        project_id=project.id,
        content="Boyce-Codd Normal Form (BCNF) is a stronger version of Third Normal Form (3NF). A relation is in BCNF if for every functional dependency X -> Y, X is a superkey.",
        token_count=35,
        pdf_page_start=180,
        pdf_page_end=180,
        printed_page_start="175",
        printed_page_end="175",
        content_type="prose",
        chunk_hash="hashchunk1"
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        project_id=project.id,
        content="Functional Dependency (FD) describes the relationship between attributes in a database relation. If attribute A uniquely determines attribute B, it is denoted A -> B.",
        token_count=30,
        pdf_page_start=160,
        pdf_page_end=160,
        printed_page_start="155",
        printed_page_end="155",
        content_type="definition",
        chunk_hash="hashchunk2"
    )
    db.add(chunk1)
    db.add(chunk2)
    db.commit()
    
    yield {"db": db, "user": user, "project": project, "doc": doc, "chunk1": chunk1, "chunk2": chunk2}
    
    # Cleanup
    db.delete(chunk1)
    db.delete(chunk2)
    db.delete(doc)
    db.delete(project)
    db.delete(user)
    db.commit()
    db.close()

@patch("app.services.ai_providers.AIProviderService.generate_structured")
def test_create_research_plan(mock_gen_struct, setup_database):
    mock_plan = {
        "topic": "BCNF Normalization",
        "expected_concepts": ["BCNF Definition", "functional dependencies", "superkey constraints"],
        "expanded_queries": ["Boyce-Codd Normal Form", "BCNF conditions", "superkeys functional dependency"],
        "key_terms": ["BCNF", "3NF", "superkey"]
    }
    mock_gen_struct.return_value = ResearchPlan.model_validate(mock_plan)

    plan = RAGEngineService.create_research_plan(
        topic_name="BCNF Normalization",
        module_title="Database Design",
        subject_name="DBMS",
        subtopics=["Definition", "Examples"]
    )

    assert plan.topic == "BCNF Normalization"
    assert "BCNF Definition" in plan.expected_concepts
    assert len(plan.expanded_queries) == 3

def test_hybrid_search_sqlite(setup_database):
    db = setup_database["db"]
    project_id = setup_database["project"].id

    # Search for "Boyce-Codd Normal Form BCNF"
    results = RAGEngineService.hybrid_search(
        db=db,
        project_id=project_id,
        queries=["Boyce-Codd Normal Form BCNF"]
    )

    assert len(results) > 0
    # First result should match Boyce-Codd chunk because of keyword frequency scoring in SQLite fallback
    assert "Boyce-Codd" in results[0]["content"]
    assert results[0]["printed_page_start"] == "175"

@patch("app.services.ai_providers.AIProviderService.generate_structured")
def test_get_evidence_package(mock_gen_struct, setup_database):
    db = setup_database["db"]
    project_id = setup_database["project"].id

    mock_plan = {
        "topic": "Functional Dependency",
        "expected_concepts": ["FD definition", "trivial functional dependencies"],
        "expanded_queries": ["Functional Dependency", "FD database normalization"],
        "key_terms": ["FD", "A -> B"]
    }
    mock_gen_struct.return_value = ResearchPlan.model_validate(mock_plan)

    pkg = RAGEngineService.get_evidence_package(
        db=db,
        project_id=project_id,
        topic_name="Functional Dependency",
        module_title="Database Design",
        subject_name="DBMS",
        subtopics=["Definition"]
    )

    assert pkg["topic"] == "Functional Dependency"
    assert len(pkg["evidence"]) > 0
    # The correct functional dependency chunk must be included in the evidence package
    assert any("Functional Dependency" in c["content"] for c in pkg["evidence"])
