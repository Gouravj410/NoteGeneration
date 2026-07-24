import hashlib
from uuid import UUID
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.document import Document, DocumentPage, DocumentChunk
from app.services.pdf_processor import PDFProcessorService
from app.services.chunker import chunker_service
from app.services.storage import storage_service
from app.services.ai_providers import ai_provider

@celery_app.task(name="tasks.process_document")
def process_document(document_id: str):
    db = SessionLocal()
    
    try:
        # Fetch document
        doc_uuid = UUID(document_id)
        document = db.query(Document).filter(Document.id == doc_uuid).first()
        if not document:
            return f"Document {document_id} not found."

        # 1. Update status: extracting
        document.processing_status = "extracting"
        db.commit()

        # 2. Get local file path
        file_path = storage_service.get_file_path(document.storage_key)
        
        # 3. Extract text pages
        pages = PDFProcessorService.extract_pages(file_path)
        
        # Save page-by-page text representation for direct viewer mapping
        for p in pages:
            db_page = DocumentPage(
                document_id=document.id,
                page_index=p["page_index"],
                printed_page_number=p["printed_page"],
                text_content=p["text"]
            )
            db.add(db_page)
        
        document.page_count = len(pages)
        document.processing_status = "chunking"
        db.commit()

        # 4. Perform semantic chunking
        chunks = chunker_service.chunk_document(pages)

        # 5. Generate embeddings and save chunks
        document.processing_status = "embedding"
        db.commit()

        for chunk_data in chunks:
            content = chunk_data["content"]
            # Deduplicate using SHA256 hashes
            chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            
            # Generate embedding vector
            embedding_vector = ai_provider.generate_embedding(content)

            db_chunk = DocumentChunk(
                document_id=document.id,
                project_id=document.project_id,
                content=content,
                token_count=chunk_data["token_count"],
                chapter=chunk_data["chapter"],
                section=chunk_data["section"],
                subsection=chunk_data["subsection"],
                pdf_page_start=chunk_data["pdf_page_start"],
                pdf_page_end=chunk_data["pdf_page_end"],
                printed_page_start=chunk_data["printed_page_start"],
                printed_page_end=chunk_data["printed_page_end"],
                content_type=chunk_data["content_type"],
                embedding=embedding_vector,
                chunk_hash=chunk_hash
            )
            db.add(db_chunk)

        # 6. Finalize status: indexed
        document.processing_status = "indexed"
        db.commit()
        return f"Successfully processed and indexed document {document.filename}."

    except Exception as e:
        db.rollback()
        # Ensure we mark the document state as failed and record details to prevent UI lockups
        db_fail = SessionLocal()
        document_fail = db_fail.query(Document).filter(Document.id == UUID(document_id)).first()
        if document_fail:
            document_fail.processing_status = "failed"
            document_fail.error_message = str(e)
            db_fail.commit()
        db_fail.close()
        raise e
        
    finally:
        db.close()

@celery_app.task(name="tasks.generate_topic_notes")
def generate_topic_notes(project_id: str, topic_id: str, mode: str = "detailed"):
    # Placeholder for notes generation (to be completed in Phase 5)
    return f"Generated notes for topic {topic_id} in mode {mode}"
