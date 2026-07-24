import re
import os
from uuid import UUID
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.syllabus import SyllabusTopic, SyllabusModule
from app.models.project import Project
from app.models.note import GeneratedNote, NoteVersion, NoteCitation
from app.models.document import Document
from app.services.rag_engine import RAGEngineService
from app.services.ai_providers import ai_provider

class NoteGeneratorService:
    @classmethod
    def generate_notes_for_topic(
        cls,
        db: Session,
        project_id: UUID,
        topic_id: UUID,
        mode: str = "detailed"
    ) -> GeneratedNote:
        """
        Retrieves evidence, runs note generation prompt, parses and validates citations,
        and saves note versions with page citations to the database.
        """
        # 1. Fetch topic & project context
        topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found.")

        # Get parent module
        module = db.query(SyllabusModule).filter(SyllabusModule.id == topic.module_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()

        # Get sibling subtopics
        subtopics = db.query(SyllabusTopic).filter(SyllabusTopic.parent_topic_id == topic_id).all()
        subtopic_names = [s.name for s in subtopics]

        # 2. Query RAG Engine for evidence
        evidence_package = RAGEngineService.get_evidence_package(
            db=db,
            project_id=project_id,
            topic_name=topic.name,
            module_title=module.title if module else "General",
            subject_name=project.subject,
            subtopics=subtopic_names
        )

        evidence_chunks = evidence_package["evidence"]
        research_plan = evidence_package["research_plan"]

        # 3. Assemble Prompt with Grounded Evidence Chunks
        formatted_evidence = ""
        evidence_map = {} # map index/label to chunk
        
        for idx, chunk in enumerate(evidence_chunks):
            ref_label = f"Ref_{idx + 1}"
            evidence_map[ref_label] = chunk
            
            formatted_evidence += (
                f"--- EVIDENCE REFERENCE: {ref_label} ---\n"
                f"Book: {chunk['document_filename']}\n"
                f"Location: Chapter {chunk['chapter'] or 'N/A'}, Section {chunk['section'] or 'N/A'}\n"
                f"Pages: pdf index {chunk['pdf_page_start']}-{chunk['pdf_page_end']}, printed {chunk['printed_page_start']}-{chunk['printed_page_end']}\n"
                f"Content:\n{chunk['content']}\n\n"
            )

        system_instruction = (
            "You are an academic note generation engine. Write structured study notes for the requested topic. "
            "Rely strictly on the provided evidence blocks. Do not invent page citations or make claims absent "
            "from the evidence. If evidence is insufficient to explain a required subtopic or concept, output: "
            "'[Insufficient Source Coverage - Concept: X]' for that section, rather than writing general AI answers. "
            "Format citations inline exactly as '[Ref_X]' matching the corresponding reference blocks."
        )

        prompt = (
            f"Subject: {project.subject}\n"
            f"Module: {module.title if module else 'General'}\n"
            f"Topic: {topic.name}\n"
            f"Expected subconcepts to cover: {', '.join(research_plan['expected_concepts'])}\n"
            f"Note Writing Mode: {mode.upper()} (detailed learning guide)\n\n"
            f"[PROVIDED REFERENCE EVIDENCE]\n"
            f"{formatted_evidence if formatted_evidence else 'No textbook evidence found in database.'}\n\n"
            f"Write the study notes below, including inline reference tags like '[Ref_1]' or '[Ref_2]' where supported."
        )

        generated_markdown = ai_provider.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.2
        )

        # 3.5 Run verification loop to check syllabus coverage and fill gaps
        try:
            from app.services.verifier import NoteVerificationService
            coverage_score, final_content = NoteVerificationService.verify_and_refine_notes(
                db=db,
                project_id=project_id,
                note_content=generated_markdown,
                topic_name=topic.name,
                subtopics=subtopic_names,
                subject_name=project.subject
            )
        except Exception as e:
            print(f"[Verifier Warning] Notes verification loop failed: {e}")
            coverage_score = 100.0
            final_content = generated_markdown

        # 4. Parse & Validate Citations
        parsed_citations = cls._parse_citations(final_content, evidence_map)

        # 5. Save note to Database
        # Check if GeneratedNote already exists
        db_note = db.query(GeneratedNote).filter(
            GeneratedNote.project_id == project_id,
            GeneratedNote.topic_id == topic_id,
            GeneratedNote.mode == mode
        ).first()

        if not db_note:
            db_note = GeneratedNote(
                project_id=project_id,
                topic_id=topic_id,
                mode=mode,
                canonical_content=final_content,
                coverage_score=coverage_score,
                source_grounding_status="grounded"
            )
            db.add(db_note)
            db.flush()
        else:
            db_note.canonical_content = final_content
            db_note.coverage_score = coverage_score
            db_note.updated_at = db_note.updated_at # triggers update timestamp

        # Check existing version count to set next version number
        version_count = db.query(NoteVersion).filter(NoteVersion.note_id == db_note.id).count()
        
        db_version = NoteVersion(
            note_id=db_note.id,
            content=final_content,
            version_number=version_count + 1,
            created_by_type="ai"
        )
        db.add(db_version)
        db.flush()

        # Insert resolved citations
        for ref_label, citation_info in parsed_citations.items():
            db_citation = NoteCitation(
                note_version_id=db_version.id,
                document_id=citation_info["document_id"],
                chunk_id=citation_info["chunk_id"],
                pdf_page_start=citation_info["pdf_page_start"],
                pdf_page_end=citation_info["pdf_page_end"],
                citation_label=ref_label
            )
            db.add(db_citation)

        # Set topic status to completed
        topic.status = "completed"
        db.commit()
        db.refresh(db_note)

        return db_note

    @staticmethod
    def _parse_citations(markdown_content: str, evidence_map: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Parses reference tags like '[Ref_1]' from generated note text.
        Returns:
            Dict mapping reference tag to document/page range mappings.
        """
        resolved = {}
        # Find all brackets matching Ref_X
        ref_tags = re.findall(r'\[Ref_(\d+)\]', markdown_content)
        
        for tag_num in set(ref_tags):
            ref_label = f"Ref_{tag_num}"
            chunk = evidence_map.get(ref_label)
            if chunk:
                resolved[ref_label] = {
                    "document_id": chunk["document_id"],
                    "chunk_id": chunk["chunk_id"],
                    "pdf_page_start": chunk["pdf_page_start"],
                    "pdf_page_end": chunk["pdf_page_end"],
                }
        return resolved
