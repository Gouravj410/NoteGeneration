import os
import shutil
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.syllabus import SyllabusVersion, SyllabusModule, SyllabusTopic
from app.schemas.syllabus import SyllabusExtractResponse, SyllabusVersionResponse, ModuleResponse, TopicResponse, SubtopicResponse
from app.services.pdf_processor import PDFProcessorService
from app.services.ai_providers import ai_provider

router = APIRouter()

@router.post("/{project_id}/upload", response_model=SyllabusExtractResponse)
async def upload_syllabus(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify project ownership
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate file extension
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF syllabus files are supported currently."
        )

    # Save to temp file
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"syllabus_{project_id}.pdf")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract pages
        pages = PDFProcessorService.extract_pages(temp_path)
        full_text = "\n".join([page["text"] for page in pages])

        if len(full_text.strip()) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract enough text from the PDF. Ensure it is not corrupted."
            )

        # Extract structured syllabus JSON using LLM
        system_instruction = (
            "You are an expert academic parser. Analyze the syllabus text and extract the course "
            "details, modules, units, topics, and subtopics. Follow the strict JSON schema requested."
        )
        prompt = (
            f"Analyze this syllabus text and structure it into modules, topics, and subtopics.\n"
            f"Subject Name context: {project.subject}\n\n"
            f"Syllabus Text:\n{full_text[:20000]}" # Truncate if extreme, syllabi are usually short
        )

        extracted_syllabus = ai_provider.generate_structured(
            prompt=prompt,
            response_model=SyllabusExtractResponse,
            system_instruction=system_instruction
        )

        return extracted_syllabus

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.put("/{project_id}/confirm", response_model=SyllabusVersionResponse)
def confirm_syllabus(
    project_id: UUID,
    syllabus_data: SyllabusExtractResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Set all previous syllabus versions for this project to inactive
    db.query(SyllabusVersion).filter(
        SyllabusVersion.project_id == project_id
    ).update({SyllabusVersion.is_active: False})

    # Save new SyllabusVersion
    db_version = SyllabusVersion(
        project_id=project_id,
        raw_json=syllabus_data.model_dump(),
        is_active=True
    )
    db.add(db_version)
    db.flush()  # Populates db_version.id

    # Create module and topic records
    for m_idx, mod in enumerate(syllabus_data.modules):
        db_module = SyllabusModule(
            syllabus_version_id=db_version.id,
            module_number=mod.module_number,
            title=mod.title,
            description=mod.description,
            position=m_idx
        )
        db.add(db_module)
        db.flush()

        for t_idx, top in enumerate(mod.topics):
            db_topic = SyllabusTopic(
                module_id=db_module.id,
                name=top.name,
                position=t_idx,
                depth=1,
                status="not_started"
            )
            db.add(db_topic)
            db.flush()

            for s_idx, subtop in enumerate(top.subtopics):
                db_subtopic = SyllabusTopic(
                    module_id=db_module.id,
                    parent_topic_id=db_topic.id,
                    name=subtop,
                    position=s_idx,
                    depth=2,
                    status="not_started"
                )
                db.add(db_subtopic)

    db.commit()
    db.refresh(db_version)
    
    modules_data = []
    for mod in db_version.modules:
        topics_data = []
        # Filter root topics
        root_topics = [t for t in mod.topics if t.parent_topic_id is None]
        for top in root_topics:
            subtopics_data = [
                SubtopicResponse.model_validate(sub) 
                for sub in mod.topics 
                if sub.parent_topic_id == top.id
            ]
            topics_data.append(
                TopicResponse(
                    id=top.id,
                    module_id=top.module_id,
                    parent_topic_id=top.parent_topic_id,
                    name=top.name,
                    description=top.description,
                    position=top.position,
                    depth=top.depth,
                    status=top.status,
                    subtopics=subtopics_data
                )
            )
        modules_data.append(
            ModuleResponse(
                id=mod.id,
                module_number=mod.module_number,
                title=mod.title,
                description=mod.description,
                position=mod.position,
                topics=topics_data
            )
        )

    return SyllabusVersionResponse(
        id=db_version.id,
        project_id=db_version.project_id,
        raw_json=db_version.raw_json,
        is_active=db_version.is_active,
        created_at=db_version.created_at,
        modules=modules_data
    )

@router.get("/{project_id}/active", response_model=SyllabusVersionResponse)
def get_active_syllabus(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    db_version = db.query(SyllabusVersion).filter(
        SyllabusVersion.project_id == project_id,
        SyllabusVersion.is_active == True
    ).first()

    if not db_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No confirmed syllabus outline found for this project."
        )

    modules_data = []
    for mod in db_version.modules:
        topics_data = []
        root_topics = [t for t in mod.topics if t.parent_topic_id is None]
        for top in root_topics:
            subtopics_data = [
                SubtopicResponse.model_validate(sub) 
                for sub in mod.topics 
                if sub.parent_topic_id == top.id
            ]
            topics_data.append(
                TopicResponse(
                    id=top.id,
                    module_id=top.module_id,
                    parent_topic_id=top.parent_topic_id,
                    name=top.name,
                    description=top.description,
                    position=top.position,
                    depth=top.depth,
                    status=top.status,
                    subtopics=subtopics_data
                )
            )
        modules_data.append(
            ModuleResponse(
                id=mod.id,
                module_number=mod.module_number,
                title=mod.title,
                description=mod.description,
                position=mod.position,
                topics=topics_data
            )
        )

    return SyllabusVersionResponse(
        id=db_version.id,
        project_id=db_version.project_id,
        raw_json=db_version.raw_json,
        is_active=db_version.is_active,
        created_at=db_version.created_at,
        modules=modules_data
    )
