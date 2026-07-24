import os
from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.services.ai_providers import ai_provider
from app.models.document import DocumentChunk, Document

# Pydantic schema constraints for structured outputs
class ResearchPlan(BaseModel):
    topic: str = Field(..., description="Topic name")
    expected_concepts: List[str] = Field(..., description="Key concepts, definitions, and theories to cover")
    expanded_queries: List[str] = Field(..., description="List of search query variations for vector and keyword search")
    key_terms: List[str] = Field(..., description="Academic keywords, formula names, or code syntax items to look for")

class RAGEngineService:
    @staticmethod
    def create_research_plan(
        topic_name: str,
        module_title: str,
        subject_name: str,
        subtopics: List[str]
    ) -> ResearchPlan:
        """
        Creates a structured academic research plan for a topic before searching.
        """
        system_instruction = (
            "You are an academic researcher. Analyze the target syllabus topic and draft a research plan "
            "outlining what concepts must be retrieved and studied to produce complete study notes."
        )
        prompt = (
            f"Subject: {subject_name}\n"
            f"Module: {module_title}\n"
            f"Topic: {topic_name}\n"
            f"Syllabus Subtopics/Keywords: {', '.join(subtopics) if subtopics else 'None specified'}\n\n"
            f"Generate a structured research plan including search query variations and expected concepts."
        )

        plan = ai_provider.generate_structured(
            prompt=prompt,
            response_model=ResearchPlan,
            system_instruction=system_instruction
        )
        return plan

    @staticmethod
    def hybrid_search(
        db: Session,
        project_id: UUID,
        queries: List[str],
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search (Vector + Full-Text Search) across all queries,
        merging candidates using Reciprocal Rank Fusion (RRF).
        """
        # Store RRF scores and chunk objects
        rrf_scores = {}
        chunks_cache = {}
        
        # Constant for RRF smoothing
        K = 60

        for query_text in queries:
            if db.bind.dialect.name == "sqlite":
                # Fallback keyword ranking search for SQLite tests
                terms = query_text.lower().split()
                all_chunks = db.query(DocumentChunk).filter(DocumentChunk.project_id == project_id).all()
                matched = []
                for chunk in all_chunks:
                    score = sum(1 for term in terms if term in chunk.content.lower())
                    matched.append((chunk.id, score))
                
                # Sort by score descending and apply RRF ranks
                matched.sort(key=lambda x: x[1], reverse=True)
                for rank, (chunk_id, score) in enumerate(matched[:limit]):
                    rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (K + rank + 1))
            else:
                # Generate embedding for Postgres Vector search
                query_vector = ai_provider.generate_embedding(query_text)
                
                # --- 1. Vector Search ---
                vector_sql = text("""
                    SELECT id, 1 - (embedding <=> :vector) AS similarity
                    FROM document_chunks
                    WHERE project_id = :project_id
                    ORDER BY embedding <=> :vector
                    LIMIT :limit
                """)
                
                vector_results = db.execute(vector_sql, {
                    "vector": str(query_vector),
                    "project_id": project_id,
                    "limit": limit
                }).fetchall()
                
                for rank, row in enumerate(vector_results):
                    chunk_id = row[0]
                    rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (K + rank + 1))

                # --- 2. Full-Text Search ---
                fts_sql = text("""
                    SELECT id, ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', :query)) AS rank
                    FROM document_chunks
                    WHERE project_id = :project_id AND to_tsvector('english', content) @@ plainto_tsquery('english', :query)
                    ORDER BY rank DESC
                    LIMIT :limit
                """)
                
                fts_results = db.execute(fts_sql, {
                    "query": query_text,
                    "project_id": project_id,
                    "limit": limit
                }).fetchall()

                for rank, row in enumerate(fts_results):
                    chunk_id = row[0]
                    rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (K + rank + 1))



        # Retrieve top unique chunks sorted by RRF score
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:limit]
        
        if not sorted_chunk_ids:
            return []

        # Bulk fetch document chunk objects matching IDs
        db_chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(sorted_chunk_ids)).all()
        chunks_map = {c.id: c for c in db_chunks}

        # Resolve document filenames for citation labels
        doc_ids = list(set([c.document_id for c in db_chunks]))
        documents = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {d.id: d for d in documents}

        fused_results = []
        for cid in sorted_chunk_ids:
            chunk = chunks_map.get(cid)
            if not chunk:
                continue
            doc = doc_map.get(chunk.document_id)
            fused_results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_filename": doc.filename if doc else "Reference Book",
                "content": chunk.content,
                "token_count": chunk.token_count,
                "pdf_page_start": chunk.pdf_page_start,
                "pdf_page_end": chunk.pdf_page_end,
                "printed_page_start": chunk.printed_page_start,
                "printed_page_end": chunk.printed_page_end,
                "chapter": chunk.chapter,
                "section": chunk.section,
                "subsection": chunk.subsection,
                "content_type": chunk.content_type,
                "rrf_score": rrf_scores[cid]
            })

        return fused_results

    @staticmethod
    def rerank_candidates(
        query: str,
        candidates: List[Dict[str, Any]],
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidates using Cohere Rerank if configured.
        Otherwise falls back to RRF ordering.
        """
        if not candidates:
            return []

        cohere_key = settings.COHERE_API_KEY
        if cohere_key and cohere_key != "your-cohere-api-key-here":
            try:
                import cohere
                co = cohere.Client(cohere_key)
                
                # Format candidates for Cohere
                texts = [c["content"] for c in candidates]
                response = co.rerank(
                    model="rerank-english-v3.0",
                    query=query,
                    documents=texts,
                    top_n=limit
                )

                reranked = []
                for result in response.results:
                    idx = result.index
                    candidate = candidates[idx]
                    candidate["rerank_score"] = result.relevance_score
                    reranked.append(candidate)
                return reranked
            except Exception as e:
                print(f"[Rerank Warning] Cohere reranking failed, falling back to RRF: {e}")

        # Fallback: return top K candidates by RRF score
        return candidates[:limit]

    @classmethod
    def get_evidence_package(
        cls,
        db: Session,
        project_id: UUID,
        topic_name: str,
        module_title: str,
        subject_name: str,
        subtopics: List[str]
    ) -> Dict[str, Any]:
        """
        Main pipeline method: plans, searches, reranks, and builds the Evidence Package.
        """
        # 1. Draft research plan & expand queries
        plan = cls.create_research_plan(topic_name, module_title, subject_name, subtopics)
        
        # 2. Hybrid search & fusion
        search_queries = [topic_name] + plan.expanded_queries[:3]  # use top query variants
        candidates = cls.hybrid_search(db, project_id, search_queries)
        
        # 3. Rerank
        evidence_chunks = cls.rerank_candidates(topic_name, candidates)

        return {
            "topic": topic_name,
            "research_plan": plan.model_dump(),
            "evidence": evidence_chunks
        }
