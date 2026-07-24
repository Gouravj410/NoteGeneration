from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.services.rag_engine import RAGEngineService
from app.services.ai_providers import ai_provider

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # list of {"role": "user"/"assistant", "content": "..."}

class ChatResponse(BaseModel):
    response: str
    sources: list[dict]

@router.post("/{project_id}/chat", response_model=ChatResponse)
def ask_tutor(
    project_id: UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # 1. Hybrid Search to retrieve grounded sources
    # Use user query + last question details
    search_queries = [payload.message]
    candidates = RAGEngineService.hybrid_search(db, project_id, search_queries, limit=5)
    
    # 2. Format evidence context
    context = ""
    sources = []
    for idx, chunk in enumerate(candidates):
        ref_num = idx + 1
        context += f"[Source {ref_num}] (Book: {chunk['document_filename']}, Pages: {chunk['printed_page_start']}-{chunk['printed_page_end']})\n{chunk['content']}\n\n"
        sources.append({
            "label": f"[{ref_num}]",
            "document_filename": chunk["document_filename"],
            "printed_pages": f"{chunk['printed_page_start']}-{chunk['printed_page_end']}",
            "pdf_pages": f"{chunk['pdf_page_start']}-{chunk['pdf_page_end']}"
        })

    # 3. Build history string
    history_str = ""
    for h in payload.history[-6:]:  # use last 6 messages
        role_label = "Student" if h["role"] == "user" else "Tutor"
        history_str += f"{role_label}: {h['content']}\n"

    # 4. Invoke LLM with System instructions
    system_instruction = (
        "You are StudyForge AI, a helpful, textbook-grounded academic tutor. "
        "Your goal is to answer the student's question clearly. Answer only from the provided textbook sources. "
        "If the textbook sources do not contain the answer, say 'I cannot find that in your uploaded textbooks.' "
        "Cite the sources you use inline as [Source 1], [Source 2] etc."
    )

    prompt = (
        f"[TEXTBOOK REFERENCES]\n{context}\n"
        f"[CONVERSATION HISTORY]\n{history_str}\n"
        f"Student: {payload.message}\n"
        f"Tutor:"
    )

    tutor_reply = ai_provider.generate_text(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=0.3
    )

    return ChatResponse(response=tutor_reply, sources=sources)
