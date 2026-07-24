import os
from typing import Type, TypeVar, Any
from pydantic import BaseModel
from openai import OpenAI
import google.generativeai as genai
from app.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

T = TypeVar("T", bound=BaseModel)

class AIProviderService:
    def __init__(self):
        self.openai_client = None
        self.gemini_configured = False
        
        # Initialize OpenAI if key is present
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key-here":
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
        # Initialize Gemini if key is present
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_configured = True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.1
    ) -> T:
        """
        Calls the LLM provider to obtain a Pydantic model response.
        Falls back to local mock data ONLY if keys are not configured.
        """
        active_provider = provider or settings.DEFAULT_LLM_PROVIDER
        
        # Fallback if keys are placeholders
        if active_provider == "openai" and not self.openai_client:
            if self.gemini_configured:
                active_provider = "gemini"
            else:
                return self._generate_mock_structured(prompt, response_model)
                
        if active_provider == "gemini" and not self.gemini_configured:
            if self.openai_client:
                active_provider = "openai"
            else:
                return self._generate_mock_structured(prompt, response_model)

        if active_provider == "openai":
            active_model = model or settings.DEFAULT_STRONG_MODEL
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            # Use beta client's schema-constrained parsing if available
            response = self.openai_client.beta.chat.completions.parse(
                model=active_model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
            )
            return response.choices[0].message.parsed
            
        elif active_provider == "gemini":
            active_model = model or "gemini-1.5-flash"
            # Map default strong gpt model to gemini-1.5-pro if specified
            if active_model == "gpt-4o" or active_model == "gpt-4o-mini":
                active_model = "gemini-1.5-flash"
                
            model_instance = genai.GenerativeModel(
                model_name=active_model,
                system_instruction=system_instruction
            )
            
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=response_model,
                    temperature=temperature
                )
            )
            return response_model.model_validate_json(response.text)
            
        raise ValueError(f"Unknown AI Provider: {active_provider}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.5
    ) -> str:
        """
        Generate raw text response from provider (e.g. for note generation or tutor answers)
        """
        active_provider = provider or settings.DEFAULT_LLM_PROVIDER
        
        # Fallback if keys are placeholders
        if active_provider == "openai" and not self.openai_client:
            if self.gemini_configured:
                active_provider = "gemini"
            else:
                return self._generate_mock_text(prompt)
                
        if active_provider == "gemini" and not self.gemini_configured:
            if self.openai_client:
                active_provider = "openai"
            else:
                return self._generate_mock_text(prompt)

        if active_provider == "openai":
            active_model = model or settings.DEFAULT_STRONG_MODEL
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.openai_client.chat.completions.create(
                model=active_model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        elif active_provider == "gemini":
            active_model = model or "gemini-1.5-flash"
            if active_model == "gpt-4o" or active_model == "gpt-4o-mini":
                active_model = "gemini-1.5-flash"
                
            model_instance = genai.GenerativeModel(
                model_name=active_model,
                system_instruction=system_instruction
            )
            response = model_instance.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature)
            )
            return response.text
            
        raise ValueError(f"Unknown AI Provider: {active_provider}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_embedding(
        self,
        text: str,
        model: str | None = None
    ) -> list[float]:
        """
        Generate embeddings vector for pgvector storage
        """
        if not self.openai_client:
            # Local mock 1536 float array if offline
            import random
            return [random.uniform(-1, 1) for _ in range(1536)]
            
        active_model = model or settings.DEFAULT_EMBEDDING_MODEL
        response = self.openai_client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=active_model
        )
        return response.data[0].embedding

    def _generate_mock_structured(self, prompt: str, response_model: Type[T]) -> T:
        """
        Fallback mock data generator for syllabus parsing, if no API keys are provided.
        """
        # If user is parsing a syllabus, return a clean structured mockup syllabus
        if "syllabus" in prompt.lower() or "modules" in prompt.lower():
            mock_data = {
                "subject": "Database Management Systems",
                "modules": [
                  {
                    "module_number": 1,
                    "title": "Introduction to DBMS & Relational Model",
                    "description": "Fundamental concepts, schemas, architectures and relational databases",
                    "topics": [
                      {
                        "name": "Three Schema Architecture",
                        "subtopics": ["External Level", "Conceptual Level", "Internal Level", "Data Independence"]
                      },
                      {
                        "name": "ER Modeling",
                        "subtopics": ["Entities", "Attributes", "Relationships", "Mapping constraints"]
                      }
                    ]
                  },
                  {
                    "module_number": 2,
                    "title": "Database Design & Normalization",
                    "description": "Relational algebra and normal forms",
                    "topics": [
                      {
                        "name": "Functional Dependencies",
                        "subtopics": ["Definition", "Axioms / Rules"]
                      },
                      {
                        "name": "Normal Forms",
                        "subtopics": ["First Normal Form", "Second Normal Form", "Third Normal Form", "Boyce-Codd Normal Form (BCNF)"]
                      }
                    ]
                  }
                ]
            }
            return response_model.model_validate(mock_data)
        
        # Simple generic model fallback
        return response_model.model_construct()

    def _generate_mock_text(self, prompt: str) -> str:
        return f"Mock response for prompt: {prompt[:100]}...\n[Configuration required: please configure OPENAI_API_KEY or GEMINI_API_KEY in .env]"

ai_provider = AIProviderService()
