import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from app.config import settings
from app.db.base import Base

# Database engine
database_url = settings.DATABASE_URL

# For SQLite, ensure directory exists
if "sqlite" in database_url:
    # Ensure foreign keys are enabled if needed
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_async_engine(
    database_url,
    echo=False,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db():
    """Create all tables in the database and auto-migrate newly added columns."""
    async with engine.begin() as conn:
        # Import models so they are registered on Base.metadata
        import app.db.models
        await conn.run_sync(Base.metadata.create_all)

        # Auto-migrate newly added columns for SQLite local development
        if "sqlite" in settings.DATABASE_URL:
            from sqlalchemy import text
            def _migrate_columns(connection):
                # 1. users table
                res = connection.execute(text("PRAGMA table_info(users)"))
                existing_user_cols = {row[1] for row in res.fetchall()}
                new_cols = [
                    ("phone", "VARCHAR(32)"),
                    ("codeforces_handle", "VARCHAR(128)"),
                    ("target_role", "VARCHAR(128) DEFAULT 'Full Stack Software Engineer'"),
                    ("target_company", "VARCHAR(128) DEFAULT 'Google'"),
                    ("target_location", "VARCHAR(128) DEFAULT 'India'"),
                    ("experience_level", "VARCHAR(64) DEFAULT 'Mid'"),
                    ("metadata_info", "JSON")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_user_cols:
                        connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))

                # 2. interviews table
                res_intv = connection.execute(text("PRAGMA table_info(interviews)"))
                existing_intv_cols = {row[1] for row in res_intv.fetchall()}
                if "architecture_diagram" not in existing_intv_cols:
                    connection.execute(text("ALTER TABLE interviews ADD COLUMN architecture_diagram JSON"))
                if "interviewer_persona" not in existing_intv_cols:
                    connection.execute(text("ALTER TABLE interviews ADD COLUMN interviewer_persona JSON"))
                if "resume_id" not in existing_intv_cols:
                    connection.execute(text("ALTER TABLE interviews ADD COLUMN resume_id VARCHAR(64)"))
                if "resume_data" not in existing_intv_cols:
                    connection.execute(text("ALTER TABLE interviews ADD COLUMN resume_data JSON"))
                if "candidate_name" not in existing_intv_cols:
                    connection.execute(text("ALTER TABLE interviews ADD COLUMN candidate_name VARCHAR(128)"))

                # 3. feedback_reports table
                res_fb = connection.execute(text("PRAGMA table_info(feedback_reports)"))
                existing_fb_cols = {row[1] for row in res_fb.fetchall()}
                if "architecture_report" not in existing_fb_cols:
                    connection.execute(text("ALTER TABLE feedback_reports ADD COLUMN architecture_report JSON"))

            await conn.run_sync(_migrate_columns)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
