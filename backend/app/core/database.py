import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

database_url = settings.DATABASE_URL

# Fallback to SQLite if Postgres is not running or has authentication issues
if "postgresql" in database_url:
    import psycopg2
    try:
        # Dry-run connection check to Postgres
        conn = psycopg2.connect(
            database_url.replace("postgresql://", "postgresql://").split("?")[0],
            connect_timeout=1
        )
        conn.close()
    except Exception as e:
        print(f"[Database Warning] PostgreSQL connection check failed: {e}. Falling back to SQLite.")
        database_url = "sqlite:///./test.db"

if "sqlite" in database_url:
    engine = create_engine(
        database_url, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
