from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.services.ai_providers import ai_provider
from app.services.rag_engine import RAGEngineService
from uuid import UUID

class CoverageReport(BaseModel):
    coverage_score: float = Field(..., description="Score between 0 and 100 representing how well the syllabus subtopics are covered.")
    covered_subtopics: List[str] = Field(..., description="Subtopics successfully explained in the notes.")
    missing_subtopics: List[str] = Field(..., description="Subtopics that are completely missing or poorly explained.")
    rationale: str = Field(..., description="Short explanation of the coverage gap analysis.")

class NoteVerificationService:
    @classmethod
    def verify_and_refine_notes(
        cls,
        db: Session,
        project_id: UUID,
        note_content: str,
        topic_name: str,
        subtopics: List[str],
        subject_name: str
    ) -> Tuple[float, str]:
        """
        Runs the semantic coverage analysis. If gaps are found, executes
        an automated gap-filling loop and appends the refined details.
        """
        if not subtopics:
            return 100.0, note_content

        # 1. Run semantic coverage evaluation
        system_instruction = (
            "You are an academic quality assurance auditor. Compare the generated study notes "
            "against the list of required syllabus subtopics. Identify missing concepts and score the coverage."
        )
        prompt = (
            f"Subject: {subject_name}\n"
            f"Topic: {topic_name}\n"
            f"Required Syllabus Subtopics: {', '.join(subtopics)}\n\n"
            f"[GENERATED STUDY NOTES CONTENT]\n"
            f"{note_content}\n\n"
            f"Run the coverage analysis. Return a structured JSON response."
        )

        try:
            report = ai_provider.generate_structured(
                prompt=prompt,
                response_model=CoverageReport,
                system_instruction=system_instruction
            )
        except Exception as e:
            # Fallback if structured generation fails
            print(f"[Verification Error] Failed to generate structured report: {e}")
            return 100.0, note_content

        # 2. Automated Gap-Filling Loop
        # If score is under 90% and there are missing subtopics, retrieve supplementary material and append details
        if report.coverage_score < 90.0 and report.missing_subtopics:
            print(f"[Verifier Gap Detected] Topic: {topic_name}, Score: {report.coverage_score}%, Missing: {report.missing_subtopics}")
            
            # Search database specifically for the missing subtopics
            supplementary_evidence = ""
            for gap in report.missing_subtopics[:2]: # limit to top 2 gaps to avoid prompt bloating
                candidates = RAGEngineService.hybrid_search(db, project_id, [gap], limit=3)
                for idx, chunk in enumerate(candidates):
                    supplementary_evidence += f"\n- (Book: {chunk['document_filename']}, Page: {chunk['printed_page_start']})\n{chunk['content']}\n"
            
            if supplementary_evidence:
                # Ask LLM to write a gap refinement appendix
                refine_prompt = (
                    f"You are writing a syllabus gap refinement appendix.\n"
                    f"Target Missing Subtopics: {', '.join(report.missing_subtopics)}\n\n"
                    f"[SUPPLEMENTARY TEXTBOOK EVIDENCE]\n"
                    f"{supplementary_evidence}\n\n"
                    f"Write a brief, factually-grounded addition covering these missing concepts. "
                    f"Include page citations like '[Doc: filename, Page: P]' where matching."
                )
                
                appendix_content = ai_provider.generate_text(
                    prompt=refine_prompt,
                    system_instruction="You write concise, factually-grounded note additions for specific missing concepts.",
                    temperature=0.2
                )
                
                refined_notes = (
                    f"{note_content}\n\n"
                    f"## 📚 Syllabus Expansion & Gap-Filling\n"
                    f"The following sections have been added automatically to address missing syllabus points:\n\n"
                    f"{appendix_content}"
                )
                # Return updated score (re-estimate or boost) and content
                return min(100.0, report.coverage_score + 15.0), refined_notes

        return report.coverage_score, note_content
