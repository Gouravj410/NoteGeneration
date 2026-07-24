from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api import auth, projects, syllabus, documents, notes, tutor

# Fast creation of tables on startup if migrations aren't run yet
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production to matching client URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(projects.router, prefix=f"{settings.API_V1_STR}/projects", tags=["Projects"])
app.include_router(syllabus.router, prefix=f"{settings.API_V1_STR}/projects/syllabus", tags=["Syllabus"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])
app.include_router(notes.router, prefix=f"{settings.API_V1_STR}/notes", tags=["Notes"])
app.include_router(tutor.router, prefix=f"{settings.API_V1_STR}/projects/tutor", tags=["Tutor"])

@app.get("/")
def read_root():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": "1.0.0"}
